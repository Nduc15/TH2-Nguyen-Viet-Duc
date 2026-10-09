#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <DHT.h>
#include <ArduinoJson.h>
#include <sys/time.h>

// ===== Cau hinh =====
const char* WIFI_SSID = "Wokwi-GUEST";   // mang WiFi gia lap cua Wokwi
const char* WIFI_PASS = "";
const char* MQTT_HOST = "broker.hivemq.com";
const int   MQTT_PORT = 1883;
const char* MQTT_TOPIC = "iot/b23dcat054/sensors";  // doi cho khop voi collector.py
const char* DEVICE_ID = "ESP32_01";
const unsigned long PUBLISH_MS = 2000;

#define DHT_PIN 15
#define LDR_PIN 34
DHT dht(DHT_PIN, DHT22);
WiFiClient wifiClient;
PubSubClient mqtt(wifiClient);

void connectWiFi() {
  WiFi.begin(WIFI_SSID, WIFI_PASS, 6);
  while (WiFi.status() != WL_CONNECTED) { delay(300); Serial.print("."); }
  Serial.println("\nWiFi OK");
  configTime(0, 0, "pool.ntp.org");
  while (time(nullptr) < 1700000000) { delay(200); Serial.print("t"); }  // cho dong bo gio
  Serial.println("\nNTP OK");
}
void connectMQTT() {
  while (!mqtt.connected()) {
    String cid = String("esp32-") + String(random(0xffff), HEX);
    if (mqtt.connect(cid.c_str())) Serial.println("MQTT OK");
    else { Serial.printf("MQTT fail rc=%d\n", mqtt.state()); delay(2000); }
  }
}

void setup() {
  Serial.begin(115200);
  dht.begin();
  mqtt.setServer(MQTT_HOST, MQTT_PORT);
  connectWiFi();
}

void loop() {
  if (!mqtt.connected()) connectMQTT();
  mqtt.loop();

  static unsigned long last = 0;
  if (millis() - last < PUBLISH_MS) return;
  last = millis();

  float t = dht.readTemperature();
  float h = dht.readHumidity();
  int ldr = analogRead(LDR_PIN);               // 0-4095
  int light = map(ldr, 0, 4095, 0, 100);       // % anh sang

  if (isnan(t) || isnan(h)) { Serial.println("Doc DHT22 loi, bo qua"); return; }

  struct timeval tv; gettimeofday(&tv, NULL);
  long long ts_ms = (long long)tv.tv_sec * 1000 + tv.tv_usec / 1000;

  StaticJsonDocument<200> doc;
  doc["device_id"] = DEVICE_ID;
  doc["temperature"] = t;
  doc["humidity"] = h;
  doc["light"] = light;
  doc["ts_publish_ms"] = ts_ms;                // collector dung de tinh do tre
  char buf[200];
  serializeJson(doc, buf);

  mqtt.publish(MQTT_TOPIC, buf);
  Serial.println(buf);
}