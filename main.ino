#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <DHT.h>

// Cấu hình WiFi và MQTT
const char* ssid = "TEN_WIFI_CUA_BAN";
const char* password = "MAT_KHAU_WIFI";
const char* mqtt_server = "IP_MAY_TINH_CUA_BAN"; // Ví dụ: 192.168.1.100

// Cấu hình Cảm biến
#define DHTPIN 4
#define DHTTYPE DHT22
DHT dht(DHTPIN, DHTTYPE);
const int LDR_PIN = 34; // Chân Analog đọc ánh sáng

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
    if (client.connect("ESP32_Client")) {
      Serial.println("Connected to MQTT");
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

  // Đọc dữ liệu
  float h = dht.readHumidity();
  float t = dht.readTemperature();
  int ldr = analogRead(LDR_PIN);

  // Kiểm tra lỗi cảm biến
  if (isnan(h) || isnan(t)) {
    Serial.println("Lỗi đọc DHT!");
    delay(2000);
    return;
  }

  // Đóng gói JSON
  StaticJsonDocument<200> doc;
  doc["device_id"] = "ESP32_01";
  doc["temperature"] = t;
  doc["humidity"] = h;
  doc["light"] = ldr;

  char jsonBuffer[256];
  serializeJson(doc, jsonBuffer);

  // Publish lên MQTT
  client.publish("home/room1/sensors", jsonBuffer);
  Serial.println(jsonBuffer);

  delay(5000); // Gửi 5 giây 1 lần
}