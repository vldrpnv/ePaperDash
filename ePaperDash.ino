/**
 * ePaperDash
 *
 * MQTT dashboard image display for the Seeed Studio XIAO 7.5" ePaper Panel
 * (https://www.seeedstudio.com/XIAO-7-5-ePaper-Panel-p-6416.html)
 *
 * Hardware
 * --------
 *   MCU     : Seeed XIAO ESP32-C3
 *   Display : 7.5" ePaper, 800 × 480 px, UC8179 driver (B/W)
 *
 * Behaviour
 * ---------
 *   1. Wake from deep sleep (or power-on).
 *   2. Connect to WiFi.
 *   3. Connect to MQTT broker and subscribe to MQTT_TOPIC_IMAGE.
 *   4. Wait up to MQTT_MESSAGE_TIMEOUT_MS for a retained message.
 *   5. If a new image is received (different CRC from the last one), refresh
 *      the ePaper display.
 *   6. Disconnect, then deep-sleep for CHECK_INTERVAL_SEC (default: 60 s).
 *
 * Image format
 * ------------
 *   Raw 1-bit-per-pixel bitmap, 800 × 480 pixels, MSB-first, row-major.
 *   Total payload size: 800 × 480 / 8 = 48 000 bytes.
 *   Pixel value 1 → black,  0 → white.
 *
 * Required libraries (install via Arduino Library Manager)
 * ---------------------------------------------------------
 *   - GxEPD2          by Jean-Marc Zingg  (>= 1.5.0)
 *   - Adafruit GFX    by Adafruit
 *   - PubSubClient    by Nick O'Leary     (>= 2.8.0)
 *
 * Board: "XIAO_ESP32C3" (Seeed Arduino Boards package)
 */

#include <WiFi.h>
#include <PubSubClient.h>
#include <GxEPD2_BW.h>
#include <SPI.h>
#include "config.h"
#include "initial_image.h"
#include "logging.h"

// ---------------------------------------------------------------------------
// Display object
//
// Primary model  : GxEPD2_750_T7  (GDEW075T7 / UC8179, 800×480 B/W)
//                  – matches Waveshare 7.5" V2 and Seeed 7.5" panel
// Fallback model : GxEPD2_750_M07 (GDEW075M07 / UC8179, 800×480 B/W)
//                  – uncomment the two lines below and comment out the ones
//                    above if the display produces a garbled image
// ---------------------------------------------------------------------------
GxEPD2_BW<GxEPD2_750_T7, GxEPD2_750_T7::HEIGHT> display(
    GxEPD2_750_T7(EPD_CS, EPD_DC, EPD_RST, EPD_BUSY));

// GxEPD2_BW<GxEPD2_750_M07, GxEPD2_750_M07::HEIGHT> display(
//     GxEPD2_750_M07(EPD_CS, EPD_DC, EPD_RST, EPD_BUSY));

// ---------------------------------------------------------------------------
// Image buffer: 800 × 480 / 8 = 48 000 bytes, allocated on the heap
// ---------------------------------------------------------------------------
static const uint32_t IMAGE_BYTES = (uint32_t)DISPLAY_WIDTH * DISPLAY_HEIGHT / 8;

static uint8_t*       imageBuffer  = nullptr;
static volatile bool  imageReceived = false;

// CRC of the last image rendered – kept across deep-sleep cycles in RTC RAM
RTC_DATA_ATTR static uint32_t lastImageCrc = 0;

WiFiClient   wifiClient;
PubSubClient mqttClient(wifiClient);

// ---------------------------------------------------------------------------
// Forward declarations
// ---------------------------------------------------------------------------
static void goToSleep();

// ---------------------------------------------------------------------------
// CRC-32 (standard polynomial, used for change-detection only)
// ---------------------------------------------------------------------------
static uint32_t crc32(const uint8_t* data, size_t length)
{
    uint32_t crc = 0xFFFFFFFFu;
    for (size_t i = 0; i < length; i++) {
        crc ^= data[i];
        for (int b = 0; b < 8; b++) {
            crc = (crc >> 1) ^ (0xEDB88320u & (uint32_t)(-(int32_t)(crc & 1u)));
        }
    }
    return ~crc;
}

