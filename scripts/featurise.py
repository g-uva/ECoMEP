#!/usr/bin/env python3
import sys, pathlib, pandas as pd, yaml

clean_dir, feat_dir = map(pathlib.Path, sys.argv[1:3])
params = yaml.safe_load(pathlib.Path("params.yaml").read_text())
feat_dir.mkdir(parents=True, exist_ok=True)

parquets = list(clean_dir.rglob("*.parquet"))
if not parquets:
    raise RuntimeError(f"No Parquet files found in {clean_dir}")

df = pd.concat([pd.read_parquet(p) for p in parquets]).sort_index()
df = df[~df.index.duplicated(keep="first")]
df = df.asfreq("3min")

col = params["target"]
df[col] = df[col].interpolate("time").ffill().bfill()

for lag in params["features"]["lags"]:
    steps = int(lag * 60 / 3)
    df[f"lag_{lag}h"] = df[col].shift(steps)

df = df.dropna(subset=[col])
df = df.select_dtypes("number")

split = int(len(df) * (1 - params["data"]["test_size"]))
train, test = df.iloc[:split], df.iloc[split:]

train.to_parquet(feat_dir / "train.parquet")
test.to_parquet(feat_dir / "test.parquet")
print(f"Wrote {len(train)} train and {len(test)} test rows")
