#!/usr/bin/env python3
import json, pathlib, math

ROOT = pathlib.Path(__file__).resolve().parents[1]

def load_metric(path):
    try:
        with open(path) as f:
            m = json.load(f)
        test = m.get("metrics", {}).get("test", {})
        mae = test.get("mae", math.inf)
        return {"file": path.name, "mae": mae, "model_path": m.get("model_path"), "model_type": m.get("model_type")}
    except Exception:
        return None

def main():
    metrics_dir = ROOT / "metrics"
    candidates = []
    for name in ["metrics.json","xgb.json","lstm.json"]:
        p = metrics_dir / name
        if p.exists():
            m = load_metric(p)
            if m: candidates.append(m)

    # Fallbacks for baseline if not embedded in metrics.json
    for c in candidates:
        if not c["model_path"] and c["file"] == "metrics.json":
            c["model_path"] = "models/baseline.joblib"
            c["model_type"] = "sklearn"

    if not candidates:
        raise SystemExit("No metrics found to select a champion.")

    champ = sorted(candidates, key=lambda x: (x["mae"], x["file"]))[0]
    out = {
        "champion_metrics_file": champ["file"],
        "model_type": champ["model_type"],
        "model_path": champ["model_path"]
    }
    (ROOT/"models").mkdir(exist_ok=True, parents=True)
    with open(ROOT/"models"/"champion.json", "w") as f:
        json.dump(out, f, indent=2)

    print(f"Champion: {out}")

if __name__ == "__main__":
    main()
