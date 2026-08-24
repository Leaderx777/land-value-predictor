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

The existing API demo model uses acreage, distance to city, road frontage, zoning score, and utilities. It remains useful for demonstrating the end-to-end API workflow with Land Scout.

### Peoria County real-data research baseline

A separate research pipeline works from official public Peoria County parcel/sale records. It uses valuation-oriented fields and deliberately excludes owner names and mailing addresses.

The first baseline features are acreage, land assessment, total assessment, sale year, property class, city, and ZIP code. The baseline uses a chronological holdout so newer transactions are tested against a model trained on older transactions.

## Peoria County official data workflow

Download the public parcel/sales feeds:

```bash
python scripts/fetch_peoria_data.py
```

Profile and clean the sale records:

```bash
python scripts/profile_peoria_sales.py
```

Build a property-class verification template:

```bash
python scripts/build_peoria_class_mapping.py
```

The county's official Board of Review materials identify these broad property categories: Residential, Residential Vacant Land, Condo, Duplex, Commercial/Industrial, Farm Improved, and Farmland Only. The GIS tax-year parcel layer also exposes `AgParcelFlag`, `PropertyClass`, and `LandUse` fields. The project does not guess how raw class codes map to those categories; observed codes are exported to a reviewable mapping file and must be verified before any class is treated as land-only.

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

- verify the observed Peoria raw property-class values against county definitions
- isolate Residential Vacant Land and Farmland Only transactions only after verification
- evaluate the tax-year parcel layer's `AgParcelFlag` and `LandUse` as enrichment features
- join deeper sales history to parcel records and remove invalid/non-market transactions where identifiable
- add comparable-sale, recency, and geographic features
- add Tazewell, Woodford, Fulton, Knox, and other Central Illinois county sources
- add taxes, zoning, flood, road-access, and utility data
- compare baseline models with time-based validation
- track experiments with MLflow
- expose model/data version through the API
- deploy the validated API for Land Scout
