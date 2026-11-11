/*
 * The real fireflies: one ESP32, several LEDs, each LED its own firefly.
 *
 * Same rule as fireflysync/oscillator.py, in C++, once per LED:
 *   - each LED has a phase that rises from 0 to 1 once per PERIOD
 *   - at 1 it fires: the LED flashes and the board sends FIRE|esp32-L<n>|...
 *   - when it hears a flash it is pulled forward (more when close to firing:
 *     the Mirollo-Strogatz curve)
 *   - for the first REFRACTORY of each cycle it ignores incoming flashes
 *
 * Who hears whom:
 *   - LEDs on this board hear each other instantly (they sit side by side)
 *   - every LED hears the laptop's virtual drones over Wi-Fi
 *
 * Finding each other - nothing to type:
 *   - every 2 s the board broadcasts HELLO|esp32|<number of LEDs>; the laptop
 *     learns the board's IP from it
 *   - the board learns the laptop's address from any packet it receives
 *   - PING|<n> from the laptop is echoed straight back, so the laptop can
 *     measure the Wi-Fi delay itself
 *
 * Press the BOOT button to throw every LED to a random phase: they blink out
 * of step, then pull back into sync with each other and the screen.
 *
 * Setup: copy secrets.h.example to secrets.h, fill in the 2.4 GHz hotspot,
 * upload, then double-click demo_esp32.bat on the laptop. See docs/HARDWARE.md.
 */
#include <WiFi.h>
#include <WiFiUdp.h>
#include <math.h>
#include "secrets.h"

// ---- Must match the laptop simulation (scripts/_common.py defaults) ------
const float PERIOD_S    = 1.0f;
const float COUPLING    = 0.01f;     // per flash heard
const float DISSIPATION = 3.0f;
const float REFRACTORY  = 0.05f;
const char* ID_PREFIX   = "esp32-L"; // LED n is esp32-L<n>; the laptop adds each one it hears

// ---- Hardware --------------------------------------------------------------
// One entry per LED. Safe output pins on an ESP32 DevKit V1 (WROOM-32).
// Avoid 0 (button), 2 (built-in LED), 6-11 (flash), 12 (boot), 34-39 (input only).
// Only one LED wired?  Use  {2}  to run on the built-in LED alone.
const int LED_PINS[]       = {4, 16, 17, 18, 19, 21};
const int NUM_LEDS         = sizeof(LED_PINS) / sizeof(LED_PINS[0]);
const int BUILTIN_LED      = 2;      // mirrors LED 1, so the board blinks even unwired
const int FIRE_BUTTON_PIN  = 0;      // the BOOT button
const uint32_t FLASH_MS    = 80;

const uint16_t PORT        = 4210;   // this board listens here
const uint16_t LAPTOP_PORT = 4211;   // the laptop listens here

WiFiUDP udp;
IPAddress laptopIP;
uint16_t laptopPort = 0;
bool haveLaptop = false;

float phase[NUM_LEDS];
uint32_t ledOffAt[NUM_LEDS];
bool ledOn[NUM_LEDS];
bool firedThisLoop[NUM_LEDS];
uint32_t seq = 0, fires = 0, heard = 0;
uint32_t lastMicros = 0, lastButton = 0, lastStatus = 0, lastHello = 0;

char rx[96];
char tx[64];

// The curve between phase and "charge". See oscillator.py for why.
float chargeOf(float p) { return log1pf(expm1f(DISSIPATION) * p) / DISSIPATION; }
float phaseOf(float x)  { return expm1f(DISSIPATION * x) / expm1f(DISSIPATION); }
float randomPhase()     { return (esp_random() % 10000) / 10000.0f; }

void setLed(int i, bool on) {
  digitalWrite(LED_PINS[i], on ? HIGH : LOW);
  if (i == 0 && LED_PINS[0] != BUILTIN_LED) digitalWrite(BUILTIN_LED, on ? HIGH : LOW);
}

void fire(int i) {
  fires++;
  setLed(i, true);
  ledOn[i] = true;
  ledOffAt[i] = millis() + FLASH_MS;
  if (haveLaptop) {
    int n = snprintf(tx, sizeof(tx), "FIRE|%s%d|%lu|0", ID_PREFIX, i + 1, (unsigned long)seq++);
    udp.beginPacket(laptopIP, laptopPort);
    udp.write((const uint8_t*)tx, n);
    udp.endPacket();
  }
}

// One flash reaches LED i. Returns true if that pushed it to fire.
bool nudge(int i) {
  if (phase[i] < REFRACTORY) return false;           // just flashed: ignore
  float x = chargeOf(phase[i]) + COUPLING;
  if (x >= 1.0f) { phase[i] = 0.0f; return true; }
  phase[i] = phaseOf(x);
  return false;
}

