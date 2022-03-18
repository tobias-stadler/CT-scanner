#include "xrayclient.h"

#include <sys/param.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/semphr.h"
#include "esp_system.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "esp_log.h"
#include "nvs_flash.h"
#include "tcpip_adapter.h"
#include "lwip/err.h"
#include "lwip/sockets.h"
#include "lwip/sys.h"
#include <lwip/netdb.h>
#include "errno.h"
#include "math.h"

#include "defutil.h"

#define XRAYCLIENT_MSGSIZE 33

#define XRAYCLIENT_RXSIZE 256
#define XRAYCLIENT_TXSIZE 256
#define XRAYCLIENT_PORT 25599
#define XRAYCLIENT_ADDR "192.168.1.11"

static const char *TAG = "Network/XrayClient";

static int sock = -1;

static uint8_t *rx_buf = NULL;
static uint8_t *tx_buf = NULL;

static bool running = false;
static bool retry = false;

static SemaphoreHandle_t xmute = NULL;

static xrayclient_newpos_cb_t newpos_cb = NULL;

static float *status_pos = NULL;

// Send whole buffer of bytes
static void send_all(uint8_t* data, size_t len) {
    int bytes_sent = 0;
    if(sock < 0) {
        ESP_LOGE(TAG, "Send failed: Invalid socket");
    }
    while(bytes_sent < len) {
        int sent = send(sock, data, len-bytes_sent, 0);
        if(sent < 0) {
            ESP_LOGE(TAG, "Send failed: errno %d", errno);
            retry = true;
            return;
        }
        bytes_sent += sent;
    }
}


// Send message containing opcode, integer and token
static void send_cmd_i(uint8_t op, int val, uint32_t token) {
    if(tx_buf == NULL) {
        ESP_LOGE(TAG, "Send failed: TX buffer is nullptr");
        return;
    }
    xSemaphoreTake(xmute, portMAX_DELAY);
    memset(tx_buf, 0x00, XRAYCLIENT_MSGSIZE);
    tx_buf[0] = op;

    uint32_t ntoken = htonl(token);
    memcpy(tx_buf+1, &ntoken, sizeof(uint32_t));

    uint32_t nval = htonl(val);
    memcpy(tx_buf+1+sizeof(uint32_t), &nval, sizeof(uint32_t));
    send_all(tx_buf, XRAYCLIENT_MSGSIZE);
    xSemaphoreGive(xmute);
}

// Send message containing opcode, float and token
static void send_cmd_f(uint8_t op, float val, uint32_t token) {
    send_cmd_i(op, round(val*100.0f), token);
}

//CAUTION: data in network byte order
static void parse_frame(unsigned char op, uint8_t *data) {


    uint32_t nval = 0;
    memcpy(&nval, data, sizeof(uint32_t));

    uint32_t nval2 = 0;
    memcpy(&nval2, data+sizeof(uint32_t), sizeof(uint32_t));

    uint32_t val = ntohl(nval);
    uint32_t val2 = ntohl(nval2);
    ESP_LOGI(TAG, "Message received: %#08X, %d, %d", op, val, val2);
    switch (op) {
    case (0x0A):
        ESP_LOGI(TAG, "Command: New Position");
        float fval = (float)val2/100.0f;
        if(newpos_cb != NULL) newpos_cb(fval, val);
        break;
    case (0x0F):
        ESP_LOGI(TAG, "Command: Request current status");
        send_cmd_f(0xAF, *status_pos, 0);
        break;
    }
}

