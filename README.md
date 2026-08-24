# Land Value Predictor

An end-to-end machine-learning MVP for estimating land value from structured property features. It exposes predictions through FastAPI and is connected to [Land Scout Lite](https://github.com/Leaderx777/land-scout-lite).

## What it demonstrates

- tabular data ingestion
- feature/target separation
- train/test validation
- Random Forest regression
- MAE and R² metrics
- persisted model artifacts
- interactive Streamlit predictions
- FastAPI model serving
- automated tests
- cross-project API integration with Land Scout Lite
- official Peoria County GIS/sales-data ingestion
- real-sales cleaning and profiling
- chronological holdout validation for a research baseline

## Two model tracks

### Synthetic demo model

The existing API demo model uses:

- `acres`
- `distance_to_city_miles`
- `road_frontage_ft`
- `zoning_score`
- `utilities`

It remains useful for demonstrating the end-to-end API workflow with Land Scout.

### Peoria County real-data research baseline

A separate research pipeline now works from official public Peoria County parcel/sale records. It uses only valuation-oriented fields and deliberately excludes owner names and mailing addresses.

The first baseline features are:

- acreage
- land assessment
- total assessment
- sale year
- property class
- city
- ZIP code

The baseline uses a chronological holdout instead of a random split so newer transactions are tested against a model trained on older transactions.

## Peoria County official data workflow

Download the public parcel/sales feeds:

```bash
python scripts/fetch_peoria_data.py
```

Profile and clean the sale records:

```bash
python scripts/profile_peoria_sales.py
```

This produces local research outputs under `artifacts/real_data/`, including a property-class profile. Property-class codes are summarized but are **not yet assumed** to mean vacant land, farmland, or another land category until their meanings are independently verified.

Train the first real-data baseline:

```bash
python train_peoria_baseline.py
```

The real baseline is saved separately under `artifacts/peoria_baseline/`. It does not automatically replace the synthetic API model.

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

Run tests:

```bash
pytest
```

## Land Scout integration

Land Scout Lite sends deal features to this API and receives `estimated_value`. Land Scout handles Central Illinois filtering and opportunity ranking while this repository owns valuation and real-data ingestion.

## Important limitation

The public Peoria County feeds are real data, but the real-data baseline is still a research model. It has not yet been validated as appraisal-grade or investment-grade and should not be used as a substitute for professional valuation or due diligence. The production API continues to use the synthetic demonstration model until the real-data pipeline passes stronger validation.

## Next steps

- verify Peoria County property-class definitions and isolate land-only transaction classes
- join deeper sales history to parcel records and remove invalid/non-market transactions where identifiable
- add comparable-sale, recency, and geographic features
- add Tazewell, Woodford, Fulton, Knox, and other Central Illinois county sources
- add taxes, zoning, flood, road-access, and utility data
- compare baseline models with time-based validation
- track experiments with MLflow
- expose model/data version through the API
- deploy the validated API for Land Scout