// ---------------------------------------------------------------------------
// MQTT callback – called by PubSubClient when a message arrives
// ---------------------------------------------------------------------------
static void onMqttMessage(char* topic, byte* payload, unsigned int length)
{
    if (strcmp(topic, MQTT_TOPIC_IMAGE) != 0) return;

    if (length != IMAGE_BYTES) {
        Serial.printf(LOG_MQTT "Unexpected payload size %u (expected %u) – ignoring\n",
                      length, IMAGE_BYTES);
        return;
    }

    if (imageBuffer) {
        memcpy(imageBuffer, payload, length);
        imageReceived = true;
        Serial.printf(LOG_MQTT "Image received (%u bytes)\n", length);
    }
}

// ---------------------------------------------------------------------------
// WiFi helpers
// ---------------------------------------------------------------------------
static bool wifiConnect()
{
    Serial.printf(LOG_WIFI "Connecting to \"%s\"", WIFI_SSID);
    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    unsigned long start = millis();
    while (WiFi.status() != WL_CONNECTED) {
        if (millis() - start >= WIFI_TIMEOUT_MS) {
            Serial.println("\n" LOG_WIFI "Connection timed out");
            return false;
        }
        delay(500);
        Serial.print(".");
    }
    Serial.printf("\n" LOG_WIFI "Connected – IP: %s\n", WiFi.localIP().toString().c_str());
    return true;
}

// ---------------------------------------------------------------------------
// MQTT helpers
// ---------------------------------------------------------------------------
static bool mqttConnect()
{
    Serial.printf(LOG_MQTT "Connecting to %s:%d", MQTT_BROKER, MQTT_PORT);
    mqttClient.setServer(MQTT_BROKER, MQTT_PORT);
    mqttClient.setCallback(onMqttMessage);

    // Enlarge the internal buffer so that a 48 000-byte image fits in one message
    if (!mqttClient.setBufferSize(IMAGE_BYTES + 512)) {
        Serial.println("\n" LOG_MQTT "Failed to allocate receive buffer");
        return false;
    }

    unsigned long start = millis();
    while (!mqttClient.connected()) {
        if (millis() - start >= MQTT_TIMEOUT_MS) {
            Serial.println("\n" LOG_MQTT "Connection timed out");
            return false;
        }

        bool ok = (strlen(MQTT_USERNAME) > 0)
                  ? mqttClient.connect(MQTT_CLIENT_ID, MQTT_USERNAME, MQTT_PASSWORD)
                  : mqttClient.connect(MQTT_CLIENT_ID);

        if (!ok) {
            delay(1000);
            Serial.print(".");
        }
    }
    Serial.println("\n" LOG_MQTT "Connected");
    return true;
}

// ---------------------------------------------------------------------------
// Render the initial (built-in) image from PROGMEM on first boot
// ---------------------------------------------------------------------------
static void showInitialImage()
{
    Serial.println(LOG_EPD "Displaying initial image…");
    display.init(115200, true, 2, false);
    display.setRotation(0);
    display.setFullWindow();

    // GxEPD2 uses a paged-drawing model to keep RAM usage low.
    // The display height is divided into horizontal strips ("pages"); the
    // draw commands inside the do-while loop are replayed once per page.
    // firstPage() resets to the first strip; nextPage() advances to the next
    // and returns false when all strips have been transferred to the panel.
    display.firstPage();
    do {
        display.fillScreen(GxEPD_WHITE);
        display.drawBitmap(0, 0, INITIAL_IMAGE,
                           DISPLAY_WIDTH, DISPLAY_HEIGHT,
                           GxEPD_BLACK);
    } while (display.nextPage());

    display.powerOff();

    // Record the CRC of the initial image so it is not re-rendered on the
    // next wake cycle unless a different image arrives via MQTT.
    memcpy_P(imageBuffer, INITIAL_IMAGE, IMAGE_BYTES);
    lastImageCrc = crc32(imageBuffer, IMAGE_BYTES);

    Serial.println(LOG_EPD "Initial image displayed");
}

