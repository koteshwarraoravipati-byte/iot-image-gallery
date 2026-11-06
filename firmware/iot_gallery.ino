// AI-Thinker ESP32-CAM, Arduino ESP32 core 3.x.
// Button GPIO13 -> JPEG -> authenticated URL API -> private S3 HTTPS PUT.
#include "esp_camera.h"
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <time.h>
#include "config.h"

#define BUTTON_PIN 13
#define LED_PIN 12
unsigned long lastWifiAttempt = 0;
bool cameraReady = false;

void blinkError() {
  for (int i = 0; i < 3; i++) {
    digitalWrite(LED_PIN, HIGH); delay(150);
    digitalWrite(LED_PIN, LOW); delay(150);
  }
}

bool initCamera() {
  camera_config_t c = {}; // Zero all fields, including core-version extensions.
  c.ledc_channel = LEDC_CHANNEL_0; c.ledc_timer = LEDC_TIMER_0;
  c.pin_d0 = 5; c.pin_d1 = 18; c.pin_d2 = 19; c.pin_d3 = 21;
  c.pin_d4 = 36; c.pin_d5 = 39; c.pin_d6 = 34; c.pin_d7 = 35;
  c.pin_xclk = 0; c.pin_pclk = 22; c.pin_vsync = 25; c.pin_href = 23;
  c.pin_sccb_sda = 26; c.pin_sccb_scl = 27; c.pin_pwdn = 32; c.pin_reset = -1;
  c.xclk_freq_hz = 20000000; c.pixel_format = PIXFORMAT_JPEG;
  c.frame_size = psramFound() ? FRAMESIZE_SXGA : FRAMESIZE_VGA;
  c.jpeg_quality = 12; c.fb_count = 1;
  c.fb_location = psramFound() ? CAMERA_FB_IN_PSRAM : CAMERA_FB_IN_DRAM;
  c.grab_mode = CAMERA_GRAB_WHEN_EMPTY;
  return esp_camera_init(&c) == ESP_OK;
}

bool clockReady() {
  // TLS needs a credible clock. NTP is initialized at boot and syncs after WiFi.
  return time(nullptr) > 1735689600; // 2025-01-01, not a substitute for CA checks.
}

void captureAndUpload() {
  if (!cameraReady || WiFi.status() != WL_CONNECTED || !clockReady()) {
    Serial.println("Camera, WiFi or clock not ready"); blinkError(); return;
  }
  camera_fb_t* fb = esp_camera_fb_get();
  if (!fb) { Serial.println("Capture failed"); blinkError(); return; }
  WiFiClientSecure tls;
  tls.setCACert(AWS_ROOT_CA);
  HTTPClient http;
  http.setConnectTimeout(10000); http.setTimeout(15000);
  int code = -1;
  String url;
  if (http.begin(tls, PRESIGN_API)) {
    http.addHeader("X-Device-Secret", DEVICE_SECRET);
    http.addHeader("X-Image-Bytes", String((unsigned int)fb->len));
    code = http.POST("");
    if (code == 200) url = http.getString();
    http.end();
  }
  // Never log the secret or bearer URL. No automatic retry of expired URLs.
  if (code != 200 || !url.startsWith("https://")) {
    esp_camera_fb_return(fb); Serial.printf("URL API failed: %d\n", code); blinkError(); return;
  }
  tls.stop();
  HTTPClient upload;
  upload.setConnectTimeout(10000); upload.setTimeout(20000);
  code = -1;
  if (upload.begin(tls, url)) {
    upload.addHeader("Content-Type", "image/jpeg");
    code = upload.PUT(fb->buf, fb->len);
    upload.end();
  }
  esp_camera_fb_return(fb);
  Serial.printf("Upload HTTP %d\n", code);
  if (code == 200) { digitalWrite(LED_PIN, HIGH); delay(1000); digitalWrite(LED_PIN, LOW); }
  else blinkError();
}

void setup() {
  Serial.begin(115200);
  pinMode(LED_PIN, OUTPUT); digitalWrite(LED_PIN, LOW);
  pinMode(BUTTON_PIN, INPUT_PULLUP);
  cameraReady = initCamera();
  if (!cameraReady) Serial.println("Camera init failed; check wiring/board and reboot");
  WiFi.mode(WIFI_STA); WiFi.setAutoReconnect(true);
  WiFi.begin(WIFI_SSID, WIFI_PASS); lastWifiAttempt = millis();
  configTime(0, 0, "pool.ntp.org", "time.nist.gov");
}

void loop() {
  if (WiFi.status() != WL_CONNECTED && millis() - lastWifiAttempt >= 10000) {
    lastWifiAttempt = millis(); WiFi.disconnect(); WiFi.begin(WIFI_SSID, WIFI_PASS);
  }
  // Poll and debounce; no ISR races or millis() call from an interrupt.
  static int lastReading = HIGH, stable = HIGH;
  static unsigned long changedAt = 0;
  int reading = digitalRead(BUTTON_PIN);
  if (reading != lastReading) { changedAt = millis(); lastReading = reading; }
  if (millis() - changedAt >= 50 && reading != stable) {
    stable = reading;
    if (stable == LOW) captureAndUpload();
  }
  delay(10);
}
