#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset
import yaml


def read_params(path: Path) -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)


def smape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    denom = (np.abs(y_true) + np.abs(y_pred)) / 2.0
    denom = np.where(denom == 0, 1.0, denom)
    return float(np.mean(np.abs(y_true - y_pred) / denom))


class SeqDataset(Dataset):
    def __init__(self, series: np.ndarray, seq_len: int):
        self.seq_len = seq_len
        self.series = series
        self.samples = self._build_samples()

    def _build_samples(self) -> List[Tuple[np.ndarray, float]]:
        samples = []
        for i in range(len(self.series) - self.seq_len):
            x = self.series[i : i + self.seq_len]
            y = self.series[i + self.seq_len]
            samples.append((x.astype(np.float32), float(y)))
        return samples

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        x, y = self.samples[idx]
        return torch.tensor(x).unsqueeze(-1), torch.tensor(y)


class LSTMReg(nn.Module):
    def __init__(self, input_size: int, hidden_size: int, num_layers: int):
        super().__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers=num_layers, batch_first=True)
        self.head = nn.Linear(hidden_size, 1)

    def forward(self, x):
        out, _ = self.lstm(x)
        out = out[:, -1, :]
        return self.head(out).squeeze(-1)


def train_model(model, loader, val_loader, epochs, lr, device):
    model.to(device)
    optim = torch.optim.Adam(model.parameters(), lr=lr)
    loss_fn = nn.MSELoss()
    for _ in range(epochs):
        model.train()
        for xb, yb in loader:
            xb, yb = xb.to(device), yb.to(device)
            optim.zero_grad()
            pred = model(xb)
            loss = loss_fn(pred, yb)
            loss.backward()
            optim.step()
        if val_loader:
            model.eval()
            with torch.no_grad():
                for xb, yb in val_loader:
                    xb, yb = xb.to(device), yb.to(device)
                    loss_fn(model(xb), yb)
    return model


def to_sequences(series: pd.Series, seq_len: int):
    ds = SeqDataset(series.to_numpy(), seq_len=seq_len)
    return ds


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--params", default="params.yaml")
    args = ap.parse_args()

    params = read_params(Path(args.params))
    df = pd.read_parquet(Path(params["data"]["features_path"]))
    df.sort_values(["src_node", "dst_node", "window_start_ts"], inplace=True)

    out_dir = Path("models/lstm")
    out_dir.mkdir(parents=True, exist_ok=True)
    metrics_dir = Path("reports/metrics")
    metrics_dir.mkdir(parents=True, exist_ok=True)

    cfg = params["lstm"]
    seq_len = int(cfg["seq_len"])
    device = "cuda" if torch.cuda.is_available() else "cpu"

    metrics: Dict[str, Dict] = {}
    targets = ["sum_energy_Wh", "sum_duration_s"]

    for target in targets:
        target_dir = out_dir / target
        target_dir.mkdir(parents=True, exist_ok=True)
        metrics[target] = {}

        for (src, dst), grp in df.groupby(["src_node", "dst_node"]):
            train_vals = grp[grp["split"] == "train"][target]
            val_vals = grp[grp["split"] == "val"][target]
            test_vals = grp[grp["split"] == "test"][target]

            if len(train_vals) <= seq_len or len(test_vals) == 0:
                continue

            train_ds = to_sequences(train_vals, seq_len)
            val_ds = to_sequences(val_vals, seq_len) if len(val_vals) > seq_len else None
            test_ds = to_sequences(test_vals, seq_len)

            train_loader = DataLoader(train_ds, batch_size=int(cfg["batch_size"]), shuffle=True)
            val_loader = DataLoader(val_ds, batch_size=int(cfg["batch_size"]), shuffle=False) if val_ds else None
            test_loader = DataLoader(test_ds, batch_size=int(cfg["batch_size"]), shuffle=False)

            model = LSTMReg(input_size=1, hidden_size=int(cfg["hidden_size"]), num_layers=int(cfg["num_layers"]))
            model = train_model(model, train_loader, val_loader, epochs=int(cfg["epochs"]), lr=float(cfg["lr"]), device=device)

            preds, truth = [], []
            model.eval()
            with torch.no_grad():
                for xb, yb in test_loader:
                    xb = xb.to(device)
                    out = model(xb).cpu().numpy()
                    preds.extend(out.tolist())
                    truth.extend(yb.numpy().tolist())

            y_true = np.array(truth)
            y_pred = np.array(preds)[: len(y_true)]
            mae = float(np.mean(np.abs(y_true - y_pred)))
            rmse = float(np.sqrt(np.mean((y_true - y_pred) ** 2)))
            metrics[target][f"{src}_{dst}"] = {
                "mae": mae,
                "rmse": rmse,
                "smape": smape(y_true, y_pred),
            }

            torch.save(
                {"model_state": model.state_dict(), "seq_len": seq_len},
                target_dir / f"{src}_{dst}.pt",
            )

    with open(metrics_dir / "lstm.json", "w") as f:
        json.dump(metrics, f, indent=2)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
