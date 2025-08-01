#!/usr/bin/env python3
import sys, pathlib, pandas as pd

raw_dir, clean_dir = map(pathlib.Path, sys.argv[1:3])
clean_dir.mkdir(parents=True, exist_ok=True)

def tidy(df: pd.DataFrame) -> pd.DataFrame:
    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
    df = df.set_index('timestamp').sort_index()
    df = df.loc[~df.index.duplicated()]           # drop accidental dupes
    return df

for csv in raw_dir.rglob("*.csv"):
    df = tidy(pd.read_csv(csv))
    out = clean_dir / (csv.stem + ".parquet")
    df.to_parquet(out, index=True)
    print(f"Wrote {out} ({len(df)} rows)")
