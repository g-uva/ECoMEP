#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict

import numpy as np
import pandas as pd
import statsmodels.api as sm
import yaml


def read_params(path: Path) -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)


def smape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    denom = (np.abs(y_true) + np.abs(y_pred)) / 2.0
    denom = np.where(denom == 0, 1.0, denom)
    return float(np.mean(np.abs(y_true - y_pred) / denom))


def train_series(y: pd.Series, order=(1, 0, 1)):
    model = sm.tsa.ARIMA(y, order=order)
    return model.fit()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--params", default="params.yaml")
    args = ap.parse_args()

    params = read_params(Path(args.params))
    features_path = Path(params["data"]["features_path"])
    df = pd.read_parquet(features_path)
    df.sort_values(["src_node", "dst_node", "window_start_ts"], inplace=True)

    out_dir = Path("models/arima")
    out_dir.mkdir(parents=True, exist_ok=True)
    metrics_dir = Path("reports/metrics")
    metrics_dir.mkdir(parents=True, exist_ok=True)

    order = tuple(params.get("arima", {}).get("order", (1, 0, 1)))
    targets = ["sum_energy_Wh", "sum_duration_s"]
    results: Dict[str, Dict] = {}

    for target in targets:
        target_dir = out_dir / target
        target_dir.mkdir(parents=True, exist_ok=True)
        results[target] = {}
        for (src, dst), grp in df.groupby(["src_node", "dst_node"]):
            train_mask = grp["split"].isin(["train", "val"])
            test_mask = grp["split"] == "test"
            if test_mask.sum() == 0 or train_mask.sum() < 3:
                continue
            y_train = grp.loc[train_mask, target]
            y_test = grp.loc[test_mask, target]

            try:
                fitted = train_series(y_train, order=order)
                forecast = fitted.forecast(steps=len(y_test))
            except Exception:
                continue

            y_true = y_test.to_numpy()
            y_pred = np.array(forecast)

            mae = float(np.mean(np.abs(y_true - y_pred)))
            rmse = float(np.sqrt(np.mean((y_true - y_pred) ** 2)))
            results[target][f"{src}_{dst}"] = {
                "mae": mae,
                "rmse": rmse,
                "smape": smape(y_true, y_pred),
            }

            model_path = target_dir / f"{src}_{dst}.pkl"
            fitted.save(model_path)

    metrics_path = metrics_dir / "arima.json"
    with open(metrics_path, "w") as f:
        json.dump(results, f, indent=2)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
