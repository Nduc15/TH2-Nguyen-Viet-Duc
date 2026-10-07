import paho.mqtt.client as mqtt
import time, json, random

MQTT_BROKER = "broker.hivemq.com"
MQTT_TOPIC = "ptit/b23dcat054/sensors"

client = mqtt.Client()
client.connect(MQTT_BROKER, 1883, 60)
print("Đã kết nối HiveMQ. Bắt đầu gửi dữ liệu giả lập...")

while True:
    data = {
        "device_id": "ESP32_SIMULATOR",
        "temperature": round(random.uniform(20.0, 35.0), 1),
        "humidity": round(random.uniform(50.0, 80.0), 1),
        "light": random.randint(100, 1024)
    }
    client.publish(MQTT_TOPIC, json.dumps(data))
    print(f"Đã gửi: {data}")
    time.sleep(5) # Gửi 5 giây 1 lần