#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
from typing import List

import numpy as np
import pandas as pd
import pyarrow.dataset as ds
import yaml


def read_params(path: Path) -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)


def load_gold(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Gold path not found: {path}")
    fmt = "parquet"
    dataset = ds.dataset(path, format=fmt, partitioning="hive")
    table = dataset.to_table()
    df = table.to_pandas()
    return df


def add_lags_and_rollups(
    df: pd.DataFrame, group_cols: List[str], targets: List[str], max_lag: int, rolling: int
) -> pd.DataFrame:
    df = df.copy()
    df.sort_values(["window_start_ts"], inplace=True)
    for t in targets:
        for lag in range(1, max_lag + 1):
            df[f"{t}_lag_{lag}"] = df.groupby(group_cols)[t].shift(lag)
        if rolling > 0:
            df[f"{t}_roll_mean"] = (
                df.groupby(group_cols)[t].rolling(rolling, min_periods=1).mean().reset_index(level=group_cols, drop=True)
            )
            df[f"{t}_roll_std"] = (
                df.groupby(group_cols)[t].rolling(rolling, min_periods=1).std().reset_index(level=group_cols, drop=True)
            )
    return df


def assign_splits(df: pd.DataFrame, group_cols: List[str], fracs: dict) -> pd.DataFrame:
    df = df.copy()
    df["split"] = "test"
    for _, grp in df.groupby(group_cols, sort=False):
        n = len(grp)
        if n == 0:
            continue
        train_end = max(1, int(n * fracs["train"]))
        val_end = max(train_end, int(n * (fracs["train"] + fracs["val"])))
        if val_end >= n:
            val_end = n - 1 if n > 1 else n
        idx = grp.index.to_list()
        df.loc[idx[:train_end], "split"] = "train"
        df.loc[idx[train_end:val_end], "split"] = "val"
        df.loc[idx[val_end:], "split"] = "test"
    return df


def maybe_join_kpis(df: pd.DataFrame, kpi_path: Path) -> pd.DataFrame:
    if not kpi_path or not kpi_path.exists():
        return df
    kpi = pd.read_parquet(kpi_path)
    time_col = None
    for cand in ["window_start_ts", "timestamp", "ts"]:
        if cand in kpi.columns:
            time_col = cand
            break
    key_col = None
    for cand in ["site", "node", "src_node"]:
        if cand in kpi.columns:
            key_col = cand
            break
    if not time_col or not key_col:
        return df
    kpi[time_col] = pd.to_datetime(kpi[time_col])
    df = df.merge(
        kpi,
        left_on=["src_node", "window_start_ts"],
        right_on=[key_col, time_col],
        how="left",
        suffixes=("", "_kpi"),
    )
    df.drop(columns=[c for c in [key_col, time_col] if c in df.columns and c not in ["src_node", "window_start_ts"]], inplace=True, errors="ignore")
    return df


def build_features(params: dict) -> None:
    gold_path = Path(params["data"]["gold_path"])
    features_path = Path(params["data"]["features_path"])
    features_path.parent.mkdir(parents=True, exist_ok=True)

    df = load_gold(gold_path)
    df["window_start_ts"] = pd.to_datetime(df["window_start_ts"])
    df["window_end_ts"] = pd.to_datetime(df["window_end_ts"])
    df.sort_values(["src_node", "dst_node", "window_start_ts"], inplace=True)

    targets = ["sum_energy_Wh", "sum_duration_s"]
    df = add_lags_and_rollups(
        df,
        group_cols=["src_node", "dst_node"],
        targets=targets,
        max_lag=int(params["features"]["max_lag"]),
        rolling=int(params["features"]["rolling"]),
    )

    df["hour"] = df["window_start_ts"].dt.hour
    df["dow"] = df["window_start_ts"].dt.dayofweek
    df["month"] = df["window_start_ts"].dt.month

    kpi_path = Path(params.get("features", {}).get("kpi_path", ""))
    df = maybe_join_kpis(df, kpi_path)

    df = assign_splits(
        df,
        group_cols=["src_node", "dst_node"],
        fracs={
            "train": float(params["split"]["train_frac"]),
            "val": float(params["split"]["val_frac"]),
            "test": float(params["split"]["test_frac"]),
        },
    )

    df.to_parquet(features_path, index=False)


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--params", default="params.yaml", help="Path to params YAML.")
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    params = read_params(Path(args.params))
    build_features(params)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
