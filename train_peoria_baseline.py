"""Evaluate only evidence-gated land sales. Never promotes a model to the API."""

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from land_validation import sha256
from research_evaluation import (calibration_radius, chronological_partitions,
                                 comparable_estimates, error_metrics)

INPUT = Path("artifacts/verified_land/sales.csv")
OUT_DIR = Path("artifacts/peoria_baseline")
MODEL_PATH = OUT_DIR / "model.joblib"
METRICS_PATH = OUT_DIR / "metrics.json"
NUMERIC = ["acres", "latitude", "longitude"]
CATEGORICAL = ["verified_category"]
FEATURES = NUMERIC + CATEGORICAL


def build_pipeline():
    return Pipeline([
        ("prep", ColumnTransformer([
            ("num", "passthrough", NUMERIC),
            ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL)])),
        ("model", RandomForestRegressor(n_estimators=350, min_samples_leaf=3,
                                         random_state=42, n_jobs=-1))])


def evaluate(df):
    train, calibration, test = chronological_partitions(df)
    model = build_pipeline().fit(train[FEATURES], train.sale_price)
    prediction = model.predict(test[FEATURES])
    comp, counts = comparable_estimates(train, test)
    supported = np.isfinite(comp)
    # Refuse categories/acreages outside training support as well as weak comparables.
    supported &= test.verified_category.isin(train.verified_category).to_numpy()
    supported &= test.acres.between(train.acres.min(), train.acres.max()).to_numpy()
    naive = test.acres.to_numpy() * float((train.sale_price / train.acres).median())
    result = {
        "status": "research_only_not_investment_validated", "investment_suitable": False,
        "features": FEATURES,
        "training_rows": len(train), "calibration_rows": len(calibration), "holdout_rows": len(test),
        "train_through": str(train.sale_date.max()),
        "calibration_from": str(calibration.sale_date.min()),
        "calibration_through": str(calibration.sale_date.max()), "holdout_from": str(test.sale_date.min()),
        "random_forest_all": error_metrics(test.sale_price, prediction),
        "median_price_per_acre_all": error_metrics(test.sale_price, naive),
        "supported_rows": int(supported.sum()), "abstained_rows": int((~supported).sum()),
        "support_coverage": float(supported.mean()),
        "segments": {}, "geographic_holdouts": {},
        "limitations": ["Research settings; no investment acceptance thresholds approved",
                        "Countywide evidence may not represent small vacant-lot deals",
                        "Interval coverage under time/geographic shift is empirical, not guaranteed",
                        "No zoning, flood, utility, access, buildability or title due-diligence verification"]}
    if supported.any():
        result["random_forest_supported"] = error_metrics(test.sale_price[supported], prediction[supported])
        result["comparables_supported"] = error_metrics(test.sale_price[supported], comp[supported])
    for category in sorted(test.verified_category.unique()):
        mask = test.verified_category.eq(category).to_numpy()
        result["segments"][category] = error_metrics(test.sale_price[mask], prediction[mask])
    # Each area is tested using earlier sales from OTHER areas only.
    for area in sorted(test.geographic_area.unique()):
        other = train[train.geographic_area.ne(area)]
        target = test[test.geographic_area.eq(area)]
        if len(other) < 20 or len(target) < 10 or not target.verified_category.isin(other.verified_category).all():
            result["geographic_holdouts"][area] = {"status": "insufficient_support", "rows": len(target)}
        else:
            geographic_model = build_pipeline().fit(other[FEATURES], other.sale_price)
            result["geographic_holdouts"][area] = error_metrics(target.sale_price, geographic_model.predict(target[FEATURES]))
    cal_comp, _ = comparable_estimates(train, calibration)
    cal_support = np.isfinite(cal_comp) & calibration.verified_category.isin(train.verified_category).to_numpy()
    cal_support &= calibration.acres.between(train.acres.min(), train.acres.max()).to_numpy()
    radius = None
    result["interval"] = {"status": "insufficient_supported_calibration", "calibration_rows": int(cal_support.sum())}
    if cal_support.sum() >= 20 and supported.any():
        residuals = np.abs(calibration.sale_price.to_numpy()[cal_support] - model.predict(calibration.loc[cal_support, FEATURES]))
        radius = calibration_radius(residuals)
        low, high = np.maximum(0, prediction - radius), prediction + radius
        actual = test.sale_price.to_numpy()
        result["interval"] = {
            "status": "research_empirical", "nominal_coverage": .9,
            "calibration_rows": int(cal_support.sum()), "radius_dollars": radius,
            "holdout_coverage": float(((actual[supported] >= low[supported]) & (actual[supported] <= high[supported])).mean()),
            "median_width_pct_of_price": float(np.median((high[supported] - low[supported]) / actual[supported]) * 100)}
    output = test[["parcel_id", "sale_date", "sale_price", "verified_category", "geographic_area"]].copy()
    output["supported"] = supported
    output["comparable_count"] = counts
    output["estimated_value"] = np.where(supported, prediction, np.nan)
    output["comparable_estimate"] = comp
    output["lower"] = np.where(supported, np.maximum(0, prediction - radius), np.nan) if radius is not None else np.nan
    output["upper"] = np.where(supported, prediction + radius, np.nan) if radius is not None else np.nan
    return model, result, output


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    # Delete obsolete artifacts before validating: a failed rebuild must not leave a usable stale model.
    MODEL_PATH.unlink(missing_ok=True)
    (OUT_DIR / "holdout_predictions.csv").unlink(missing_ok=True)
    report = {"status": "blocked", "investment_suitable": False}
    try:
        audit_path = INPUT.with_name("audit.json")
        audit = json.loads(audit_path.read_text())
        if audit.get("cohort_sha256") != sha256(INPUT):
            raise ValueError("Cohort hash does not match audit; rebuild verified land sales")
        for path, expected in audit.get("input_hashes", {}).items():
            source = Path(path)
            observed = sha256(source) if source.exists() else None
            if observed != expected:
                raise ValueError(f"Evidence input changed: {path}; rebuild verified land sales")
        if not audit.get("eligible_rows"):
            raise ValueError("No verified land-only market sales. Supply historical classification and transaction evidence; see docs/VALIDATION.md")
        df = pd.read_csv(INPUT, dtype={"parcel_id": "string"})
        df["sale_date"] = pd.to_datetime(df.sale_date, utc=True)
        model, report, output = evaluate(df)
        report["cohort_sha256"] = sha256(INPUT)
        report["data_audit"] = audit
        # Persist uncertainty settings alongside research model; serving is deliberately separate.
        joblib.dump({"model": model, "metrics": report}, MODEL_PATH)
        output.to_csv(OUT_DIR / "holdout_predictions.csv", index=False)
    except (FileNotFoundError, ValueError, KeyError) as exc:
        report["reason"] = str(exc)
        METRICS_PATH.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
        print(json.dumps(report, indent=2))
        raise SystemExit(2)
    METRICS_PATH.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
