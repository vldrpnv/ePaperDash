#pragma once

// =============================================================================
// Serial log-prefix constants
//
// Every Serial.print/printf call in the firmware uses one of these prefixes so
// that log lines are easily identifiable in the serial monitor.
// =============================================================================
#define LOG_EPD    "[EPD] "
#define LOG_WIFI   "[WiFi] "
#define LOG_MQTT   "[MQTT] "
#define LOG_MAIN   "[ePaperDash] "
#define LOG_ERROR  "[ERROR] "
