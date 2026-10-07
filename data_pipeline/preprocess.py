from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
import pandas as pd

INFLUX_URL = "https://us-east-1-1.aws.cloud2.influxdata.com"
INFLUX_TOKEN = "i52ITEmQzgaWjXbo-MYXbCgY1k188esp-iEdl4e18x7gmb4B_uAeb3r80iplSrwWC2JcSbn9CrZ1nCv1HiGUtQ==" # Copy Token từ giao diện web InfluxDB dán vào đây
ORG = "èq"
BUCKET = "iot_data"

client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=ORG)
query_api = client.query_api()
write_api = client.write_api(write_options=SYNCHRONOUS)

def process_data():
    print("Bắt đầu tiền xử lý dữ liệu...")
    
    query = f"""
    from(bucket: "{BUCKET}")
      |> range(start: -1h)
      |> filter(fn: (r) => r["_measurement"] == "sensor_raw")
      |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
    """
    df = query_api.query_data_frame(query)
    
    if df.empty:
        print("Không có dữ liệu mới.")
        return

    df['_time'] = pd.to_datetime(df['_time'])
    df.set_index('_time', inplace=True)
    df = df[['temperature', 'humidity', 'light']]

    df.interpolate(method='linear', inplace=True)

    Q1 = df['temperature'].quantile(0.25)
    Q3 = df['temperature'].quantile(0.75)
    IQR = Q3 - Q1
    df = df[~((df['temperature'] < (Q1 - 1.5 * IQR)) | (df['temperature'] > (Q3 + 1.5 * IQR)))]

    df_resampled = df.resample('1T').mean().dropna()

    for index, row in df_resampled.iterrows():
        p = Point("sensor_processed") \
            .tag("device_id", "ESP32_01") \
            .field("temperature", float(row['temperature'])) \
            .field("humidity", float(row['humidity'])) \
            .field("light", float(row['light'])) \
            .time(index)
        write_api.write(bucket=BUCKET, org=ORG, record=p)
        
    print("Tiền xử lý hoàn tất!")

if __name__ == "__main__":
    process_data()