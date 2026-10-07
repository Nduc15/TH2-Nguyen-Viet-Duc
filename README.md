# Bài thực hành 2: Thu thập, Lưu trữ và Tiền xử lý dữ liệu IoT
**Môn học:** IoT và Ứng dụng (INT14149)

## 1. Cấu trúc thư mục
- `firmware/main.cpp`: Code ESP32 đọc cảm biến và gửi lên HiveMQ.
- `data_pipeline/collector.py`: Script subscribe dữ liệu MQTT và ghi vào InfluxDB cục bộ.
- `data_pipeline/preprocess.py`: Script làm sạch dữ liệu, khử nhiễu và resample.
- `app/app.py`: Web App giám sát dữ liệu bằng Streamlit.

## 2. Hướng dẫn chạy

**Bước 1: Khởi động Cơ sở dữ liệu InfluxDB**
- Chạy file `influxd.exe` đã tải về máy tính. 
- Mở trình duyệt vào `http://localhost:8086`, tạo tổ chức `myorg` và bucket `iot_data`.
- Lấy mã API Token dán vào các file Python.

**Bước 2: Cài đặt thư viện Python**
```bash
pip install -r requirements.txt