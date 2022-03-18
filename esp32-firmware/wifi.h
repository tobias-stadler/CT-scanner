#ifndef NET_WIFI_H
#define NET_WIFI_H

#include <esp_system.h>

// WIFI API Wrapper for quick prototyping of network applications. Sets up WIFI modem, network stack and addresses.

//Lifecycle
void network_wifi_init(void);
void network_wifi_start(void);
void network_wifi_stop(void);

// Start network connection as access-point(AP) or client(STATION->sta)
void network_wifi_sta_init(void);
void network_wifi_ap_init(void);
void network_wifi_sta_ap_init(void);

// Wait for successful wifi connection (useful when using station mode)
bool network_wifi_wait_connected(void);

#endif
