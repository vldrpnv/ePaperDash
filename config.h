#pragma once

// =============================================================================
// WiFi credentials
// =============================================================================
#define WIFI_SSID        "your_wifi_ssid"
#define WIFI_PASSWORD    "your_wifi_password"

// =============================================================================
// MQTT broker settings
// =============================================================================
#define MQTT_BROKER      "192.168.1.100"   // IP or hostname of your MQTT broker
#define MQTT_PORT        1883
#define MQTT_CLIENT_ID   "xiao_epaper_dash"
#define MQTT_USERNAME    ""                // Leave empty if no authentication
#define MQTT_PASSWORD    ""                // Leave empty if no authentication

// Topic that carries the raw 1-bpp bitmap image (48 000 bytes, 800 × 480)
#define MQTT_TOPIC_IMAGE "epaper/image"

// =============================================================================
// Timing
// =============================================================================
#define CHECK_INTERVAL_SEC       60     // Deep-sleep duration between checks
#define WIFI_TIMEOUT_MS          20000  // Max time to wait for WiFi connection
#define MQTT_TIMEOUT_MS          10000  // Max time to wait for MQTT connection
#define MQTT_MESSAGE_TIMEOUT_MS  5000   // Max time to wait for retained message

// =============================================================================
// Display geometry  (Seeed 7.5" ePaper Panel, 800 × 480)
// =============================================================================
#define DISPLAY_WIDTH   800
#define DISPLAY_HEIGHT  480

// =============================================================================
// SPI / ePaper pin assignments for XIAO ESP32-C3
//
//   Function  | XIAO label | GPIO
//   ----------|------------|------
//   SPI CLK   |    D8      |  8    (hardware SPI default – no #define needed)
//   SPI MOSI  |    D10     |  10   (hardware SPI default – no #define needed)
//   CS        |    D1      |  3
//   DC        |    D3      |  5
//   RST       |    D0      |  2
//   BUSY      |    D2      |  4
// =============================================================================
#define EPD_CS    3
#define EPD_DC    5
#define EPD_RST   2
#define EPD_BUSY  4
