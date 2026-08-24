# Land Value Predictor

An end-to-end machine-learning MVP for estimating land value from structured property features.

## What it demonstrates

- tabular data ingestion
- feature/target separation
- train/test validation
- Random Forest regression
- MAE and R² metrics
- persisted model artifact
- interactive Streamlit predictions
- automated tests

## Features

The starter model uses:

- `acres`
- `distance_to_city_miles`
- `road_frontage_ft`
- `zoning_score`
- `utilities`

## Run locally

```bash
git clone https://github.com/Leaderx777/land-value-predictor.git
cd land-value-predictor
python -m venv .venv
```

Activate the environment and install dependencies:

```bash
pip install -r requirements.txt
```

Train the model:

```bash
python train.py
```

Run the app:

```bash
streamlit run app.py
```

Run tests:

```bash
pytest
```

## Important limitation

The included dataset is synthetic and exists only to demonstrate the ML workflow. This project is not an appraisal service and should not be used to make real property valuation decisions without real market data and proper validation.

## Next steps

- ingest real parcel/comparable-sales data
- add location/county features
- add taxes, zoning, flood and utility information
- compare multiple model families
- track experiments with MLflow
- expose predictions through FastAPI
- add CI with GitHub Actions
