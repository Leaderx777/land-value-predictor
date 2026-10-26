"""Build a documented, fail-closed research cohort; never fabricate evidence."""

import json
from pathlib import Path

import pandas as pd

from land_validation import MAPPING_COLUMNS, REVIEW_COLUMNS, build_verified_cohort, sha256
from real_data import prepare_peoria_sales

RAW = Path("data/official/peoria_parcel_sales.csv")
MAPPING = Path("config/peoria_property_classes.csv")
REVIEWS = Path("data/review/peoria_transaction_reviews.csv")
OUT = Path("artifacts/verified_land")


def main():
    if not RAW.exists():
        raise SystemExit("Run python -m scripts.fetch_peoria_data first")
    OUT.mkdir(parents=True, exist_ok=True)
    raw = pd.read_csv(RAW, dtype={"parcel_id": "string", "property_class": "string", "zip_code": "string"})
    clean = prepare_peoria_sales(raw)
    mapping = pd.read_csv(MAPPING, dtype="string") if MAPPING.exists() else pd.DataFrame(columns=MAPPING_COLUMNS)
    reviews = pd.read_csv(REVIEWS, dtype="string") if REVIEWS.exists() else pd.DataFrame(columns=REVIEW_COLUMNS)
    eligible, exclusions, report = build_verified_cohort(clean, mapping, reviews)
    report.update({"raw_rows": len(raw), "clean_rows": len(clean),
                   "raw_sha256": sha256(RAW),
                   "mapping_sha256": sha256(MAPPING) if MAPPING.exists() else None,
                   "reviews_sha256": sha256(REVIEWS) if REVIEWS.exists() else None})
    report["input_hashes"] = {str(path): sha256(path) if path.exists() else None
                             for path in [RAW, MAPPING, REVIEWS]}
    eligible.to_csv(OUT / "sales.csv", index=False)
    exclusions.to_csv(OUT / "exclusions.csv", index=False)
    report["cohort_sha256"] = sha256(OUT / "sales.csv")
    (OUT / "audit.json").write_text(json.dumps(report, indent=2) + "\n")
    # A separate file means regeneration cannot erase evidence already reviewed.
    template = OUT / "transaction_review_template.csv"
    pending = clean[ ["parcel_id", "sale_date", "sale_price"] ].copy()
    for col in REVIEW_COLUMNS[3:]:
        pending[col] = ""
    pending.to_csv(template, index=False)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
