from pathlib import Path

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from train import FEATURES, MODEL_PATH

app = FastAPI(title="Land Value Predictor API", version="1.0.0")


class LandFeatures(BaseModel):
    acres: float = Field(gt=0)
    distance_to_city_miles: float = Field(ge=0)
    road_frontage_ft: float = Field(ge=0)
    zoning_score: int = Field(ge=1, le=5)
    utilities: int = Field(ge=0, le=1)


def load_model():
    if not MODEL_PATH.exists():
        raise HTTPException(status_code=503, detail="Model not trained. Run python train.py first.")
    return joblib.load(MODEL_PATH)


@app.get("/health")
def health():
    return {"status": "ok", "model_ready": MODEL_PATH.exists()}


@app.post("/predict")
def predict(payload: LandFeatures):
    model = load_model()
    row = pd.DataFrame([[getattr(payload, name) for name in FEATURES]], columns=FEATURES)
    prediction = float(model.predict(row)[0])
    return {
        "estimated_value": round(prediction, 2),
        "model": "random_forest_demo",
        "data_note": "synthetic-training-data demo; not an appraisal",
    }
