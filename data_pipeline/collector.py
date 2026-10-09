"""Collector: subscribe MQTT -> validate -> ghi InfluxDB (sensor_raw) + do do tre."""
import json
import math
import os
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt
from dotenv import load_dotenv
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

load_dotenv()


def env(name, default=None):
    value = os.getenv(name, default)
    if value is None:
        raise SystemExit(f"Thieu bien moi truong {name}. Hay tao file .env (xem .env.example)")
    return value


INFLUX_URL = env("INFLUX_URL")
INFLUX_TOKEN = env("INFLUX_TOKEN")
ORG = env("INFLUX_ORG")
BUCKET = env("INFLUX_BUCKET", "iot_data")
MQTT_BROKER = env("MQTT_BROKER", "broker.hivemq.com")
MQTT_PORT = int(env("MQTT_PORT", "1883"))
MQTT_TOPIC = env("MQTT_TOPIC", "iot/b23dcat054/sensors")

# Khoang gia tri vat ly hop le cua cam bien (khong phai nguong outlier)
LIMITS = {"temperature": (-40.0, 80.0), "humidity": (0.0, 100.0), "light": (0.0, 100.0)}
MAX_CLOCK_DIFF_MS = 24 * 3600 * 1000  # lech qua 1 ngay thi coi timestamp thiet bi la sai

influx_client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=ORG)
write_api = influx_client.write_api(write_options=SYNCHRONOUS)

stats = {"received": 0, "saved": 0, "invalid": 0, "write_errors": 0}
lat_mqtt, lat_db = [], []


def validate(data):
    """Tra ve dict {field: float} neu hop le, nguoc lai None."""
    if not isinstance(data, dict):
        return None
    values = {}
    for key, (lo, hi) in LIMITS.items():
        v = data.get(key)
        if isinstance(v, bool) or not isinstance(v, (int, float)) or math.isnan(v):
            return None
        if not lo <= v <= hi:
            return None
        values[key] = float(v)
    return values


def summarize(name, arr):
    s = sorted(arr)
    p95 = s[int(0.95 * (len(s) - 1))]
    print(f"  {name}: n={len(s)} min={s[0]:.0f} mean={sum(s)/len(s):.0f} "
          f"p95={p95:.0f} max={s[-1]:.0f} (ms)")


def print_stats():
    print(f"[STATS] {stats}")
    if lat_mqtt:
        summarize("Do tre MQTT (thiet bi -> collector)", lat_mqtt)
        summarize("Do tre end-to-end (thiet bi -> InfluxDB)", lat_db)


def on_connect(client, userdata, flags, rc):
    print(f"Connected to broker, rc={rc}")
    client.subscribe(MQTT_TOPIC)  # subscribe lai moi khi tu dong ket noi lai
    print(f"Subscribed: {MQTT_TOPIC}")


def on_message(client, userdata, msg):
    recv_ms = time.time() * 1000
    stats["received"] += 1
    try:
        data = json.loads(msg.payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        stats["invalid"] += 1
        return

    values = validate(data)
    if values is None:
        stats["invalid"] += 1
        print(f"Bo qua ban tin khong hop le: {msg.payload[:80]!r}")
        return

    device_id = str(data.get("device_id", "unknown"))
    ts_pub = data.get("ts_publish_ms")
    has_ts = isinstance(ts_pub, (int, float)) and abs(recv_ms - ts_pub) < MAX_CLOCK_DIFF_MS
    # Dung timestamp cua thiet bi lam thoi gian do -> ban tin gui lai se ghi de, khong bi trung
    event_time = (datetime.fromtimestamp(ts_pub / 1000, tz=timezone.utc)
                  if has_ts else datetime.now(timezone.utc))

    point = Point("sensor_raw").tag("device_id", device_id).time(event_time, WritePrecision.MS)
    for k, v in values.items():
        point.field(k, v)

    try:
        write_api.write(bucket=BUCKET, org=ORG, record=point)
    except Exception as e:
        stats["write_errors"] += 1
        print(f"Loi ghi InfluxDB: {e}")
        return

    stats["saved"] += 1
    print(f"Saved [{device_id}]: Temp={values['temperature']}, "
          f"Hum={values['humidity']}, Light={values['light']}")

    if has_ts:
        done_ms = time.time() * 1000
        mqtt_ms, db_ms = recv_ms - ts_pub, done_ms - ts_pub
        lat_mqtt.append(mqtt_ms)
        lat_db.append(db_ms)
        try:
            lp = (Point("pipeline_latency").tag("device_id", device_id)
                  .field("mqtt_ms", float(mqtt_ms)).field("e2e_ms", float(db_ms))
                  .time(event_time, WritePrecision.MS))
            write_api.write(bucket=BUCKET, org=ORG, record=lp)
        except Exception as e:
            print(f"Loi ghi do tre: {e}")
        if len(lat_db) % 20 == 0:
            print_stats()


try:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)  # paho-mqtt >= 2.0
except AttributeError:
    client = mqtt.Client()                                   # paho-mqtt 1.x
client.on_connect = on_connect
client.on_message = on_message
client.reconnect_delay_set(min_delay=1, max_delay=30)

if __name__ == "__main__":
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_forever(retry_first_connection=True)  # tu ket noi lai khi mat mang
    except KeyboardInterrupt:
        print("\nDung collector.")
        print_stats()
    finally:
        client.disconnect()
        influx_client.close()