"""Train a first real-data Peoria County valuation baseline.

This model is intentionally separate from the demo API model. It uses a chronological
holdout so newer sales are evaluated against models trained on older sales.
"""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from real_data import prepare_peoria_sales

INPUT = Path("data/official/peoria_parcel_sales.csv")
OUT_DIR = Path("artifacts/peoria_baseline")
MODEL_PATH = OUT_DIR / "model.joblib"
METRICS_PATH = OUT_DIR / "metrics.json"

NUMERIC = ["acres", "land_lot_value", "total_assessed_value", "sale_year"]
CATEGORICAL = ["property_class", "city", "zip_code"]
TARGET = "sale_price"


def chronological_split(df: pd.DataFrame, holdout_fraction: float = 0.2):
    if len(df) < 20:
        raise ValueError("Need at least 20 clean Peoria sales for a meaningful baseline split.")
    ordered = df.sort_values("sale_date").reset_index(drop=True)
    split = max(1, int(len(ordered) * (1 - holdout_fraction)))
    return ordered.iloc[:split].copy(), ordered.iloc[split:].copy()


def build_pipeline() -> Pipeline:
    prep = ColumnTransformer(
        [
            ("num", "passthrough", NUMERIC),
            ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL),
        ]
    )
    model = RandomForestRegressor(
        n_estimators=350,
        random_state=42,
        min_samples_leaf=3,
        n_jobs=-1,
    )
    return Pipeline([("prep", prep), ("model", model)])


def main() -> None:
    if not INPUT.exists():
        raise SystemExit(
            "Official Peoria data not found. Run `python scripts/fetch_peoria_data.py` first."
        )

    raw = pd.read_csv(INPUT)
    df = prepare_peoria_sales(raw)
    train, test = chronological_split(df)

    pipeline = build_pipeline()
    pipeline.fit(train[NUMERIC + CATEGORICAL], train[TARGET])
    pred = pipeline.predict(test[NUMERIC + CATEGORICAL])

    mae = float(mean_absolute_error(test[TARGET], pred))
    r2 = float(r2_score(test[TARGET], pred)) if len(test) > 1 else None
    median_price = float(test[TARGET].median())
    metrics = {
        "dataset": "Peoria County public parcel/sales feed",
        "training_rows": int(len(train)),
        "holdout_rows": int(len(test)),
        "train_through": str(train["sale_date"].max()),
        "holdout_from": str(test["sale_date"].min()),
        "mae": round(mae, 2),
        "mae_pct_of_holdout_median": round(mae / median_price * 100, 2) if median_price else None,
        "r2": round(r2, 4) if r2 is not None else None,
        "features": NUMERIC + CATEGORICAL,
        "status": "research baseline; not appraisal-grade",
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, MODEL_PATH)
    METRICS_PATH.write_text(json.dumps(metrics, indent=2))

    print(json.dumps(metrics, indent=2))
    print(f"Saved research baseline to {MODEL_PATH}")


if __name__ == "__main__":
    main()
