import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split

DATA_PATH = Path("data/sample_land.csv")
MODEL_DIR = Path("artifacts")
MODEL_PATH = MODEL_DIR / "land_value_model.joblib"
METRICS_PATH = MODEL_DIR / "metrics.json"

FEATURES = [
    "acres",
    "distance_to_city_miles",
    "road_frontage_ft",
    "zoning_score",
    "utilities",
]
TARGET = "price"


def load_data(path: Path = DATA_PATH) -> pd.DataFrame:
    df = pd.read_csv(path)
    missing = [col for col in FEATURES + [TARGET] if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    return df


def train_model(df: pd.DataFrame, random_state: int = 42):
    X = df[FEATURES]
    y = df[TARGET]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=random_state
    )

    model = RandomForestRegressor(
        n_estimators=250,
        random_state=random_state,
        min_samples_leaf=2,
    )
    model.fit(X_train, y_train)

    predictions = model.predict(X_test)
    metrics = {
        "mae": round(float(mean_absolute_error(y_test, predictions)), 2),
        "r2": round(float(r2_score(y_test, predictions)), 4),
        "rows": int(len(df)),
    }
    return model, metrics


def main() -> None:
    df = load_data()
    model, metrics = train_model(df)

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    METRICS_PATH.write_text(json.dumps(metrics, indent=2))

    print(f"Saved model to {MODEL_PATH}")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
