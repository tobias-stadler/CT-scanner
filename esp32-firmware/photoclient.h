#ifndef PHOTOCLIENT_H
#define PHOTOCLIENT_H
#include "esp_system.h"

// Implementation of the network protocol for controlling the camera

typedef void (*photoclient_jpeg_cb_t)(uint32_t iso, uint32_t exposure, uint32_t focuslen, uint32_t token);
typedef void (*photoclient_raw_cb_t)(uint32_t iso, uint32_t exposure, uint32_t focuslen, uint32_t token);


//lifecycle control
void photoclient_init();
void photoclient_start();
void photoclient_stop();
void photoclient_destroy();

//Callbacks
void photoclient_set_jpeg_cb(photoclient_jpeg_cb_t cb);
void photoclient_set_raw_cb(photoclient_raw_cb_t cb);

//Commands
void photoclient_send_jpeg_empty(uint32_t token);
void photoclient_send_raw_empty(uint32_t token);

#endif
