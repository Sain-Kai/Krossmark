#include <esp_now.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include "esp_wifi.h"

// ── WIFI ───────────────────────────────
const char* SSID     = "Sain";
const char* PASSWORD = "01010000";

// ── PI ─────────────────────────────────
const char* PI_URL = "http://172.25.171.232:5000/sensors";

// ── CHANNEL ────────────────────────────
#define WIFI_CHANNEL 6

// ── PINS ───────────────────────────────
#define PIR_PIN 13
#define MIC_PIN 33

#define AUDIO_SAMPLES 4000   // 🔥 reduced for stability
#define MIC_SPIKE_THRESHOLD 150

bool triggerReceived = false;
uint16_t audioBuf[AUDIO_SAMPLES];

// ── COOLDOWN ───────────────────────────
unsigned long lastTrigger = 0;
#define NODE2_COOLDOWN 5000

// ── RECEIVE ────────────────────────────
void onReceive(const esp_now_recv_info_t* info, const uint8_t* data, int len) {

  Serial.print("[RX FROM] ");
  for (int i = 0; i < 6; i++) {
    Serial.printf("%02X", info->src_addr[i]);
    if (i < 5) Serial.print(":");
  }
  Serial.println();

  if (len > 0) {
    triggerReceived = true;
    Serial.println("[TRIGGER RECEIVED]");
  }
}

// ── WIFI CHECK ─────────────────────────
void ensureWiFi() {
  if (WiFi.status() == WL_CONNECTED) return;

  Serial.println("[RECONNECTING WIFI]");
  WiFi.disconnect();
  WiFi.begin(SSID, PASSWORD);

  int retries = 0;
  while (WiFi.status() != WL_CONNECTED && retries < 10) {
    delay(500);
    Serial.print(".");
    retries++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n[WiFi RECONNECTED]");
    esp_wifi_set_channel(WIFI_CHANNEL, WIFI_SECOND_CHAN_NONE);
  }
}

// ── MAIN WORK ──────────────────────────
void captureAndSend() {

  Serial.println("[START CAPTURE]");

  uint8_t pir = digitalRead(PIR_PIN);

  uint32_t sum = 0;

  for (int i = 0; i < AUDIO_SAMPLES; i++) {
    uint16_t val = analogRead(MIC_PIN);
    if (val < 50) val = 0;

    audioBuf[i] = val;
    sum += val;

    delayMicroseconds(125);
  }

  float avg = sum / (float)AUDIO_SAMPLES;
  uint8_t spike = avg > MIC_SPIKE_THRESHOLD;

  ensureWiFi();

  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[WiFi FAIL]");
    return;
  }

  size_t size = 2 + AUDIO_SAMPLES * 2;

  uint8_t* payload = (uint8_t*)malloc(size);
  if (!payload) {
    Serial.println("[MEMORY FAIL]");
    return;
  }

  payload[0] = pir;
  payload[1] = spike;

  memcpy(payload + 2, audioBuf, AUDIO_SAMPLES * 2);

  HTTPClient http;
  http.begin(PI_URL);
  http.addHeader("Content-Type", "application/octet-stream");

  int code = http.POST(payload, size);

  Serial.printf("[HTTP CODE] %d\n", code);

  if (code > 0) {
    String response = http.getString();
    Serial.println("[PI RESPONSE]");
    Serial.println(response);
  }

  free(payload);
  http.end();
}

// ── SETUP ──────────────────────────────
void setup() {
  Serial.begin(115200);

  pinMode(PIR_PIN, INPUT);

  // 🔥 IMPORTANT: dual mode
  WiFi.mode(WIFI_AP_STA);
  WiFi.begin(SSID, PASSWORD);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\n[WiFi OK]");

  // 🔥 FORCE CHANNEL AFTER WIFI
  esp_wifi_set_channel(WIFI_CHANNEL, WIFI_SECOND_CHAN_NONE);

  if (esp_now_init() != ESP_OK) {
    Serial.println("ESP-NOW FAIL");
    return;
  }

  esp_now_register_recv_cb(onReceive);

  Serial.println("[NODE2 READY]");
}

// ── LOOP ───────────────────────────────
void loop() {

  if (triggerReceived && millis() - lastTrigger > NODE2_COOLDOWN) {
    triggerReceived = false;
    lastTrigger = millis();

    captureAndSend();
  }

  delay(10);
}