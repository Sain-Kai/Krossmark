#include <WiFi.h>
#include <esp_now.h>
#include "esp_wifi.h"
#include <Wire.h>
#include <math.h>

uint8_t SENSOR_MAC[] = {0xF0, 0x24, 0xF9, 0x45, 0x48, 0xAC};

#define WIFI_CHANNEL 6

const int IR1_PIN = 27;
const int IR2_PIN = 26;
const int LED_PIN = 2;

// ADXL
const int SDA_PIN = 33;
const int SCL_PIN = 32;
const int ADXL_ADDR = 0x53;

const unsigned long COOLDOWN_MS = 3000;

const float DELTA_THRESHOLD = 0.07;
const float SHOCK_THRESHOLD = 1.5;

unsigned long lastFired = 0;

typedef struct {
  uint8_t trigger;
} TriggerPacket;

void onSent(const wifi_tx_info_t *info, esp_now_send_status_t status) {
  Serial.print("[SEND STATUS] ");
  Serial.println(status == ESP_NOW_SEND_SUCCESS ? "SUCCESS" : "FAIL");
}

void adxl_write(byte reg, byte val) {
  Wire.beginTransmission(ADXL_ADDR);
  Wire.write(reg);
  Wire.write(val);
  Wire.endTransmission();
}

void adxl_init() {
  Wire.begin(SDA_PIN, SCL_PIN);
  adxl_write(0x2D, 0x08);
  adxl_write(0x31, 0x09); 
}

float adxl_magnitude() {
  Wire.beginTransmission(ADXL_ADDR);
  Wire.write(0x32);
  Wire.endTransmission(false);
  Wire.requestFrom(ADXL_ADDR, 6, true);

  int16_t x = Wire.read() | (Wire.read() << 8);
  int16_t y = Wire.read() | (Wire.read() << 8);
  int16_t z = Wire.read() | (Wire.read() << 8);

  float ax = x * 0.004;
  float ay = y * 0.004;
  float az = z * 0.004;

  return sqrt(ax * ax + ay * ay + az * az);
}

bool detectDisturbance() {
  float prev = adxl_magnitude();

  for (int i = 0; i < 10; i++) {
    float curr = adxl_magnitude();
    float delta = abs(curr - prev);

    if (curr > SHOCK_THRESHOLD) return true;
    if (delta > DELTA_THRESHOLD) return true;

    prev = curr;
    delay(5);
  }
  return false;
}

// ── SEND ───────────────────────────────
void sendTrigger() {
  TriggerPacket pkt;
  pkt.trigger = 1;

  esp_err_t result = esp_now_send(SENSOR_MAC, (uint8_t*)&pkt, sizeof(pkt));

  if (result == ESP_OK) Serial.println("[ESP-NOW] SENT");
  else Serial.println("[ESP-NOW] FAIL");
}

// ── SETUP ──────────────────────────────
void setup() {
  Serial.begin(115200);

  pinMode(IR1_PIN, INPUT);
  pinMode(IR2_PIN, INPUT);
  pinMode(LED_PIN, OUTPUT);

  WiFi.mode(WIFI_STA);

  // Force channel BEFORE init
  esp_wifi_set_channel(WIFI_CHANNEL, WIFI_SECOND_CHAN_NONE);

  if (esp_now_init() != ESP_OK) {
    Serial.println("ESP-NOW INIT FAIL");
    return;
  }

  esp_now_register_send_cb(onSent);

  esp_now_peer_info_t peer = {};
  memcpy(peer.peer_addr, SENSOR_MAC, 6);
  peer.channel = WIFI_CHANNEL;
  peer.encrypt = false;

  if (esp_now_add_peer(&peer) != ESP_OK) {
    Serial.println("PEER ADD FAIL");
    return;
  }

  adxl_init();

  Serial.println("[NODE1 READY]");
}

// ── LOOP ───────────────────────────────
void loop() {

  bool ir1 = digitalRead(IR1_PIN) == LOW;
  bool ir2 = digitalRead(IR2_PIN) == LOW;
  bool disturbance = detectDisturbance();

  unsigned long now = millis();

  if ((ir1 || ir2 || disturbance) && (now - lastFired > COOLDOWN_MS)) {

    Serial.println("[TRIGGER]");

    lastFired = now;

    digitalWrite(LED_PIN, HIGH);
    sendTrigger();
    delay(200);
    digitalWrite(LED_PIN, LOW);
  }

  delay(50);
}