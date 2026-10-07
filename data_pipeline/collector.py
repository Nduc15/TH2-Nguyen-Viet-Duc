import json
import paho.mqtt.client as mqtt
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from datetime import datetime

# Cấu hình InfluxDB
INFLUX_URL = "https://us-east-1-1.aws.cloud2.influxdata.com"
INFLUX_TOKEN = "i52ITEmQzgaWjXbo-MYXbCgY1k188esp-iEdl4e18x7gmb4B_uAeb3r80iplSrwWC2JcSbn9CrZ1nCv1HiGUtQ=="  # Copy Token từ giao diện web InfluxDB dán vào đây
ORG = "èq"
BUCKET = "iot_data"

influx_client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=ORG)
write_api = influx_client.write_api(write_options=SYNCHRONOUS)

# Cấu hình MQTT Công cộng
MQTT_BROKER = "broker.hivemq.com"
MQTT_TOPIC = "ptit/b23dcat054/sensors"

def on_connect(client, userdata, flags, rc):
    print(f"Connected to HiveMQ Broker with result code {rc}")
    client.subscribe(MQTT_TOPIC)

def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode('utf-8')
        data = json.loads(payload)
        
        if not all(k in data for k in ("temperature", "humidity", "light")):
            return

        point = Point("sensor_raw") \
            .tag("device_id", data.get("device_id", "unknown")) \
            .field("temperature", float(data["temperature"])) \
            .field("humidity", float(data["humidity"])) \
            .field("light", float(data["light"])) \
            .time(datetime.utcnow(), WritePrecision.NS)
            
        write_api.write(bucket=BUCKET, org=ORG, record=point)
        print(f"Saved: Temp={data['temperature']}, Hum={data['humidity']}")
        
    except Exception as e:
        pass # Bỏ qua lỗi nếu nhặt nhầm data không đúng định dạng của người khác

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect(MQTT_BROKER, 1883, 60)
client.loop_forever()