"""Tien xu ly: doc sensor_raw -> IQR -> resample -> noi suy -> dac trung -> chuan hoa -> sensor_processed."""
import argparse
import os
import time

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from influxdb_client import InfluxDBClient
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

FIELDS = ["temperature", "humidity", "light"]
FEATURE_FIELDS = ["temperature", "humidity"]

client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=ORG)
query_api = client.query_api()
write_api = client.write_api(write_options=SYNCHRONOUS)


def read_raw(time_range):
    flux = f'''
    from(bucket: "{BUCKET}")
      |> range(start: {time_range})
      |> filter(fn: (r) => r["_measurement"] == "sensor_raw")
      |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
    '''
    result = query_api.query_data_frame(flux)
    if isinstance(result, list):
        result = pd.concat(result, ignore_index=True) if result else pd.DataFrame()
    return result


def process_device(device_id, raw, freq):
    print(f"\n=== Thiet bi: {device_id} ===")
    df = raw.copy()
    df["_time"] = pd.to_datetime(df["_time"], utc=True)
    df = df.set_index("_time").sort_index()
    df = df.reindex(columns=FIELDS).astype(float)
    df = df[~df.index.duplicated(keep="last")]          # bo ban ghi trung timestamp
    print(f"Ban ghi raw: {len(df)}")

    # --- Phat hien outlier: IQR (loai) + Z-score (chi de doi chieu) ---
    for col in FIELDS:
        q1, q3 = df[col].quantile(0.25), df[col].quantile(0.75)
        iqr = q3 - q1
        mask = (df[col] < q1 - 1.5 * iqr) | (df[col] > q3 + 1.5 * iqr)
        with np.errstate(divide="ignore", invalid="ignore"):
            z = (df[col] - df[col].mean()) / df[col].std(ddof=0)
        print(f"  {col}: IQR phat hien {int(mask.sum())} outlier, "
              f"Z-score(|z|>3) phat hien {int((z.abs() > 3).sum())}")
        df.loc[mask, col] = np.nan                       # danh dau thieu, se noi suy sau

    # --- Resampling + xu ly gia tri thieu ---
    res = df.resample(freq).mean()
    missing_before = int(res.isna().sum().sum())
    res = res.interpolate(method="time", limit=5, limit_area="inside")
    missing_after = int(res.isna().sum().sum())
    print(f"Resample {freq}: {len(res)} cua so | o thieu: {missing_before} "
          f"-> sau noi suy con {missing_after}")
    res = res.dropna(how="all")

    # --- Dac trung: rolling mean, delta ---
    for col in FEATURE_FIELDS:
        res[f"{col}_roll3"] = res[col].rolling(3, min_periods=1).mean()
        res[f"{col}_delta"] = res[col].diff().fillna(0.0)

    # --- Chuan hoa min-max ---
    for col in FIELDS:
        lo, hi = res[col].min(), res[col].max()
        res[f"{col}_norm"] = (res[col] - lo) / (hi - lo) if hi > lo else 0.0

    res["device_id"] = device_id
    write_api.write(bucket=BUCKET, org=ORG, record=res,
                    data_frame_measurement_name="sensor_processed",
                    data_frame_tag_columns=["device_id"])
    print(f"Da ghi {len(res)} dong vao sensor_processed")
    return len(res)


def run(time_range, freq):
    print(f"Bat dau tien xu ly (range={time_range}, resample={freq})...")
    raw = read_raw(time_range)
    if raw.empty:
        print("Khong co du lieu trong khoang thoi gian nay.")
        return
    if "device_id" not in raw.columns:
        raw["device_id"] = "unknown"
    total = 0
    for device_id, group in raw.groupby("device_id"):
        total += process_device(str(device_id), group, freq)
    print(f"\nTien xu ly hoan tat! Tong {total} dong.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--range", default="-1h", help="vd: -30m, -1h, -24h")
    ap.add_argument("--freq", default="1min", help="cua so resample, vd: 30s, 1min, 5min")
    ap.add_argument("--every", type=int, default=0, help="chay lap lai moi N giay (0 = chay 1 lan)")
    args = ap.parse_args()
    try:
        run(args.range, args.freq)
        while args.every > 0:
            time.sleep(args.every)
            run(args.range, args.freq)
    except KeyboardInterrupt:
        print("\nDung.")
    finally:
        client.close()