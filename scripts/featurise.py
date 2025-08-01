#!/usr/bin/env python3
import sys, pathlib, pandas as pd, yaml

clean_dir, feat_dir = map(pathlib.Path, sys.argv[1:3])
params = yaml.safe_load(pathlib.Path("params.yaml").read_text())
feat_dir.mkdir(parents=True, exist_ok=True)

# collect every Parquet under data/clean/** recursively
parquets = list(clean_dir.rglob("*.parquet"))
if not parquets:
    raise RuntimeError(f"No Parquet files found in {clean_dir}")

df = pd.concat([pd.read_parquet(p) for p in parquets]).sort_index()
print("Rows after concat:", len(df))

df = df[~df.index.duplicated(keep="first")]
print("Rows after de-dup :", len(df))

# resample to regular 3-minute grid (optional but handy)
df = df.asfreq("3min")
print("Rows after asfreq :", len(df), "NAs:", df.isna().sum().sum())

# a) forward-fill small gaps in the *target* only (max 6 min)
df[params["target"]] = df[params["target"]].ffill(limit=2)

# b) remove rows where target is still missing
df = df.dropna(subset=[params["target"]])

print("Target column :", params["target"] in df.columns)
print("Non-NaN target:", df[params["target"]].notna().sum())

if params["target"] not in df.columns:
    raise RuntimeError(f"Target column '{params['target']}' not found. "
                       f"Available columns: {list(df.columns)[:10]} ...")

# c) create lag features exactly as before
for lag in params["features"]["lags"]:
    steps = int(lag * 60 / 3)
    df[f"lag_{lag}h"] = df[params["target"]].shift(steps)

# d) now drop rows that have NaNs in *target + lags* only
cols_to_check = [params["target"]] + [f"lag_{lag}h" for lag in params["features"]["lags"]]
df = df.dropna(subset=cols_to_check)

# # lag features
# for lag in params["features"]["lags"]:
#     steps = int(lag*60/3)          # hours → 3-min steps
#     df[f"lag_{lag}h"] = df[params["target"]].shift(steps)

# df = df.dropna()
# print("Rows after lag+dropna:", len(df))

# # time-based train / test split
# split = int(len(df) * (1 - params["data"]["test_size"]))
# train, test = df.iloc[:split], df.iloc[split:]

# train.to_parquet(feat_dir / "train.parquet")
# test.to_parquet(feat_dir / "test.parquet")
# print(f"Wrote {len(train)} train and {len(test)} test rows")
