/*
 * PHASE 0 - ESP32 side of the Wi-Fi round-trip test.
 *
 * Connects to Wi-Fi, listens on UDP port 4210, and sends every packet it
 * receives straight back to whoever sent it. The laptop script measures how
 * long the round trip took. The LED toggles on every packet so you can see
 * it working.
 *
 * Setup:
 *   1. Copy secrets.h.example to secrets.h and fill in the hotspot details.
 *   2. Hotspot must be 2.4 GHz - the ESP32 cannot see 5 GHz networks.
 *   3. Upload, open Serial Monitor at 115200 baud, note the IP it prints.
 *   4. On the laptop: python scripts/latency_test.py --peer <that IP>
 */
#include <WiFi.h>
#include <WiFiUdp.h>
#include "secrets.h"

const uint16_t PORT = 4210;
const int LED_PIN = 2;          // built-in LED on most ESP32 DevKit boards

WiFiUDP udp;
uint8_t buf[128];

void setup() {
  Serial.begin(115200);
  pinMode(LED_PIN, OUTPUT);

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  Serial.print("Connecting to ");
  Serial.print(WIFI_SSID);
  while (WiFi.status() != WL_CONNECTED) {
    delay(250);
    Serial.print(".");
  }
  // Power saving holds packets back in bursts - exactly the delay we are
  // trying to measure. Turn it off once connected.
  WiFi.setSleep(false);

  Serial.println();
  Serial.print("Connected. IP address: ");
  Serial.println(WiFi.localIP());

  udp.begin(PORT);
  Serial.printf("Listening for UDP on port %u\n", PORT);
}

void loop() {
  int size = udp.parsePacket();
  if (size > 0) {
    int len = udp.read(buf, sizeof(buf));
    // Reply first, blink second: anything slow before the reply would
    // show up as extra delay in the measurement.
    udp.beginPacket(udp.remoteIP(), udp.remotePort());
    udp.write(buf, len);
    udp.endPacket();
    digitalWrite(LED_PIN, !digitalRead(LED_PIN));
  }
}
