# Land Value Predictor

An end-to-end machine-learning MVP for estimating land value from structured property features. It now exposes predictions through FastAPI and is connected to [Land Scout Lite](https://github.com/Leaderx777/land-scout-lite).

## What it demonstrates

- tabular data ingestion
- feature/target separation
- train/test validation
- Random Forest regression
- MAE and R² metrics
- persisted model artifact
- interactive Streamlit predictions
- FastAPI model serving
- automated tests
- cross-project API integration with Land Scout Lite

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
pip install -r requirements.txt
python train.py
```

Run the standalone Streamlit app:

```bash
streamlit run app.py
```

Or start the API used by Land Scout Lite:

```bash
uvicorn api:app --reload --port 8000
```

API endpoints:

- `GET /health`
- `POST /predict`

Example request:

```json
{
  "acres": 5.0,
  "distance_to_city_miles": 12.0,
  "road_frontage_ft": 250.0,
  "zoning_score": 3,
  "utilities": 1
}
```

Run tests:

```bash
pytest
```

## Land Scout integration

Land Scout Lite sends deal features to this API and receives `estimated_value`. This separates the valuation model from the deal-screening interface, which is closer to a production service architecture than copying model logic into both projects.

## Important limitation

The included dataset is synthetic and exists only to demonstrate the ML workflow. This project is not an appraisal service and should not be used to make real property valuation decisions without real market data and proper validation.

## Next steps

- ingest real parcel/comparable-sales data
- add location/county features
- add taxes, zoning, flood and utility information
- compare multiple model families
- track experiments with MLflow
- deploy the API to a hosted service
- add batch deal enrichment in Land Scout
