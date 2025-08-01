#!/usr/bin/env python3
import sys, pathlib, pandas as pd, yaml
from sklearn.model_selection import train_test_split

clean_dir, feat_dir = map(pathlib.Path, sys.argv[1:3])
params = yaml.safe_load(pathlib.Path("params.yaml").read_text())
feat_dir.mkdir(parents=True, exist_ok=True)

# 1. Concatenate all clean Parquets
df = pd.concat([pd.read_parquet(p) for p in clean_dir.glob("*.parquet")])
df = df.asfreq("3min")             # regularise to 3-minute grid

# 2. Generate lag features
for lag in params["features"]["lags"]:
    df[f"lag_{lag}h"] = df[params["target"]].shift(int(lag*60/3))  # 3 min step

df = df.dropna()

# 3. Train/test split by time
train_idx, test_idx = train_test_split(
    df.index, test_size=params["data"]["test_size"], shuffle=False
)
df.loc[train_idx].to_parquet(feat_dir / "train.parquet")
df.loc[test_idx].to_parquet(feat_dir / "test.parquet")
print(f"Saved features: {len(train_idx)} train / {len(test_idx)} test rows")
