#!/usr/bin/env python3
import sys, pathlib, json, yaml, joblib, pandas as pd
from sklearn.metrics import mean_absolute_error, root_mean_squared_error
from sklearn.ensemble import GradientBoostingRegressor

feat_dir, model_path = map(pathlib.Path, sys.argv[1:3])
params = yaml.safe_load(pathlib.Path("params.yaml").read_text())

train = pd.read_parquet(feat_dir / "train.parquet")
test  = pd.read_parquet(feat_dir / "test.parquet")
y_train = train[params["target"]]
y_test  = test[params["target"]]
X_train = train.drop(columns=[params["target"]])
X_test  = test.drop(columns=[params["target"]])

reg = GradientBoostingRegressor(
    n_estimators=params["model"]["n_estimators"],
    max_depth=params["model"]["max_depth"],
    learning_rate=params["model"]["learning_rate"],
)
reg.fit(X_train, y_train)

pred = reg.predict(X_test)
metrics = {
    "MAE": mean_absolute_error(y_test, pred),
    "RMSE": root_mean_squared_error(y_test, pred, squared=False),
}
metrics_path = pathlib.Path("metrics/metrics.json")
metrics_path.parent.mkdir(parents=True, exist_ok=True)
metrics_path.write_text(json.dumps(metrics, indent=2))
# feat_dir.joinpath("metrics.json").write_text(json.dumps(metrics, indent=2))

model_path.parent.mkdir(parents=True, exist_ok=True)
joblib.dump(reg, model_path)
print(f"Model → {model_path}; metrics → {feat_dir/'metrics.json'}")
