#include "stepper.h"

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"
#include "esp_system.h"
#include "esp_event.h"
#include "esp_types.h"
#include "esp_log.h"
#include "driver/gpio.h"
#include "driver/timer.h"
#include "driver/periph_ctrl.h"
#include "stdio.h"
#include "math.h"

#define STEPPER_TG TIMER_GROUP_0
#define STEPPER_T TIMER_0
#define STEPPER_DIVIDER 8

#define STEPPER_MAXNUM 8

static const char* TAG = "Stepper";

static const rmt_item32_t RMTMSG_STEP[] = {{{{200, 1, 200, 0}}}}; //, {{{0, 1, 0, 0}}}

static bool running = false;

static stepper_t* stepper;

// Wait for hardware timer to reach certain value (used for generating precise delays)
static void wait_timer(uint64_t val) {
    uint64_t cur_time;
    timer_get_counter_value(STEPPER_TG, STEPPER_T, &cur_time);
    uint64_t new_time = cur_time + val;
    while(cur_time < new_time) {
        timer_get_counter_value(STEPPER_TG, STEPPER_T, &cur_time);
    }
}

// Generate single step pulse
static inline void stepper_pulse(stepper_t* pStepp, uint32_t dir)
{
    //ESP_LOGI(TAG, "Pulse for step %d", pStepp->_cur_pos);
    gpio_set_level(pStepp -> cfg_dir_pin, dir);
    rmt_write_items(pStepp -> cfg_rmt_channel, RMTMSG_STEP, 1, false);
}


// Initialize hardware timer for generating precise delay times
static void steptimer_init(){
    timer_config_t cfg;
    cfg.divider = STEPPER_DIVIDER;
    cfg.alarm_en = TIMER_ALARM_DIS;
    cfg.counter_dir = TIMER_COUNT_UP;
    cfg.auto_reload = false;
    cfg.counter_en = TIMER_START;
    cfg.intr_type = TIMER_INTR_NONE;

    timer_init(STEPPER_TG, STEPPER_T, &cfg);
    timer_set_counter_value(STEPPER_TG, STEPPER_T, 0UL);
    timer_set_alarm_value(STEPPER_TG, STEPPER_T, 0UL);
}

// Initialize RMT peripheral
static void steprmt_init(stepper_t *pStepp) {

    rmt_config_t cfg = { .rmt_mode = RMT_MODE_TX,
            .channel = pStepp -> cfg_rmt_channel,
            .gpio_num = pStepp -> cfg_step_pin,
            .clk_div = 8,
            .mem_block_num = 1,
            .tx_config = {
                    .carrier_freq_hz = 1000,
                    .carrier_level = RMT_CARRIER_LEVEL_LOW,
                    .idle_level = RMT_IDLE_LEVEL_LOW,
                    .carrier_duty_percent = 50,
                    .carrier_en = false,
                    .loop_en = false,
                    .idle_output_en = true
             }
    };

    ESP_ERROR_CHECK(rmt_config(&cfg));
    ESP_ERROR_CHECK(rmt_driver_install(cfg.channel, 0, 0));

}

// Setup outputs
static void stepgpio_init(stepper_t* pStepp)
{
    gpio_pad_select_gpio(pStepp -> cfg_dir_pin);
    gpio_set_direction(pStepp -> cfg_dir_pin, GPIO_MODE_OUTPUT);
    gpio_set_level(pStepp -> cfg_dir_pin, 0);

    gpio_pad_select_gpio(pStepp -> cfg_MS1_pin);
    gpio_set_direction(pStepp -> cfg_MS1_pin, GPIO_MODE_OUTPUT);
    gpio_set_level(pStepp -> cfg_MS1_pin, (pStepp ->cfg_microstepping >> 2) & 1);

    gpio_pad_select_gpio(pStepp -> cfg_MS2_pin);
    gpio_set_direction(pStepp -> cfg_MS2_pin, GPIO_MODE_OUTPUT);
    gpio_set_level(pStepp -> cfg_MS2_pin, (pStepp ->cfg_microstepping >> 1) & 1);

    gpio_pad_select_gpio(pStepp -> cfg_MS3_pin);
    gpio_set_direction(pStepp -> cfg_MS3_pin, GPIO_MODE_OUTPUT);
    gpio_set_level(pStepp -> cfg_MS3_pin, (pStepp ->cfg_microstepping >> 0) & 1);
}


//Setup state of stepper struct
void stepper_init(stepper_t* pStepp)
{
    if(stepper != NULL || pStepp == NULL) {
        ESP_LOGE(TAG, "Invalid initialization!");
        return;
    }

    stepper = pStepp;

    pStepp->_cur_pos = 0;
    pStepp->ctr_angle = 0.0f;
    pStepp->ctr_steps_abs = 0;
    pStepp->ctr_v = 10;

    stepgpio_init(pStepp);
    steprmt_init(pStepp);

    running = false;
    steptimer_init();
}

// Move stepper to requested position (blocking operation)
void stepper_move_steps_abs()
{
    int diff = stepper->ctr_steps_abs-stepper->_cur_pos;
    while(diff != 0) {
        if(diff > 0) {
            stepper_pulse(stepper, 1);
            stepper->_cur_pos++;
        } else if (diff < 0) {
            stepper_pulse(stepper, 0);
            stepper->_cur_pos--;
        }
        diff = stepper->ctr_steps_abs-stepper->_cur_pos;
        wait_timer(10000000/(stepper->ctr_v));
    }
    stepper->ctr_angle = (stepper->ctr_steps_abs*360.0f)/(float)stepper->cfg_stepsPerRev;
}

// Convert angle to steps and move stepper
void stepper_move_angle()
{
    stepper->ctr_steps_abs = roundf((stepper->ctr_angle*stepper->cfg_stepsPerRev)/360.0f);
    stepper_move_steps_abs();
}

// Set current position as home position
void stepper_zero()
{
    stepper->ctr_angle = 0.0f;
    stepper->ctr_steps_abs = 0;
    stepper->_cur_pos = 0;
}

// Move stepper to current home position
void stepper_move_zero()
{
    stepper->ctr_steps_abs = 0;
    stepper_move_steps_abs();
}

