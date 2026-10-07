import streamlit as st
import pandas as pd
import plotly.express as px
from influxdb_client import InfluxDBClient

INFLUX_URL = "https://us-east-1-1.aws.cloud2.influxdata.com"
INFLUX_TOKEN = "i52ITEmQzgaWjXbo-MYXbCgY1k188esp-iEdl4e18x7gmb4B_uAeb3r80iplSrwWC2JcSbn9CrZ1nCv1HiGUtQ==" # Copy Token từ giao diện web InfluxDB dán vào đây
ORG = "èq"
BUCKET = "iot_data"

client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=ORG)

st.set_page_config(page_title="IoT Data Dashboard", layout="wide")
st.title("📊 Hệ thống giám sát cảm biến IoT Real-time")

def get_data(measurement):
    query = f"""
    from(bucket: "{BUCKET}")
      |> range(start: -1h)
      |> filter(fn: (r) => r["_measurement"] == "{measurement}")
      |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
    """
    df = client.query_api().query_data_frame(query)
    if not df.empty:
        if isinstance(df, list):
            df = pd.concat(df)
        df['_time'] = pd.to_datetime(df['_time'])
        df = df.sort_values(by="_time")
    return df

col1, col2 = st.columns(2)

with col1:
    st.subheader("Dữ liệu thô (Raw Data)")
    df_raw = get_data("sensor_raw")
    if not df_raw.empty:
        fig1 = px.line(df_raw, x='_time', y=['temperature', 'humidity'], title='Nhiệt độ & Độ ẩm (Raw)')
        st.plotly_chart(fig1, use_container_width=True)
    else:
        st.info("Chưa có dữ liệu thô.")

with col2:
    st.subheader("Dữ liệu đã xử lý (Processed Data)")
    df_processed = get_data("sensor_processed")
    if not df_processed.empty:
        fig2 = px.line(df_processed, x='_time', y=['temperature', 'humidity'], title='Nhiệt độ & Độ ẩm (Cleaned & Resampled)')
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Chưa có dữ liệu đã tiền xử lý. Hãy chạy file preprocess.py")