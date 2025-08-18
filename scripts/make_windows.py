#!/usr/bin/env python3
import pathlib, yaml, numpy as np, pandas as pd, json

ROOT = pathlib.Path(__file__).resolve().parents[1]

def clean_xy(X, y):
    # Replace NaN/Inf in X; drop samples where y is not finite
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
    mask = np.isfinite(y)
    if mask.sum() == 0:
        raise ValueError("All targets are NaN/Inf after windowing.")
    return X[mask], y[mask]

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

def load_aliases():
    path = ROOT / "schema" / "aliases.yaml"
    if path.exists():
        with open(path) as f:
            cfg = yaml.safe_load(f) or {}
        return cfg.get("aliases", {}) or {}
    return {}

def resolve_target_and_rename(df: pd.DataFrame, params, aliases) -> str:
    # 1) explicit target name from params.yaml
    tgt = params["training"]["target_col"]
    if tgt in df.columns:
        return tgt
    # 2) alias map under canonical key "target"
    for cand in (aliases.get("target") or []):
        if cand in df.columns:
            if "target" not in df.columns:
                df.rename(columns={cand: "target"}, inplace=True)
            return "target"
    # 3) fail with a helpful message
    raise KeyError(
        f"Target column not found. Looked for '{tgt}' and aliases {aliases.get('target')}. "
        f"Available columns: {list(df.columns)[:40]}{'...' if df.shape[1]>40 else ''}."
    )

def build_windows(df, target_col, window, horizon, stride):
    # ensure numeric columns only (except target which we access separately)
    num_cols = [c for c in df.columns if c != target_col and pd.api.types.is_numeric_dtype(df[c])]
    X = df[num_cols].values
    y = df[target_col].values
    n = len(df)
    samples, ys = [], []
    for start in range(0, n - window - horizon + 1, stride):
        end = start + window
        samples.append(X[start:end, :])
        ys.append(y[end + horizon - 1])
    return np.array(samples, dtype=np.float32), np.array(ys, dtype=np.float32), num_cols

def main():
    p = load_params()
    aliases = load_aliases()
    feats_dir = ROOT / p["data"]["features_dir"]

    df_tr = pd.read_parquet(feats_dir / "train.parquet")
    df_te = pd.read_parquet(feats_dir / "test.parquet")

    # Resolve / harmonise target in both splits
    target = resolve_target_and_rename(df_tr, p, aliases)
    if target not in df_te.columns:
        for cand in (aliases.get("target") or []):
            if cand in df_te.columns and target not in df_te.columns:
                df_te.rename(columns={cand: target}, inplace=True)
                break

    # time-ordered split of training into train/val
    n = len(df_tr)
    n_val = max(1, int(n * p["seq"]["val_frac"]))
    df_tr_core = df_tr.iloc[: n - n_val]
    df_val = df_tr.iloc[n - n_val : ]

    window = p["seq"]["window"]
    horizon = p["seq"]["horizon"]
    stride = p["seq"]["stride"]

    Xtr, ytr, xcols = build_windows(df_tr_core, target, window, horizon, stride)
    Xva, yva, _     = build_windows(df_val,      target, window, horizon, stride)
    Xte, yte, _     = build_windows(df_te,       target, window, horizon, stride)
    
    Xtr, ytr = clean_xy(Xtr, ytr)
    Xva, yva = clean_xy(Xva, yva)
    Xte, yte = clean_xy(Xte, yte)

    outd = ROOT / "data" / "windows"
    outd.mkdir(parents=True, exist_ok=True)
    np.save(outd / "X_train.npy", Xtr)
    np.save(outd / "y_train.npy", ytr)
    np.save(outd / "X_val.npy",   Xva)
    np.save(outd / "y_val.npy",   yva)
    np.save(outd / "X_test.npy",  Xte)
    np.save(outd / "y_test.npy",  yte)

    with open(outd / "manifest.json", "w") as f:
        json.dump(
            {"feature_order": xcols, "target": target, "window": window, "horizon": horizon},
            f, indent=2
        )

if __name__ == "__main__":
    main()
