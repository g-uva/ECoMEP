#!/usr/bin/env python3
import pathlib, yaml, numpy as np, pandas as pd, json

ROOT = pathlib.Path(__file__).resolve().parents[1]

def load_params():
    with open(ROOT/"params.yaml") as f:
        p = yaml.safe_load(f)
    p.setdefault("data", {}).setdefault("features_dir", "data/features")
    p.setdefault("training", {}).setdefault("target_col", "target")
    p.setdefault("seq", {}).setdefault("window", 60)
    p["seq"].setdefault("horizon", 1)
    p["seq"].setdefault("stride", 1)
    p["seq"].setdefault("val_frac", 0.15)
    return p

def build_windows(df, target_col, window, horizon, stride):
    # assume df is time-ordered; use numeric columns
    cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    if target_col not in cols: cols = cols + [target_col]
    Xcols = [c for c in cols if c != target_col]
    X = df[Xcols].values
    y = df[target_col].values
    n = len(df)
    samples = []
    ys = []
    for start in range(0, n - window - horizon + 1, stride):
        end = start + window
        samples.append(X[start:end, :])
        ys.append(y[end + horizon - 1])
    return np.array(samples, dtype=np.float32), np.array(ys, dtype=np.float32), Xcols

def main():
    p = load_params()
    feats_dir = ROOT / p["data"]["features_dir"]
    target = p["training"]["target_col"]
    window = p["seq"]["window"]
    horizon = p["seq"]["horizon"]
    stride = p["seq"]["stride"]

    df_tr = pd.read_parquet(feats_dir / "train.parquet")
    df_te = pd.read_parquet(feats_dir / "test.parquet")

    # Split training further into train/val (tail for val)
    n = len(df_tr)
    n_val = max(1, int(n * p["seq"]["val_frac"]))
    df_tr_core = df_tr.iloc[: n - n_val]
    df_val = df_tr.iloc[n - n_val : ]

    Xtr, ytr, xcols = build_windows(df_tr_core, target, window, horizon, stride)
    Xva, yva, _     = build_windows(df_val,      target, window, horizon, stride)
    Xte, yte, _     = build_windows(df_te,       target, window, horizon, stride)

    outd = ROOT / "data" / "windows"
    outd.mkdir(parents=True, exist_ok=True)
    np.save(outd / "X_train.npy", Xtr)
    np.save(outd / "y_train.npy", ytr)
    np.save(outd / "X_val.npy",   Xva)
    np.save(outd / "y_val.npy",   yva)
    np.save(outd / "X_test.npy",  Xte)
    np.save(outd / "y_test.npy",  yte)

    with open(outd / "manifest.json", "w") as f:
        json.dump({"feature_order": xcols, "target": target, "window": window, "horizon": horizon}, f, indent=2)

if __name__ == "__main__":
    main()
