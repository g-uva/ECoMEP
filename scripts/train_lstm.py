#!/usr/bin/env python3
import json, pathlib, time, yaml
from datetime import datetime
import numpy as np
import torch
import torch.nn as nn
from sklearn.metrics import mean_absolute_error, mean_squared_error

ROOT = pathlib.Path(__file__).resolve().parents[1]
DEVICE = "cpu"

class LSTMReg(nn.Module):
    def __init__(self, in_features, hidden, layers, dropout):
        super().__init__()
        self.lstm = nn.LSTM(input_size=in_features, hidden_size=hidden, num_layers=layers, batch_first=True, dropout=dropout if layers>1 else 0.0)
        self.head = nn.Sequential(nn.Flatten(), nn.Linear(hidden, hidden//2), nn.ReLU(), nn.Linear(hidden//2, 1))
    def forward(self, x):
        out, _ = self.lstm(x)
        last = out[:, -1, :]         # [B, hidden]
        return self.head(last).squeeze(-1)

def load_params():
    with open(ROOT/"params.yaml") as f:
        p = yaml.safe_load(f)
    p.setdefault("seq", {})
    s = p["seq"]
    s.setdefault("epochs", 3)
    s.setdefault("batch_size", 128)
    s.setdefault("hidden_dim", 128)
    s.setdefault("num_layers", 2)
    s.setdefault("dropout", 0.1)
    s.setdefault("lr", 1e-3)
    s.setdefault("patience", 5)
    return p

def batches(X, y, bs, shuffle=True):
    idx = np.arange(len(X))
    if shuffle: np.random.shuffle(idx)
    for i in range(0, len(idx), bs):
        j = idx[i:i+bs]
        yield torch.tensor(X[j], dtype=torch.float32), torch.tensor(y[j], dtype=torch.float32)

def eval_metrics(model, X, y):
    with torch.no_grad():
        preds = []
        for xb, yb in batches(X, y, 4096, shuffle=False):
            preds.append(model(xb.to(DEVICE)).cpu().numpy())
        pred = np.concatenate(preds) if preds else np.array([])
    # Guard against any remaining NaNs/Infs
    mask = np.isfinite(y) & np.isfinite(pred)
    if mask.sum() == 0:
        return float("nan"), float("nan")
    y2, p2 = y[mask], pred[mask]
    from sklearn.metrics import mean_absolute_error
    # version-agnostic RMSE
    try:
        from sklearn.metrics import root_mean_squared_error
        rmse = float(root_mean_squared_error(y2, p2))
    except Exception:
        from sklearn.metrics import mean_squared_error
        rmse = float(np.sqrt(mean_squared_error(y2, p2)))
    mae  = float(mean_absolute_error(y2, p2))
    return mae, rmse

def main():
    p = load_params()
    win_dir = ROOT / "data" / "windows"
    Xtr = np.load(win_dir/"X_train.npy"); ytr = np.load(win_dir/"y_train.npy")
    Xva = np.load(win_dir/"X_val.npy");   yva = np.load(win_dir/"y_val.npy")
    Xte = np.load(win_dir/"X_test.npy");  yte = np.load(win_dir/"y_test.npy")
    
    def _clean(X, y):
        X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
        m = np.isfinite(y)
        return X[m], y[m]
    # Ensure that it cleans.
    Xtr, ytr = _clean(Xtr, ytr)
    Xva, yva = _clean(Xva, yva)
    Xte, yte = _clean(Xte, yte)

    in_features = Xtr.shape[-1]

    model = LSTMReg(in_features, p["seq"]["hidden_dim"], p["seq"]["num_layers"], p["seq"]["dropout"]).to(DEVICE)
    opt = torch.optim.Adam(model.parameters(), lr=p["seq"]["lr"])
    loss_fn = nn.MSELoss()

    best_va = float("inf"); best_state = None; history = {"epoch": [], "train_rmse": [], "val_rmse": []}
    patience = p["seq"]["patience"]; cooldown = 0

    for epoch in range(1, p["seq"]["epochs"]+1):
        model.train()
        for xb, yb in batches(Xtr, ytr, p["seq"]["batch_size"], shuffle=True):
            xb = torch.nan_to_num(xb, nan=0.0, posinf=0.0, neginf=0.0)
            xb, yb = xb.to(DEVICE), yb.to(DEVICE)
            pred = model(xb)
            loss = loss_fn(pred, yb)
            opt.zero_grad(); loss.backward(); opt.step()

        tr_mae, tr_rmse = eval_metrics(model, Xtr, ytr)
        va_mae, va_rmse = eval_metrics(model, Xva, yva)

        history["epoch"].append(epoch)
        history["train_rmse"].append(tr_rmse)
        history["val_rmse"].append(va_rmse)

        if va_rmse < best_va - 1e-6:
            best_va = va_rmse
            best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            cooldown = 0
        else:
            cooldown += 1
            if cooldown >= patience:
                break

    if best_state is not None:
        model.load_state_dict(best_state)

    te_mae, te_rmse = eval_metrics(model, Xte, yte)

    (ROOT/"models").mkdir(exist_ok=True, parents=True)
    (ROOT/"metrics").mkdir(exist_ok=True, parents=True)

    model_path = ROOT / "models" / "lstm.pt"
    torch.save({"state_dict": model.state_dict(),
                "in_features": in_features}, model_path)

    with open(win_dir/"manifest.json") as f:
        win_manifest = json.load(f)

    metrics = {
        "model_type": "lstm",
        "model_path": str(model_path.relative_to(ROOT)),
        "feature_names": win_manifest["feature_order"],
        "window": win_manifest["window"],
        "horizon": win_manifest["horizon"],
        "schema_version": p.get("schema", {}).get("version", "unknown"),
        "trained_at": datetime.utcnow().isoformat() + "Z",
        "metrics": {
            "train": {"mae": history["train_rmse"][-1]/1.253 if history["train_rmse"] else None, "rmse": history["train_rmse"][-1] if history["train_rmse"] else None},
            "val":   {"mae": None, "rmse": best_va},
            "test":  {"mae": te_mae, "rmse": te_rmse}
        },
        "curves": history
    }
    with open(ROOT/"metrics"/"lstm.json","w") as f:
        json.dump(metrics, f, indent=2)

if __name__ == "__main__":
    main()
