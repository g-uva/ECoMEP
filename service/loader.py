import json, joblib, numpy as np, pathlib, torch

ROOT = pathlib.Path(__file__).resolve().parents[1]

class SklearnPredictor:
    def __init__(self, bundle):
        self.model = bundle["model"]
        self.features = bundle.get("feature_names")
    def predict(self, row_dict):
        # pad/align columns
        import pandas as pd
        X = pd.DataFrame([row_dict])
        if self.features:
            for c in self.features:
                if c not in X: X[c] = 0.0
            X = X[self.features]
        return float(self.model.predict(X)[0])

class LSTMPredictor:
    def __init__(self, model_path):
        ckpt = torch.load(model_path, map_location="cpu")
        self.model = None
        self.state = ckpt
        self.in_features = ckpt["in_features"]
    def _build(self):
        from scripts.train_lstm import LSTMReg
        self.model = LSTMReg(self.in_features, 128, 2, 0.1)
        self.model.load_state_dict(self.state["state_dict"])
        self.model.eval()
    def predict(self, window_2d):
        # window_2d: [[feat...], ...] shape [timesteps, features]
        if self.model is None: self._build()
        x = torch.tensor([window_2d], dtype=torch.float32)
        with torch.no_grad():
            y = self.model(x).cpu().numpy()[0]
        return float(y)

def load_champion():
    champ = json.loads((ROOT/"models"/"champion.json").read_text())
    mtype = champ["model_type"]
    mpath = ROOT / champ["model_path"]
    if mtype in ("sklearn","xgboost"):
        bundle = joblib.load(mpath)
        return mtype, SklearnPredictor(bundle)
    elif mtype == "lstm":
        return mtype, LSTMPredictor(mpath)
    else:
        raise RuntimeError(f"Unsupported model_type: {mtype}")
