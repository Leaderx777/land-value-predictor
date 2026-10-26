# Land valuation research: evidence and validation

## Current decision

**Blocked for investment use.** This implementation is research infrastructure, not a validated valuation product. No profitability, accuracy, or appraisal claim is supported yet.

The downloaded parcel snapshot contains 14,495 rows; 14,289 pass basic cleaning. Its observed types are Single-Fam (12,358), missing (1,419), Multi-Fam (389), Condo (109), and UNK (14). No code is assumed to establish vacancy. With no independently sourced transaction reviews or verified mappings, the gate excludes all 14,289 clean records. This is expected, not an invitation to loosen the gate.

Official services inspected:

- https://gis.peoriacounty.gov/arcgis/rest/services/DP/Cadastral/FeatureServer/1?f=pjson — `PropClass` has alias Property Type and no coded domain. Current building assessments cannot prove historical vacancy.
- https://gis.peoriacounty.gov/arcgis/rest/services/Query_Layers/MapServer/3?f=pjson — Sales History supplies parcel number, price, date, and an object ID. It has no market-sale qualification or property classification.
- https://gis.peoriacounty.gov/arcgis/rest/services/DP/Parcel_Compare/MapServer/0?f=pjson — Tax Parcel exposes `PropertyClass` and `LandUse` without coded domains. `AgParcelFlag` means Yes/No, not necessarily Farmland Only.
- https://gis.peoriacounty.gov/arcgis/rest/services/DP/Parcel_Compare/MapServer/1?f=pjson — Tax Parcel History supplies geometry/record metadata but no property-class or land-use history. Creation/edit timestamps are not classification-effective dates.

These checks do not establish that no other suitable county source exists. A historical assessment roll, assessor export, or qualified sales export is still needed. The existing parcel feed is biased toward its recorded sale coverage and should not be treated as a complete vacant-land market sample.

## Reproduce

Run from the repository root, Python 3.12:

```bash
python -m pip install -r requirements.txt
python -m pytest -q
python -m scripts.fetch_peoria_data
python -m scripts.profile_peoria_sales
python -m scripts.build_peoria_class_mapping
python -m scripts.build_peoria_land_sales
python train_peoria_baseline.py
```

Training exits 2 and writes a blocked report if evidence or sample support is missing. Existing research model artifacts are removed before validation. The synthetic API artifact is separate and unchanged. The research workflow is manual-only to avoid automatic download/training notifications; a failed gate still uploads its summary.

## Supply evidence without overwriting it

`artifacts/verified_land/transaction_review_template.csv` is generated from clean transactions. Copy the rows actually supported by independent evidence to `data/review/peoria_transaction_reviews.csv`. Never fill flags merely to pass a check.

The transaction key is parcel ID + sale date + price. Preserve parcel IDs and classification codes as strings, including leading zeros. Review dates are normalized to UTC calendar days for transaction matching; establish local/UTC date semantics with the county before loading a source with different date conventions.

Required review fields:

| Fields | Evidence needed |
|---|---|
| `verified_property_class`, `class_valid_from`, `class_valid_to`, `class_source` | Exact raw historical classification with a documented effective interval covering sale day; this may differ from the coarse current `PropClass`. |
| `land_only_at_sale` | Explicit `true` only when improvements/vacancy status at sale is established. |
| `market_sale`, `single_parcel_sale`, `transaction_source` | Qualified arm's-length sale and a price attributable to this one parcel. Unknown, related-party, bundled, and unallocated multi-parcel sales are excluded. |
| `verified_acres`, `latitude`, `longitude`, `geographic_area`, `features_as_of`, `features_source` | Historical parcel size/location/area known by sale date. Current parcel boundaries cannot be silently joined backward through a split/merge. |

`config/peoria_property_classes.csv` maps each verified raw historical code to a category, source URL, and exact definition. Only Residential Vacant Land and Farmland Only are eligible; report them separately. Definition/source strings are provenance fields: software cannot establish that the linked document actually supports an assertion. Independent source review is still required.

Generated audits record raw, mapping, review, and cohort SHA-256 hashes; input/eligible/excluded counts; first exclusion reason per transaction; and unused review rows. Additional defects may exist after a row's first exclusion. Retain snapshots alongside the audit to reproduce a run. Raw downloads/reviews are ignored by Git.

## Validation that now runs when evidence is available

- Strictly ordered 60/20/20 distinct-date windows; no equal dates across windows; repeated parcels removed from earlier windows.
- A minimum of 20 rows per window is a software execution floor, not an adequate-market-sample claim.
- Acreage/location/category Random Forest, excluding all current assessment inputs.
- Training-only median price per acre and nearby comparable estimates. Research comparable settings: same category, 0.5–2x acreage, within 20 km, prior two years, strictly earlier sale date, other parcel, 3–10 distinct parcels. These settings require local evaluation.
- Comparable availability and training category/acreage support govern abstention. No supported prediction is output for an unsupported subject.
- MAE, median and 90th-percentile absolute percentage error; matched-support model/comparable comparisons; land-category metrics; later-sale geographic-area holdouts with explicit insufficient-support status.
- A separate calibration residual radius gives nominal 90% research intervals. Later-sale coverage and relative width are measured. Time/spatial shifts can invalidate nominal coverage; a narrow interval alone proves nothing.

## Still required before investment suitability

1. Obtain and independently verify historical land classification, improvement status, qualified sale flags, parcel splits/merges, and complete market coverage.
2. Add verified zoning, legal access, utility availability, flood exposure, buildability, and relevant submarket distinctions. Spatial proximity cannot substitute for them.
3. Evaluate rolling historical windows, a genuinely untouched later-sale set, and relevant local geographic holdouts. Inspect sample size and errors for the actual acreage/price/category of intended deals.
4. Demonstrate useful improvement over comparables and simple benchmarks on identical supported cases. Report all abstentions, failures, interval coverage/width, and population coverage.
5. Set acceptance thresholds from the intended deal economics: conservative resale proceeds minus purchase, closing, holding, improvement and selling costs must retain the required profit. No universal MAE or row-count threshold is asserted here.
6. Have an independent local valuation review, then explicitly decide deployment scope. Model/data versions, prediction support checks, comparable provenance, drift monitoring and a due-diligence workflow must be present in any real-data serving API.

## County data request (prepared; not sent)

Please identify a public download or export for Peoria County parcel sales and historical assessment classifications. Needed fields are parcel ID, sale date, consideration/net price, deed or transfer ID, market/valid-sale qualification and definition, multi-parcel indicator and price allocation, property-class code and code dictionary, land-use code/dictionary, improvements at sale, assessment/effective year, acreage and parcel geometry/location as of that year, and split/merge lineage. Please clarify whether dates are local dates or UTC timestamps and whether current parcel-sale prices represent one parcel or an entire transfer. Owner names and mailing addresses are not needed.
