#ifndef XRAYCLIENT_H
#define XRAYCLIENT_H

#include "esp_system.h"

// Implementation of the network protocol for controlling the stepper motor

typedef void (*xrayclient_newpos_cb_t)(float, uint32_t);

// Lifecycle control
void xrayclient_init();
void xrayclient_start();
void xrayclient_stop();
void xrayclient_destroy();

// Set callbacks
void xrayclient_set_newpos_cb(xrayclient_newpos_cb_t);
void xrayclient_set_status_pos(float* pStatus);
void xrayclient_send_cmd_done(float pos, uint32_t token);

#endif
