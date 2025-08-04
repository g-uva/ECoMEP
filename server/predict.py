#!/usr/bin/env python3
from pathlib import Path
from fastapi import FastAPI
from pydantic import BaseModel, Field
import pandas as pd
import joblib

model = joblib.load(Path("models/baseline.joblib"))
ALL_COLS = list(model.feature_names_in_)  # full column set

class Features(BaseModel):
    lag_1h: float = Field(..., example=0.42)
    lag_2h: float = Field(..., example=0.38)
    lag_3h: float = Field(..., example=0.35)
    lag_6h: float = Field(..., example=0.30)

app = FastAPI()

@app.post("/predict")
async def predict(f: Features):
    data = {c: None for c in ALL_COLS}   # start with full schema
    data.update(f.model_dump())          # overwrite supplied lags
    df = pd.DataFrame([data], columns=ALL_COLS)
    y_hat = model.predict(df)[0]
    return {"power_forecast": float(y_hat)}