// A flash from `source` (an LED index, or -1 for the laptop) reaches every
// other LED on the board. Any LED it fires passes its own flash on in turn.
// Each LED fires at most once per loop - the same rule as swarm.py.
void deliver(int source) {
  int queue[NUM_LEDS + 1];
  int qn = 0;
  queue[qn++] = source;
  while (qn > 0) {
    int from = queue[--qn];
    for (int i = 0; i < NUM_LEDS; i++) {
      if (i == from || firedThisLoop[i]) continue;
      if (nudge(i)) {
        firedThisLoop[i] = true;
        fire(i);
        queue[qn++] = i;
      }
    }
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(BUILTIN_LED, OUTPUT);
  for (int i = 0; i < NUM_LEDS; i++) {
    pinMode(LED_PINS[i], OUTPUT);
    setLed(i, false);
    phase[i] = randomPhase();               // start out of step on purpose
    ledOn[i] = false;
  }
  pinMode(FIRE_BUTTON_PIN, INPUT_PULLUP);

  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  Serial.print("Connecting to ");
  Serial.print(WIFI_SSID);
  while (WiFi.status() != WL_CONNECTED) { delay(250); Serial.print("."); }
  WiFi.setSleep(false);                     // power saving adds ragged delay
  Serial.println();
  Serial.print("Connected. IP address: ");
  Serial.println(WiFi.localIP());
  Serial.printf("%d LED fireflies. On the laptop: double-click demo_esp32.bat\n", NUM_LEDS);

  udp.begin(PORT);
  lastMicros = micros();
}

void loop() {
  for (int i = 0; i < NUM_LEDS; i++) firedThisLoop[i] = false;

  // 1. Time passes. Unsigned subtraction stays correct when micros() wraps.
  uint32_t now = micros();
  float dt = (now - lastMicros) / 1e6f;
  lastMicros = now;
  for (int i = 0; i < NUM_LEDS; i++) {
    phase[i] += dt / PERIOD_S;
    if (phase[i] >= 1.0f && !firedThisLoop[i]) {
      phase[i] -= 1.0f;
      if (phase[i] >= 1.0f) phase[i] = 0.0f;
      firedThisLoop[i] = true;
      fire(i);
      deliver(i);
    }
  }

  // 2. Read every waiting packet. Never block - blocking ruins the timing.
  int size;
  while ((size = udp.parsePacket()) > 0) {
    int len = udp.read((uint8_t*)rx, sizeof(rx) - 1);
    rx[len > 0 ? len : 0] = '\0';
    laptopIP = udp.remoteIP();
    laptopPort = udp.remotePort();
    haveLaptop = true;
    if (strncmp(rx, "PING|", 5) == 0) {     // echo at once: the laptop times it
      udp.beginPacket(laptopIP, laptopPort);
      udp.write((const uint8_t*)rx, len);
      udp.endPacket();
    } else if (strncmp(rx, "FIRE|", 5) == 0) {
      if (strncmp(rx + 5, ID_PREFIX, strlen(ID_PREFIX)) != 0) {   // not one of ours
        heard++;
        deliver(-1);
      }
    }
    // HELLO|laptop only teaches us the laptop's address (done above).
  }

  // 3. LEDs off after a short flash (no delay() - it would block step 2).
  uint32_t ms = millis();
  for (int i = 0; i < NUM_LEDS; i++) {
    if (ledOn[i] && (int32_t)(ms - ledOffAt[i]) >= 0) { setLed(i, false); ledOn[i] = false; }
  }

  // 4. Say hello every 2 s, so the laptop can find us without an IP.
  if (ms - lastHello > 2000) {
    lastHello = ms;
    int n = snprintf(tx, sizeof(tx), "HELLO|esp32|%d", NUM_LEDS);
    udp.beginPacket(WiFi.broadcastIP(), LAPTOP_PORT);
    udp.write((const uint8_t*)tx, n);
    udp.endPacket();
  }

  // 5. BOOT button: knock every LED out of sync for the demo.
  if (digitalRead(FIRE_BUTTON_PIN) == LOW && ms - lastButton > 500) {
    lastButton = ms;
    for (int i = 0; i < NUM_LEDS; i++) phase[i] = randomPhase();
    Serial.println("Scrambled! Watch them pull back into sync.");
  }

  // 6. Status every 5 s (Serial is slow, so keep it rare).
  if (ms - lastStatus > 5000) {
    lastStatus = ms;
    Serial.printf("fired %lu  heard %lu  laptop %s\n", (unsigned long)fires,
                  (unsigned long)heard, haveLaptop ? "connected" : "not yet seen");
  }
}
