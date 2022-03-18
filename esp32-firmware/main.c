
#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/event_groups.h"
#include "freertos/queue.h"
#include "driver/gpio.h"
#include "sdkconfig.h"
#include "wifi.h"
#include "esp_event.h"
#include "esp_system.h"
#include "string.h"
#include "esp_log.h"
#include "nvs_flash.h"
#include "xrayclient.h"
#include "photoclient.h"
#include "esp_netif.h"
#include "stepper.h"

static const char* TAG = "MAIN";

static xQueueHandle stepper_queue;
static xQueueHandle token_queue;
static float last_angle = 0.0f;
static uint32_t last_token = 0;
//static uint32_t last_exposure = 0;

static const uint8_t gpio_relais_shutter = GPIO_NUM_18;
static const uint8_t gpio_relais_focus = GPIO_NUM_19;

stepper_t stepper;


// Callback for new position command
void recv_newpos(float pos, uint32_t token)
{
    last_angle = pos;
    last_token = token;
    xQueueSend(stepper_queue, &last_angle, portMAX_DELAY);
    xQueueSend(token_queue, &last_token, portMAX_DELAY);
}


//Callback for jpeg capture command (only implemented on Android)
void recv_cmd_jpeg(uint32_t iso, uint32_t exposure, uint32_t focuslen, uint32_t token)
{
    //last_exposure = exposure;
    photoclient_send_jpeg_empty(token);
}

// Callback for raw capture command
void recv_cmd_raw(uint32_t iso, uint32_t exposure, uint32_t focuslen, uint32_t token)
{
    //last_exposure = exposure; xQueueSend()

    ESP_LOGI(TAG, "New Raw Exposure: %d (iso: %d, focuslen: %d)", exposure, iso, focuslen);

    //gpio_set_level(gpio_relais_shutter, 1);
    //gpio_set_level(gpio_relais_focus, 1);
    //vTaskDelay(100/portTICK_PERIOD_MS);

    if(exposure == 0) {
        ESP_LOGE(TAG, "Exposure = 0");
        return;
    }

    if(iso == 0){
        iso = 500;
    }

    if(focuslen != 0){
        gpio_set_level(gpio_relais_focus, 0);
        vTaskDelay(focuslen/portTICK_PERIOD_MS);
    }
    gpio_set_level(gpio_relais_shutter, 0);
    vTaskDelay(iso/portTICK_PERIOD_MS);
    gpio_set_level(gpio_relais_focus, 1);
    gpio_set_level(gpio_relais_shutter, 1);
    vTaskDelay(exposure/portTICK_PERIOD_MS);
    photoclient_send_raw_empty(token);
    ESP_LOGI(TAG, "Sent Raw Exposure");

}


//Setup non-volatile-storage (needed for wifi)
void configure_nvs(void)
{
    esp_err_t ret = nvs_flash_init();
    if(ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        ret = nvs_flash_init();
    }
    ESP_ERROR_CHECK(ret);
}

//Setup outputs for relays
void configure_relais(void) {
    gpio_pad_select_gpio(gpio_relais_focus);
    gpio_set_direction(gpio_relais_focus, GPIO_MODE_OUTPUT);
    gpio_set_level(gpio_relais_focus, 1);

    gpio_pad_select_gpio(gpio_relais_shutter);
    gpio_set_direction(gpio_relais_shutter, GPIO_MODE_OUTPUT);
    gpio_set_level(gpio_relais_shutter, 1);
}

//Setup network
void configure_network(void)
{

    network_wifi_init();
    network_wifi_ap_init();
    network_wifi_start();
}

//Entry point for stepper thread
static void stepper_task() {

    while(true) {
        float newpos = 0.0f;
        uint32_t newtoken = 0;
        xQueueReceive(stepper_queue, &newpos, portMAX_DELAY);
        xQueueReceive(token_queue, &newtoken, portMAX_DELAY);
        ESP_LOGI(TAG, "New position: %f", newpos);
        stepper.ctr_angle = newpos;
        stepper_move_angle();
        xrayclient_send_cmd_done(stepper.ctr_angle, newtoken);
        ESP_LOGI(TAG, "Positioning done: %f", newpos);
    }

    vTaskDelete(NULL);
}


// Main entry point
void app_main(void)
{
    configure_nvs();
    configure_network();
    configure_relais();

    xrayclient_init();
    xrayclient_set_newpos_cb(recv_newpos);
    xrayclient_start();

    photoclient_init();
    photoclient_set_jpeg_cb(recv_cmd_jpeg);
    photoclient_set_raw_cb(recv_cmd_raw);
    photoclient_start();

    stepper_queue = xQueueCreate(5, sizeof(float));
    token_queue = xQueueCreate(5, sizeof(uint32_t));

    stepper.cfg_dir_pin = 33;
    stepper.cfg_step_pin = 25;
    stepper.cfg_MS1_pin = 14;
    stepper.cfg_MS2_pin = 27;
    stepper.cfg_MS3_pin = 26;
    stepper.cfg_microstepping = STEPPER_CFG_MICROSTEPPING_QUARTER;
    stepper.cfg_rmt_channel = RMT_CHANNEL_0;
    stepper.cfg_stepsPerRev = 4*200;
    stepper_init(&stepper);

    xrayclient_set_status_pos(&stepper.ctr_angle);
    xTaskCreate(stepper_task, "StepperTask", 4096, NULL, 6, NULL);
    stepper.ctr_v = 100;


    vTaskDelete(NULL);
}