// ---------------------------------------------------------------------------
// Render the image buffer on the ePaper display
// ---------------------------------------------------------------------------
static void showImage()
{
    Serial.println(LOG_EPD "Refreshing display…");
    display.init(115200, true, 2, false);
    display.setRotation(0);
    display.setFullWindow();

    // GxEPD2 uses a paged-drawing model to keep RAM usage low.
    // The display height is divided into horizontal strips ("pages"); the
    // draw commands inside the do-while loop are replayed once per page.
    // firstPage() resets to the first strip; nextPage() advances to the next
    // and returns false when all strips have been transferred to the panel.
    display.firstPage();
    do {
        display.fillScreen(GxEPD_WHITE);
        display.drawBitmap(0, 0, imageBuffer,
                           DISPLAY_WIDTH, DISPLAY_HEIGHT,
                           GxEPD_BLACK);
    } while (display.nextPage());

    display.powerOff();
    Serial.println(LOG_EPD "Refresh complete");
}

// ---------------------------------------------------------------------------
// Deep-sleep helper – disconnects network interfaces, then sleeps
// ---------------------------------------------------------------------------
static void goToSleep()
{
    free(imageBuffer);
    imageBuffer = nullptr;

    if (mqttClient.connected()) mqttClient.disconnect();
    WiFi.disconnect(true);
    WiFi.mode(WIFI_OFF);

    Serial.printf(LOG_MAIN "Sleeping for %d s\n", CHECK_INTERVAL_SEC);
    Serial.flush();

    esp_sleep_enable_timer_wakeup((uint64_t)CHECK_INTERVAL_SEC * 1000000ULL);
    esp_deep_sleep_start();
}

// ---------------------------------------------------------------------------
// Arduino setup() – executed once per deep-sleep wake cycle
// ---------------------------------------------------------------------------
void setup()
{
    Serial.begin(115200);
    delay(10000);
    Serial.println("\n" LOG_MAIN "Wake-up");

    // Allocate image receive buffer from heap
    imageBuffer = (uint8_t*)malloc(IMAGE_BYTES);
    if (!imageBuffer) {
        Serial.println(LOG_ERROR "Failed to allocate image buffer – not enough heap");
        goToSleep();
        return;
    }

    // On the very first boot (lastImageCrc == 0) show the built-in initial
    // image immediately, before attempting a WiFi connection.
    if (lastImageCrc == 0) {
        showInitialImage();
    }

    bool gotImage = false;

    if (wifiConnect() && mqttConnect()) {
        bool subscribed = mqttClient.subscribe(MQTT_TOPIC_IMAGE);
        if (subscribed) {
            Serial.printf(LOG_MQTT "Subscribed to \"%s\"\n", MQTT_TOPIC_IMAGE);

            // Poll the client until the retained message arrives or timeout
            unsigned long waitStart = millis();
            while (!imageReceived &&
                   (millis() - waitStart < MQTT_MESSAGE_TIMEOUT_MS)) {
                mqttClient.loop();
                delay(10);
            }
            gotImage = imageReceived;
        } else {
            Serial.printf(LOG_ERROR "Failed to subscribe to \"%s\" (MQTT state: %d)\n",
                          MQTT_TOPIC_IMAGE, mqttClient.state());
        }
    }

    if (gotImage) {
        uint32_t newCrc = crc32(imageBuffer, IMAGE_BYTES);
        if (newCrc != lastImageCrc) {
            Serial.printf(LOG_MAIN "New image (CRC %08X → %08X) – updating display\n",
                          lastImageCrc, newCrc);
            showImage();
            lastImageCrc = newCrc;
        } else {
            Serial.println(LOG_MAIN "Image unchanged – skipping display refresh");
        }
    } else {
        Serial.println(LOG_MAIN "No image received within timeout");
    }

    goToSleep();
}

// loop() is never reached because setup() always ends with deep sleep
void loop() {}
