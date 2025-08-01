#!/usr/bin/env python3
import sys, pathlib, json, yaml, joblib, pandas as pd
from sklearn.pipeline import make_pipeline
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.ensemble import HistGradientBoostingRegressor

feat_dir, model_path = map(pathlib.Path, sys.argv[1:3])
p = yaml.safe_load(pathlib.Path("params.yaml").read_text())

train = pd.read_parquet(feat_dir / "train.parquet")
test  = pd.read_parquet(feat_dir / "test.parquet")

y_tr = train.pop(p["target"])
y_te = test.pop(p["target"])

pipe = make_pipeline(
    SimpleImputer(strategy="median"),
    HistGradientBoostingRegressor(
        max_iter=p["model"]["n_estimators"],
        max_depth=p["model"]["max_depth"],
        learning_rate=p["model"]["learning_rate"],
    )
)

pipe.fit(train, y_tr)
pred = pipe.predict(test)

metrics = {
    "MAE":  mean_absolute_error(y_te, pred),
    "RMSE": mean_squared_error(y_te, pred, squared=False)
}

model_path.parent.mkdir(parents=True, exist_ok=True)
joblib.dump(pipe, model_path)

metrics_path = pathlib.Path("metrics/metrics.json")
metrics_path.parent.mkdir(parents=True, exist_ok=True)
metrics_path.write_text(json.dumps(metrics, indent=2))
print(json.dumps(metrics, indent=2))
