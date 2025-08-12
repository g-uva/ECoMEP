#!/usr/bin/env python3
"""
ingest.py

Modes:
  1) files:  copy every CSV from RAW_DIR/** -> CLEAN_DIR/** as Parquet
             (keeps a proper UTC datetime index)
  2) kafka:  publish NDJSON (or CSV) records to a Kafka topic (to emulate streaming)

Examples:
  python ingest.py files data/raw data/clean
  python ingest.py kafka --input synthetic_metrics.ndjson --bootstrap kafka:9092 --topic metrics.raw.batch
  # if your synthetic data is CSV:
  python ingest.py kafka --input data/raw/metrics.csv --bootstrap kafka:9092 --topic metrics.raw.batch --csv
"""

import sys, argparse, json, pathlib, pandas as pd
from datetime import timezone
from typing import Iterable, Dict, Any

# ---------- common ----------
CANDIDATES = ["timestamp", "time", "datetime", "date", "ts",
              "Timestamp", "Date", "TIMESTAMP"]

def tidy_csv_to_parquet(src_csv: pathlib.Path, dst_parquet: pathlib.Path) -> int:
    df = pd.read_csv(src_csv)
    ts_col = next((c for c in CANDIDATES if c in df.columns), df.columns[0])
    df[ts_col] = pd.to_datetime(df[ts_col], utc=True, errors="coerce")
    df = df.dropna(subset=[ts_col]).set_index(ts_col).sort_index()
    df = df.loc[~df.index.duplicated(keep="first")]
    dst_parquet.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(dst_parquet)
    return len(df)

# ---------- kafka mode ----------
def _iter_ndjson(path: pathlib.Path) -> Iterable[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line: continue
            yield json.loads(line)

def _iter_csv(path: pathlib.Path) -> Iterable[Dict[str, Any]]:
    df = pd.read_csv(path)
    for _, row in df.iterrows():
        yield dict(row)

def publish_to_kafka(input_path: pathlib.Path, bootstrap: str, topic: str, is_csv: bool):
    from kafka import KafkaProducer
    producer = KafkaProducer(
        bootstrap_servers=bootstrap.split(","),
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        key_serializer=lambda k: (k or "").encode("utf-8"),
        linger_ms=50,
    )
    it = _iter_csv(input_path) if is_csv else _iter_ndjson(input_path)
    n = 0
    for rec in it:
        # derive a stable key for partitioning/compaction later
        device = rec.get("device_id") or rec.get("NodeID") or "unknown-device"
        metric = rec.get("metric_type") or "power_w"
        key = f"{device}:{metric}"
        producer.send(topic, value=rec, key=key)
        n += 1
        if n % 1000 == 0:
            producer.flush()
    producer.flush()
    print(f"Published {n} records to {topic} via {bootstrap}")

# ---------- cli ----------
def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="mode", required=True)

    sp_files = sub.add_parser("files", help="CSV -> Parquet")
    sp_files.add_argument("raw_dir", type=pathlib.Path)
    sp_files.add_argument("clean_dir", type=pathlib.Path)

    sp_kafka = sub.add_parser("kafka", help="Publish NDJSON/CSV to Kafka")
    sp_kafka.add_argument("--input", required=True, type=pathlib.Path, help="NDJSON or CSV file")
    sp_kafka.add_argument("--bootstrap", default="kafka:9092")
    sp_kafka.add_argument("--topic", default="metrics.raw.batch")
    sp_kafka.add_argument("--csv", action="store_true", help="Treat input as CSV instead of NDJSON")

    args = ap.parse_args()

    if args.mode == "files":
        raw_dir, clean_dir = args.raw_dir, args.clean_dir
        clean_dir.mkdir(parents=True, exist_ok=True)
        total = 0
        for src in raw_dir.rglob("*.csv"):
            rel = src.relative_to(raw_dir).with_suffix(".parquet")
            dst = clean_dir / rel
            rows = tidy_csv_to_parquet(src, dst)
            total += rows
            print(f"{dst}   rows={rows}")
        print(f"Ingestion completed. total_rows={total}")
    else:
        publish_to_kafka(args.input, args.bootstrap, args.topic, args.csv)

if __name__ == "__main__":
    main()
