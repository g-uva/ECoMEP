#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd
import xgboost as xgb
import yaml


def read_params(path: Path) -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)


def smape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    denom = (np.abs(y_true) + np.abs(y_pred)) / 2.0
    denom = np.where(denom == 0, 1.0, denom)
    return float(np.mean(np.abs(y_true - y_pred) / denom))


def build_features(df: pd.DataFrame, target: str) -> (pd.DataFrame, np.ndarray):
    drop_cols = {target, "split", "window_start_ts", "window_end_ts"}
    X = df.drop(columns=[c for c in drop_cols if c in df.columns])
    X = pd.get_dummies(X, columns=["src_node", "dst_node"], drop_first=False)
    X = X.fillna(0)
    y = df[target].to_numpy()
    return X, y


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--params", default="params.yaml")
    args = ap.parse_args()

    params = read_params(Path(args.params))
    df = pd.read_parquet(Path(params["data"]["features_path"]))
    df.sort_values(["window_start_ts"], inplace=True)

    out_dir = Path("models/xgb")
    out_dir.mkdir(parents=True, exist_ok=True)
    metrics_dir = Path("reports/metrics")
    metrics_dir.mkdir(parents=True, exist_ok=True)

    xgb_params = params["xgb"]
    targets = ["sum_energy_Wh", "sum_duration_s"]
    metrics: Dict[str, Dict] = {}

    for target in targets:
        train_df = df[df["split"] == "train"]
        test_df = df[df["split"] == "test"]
        if len(train_df) < 10 or len(test_df) < 1:
            continue

        X_train, y_train = build_features(train_df, target)
        X_test, y_test = build_features(test_df, target)

        model = xgb.XGBRegressor(
            max_depth=int(xgb_params["max_depth"]),
            n_estimators=int(xgb_params["n_estimators"]),
            learning_rate=float(xgb_params["learning_rate"]),
            subsample=float(xgb_params["subsample"]),
            colsample_bytree=float(xgb_params["colsample_bytree"]),
            objective="reg:squarederror",
        )
        model.fit(X_train, y_train)
        preds = model.predict(X_test)

        mae = float(np.mean(np.abs(y_test - preds)))
        rmse = float(np.sqrt(np.mean((y_test - preds) ** 2)))
        metrics[target] = {
            "mae": mae,
            "rmse": rmse,
            "smape": smape(y_test, preds),
            "n_train": len(train_df),
            "n_test": len(test_df),
            "feature_names": list(X_train.columns),
        }

        model.save_model(out_dir / f"{target}.json")

    with open(metrics_dir / "xgb.json", "w") as f:
        json.dump(metrics, f, indent=2)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
