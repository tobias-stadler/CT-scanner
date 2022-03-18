#include "photoclient.h"

#include <sys/param.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/semphr.h"

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

#define PHOTOCLIENT_MSGSIZE_RX 33
#define PHOTOCLIENT_MSGSIZE_TX 33

#define PHOTOCLIENT_RXSIZE 256
#define PHOTOCLIENT_TXSIZE 256
#define PHOTOCLIENT_PORT 25588
#define PHOTOCLIENT_ADDR "192.168.1.11"

static const char *TAG = "Network/PhotoClient";

static int sock = -1;

static uint8_t *rx_buf = NULL;
static uint8_t *tx_buf = NULL;

static bool running = false;
static bool retry = false;

static SemaphoreHandle_t xmute = NULL;

static photoclient_jpeg_cb_t jpeg_cb = NULL;
static photoclient_raw_cb_t raw_cb = NULL;

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

// Send message containing opcode and token
static void send_cmd_token(uint8_t op, uint32_t token) {
    if(tx_buf == NULL) {
        ESP_LOGE(TAG, "Send failed: TX buffer is nullptr");
        return;
    }
    xSemaphoreTake(xmute, portMAX_DELAY);
    memset(tx_buf, 0x00, PHOTOCLIENT_MSGSIZE_TX);

    tx_buf[0] = op;

    uint32_t nval = htonl(token);
    memcpy(tx_buf+1, &nval, sizeof(uint32_t));

    send_all(tx_buf, PHOTOCLIENT_MSGSIZE_TX);
    xSemaphoreGive(xmute);
}

//Extract unsigned integer from buffer
static uint32_t extract_uint32(uint8_t* data, int skip) {
    uint32_t nval = 0;
    memcpy(&nval, data+(sizeof(uint32_t)*skip), sizeof(uint32_t));
    return ntohl(nval);
}

//Parse network messages
//CAUTION: data in network byte order
static void parse_frame(unsigned char op, uint8_t *data) {

    uint32_t iso = extract_uint32(data, 1);
    uint32_t exposure = extract_uint32(data, 2);
    uint32_t focuslen = extract_uint32(data, 3);
    uint32_t token = extract_uint32(data, 0);

    ESP_LOGI(TAG, "Message received: %#08X, %d, %d, %d, %d", op, token, iso, exposure, focuslen);

    switch (op) {
    case (0x1A):
        ESP_LOGI(TAG, "Command: JPEG");
        if(jpeg_cb != NULL) jpeg_cb(iso, exposure, focuslen, token);
        break;
    case (0x1B):
        ESP_LOGI(TAG, "Command: RAW");
        if(raw_cb != NULL) raw_cb(iso, exposure, focuslen, token);
        break;
    }
}

// Entry point for receiving thread
static void tcp_client_task() {
    ESP_LOGI(TAG, "Started");
    while (running) {
        struct sockaddr_in dest_addr;
        dest_addr.sin_addr.s_addr = inet_addr(PHOTOCLIENT_ADDR);
        dest_addr.sin_family = AF_INET;
        dest_addr.sin_port = htons(PHOTOCLIENT_PORT);

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

                if (chunksize_total >= PHOTOCLIENT_RXSIZE) {
                    chunksize_total = 0;
                    ESP_LOGE(TAG, "RX buffer overflowed!");
                }
                int chunksize = recv(sock, rx_buf + chunksize_total,
                        PHOTOCLIENT_RXSIZE - chunksize_total, 0);
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

                if (chunksize_total > PHOTOCLIENT_RXSIZE) {
                    chunksize_total = 0;
                    ESP_LOGE(TAG, "RX buffer overflowed unexpectedly!");
                }

                while (chunksize_total >= PHOTOCLIENT_MSGSIZE_RX) {
                    uint8_t *msg = rx_buf + chunksize_total - PHOTOCLIENT_MSGSIZE_RX;
                    parse_frame(msg[0], msg + 1);

                    //Hexdump
                    //ESP_LOG_BUFFER_HEX_LEVEL(TAG, msg, PHOTOCLIENT_MSGSIZE, ESP_LOG_INFO);
                    chunksize_total -= PHOTOCLIENT_MSGSIZE_RX;
                }
            } else if (ret == 0) {
                // Do nothing
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
void photoclient_start() {
    if (running) {
        ESP_LOGE(TAG, "already running!");
        return;
    }

    running = true;
    xTaskCreate(tcp_client_task, "XrayTCPclient", 4096, NULL, 5, NULL);
    ESP_LOGI(TAG, "Starting...");
}

// Stop receiving thread
void photoclient_stop() {
    if (!running) {
        ESP_LOGE(TAG, "already stopped!");
        return;
    }

    running = false;
}

// Initialize buffers
void photoclient_init() {
    ESP_LOGI(TAG, "Initializing...");
    if (rx_buf == NULL)
        rx_buf = (uint8_t*) calloc(PHOTOCLIENT_RXSIZE, sizeof(uint8_t));
    if (tx_buf == NULL)
        tx_buf = (uint8_t*) calloc(PHOTOCLIENT_TXSIZE, sizeof(uint8_t));
    if (xmute == NULL)
        xmute = xSemaphoreCreateMutex();
    running = false;
    retry = false;
    sock = -1;
}

// Destroy buffers
void photoclient_destroy() {
    if (running) {
        photoclient_stop();
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

// Set callback function pointers

void photoclient_set_jpeg_cb(photoclient_jpeg_cb_t cb)
{
    jpeg_cb = cb;
}

void photoclient_set_raw_cb(photoclient_raw_cb_t cb)
{
    raw_cb = cb;
}

// Send responses without additional image data

void photoclient_send_jpeg_empty(uint32_t token)
{
    send_cmd_token(0xBA, token);
}

void photoclient_send_raw_empty(uint32_t token)
{
    send_cmd_token(0xBB, token);
}
