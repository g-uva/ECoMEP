#!/usr/bin/env python3
"""
Creates a dummy (empty) features file so DVC can track an output.
Replace with real feature-engineering later.
"""

import sys, pathlib, json, pandas as pd

src = pathlib.Path(sys.argv[1])      # data/clean
dst = pathlib.Path(sys.argv[2])      # data/features
dst.mkdir(parents=True, exist_ok=True)

# For now: concatenate all CSVs into one small Parquet
frames = [pd.read_csv(f) for f in src.glob("*.csv")]
pd.concat(frames).to_parquet(dst / "features.parquet")
print(f"Wrote {dst/'features.parquet'} with {len(frames)} chunks")
