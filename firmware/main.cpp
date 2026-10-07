#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <DHT.h>

// Cấu hình WiFi
const char* ssid = "TEN_WIFI_CUA_BAN";
const char* password = "MAT_KHAU_WIFI";

// Cấu hình MQTT Công cộng
const char* mqtt_server = "broker.hivemq.com";
const char* mqtt_topic = "ptit/b23dcat054/sensors";

#define DHTPIN 4
#define DHTTYPE DHT22
DHT dht(DHTPIN, DHTTYPE);
const int LDR_PIN = 34;

WiFiClient espClient;
PubSubClient client(espClient);

void setup_wifi() {
  delay(10);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
  }
}

void reconnect() {
  while (!client.connected()) {
    if (client.connect("ESP32_B23DCAT054")) {
      Serial.println("Connected to HiveMQ");
    } else {
      delay(5000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  setup_wifi();
  client.setServer(mqtt_server, 1883);
  dht.begin();
}

void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();

  float h = dht.readHumidity();
  float t = dht.readTemperature();
  int ldr = analogRead(LDR_PIN);

  if (isnan(h) || isnan(t)) {
    Serial.println("Lỗi đọc DHT!");
    delay(2000);
    return;
  }

  StaticJsonDocument<200> doc;
  doc["device_id"] = "ESP32_01";
  doc["temperature"] = t;
  doc["humidity"] = h;
  doc["light"] = ldr;

  char jsonBuffer[256];
  serializeJson(doc, jsonBuffer);

  client.publish(mqtt_topic, jsonBuffer);
  Serial.println(jsonBuffer);

  delay(5000);
}