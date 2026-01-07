#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml


def load_json(path: Path):
    if not path.exists():
        return {}
    with open(path, "r") as f:
        return json.load(f)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--params", default="params.yaml")
    args = ap.parse_args()

    _ = yaml.safe_load(open(args.params))

    metrics_dir = Path("reports/metrics")
    metrics_dir.mkdir(parents=True, exist_ok=True)

    summary = {
        "arima": load_json(metrics_dir / "arima.json"),
        "xgb": load_json(metrics_dir / "xgb.json"),
        "lstm": load_json(metrics_dir / "lstm.json"),
    }

    with open(metrics_dir / "summary.json", "w") as f:
        json.dump(summary, f, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
