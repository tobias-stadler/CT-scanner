#ifndef STEPPER_H
#define STEPPER_H

#include "driver/rmt.h"

// Based on timing diagrams from https://www.pololu.com/file/0J450/a4988_DMOS_microstepping_driver_with_translator.pdf (Accessed 25.02.2020)

//Early version of own stepper driver that only supports one stepper, but written with future asynchronous stepper control in mind
// It uses the RMT peripheral (intended for generating IR pulses for remotes) to generate the stepper pulses
//cfg_ -> ConFiGuration variables: set before calling stepper_add
//ctl_ -> ConTroL variables: control position
typedef enum { //MS1 MS2 MS3
    STEPPER_CFG_MICROSTEPPING_FULL = 0b000,
    STEPPER_CFG_MICROSTEPPING_HALF = 0b100,
    STEPPER_CFG_MICROSTEPPING_QUARTER = 0b010,
    STEPPER_CFG_MICROSTEPPING_EIGHTH = 0b110,
    STEPPER_CFG_MICROSTEPPING_SIXTEENTH = 0b111
} stepper_cfg_microstepping_t;

typedef struct {
    uint8_t cfg_step_pin;
    uint8_t cfg_dir_pin;
    uint8_t cfg_MS1_pin, cfg_MS2_pin, cfg_MS3_pin;
    stepper_cfg_microstepping_t  cfg_microstepping;
    int cfg_stepsPerRev;
    rmt_channel_t cfg_rmt_channel;

    float ctr_angle;
    int ctr_steps_abs;
    int ctr_v;

    int _cur_pos;
} stepper_t;

//Lifecycle
void stepper_init(stepper_t* pStepp);

//Move stepper to position set in ctl_ variables
void stepper_move_angle();
void stepper_move_steps_abs();

//Set current position as zero position for stepper
void stepper_zero();

//Move stepper to zero position
void stepper_move_zero();


#endif
