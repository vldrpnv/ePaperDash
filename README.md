# ePaperDash

Arduino firmware for the **Seeed Studio XIAO 7.5" ePaper Panel**
([product page](https://www.seeedstudio.com/XIAO-7-5-ePaper-Panel-p-6416.html)).

The device connects to a WiFi network, subscribes to an MQTT topic that carries
a dashboard image, renders the image on the 800 × 480 ePaper display, and then
deep-sleeps for 60 seconds before repeating the cycle.

A companion Python desktop service now lives in `services/desktop_dashboard_service`.
It generates dashboard images from pluggable sources, renders an SVG layout, and
publishes the 1-bit dashboard payload to MQTT for the firmware.

---

## Hardware

| Component | Details |
|-----------|---------|
| MCU | Seeed XIAO ESP32-C3 |
| Display | 7.5" ePaper, 800 × 480 px, UC8179 driver (B/W) |
| Interface | SPI (hardware SPI on XIAO ESP32-C3) |
| Power | USB-C or onboard 2 000 mAh Li-ion battery |

### Pin mapping

| Function  | XIAO label | GPIO |
|-----------|-----------|------|
| SPI CLK   | D8        | 8    |
| SPI MOSI  | D10       | 10   |
| CS        | D1        | 3    |
| DC        | D3        | 5    |
| RST       | D0        | 2    |
| BUSY      | D2        | 4    |

---

## Required libraries

Install all three via **Arduino IDE → Tools → Manage Libraries**:

| Library | Author | Version |
|---------|--------|---------|
| [GxEPD2](https://github.com/ZinggJM/GxEPD2) | Jean-Marc Zingg | ≥ 1.5.0 |
| [Adafruit GFX](https://github.com/adafruit/Adafruit-GFX-Library) | Adafruit | ≥ 1.11.0 |
| [PubSubClient](https://github.com/knolleary/pubsubclient) | Nick O'Leary | ≥ 2.8.0 |

---

## Board setup

1. Add the Seeed Arduino Boards package URL to Arduino IDE preferences:
   ```
   https://files.seeedstudio.com/arduino/package_seeeduino_boards_index.json
   ```
2. Install **Seeed XIAO ESP32C3** via **Tools → Board → Boards Manager**.
3. Select **Tools → Board → Seeed XIAO ESP32C3**.

---

## Configuration

Edit **`config.h`** before flashing:

```cpp
// WiFi
#define WIFI_SSID        "your_wifi_ssid"
#define WIFI_PASSWORD    "your_wifi_password"

// MQTT broker
#define MQTT_BROKER      "192.168.1.100"
#define MQTT_PORT        1883
#define MQTT_USERNAME    ""   // leave empty if not required
#define MQTT_PASSWORD    ""

// Image topic
#define MQTT_TOPIC_IMAGE "epaper/image"

// How often to check for a new image (seconds)
#define CHECK_INTERVAL_SEC  60
```

---

## Image format

Publish a **retained** MQTT message to `epaper/image` (or the topic you
configured) containing a raw **1-bit-per-pixel bitmap**:

| Property | Value |
|----------|-------|
| Width × Height | 800 × 480 pixels |
| Bits per pixel | 1 (MSB first) |
| Payload size | **48 000 bytes** (800 × 480 ÷ 8) |
| Pixel encoding | `0` = black, `1` = white |

The device only refreshes the display when the image CRC changes, avoiding
unnecessary e-ink wear.

### Example: publish with Python (`paho-mqtt`)

```python
import paho.mqtt.client as mqtt
from PIL import Image
import numpy as np

WIDTH, HEIGHT = 800, 480

# Convert any image to 1-bpp 800×480 bitmap
img = Image.open("dashboard.png").convert("1").resize((WIDTH, HEIGHT))
pixels = np.array(img, dtype=np.uint8)

# Pack 8 pixels into each byte (MSB first)
payload = np.packbits(pixels.flatten()).tobytes()  # 48 000 bytes

client = mqtt.Client()
client.connect("192.168.1.100", 1883)
client.publish("epaper/image", payload, qos=1, retain=True)
client.disconnect()
print(f"Published {len(payload)} bytes")
```

---

## How it works

```
Power-on / wake from deep sleep
         │
         ▼
  Connect to WiFi
         │
         ▼
  Connect to MQTT broker
         │
         ▼
  Subscribe to epaper/image
  Wait ≤ 5 s for retained message
         │
    ┌────┴────┐
    │ received│
    │ new CRC?│
    └────┬────┘
      Yes│                  No
         ▼                  ▼
  Refresh ePaper     Skip refresh
         │                  │
         └────────┬──────────┘
                  ▼
         Disconnect / power off WiFi
                  │
                  ▼
         Deep sleep 60 s
```
