#!/usr/bin/env python3
import json, sys, time, pathlib, joblib, warnings
from datetime import datetime
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error
from xgboost import XGBRegressor
import yaml

warnings.filterwarnings("ignore")
ROOT = pathlib.Path(__file__).resolve().parents[1]

def load_params():
    with open(ROOT / "params.yaml", "r") as f:
        p = yaml.safe_load(f)
    p.setdefault("data", {}).setdefault("features_dir", "data/features")
    p.setdefault("training", {}).setdefault("target_col", "target")
    p.setdefault("xgb", {}).setdefault("val_frac", 0.15)
    return p

def load_aliases():
    path = ROOT / "schema" / "aliases.yaml"
    if path.exists():
        with open(path) as f:
            cfg = yaml.safe_load(f) or {}
        return cfg.get("aliases", {}) or {}
    return {}

def resolve_target_and_rename(df: pd.DataFrame, params, aliases) -> str:
    # 1) prefer explicit target from params.yaml
    tgt = params["training"]["target_col"]
    if tgt in df.columns:
        return tgt
    # 2) try alias map: canonical "target" -> [candidates...]
    candidates = (aliases.get("target") or [])
    for cand in candidates:
        if cand in df.columns:
            # rename to canonical 'target' unless params points to another name
            if "target" not in df.columns:
                df.rename(columns={cand: "target"}, inplace=True)
            return "target"
    # 3) give a helpful error
    raise KeyError(
        f"Target column not found. Looked for '{tgt}' and aliases {candidates}. "
        f"Available columns: {list(df.columns)[:40]}{'...' if df.shape[1]>40 else ''}.\n"
        f"Fix by setting training.target_col in params.yaml OR adding a mapping under schema/aliases.yaml:\n"
        f"aliases:\n  target: ['<your_target_name_here>']"
    )

def time_ordered_val_split(df, target, val_frac):
    n = len(df)
    n_val = max(1, int(n * val_frac))
    tr = df.iloc[: n - n_val]
    va = df.iloc[n - n_val : ]
    X_tr, y_tr = tr.drop(columns=[target]), tr[target]
    X_va, y_va = va.drop(columns=[target]), va[target]
    return X_tr, y_tr, X_va, y_va

def evaluate(model, X, y):
    pred = model.predict(X)
    mae  = float(mean_absolute_error(y, pred))
    rmse = float(mean_squared_error(y, pred, squared=False))
    return mae, rmse

def main():
    params = load_params()
    aliases = load_aliases()
    feats_dir = ROOT / params["data"]["features_dir"]

    df_tr = pd.read_parquet(feats_dir / "train.parquet")
    df_te = pd.read_parquet(feats_dir / "test.parquet")

    # Resolve/rename target
    target = resolve_target_and_rename(df_tr, params, aliases)
    if target not in df_te.columns:
        # mirror the same rename in test if needed
        for cand in (aliases.get("target") or []):
            if cand in df_te.columns and target not in df_te.columns:
                df_te.rename(columns={cand: target}, inplace=True)
                break

    # Ensure numeric features (keep target even if non-numeric to error clearly later)
    nonnum_tr = [c for c in df_tr.columns if c != target and not pd.api.types.is_numeric_dtype(df_tr[c])]
    if nonnum_tr: df_tr = df_tr.drop(columns=nonnum_tr)
    nonnum_te = [c for c in df_te.columns if c != target and not pd.api.types.is_numeric_dtype(df_te[c])]
    if nonnum_te: df_te = df_te.drop(columns=nonnum_te)

    X_tr, y_tr, X_va, y_va = time_ordered_val_split(df_tr, target, params["xgb"]["val_frac"])
    X_te, y_te = df_te.drop(columns=[target]), df_te[target]

    xgbp = params["xgb"]
    model = XGBRegressor(
        tree_method=xgbp.get("tree_method","hist"),
        n_estimators=xgbp.get("n_estimators", 800),
        max_depth=xgbp.get("max_depth", 6),
        learning_rate=xgbp.get("learning_rate", 0.05),
        colsample_bytree=xgbp.get("colsample_bytree", 0.8),
        subsample=xgbp.get("subsample", 0.8),
        random_state=xgbp.get("random_state", 42),
        n_jobs=xgbp.get("n_jobs", -1),
        reg_lambda=xgbp.get("reg_lambda", 1.0),
        reg_alpha=xgbp.get("reg_alpha", 0.0),
    )

    eval_set=[(X_va, y_va)]
    model.fit(
        X_tr, y_tr,
        eval_set=eval_set,
        eval_metric=xgbp.get("eval_metric","rmse"),
        verbose=False,
        early_stopping_rounds=xgbp.get("early_stopping_rounds", 50),
    )

    feats = list(X_tr.columns)
    (ROOT / "models").mkdir(parents=True, exist_ok=True)
    (ROOT / "metrics").mkdir(parents=True, exist_ok=True)

    model_path = ROOT / "models" / "xgb.joblib"
    joblib.dump({"model": model, "feature_names": feats}, model_path)

    tr_mae, tr_rmse = evaluate(model, X_tr, y_tr)
    va_mae, va_rmse = evaluate(model, X_va, y_va)
    te_mae, te_rmse = evaluate(model, X_te, y_te)

    curves = model.evals_result() if hasattr(model, "evals_result") else {}

    metrics = {
        "model_type": "xgboost",
        "model_path": str(model_path.relative_to(ROOT)),
        "feature_names": feats,
        "schema_version": params.get("schema", {}).get("version", "unknown"),
        "trained_at": datetime.utcnow().isoformat() + "Z",
        "best_iteration": getattr(model, "best_iteration", None),
        "metrics": {
            "train": {"mae": tr_mae, "rmse": tr_rmse},
            "val":   {"mae": va_mae, "rmse": va_rmse},
            "test":  {"mae": te_mae, "rmse": te_rmse}
        },
        "curves": curves,
    }
    with open(ROOT / "metrics" / "xgb.json", "w") as f:
        json.dump(metrics, f, indent=2)

if __name__ == "__main__":
    sys.exit(main())
