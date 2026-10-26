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

The gated research baseline uses verified acreage, latitude, longitude, and land category. Current assessments are excluded because their availability at historical sale dates is unproven. Separate training, calibration, and test windows keep date ties together and purge repeat parcels across windows. Earlier nearby comparable sales and a median price-per-acre baseline are evaluated alongside the Random Forest.

## Peoria County official data workflow

Download the public parcel/sales feeds:

```bash
python -m scripts.fetch_peoria_data
```

Profile and clean the sale records:

```bash
python -m scripts.profile_peoria_sales
```

Build a property-class verification template:

```bash
python -m scripts.build_peoria_class_mapping
```

The county's official Board of Review materials identify these broad property categories: Residential, Residential Vacant Land, Condo, Duplex, Commercial/Industrial, Farm Improved, and Farmland Only. The GIS tax-year parcel layer also exposes `AgParcelFlag`, `PropertyClass`, and `LandUse` fields. The project does not guess how raw class codes map to those categories; observed codes are exported to a reviewable mapping file and must be verified before any class is treated as land-only.

Build the evidence-gated land-only cohort and evaluate it:

```bash
python -m scripts.build_peoria_land_sales
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

Run the personal cash-resale deal analyzer:

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
- enrich the initial comparable-sale/location evaluation with verified zoning, access, and land-use features
- add Tazewell, Woodford, Fulton, Knox, and other Central Illinois county sources
- add taxes, zoning, flood, road-access, and utility data
- compare baseline models with time-based validation
- track experiments with MLflow
- expose model/data version through the API
- deploy the validated API for Land Scout

## Evidence gate and readiness

See [the validation guide](docs/VALIDATION.md) for evidence requirements, commands, and current blockers. A model is never automatically approved for investment use.

- `config/peoria_property_classes.csv` is an intentionally empty, tracked evidence table. Do not invent code definitions.
- `data/review/peoria_transaction_reviews.csv` holds independently reviewed transaction evidence and is ignored by Git.
- Generated mapping inventories and review templates never replace reviewed evidence.
- Missing evidence excludes transactions. A zero-row cohort blocks training, writes a reason to `artifacts/peoria_baseline/metrics.json`, and removes any stale research model.
- Test predictions abstain when fewer than three comparable parcels support a subject or its category/acreage is outside training support.
- Prediction ranges use a separate calibration window. Their actual later-sale coverage and width are reported; nominal coverage is not a guarantee under market changes.
- The production API remains a synthetic demonstration. No research model is promoted by this pipeline.

## Personal ROI and cash-resale calculator

The Streamlit app now calculates a cash resale after a cash or seller-financed purchase. It does not offer financing to the resale buyer and does not require a trained model. Enter purchase/resale prices, costs, holding time, and any purchase-note terms.

- Net project ROI is profit divided by all deal costs, including the full purchase price, interest, buying/holding/selling costs; before income tax and per deal, not annualized.
- The editable 30% target is a proposed screening hurdle, not a measured local market average or promised return.
- Purchase-note payments, balloons and remaining payoff at resale are included without counting principal twice. A pre-resale balloon requires cash, not assumed refinancing.
- Break-even resale, peak funding, monthly cash flows and lower-price/delayed-resale scenarios are reported.
- Zero cost defaults are unfilled assumptions, not verified zero costs. Resale valuation, title, access/buildability and loan payoff terms require independent confirmation. Passing the ROI target only verifies entered arithmetic.

The research valuation pipeline remains separate. API predictions still use the synthetic demo.

## Adjustable deal limits

The analyzer sidebar independently enables/disables maximum purchase price, upfront cash (down payment + buying costs + improvements), peak deal cash, regular monthly note payment plus holding costs, minimum net project ROI, minimum profit, holding time, states, property types, and cash/seller-financed purchase requirements. Price has no default dollar ceiling. Zero is a real cap when enabled; an off switch disables a rule. Nationwide/all property types are the initial scope. The 30% ROI hurdle can be edited or disabled.

Changing sidebar limits re-screens the last submitted deal and its downside scenarios. The rule table identifies each failure, and settings can be downloaded as JSON. Peak cash includes the upfront requirement even when a same-month resale offsets it. Regular monthly limits exclude balloon amounts; balloon funding is covered by the separate peak-cash check and warning.

These controls evaluate entered deals and export criteria. The Property Search page applies them to bounded RentCast batches or CSV intake. Passing a rule set is arithmetic screening, not verified market value or due diligence. With every limit disabled no pass/fail judgment is issued.

## Nationwide listing intake

Open **Property Search** from the calculator sidebar. It reuses the enabled price, state and property-type limits; cash limits are never sent as asking-price ceilings.

- **Live RentCast:** enter a key locally or set `RENTCAST_API_KEY`. Choose rows per request (1–500) and requests per click (1–51). A resumable state/offset cursor preserves progress. Results report sampled pages, errors and whether traversal of selected states has finished. Changing states, price ceiling or page size resets the scan. No background calls or automatic retries run.
- **CSV upload:** import permitted listings for any supported calculator property type, including commercial types absent from RentCast. Download the blank template or turn retrieved listings into an underwriting worksheet, fill it, then re-upload. Rates and percentage costs in CSV use decimals, e.g. `0.08` for 8%.
- Listings with inactive status, missing facts, or last-seen dates older than seven days (or in the future) cannot pass underwriting. Source activity is not direct seller confirmation.
- Listing price may seed a proposed purchase price. Resale value, costs and financing are never filled in automatically. Every financial input must be explicit, including zero costs. Sale-value/cost source URLs and financed-purchase source URLs are required for batch calculations. The source text still needs independent review.
- Results distinguish outside listing limits, missing underwriting, invalid scenarios, failed entered limits, and passed entered limits. Passing entered limits is not a buy recommendation, verified comparability, or verified title/buildability. No automated market-demand claim is made.

Official API references: [sale listings](https://developers.rentcast.io/reference/sale-listings) and [coverage](https://developers.rentcast.io/reference/property-listings). RentCast supplies residential listings, apartments and some land, with no office/retail/industrial listing coverage. CSV intake fills the interface gap; it does not create data coverage where no source has been supplied.

No live API call has been validated in this workspace because no API key is configured. Automated tests use explicitly fictional fixtures to check paging, request bounds, errors, stale/inactive rejection and financial-input gates. Do not commit keys or private property exports.