// Entrypoint for receiving thread
static void tcp_client_task() {
    ESP_LOGI(TAG, "Started");
    while (running) {
        struct sockaddr_in dest_addr;
        dest_addr.sin_addr.s_addr = inet_addr(XRAYCLIENT_ADDR);
        dest_addr.sin_family = AF_INET;
        dest_addr.sin_port = htons(XRAYCLIENT_PORT);

        sock = socket(AF_INET, SOCK_STREAM, IPPROTO_IP);

        if (sock < 0) {
            ESP_LOGE(TAG, "Socket creation failed: errno %d", errno);
            goto fail;
        }
        ESP_LOGI(TAG, "Socket created. Connecting...");

        if (connect(sock, (struct sockaddr*) &dest_addr, sizeof(dest_addr))) {
            ESP_LOGE(TAG, "Socket connection failed: errno %d", errno);
            goto fail;
        }

        ESP_LOGI(TAG, "Socket connected. Waiting...");

        struct pollfd polldes;
        polldes.fd = sock;
        polldes.events = POLLIN;

        int chunksize_total = 0;

        while (true) {
            if (retry) {
                retry = false;
                ESP_LOGE(TAG, "Forcing reconnect!");
                goto fail;
            }

            int ret = poll(&polldes, 1, 1000);
            if (ret > 0) {

                if (chunksize_total >= XRAYCLIENT_RXSIZE) {
                    chunksize_total = 0;
                    ESP_LOGE(TAG, "RX buffer overflowed!");
                }
                int chunksize = recv(sock, rx_buf + chunksize_total,
                        XRAYCLIENT_RXSIZE - chunksize_total, 0);
                ESP_LOGI(TAG, "Received %d new bytes", chunksize);

                if (chunksize == 0) {
                    ESP_LOGI(TAG, "Socket reached EOF");
                    goto fail;
                } else if (chunksize < 0) {
                    ESP_LOGE(TAG,
                            "Socket encountered error while recv: errno %d",
                            errno);
                    goto fail;
                }
                chunksize_total += chunksize;

                //This should be unreachable, but in the worst-case it stops a buffer overflow
                if (chunksize_total > XRAYCLIENT_RXSIZE) {
                    chunksize_total = 0;
                    ESP_LOGE(TAG, "RX buffer overflowed unexpectedly!");
                }

                while (chunksize_total >= XRAYCLIENT_MSGSIZE) {
                    uint8_t *msg = rx_buf + chunksize_total - XRAYCLIENT_MSGSIZE;
                    parse_frame(msg[0], msg + 1);

                    //Hexdump
                    //ESP_LOG_BUFFER_HEX_LEVEL(TAG, msg, XRAYCLIENT_MSGSIZE, ESP_LOG_INFO);
                    chunksize_total -= XRAYCLIENT_MSGSIZE;
                }
            } else if (ret == 0) {
                if(status_pos != NULL) {
                    send_cmd_f(0xAF, *status_pos, 0);
                }
            } else {
                ESP_LOGE(TAG, "Poll failed errno %d", errno);
            }
        }

        fail:
        if (sock != -1) {
            shutdown(sock, 0);
            close(sock);
            sock = -1;
        }
        vTaskDelay(1000 / portTICK_PERIOD_MS);
        ESP_LOGI(TAG, "Trying to reconnect...");
    }

    //fail_crit:
    ESP_LOGI(TAG, "Stopped");
    running = false;
    vTaskDelete(NULL);
}

// Start receiving thread
void xrayclient_start() {
    if (running) {
        ESP_LOGE(TAG, "already running!");
        return;
    }

    running = true;
    xTaskCreate(tcp_client_task, "XrayTCPclient", 4096, NULL, 5, NULL);
    ESP_LOGI(TAG, "Starting...");
}

// Stop receiving thread
void xrayclient_stop() {
    if (!running) {
        ESP_LOGE(TAG, "already stopped!");
        return;
    }

    running = false;
}

// Initialize buffers
void xrayclient_init() {
    ESP_LOGI(TAG, "Initializing...");
    if (rx_buf == NULL)
        rx_buf = (uint8_t*) calloc(XRAYCLIENT_RXSIZE, sizeof(uint8_t));
    if (tx_buf == NULL)
        tx_buf = (uint8_t*) calloc(XRAYCLIENT_TXSIZE, sizeof(uint8_t));
    if (xmute == NULL)
        xmute = xSemaphoreCreateMutex();
    running = false;
    retry = false;
    sock = -1;
}

// Destroy buffers
void xrayclient_destroy() {
    if (running) {
        xrayclient_stop();
    }

    if (rx_buf != NULL)
        free(rx_buf);
    if (tx_buf != NULL)
        free(tx_buf);

    if (xmute != NULL)
        vSemaphoreDelete(xmute);

    rx_buf = NULL;
    tx_buf = NULL;
    xmute = NULL;
}

// Set callback function pointer
void xrayclient_set_newpos_cb(xrayclient_newpos_cb_t cb)
{
    newpos_cb = cb;
}


// Set pointer to variable that contains the current stepper angle
void xrayclient_set_status_pos(float* pos)
{
    status_pos = pos;
}

// Send command
void xrayclient_send_cmd_done(float pos, uint32_t token)
{
    send_cmd_f(0xAA, pos, token);
}
