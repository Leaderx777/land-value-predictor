# Land Value Predictor

An end-to-end machine-learning MVP for estimating land value from structured property features. It exposes predictions through FastAPI and is connected to [Land Scout Lite](https://github.com/Leaderx777/land-scout-lite).

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
- official county GIS/sales-data ingestion

## Current model features

The starter model currently uses:

- `acres`
- `distance_to_city_miles`
- `road_frontage_ft`
- `zoning_score`
- `utilities`

The production direction is to replace the synthetic training set with verified Central Illinois parcel and comparable-sales data as enough compatible features are collected.

## Peoria County official data connector

The project now includes a connector for Peoria County's public ArcGIS services. It retrieves only valuation-research fields and deliberately excludes owner names and mailing addresses.

The parcel feed includes fields such as parcel ID, property class, city, ZIP, acreage, land assessment, total assessment, latest sale price, and sale date. A separate sales-history feed provides recorded parcel sale price/date history.

Download the current public data locally:

```bash
python scripts/fetch_peoria_data.py
```

Files are written under `data/official/` and ignored by Git so downloaded county datasets are not copied into the repository.

Official source endpoints used by the connector:

- Peoria County Cadastral Parcel FeatureServer
- Peoria County GIS Sales History table

These feeds establish the first real-data layer for the Central Illinois model. The current prediction model remains a development model until the feature engineering and validation pipeline is retrained on suitable real transactions.

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

Land Scout Lite sends deal features to this API and receives `estimated_value`. Land Scout now handles Central Illinois market filtering and deal ranking while this repository owns valuation and real-data ingestion.

## Important limitation

The current trained model still uses synthetic data and exists to demonstrate the ML workflow. The newly added Peoria County feeds are real public data, but they have not yet replaced the synthetic model because the real-data feature engineering and validation work is still in progress. This project is not an appraisal service and should not be used to make real property valuation decisions without proper validation.

## Next steps

- profile and clean Peoria County sale records
- identify land/vacant/agricultural property-class codes
- engineer comparable-sale features from parcel and sales history
- add Tazewell, Woodford, Fulton, Knox, and other Central Illinois county sources
- add location, taxes, zoning, flood, road-access, and utility features
- compare multiple model families
- track experiments with MLflow
- deploy the API to a hosted service
