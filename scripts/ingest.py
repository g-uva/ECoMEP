#!/usr/bin/env python3
"""
Robust ingest: copy every CSV from data/raw/** → data/clean/**
and make sure the index is a proper UTC datetime.
"""

import sys, pathlib, pandas as pd

raw_dir, clean_dir = map(pathlib.Path, sys.argv[1:3])
clean_dir.mkdir(parents=True, exist_ok=True)

CANDIDATES = ["timestamp", "time", "datetime", "date", "ts",
              "Timestamp", "Date", "TIMESTAMP"]

def tidy(csv_path: pathlib.Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)

    ts_col = next((c for c in CANDIDATES if c in df.columns), df.columns[0])

    df[ts_col] = pd.to_datetime(df[ts_col], utc=True, errors="coerce")
    df = df.dropna(subset=[ts_col]).set_index(ts_col).sort_index()
    df = df.loc[~df.index.duplicated(keep="first")]
    return df

for src in raw_dir.rglob("*.csv"):
    df = tidy(src)

    # preserve sub-folder structure
    rel    = src.relative_to(raw_dir).with_suffix(".parquet")
    dst    = clean_dir / rel
    dst.parent.mkdir(parents=True, exist_ok=True)

    df.to_parquet(dst)
    print(f"✔︎ {dst}   rows={len(df)}")

print("Ingestion completed.")
