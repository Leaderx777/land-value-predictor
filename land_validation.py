"""Evidence-gated research data. A passing software check is not an appraisal."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd

LAND_CATEGORIES = {"Residential Vacant Land", "Farmland Only"}
KEY = ["parcel_id", "sale_date", "sale_price"]
MAPPING_COLUMNS = ["property_class", "verified_category", "verification_source", "definition"]
REVIEW_COLUMNS = KEY + [
    "verified_property_class", "class_valid_from", "class_valid_to", "class_source",
    "land_only_at_sale", "market_sale", "single_parcel_sale", "transaction_source",
    "verified_acres", "latitude", "longitude", "geographic_area",
    "features_as_of", "features_source",
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _text(series: pd.Series) -> pd.Series:
    return series.astype("string").fillna("").str.strip()


def _keys(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    frame["parcel_id"] = _text(frame["parcel_id"])
    frame["sale_date"] = pd.to_datetime(frame["sale_date"], utc=True, errors="coerce").dt.normalize()
    frame["sale_price"] = pd.to_numeric(frame["sale_price"], errors="coerce")
    return frame


def build_verified_cohort(sales: pd.DataFrame, mapping: pd.DataFrame, reviews: pd.DataFrame):
    """Require independently sourced transaction and historical feature evidence.

    Unknown evidence excludes a row. Conflicting mapping/review keys abort the build.
    Evidence URLs are provenance, not automated verification of their contents.
    """
    for frame, columns, label in [(sales, KEY, "sales"), (mapping, MAPPING_COLUMNS, "mapping"),
                                  (reviews, REVIEW_COLUMNS, "reviews")]:
        missing = set(columns) - set(frame.columns)
        if missing:
            raise ValueError(f"{label} missing columns: {sorted(missing)}")
    m = mapping[MAPPING_COLUMNS].copy()
    m["property_class"] = _text(m["property_class"])
    if m["property_class"].eq("").any() or m["property_class"].duplicated().any():
        raise ValueError("Mapping codes must be nonempty and unique")
    r = _keys(reviews[REVIEW_COLUMNS])
    if r[KEY].isna().any().any() or r["parcel_id"].eq("").any() or r.duplicated(KEY).any():
        raise ValueError("Review transaction keys must be valid and unique")
    s = _keys(sales)
    if s[KEY].isna().any().any() or s["parcel_id"].eq("").any():
        raise ValueError("Sales transaction keys must be valid")
    s = s.drop_duplicates(KEY)
    # Never trust evidence columns arriving accidentally from the raw sale feed.
    s = s.drop(columns=[c for c in REVIEW_COLUMNS if c not in KEY and c in s], errors="ignore")
    s = s.drop(columns=[c for c in MAPPING_COLUMNS if c != "property_class" and c in s], errors="ignore")
    joined = s.merge(r, on=KEY, how="left", validate="one_to_one", indicator="review_match")
    joined["verified_property_class"] = _text(joined["verified_property_class"])
    joined = joined.merge(m.rename(columns={"property_class": "verified_property_class"}),
                          on="verified_property_class", how="left", validate="many_to_one")
    reason = pd.Series("", index=joined.index, dtype="string")

    def exclude(mask, label):
        reason.loc[reason.eq("") & mask.fillna(True)] = label

    exclude(joined["review_match"].ne("both"), "missing_transaction_review")
    exclude(~joined["verified_category"].isin(LAND_CATEGORIES), "unverified_or_non_land_class")
    for col in ["verification_source", "class_source", "transaction_source", "features_source"]:
        exclude(~_text(joined[col]).str.match(r"^https?://\S+$"), "missing_evidence_source")
    exclude(_text(joined["definition"]).eq(""), "missing_class_definition")
    sale_date = joined["sale_date"]
    start = pd.to_datetime(joined["class_valid_from"], utc=True, errors="coerce")
    end = pd.to_datetime(joined["class_valid_to"], utc=True, errors="coerce")
    exclude(start.isna() | end.isna() | (start > sale_date) | (end < sale_date),
            "classification_not_valid_at_sale")
    for col in ["land_only_at_sale", "market_sale", "single_parcel_sale"]:
        exclude(_text(joined[col]).str.lower().ne("true"), f"unverified_{col}")
    as_of = pd.to_datetime(joined["features_as_of"], utc=True, errors="coerce")
    exclude(as_of.isna() | (as_of > sale_date), "features_not_available_at_sale")
    for col, low, high in [("verified_acres", 0.1, 1000), ("latitude", -90, 90),
                            ("longitude", -180, 180)]:
        joined[col] = pd.to_numeric(joined[col], errors="coerce")
        exclude(~joined[col].between(low, high), "invalid_verified_features")
    exclude(_text(joined["geographic_area"]).eq(""), "missing_geographic_area")
    joined["exclusion_reason"] = reason
    eligible = joined.loc[reason.eq("")].copy()
    eligible["acres"] = eligible["verified_acres"]
    # Strict feature allowlist prevents current assessments from leaking into training.
    eligible = eligible[KEY + ["acres", "latitude", "longitude", "geographic_area", "verified_category"]]
    report = {
        "status": "research_only" if len(eligible) else "blocked_no_verified_land_sales",
        "input_rows": len(sales), "unique_transactions": len(s),
        "eligible_rows": len(eligible), "excluded_rows": int(reason.ne("").sum()),
        "exclusion_counts": reason[reason.ne("")].value_counts().to_dict(),
        "unused_review_rows": int(len(r.merge(s[KEY], on=KEY, how="left", indicator=True)
                                           .query('_merge == "left_only"'))),
        "investment_suitable": False,
    }
    return eligible, joined[KEY + ["exclusion_reason"]], report
