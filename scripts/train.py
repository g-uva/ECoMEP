#!/usr/bin/env python3
import sys, pathlib, json, yaml, joblib, pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.ensemble import HistGradientBoostingRegressor

feat_dir, model_path = map(pathlib.Path, sys.argv[1:3])
params = yaml.safe_load(pathlib.Path("params.yaml").read_text())

train = pd.read_parquet(feat_dir / "train.parquet")
test  = pd.read_parquet(feat_dir / "test.parquet")

target = params["target"]
X_train, y_train = train.drop(columns=[target]), train[target]
X_test,  y_test  = test.drop(columns=[target]),  test[target]

reg = HistGradientBoostingRegressor(
    learning_rate=params["model"]["learning_rate"],
    max_depth=params["model"]["max_depth"],
    max_iter=params["model"]["n_estimators"]
)
reg.fit(X_train, y_train)

pred = reg.predict(X_test)
metrics = {
    "MAE":  mean_absolute_error(y_test, pred),
    "RMSE": mean_squared_error(y_test, pred, squared=False)
}

model_path.parent.mkdir(parents=True, exist_ok=True)
joblib.dump(reg, model_path)

metrics_path = pathlib.Path("metrics/metrics.json")
metrics_path.parent.mkdir(parents=True, exist_ok=True)
metrics_path.write_text(json.dumps(metrics, indent=2))
print(json.dumps(metrics, indent=2))
