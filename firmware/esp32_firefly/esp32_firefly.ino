/*
 * PHASE 2 - the real drone.
 *
 * The same firefly rule as fireflysync/oscillator.py, in C++:
 *   - a phase rises from 0 to 1 once per PERIOD
 *   - at 1 it fires: LED flashes and it sends FIRE|esp32-1|<seq>|0
 *   - when it hears a FIRE from a neighbour, its phase is pulled forward
 *     (more when it is close to firing - the Mirollo-Strogatz curve)
 *   - for the first REFRACTORY of each cycle it ignores incoming flashes
 *
 * It learns the laptop's address from whatever packet it last received, so
 * the laptop's IP never has to be typed in here.
 *
 * Press the BOOT button to throw it to a random phase: the LED goes
 * off-beat, then pulls back into sync. That is the demo.
 *
 * Setup: copy secrets.h.example to secrets.h, fill in the 2.4 GHz hotspot,
 * upload, read the IP from Serial Monitor (115200), then on the laptop:
 *     python scripts/run_live.py --peer <that IP>
 */
#include <WiFi.h>
#include <WiFiUdp.h>
#include <math.h>
#include "secrets.h"

// ---- Must match the laptop simulation (run_live.py defaults) -------------
const float PERIOD_S    = 1.0f;
const float COUPLING    = 0.01f;      // per flash; the ESP32 hears ~18 drones
const float DISSIPATION = 3.0f;
const float REFRACTORY  = 0.05f;
const char* NODE_ID     = "esp32-1";      // must match run_live.py --node-id

// ---- Hardware ------------------------------------------------------------
const uint16_t PORT       = 4210;
const int      LED_PIN    = 2;            // built-in LED on most DevKit boards
const int      BOOT_PIN   = 0;            // the BOOT button
const uint32_t FLASH_MS   = 80;

WiFiUDP udp;
IPAddress laptopIP;
uint16_t laptopPort = 0;
bool haveLaptop = false;

float phase = 0.0f;
uint32_t seq = 0;
uint32_t lastMicros = 0;
uint32_t ledOffAt = 0;
bool ledOn = false;
uint32_t lastButton = 0;
uint32_t lastStatus = 0;
uint32_t fires = 0, heard = 0;

char rx[96];
char tx[64];

// The curve between phase and "charge". See oscillator.py for why.
float chargeOf(float p) { return log1pf(expm1f(DISSIPATION) * p) / DISSIPATION; }
float phaseOf(float x)  { return expm1f(DISSIPATION * x) / expm1f(DISSIPATION); }

float randomPhase() { return (esp_random() % 10000) / 10000.0f; }

void fire() {
  fires++;
  digitalWrite(LED_PIN, HIGH);
  ledOn = true;
  ledOffAt = millis() + FLASH_MS;
  if (haveLaptop) {
    int n = snprintf(tx, sizeof(tx), "FIRE|%s|%lu|0", NODE_ID, (unsigned long)seq++);
    udp.beginPacket(laptopIP, laptopPort);
    udp.write((const uint8_t*)tx, n);
    udp.endPacket();
  }
}

void onNeighbourFired() {
  if (phase < REFRACTORY) return;          // just flashed: ignore
  float x = chargeOf(phase) + COUPLING;
  if (x >= 1.0f) { phase = 0.0f; fire(); }
  else           { phase = phaseOf(x); }
}

void setup() {
  Serial.begin(115200);
  pinMode(LED_PIN, OUTPUT);
  pinMode(BOOT_PIN, INPUT_PULLUP);

  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  Serial.print("Connecting to ");
  Serial.print(WIFI_SSID);
  while (WiFi.status() != WL_CONNECTED) { delay(250); Serial.print("."); }
  WiFi.setSleep(false);                    // power saving adds ragged delay
  Serial.println();
  Serial.print("Connected. IP address: ");
  Serial.println(WiFi.localIP());
  Serial.println("On the laptop run:  python scripts/run_live.py --peer <this IP>");

  udp.begin(PORT);
  phase = randomPhase();                   // start off-beat on purpose
  lastMicros = micros();
}

void loop() {
  // 1. Time passes. Unsigned subtraction stays correct when micros() wraps.
  uint32_t now = micros();
  float dt = (now - lastMicros) / 1e6f;
  lastMicros = now;
  phase += dt / PERIOD_S;
  if (phase >= 1.0f) {
    phase -= 1.0f;
    if (phase >= 1.0f) phase = 0.0f;
    fire();
  }

  // 2. Read every waiting packet. Never block - blocking ruins the timing.
  int size;
  while ((size = udp.parsePacket()) > 0) {
    int len = udp.read((uint8_t*)rx, sizeof(rx) - 1);
    rx[len > 0 ? len : 0] = '\0';
    laptopIP = udp.remoteIP();
    laptopPort = udp.remotePort();
    haveLaptop = true;
    if (strncmp(rx, "FIRE|", 5) == 0) {
      const char* id = rx + 5;
      size_t idLen = strlen(NODE_ID);
      bool isMe = strncmp(id, NODE_ID, idLen) == 0 && id[idLen] == '|';
      if (!isMe) { heard++; onNeighbourFired(); }
    }
    // HELLO packets only teach us the laptop's address.
  }

  // 3. LED off after a short flash (no delay() - it would block step 2).
  if (ledOn && (int32_t)(millis() - ledOffAt) >= 0) {
    digitalWrite(LED_PIN, LOW);
    ledOn = false;
  }

  // 4. BOOT button: knock it out of sync for the demo.
  if (digitalRead(BOOT_PIN) == LOW && millis() - lastButton > 500) {
    lastButton = millis();
    phase = randomPhase();
    Serial.println("Scrambled! Watch it pull back into sync.");
  }

  // 5. Status every 5 s (Serial is slow, so keep it rare).
  if (millis() - lastStatus > 5000) {
    lastStatus = millis();
    Serial.printf("fired %lu  heard %lu  laptop %s\n", (unsigned long)fires,
                  (unsigned long)heard, haveLaptop ? "connected" : "not yet seen");
  }
}
