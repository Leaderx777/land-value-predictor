"""Out-of-time research evaluation with frozen training-only comparables."""

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, r2_score


def chronological_partitions(df):
    dates = sorted(df.sale_date.unique())
    if len(dates) < 5:
        raise ValueError("Need at least five distinct sale dates")
    first, second = dates[int(len(dates) * .6)], dates[int(len(dates) * .8)]
    train = df[df.sale_date < first].copy()
    calibration = df[(df.sale_date >= first) & (df.sale_date < second)].copy()
    test = df[df.sale_date >= second].copy()
    # Put repeat parcels only in their latest partition, never across partitions.
    calibration = calibration[~calibration.parcel_id.isin(test.parcel_id)]
    train = train[~train.parcel_id.isin(pd.concat([calibration.parcel_id, test.parcel_id]))]
    if min(len(train), len(calibration), len(test)) < 20:
        raise ValueError("Need at least 20 independent rows per partition after parcel purging; this is a run floor, not proof of reliability")
    return train, calibration, test


def comparable_estimates(training, subjects, max_km=20, max_age_days=730, minimum=3):
    """Same category, 0.5–2x acreage, <=20km, strictly earlier, last two years.

    These are provisional research settings, not appraiser-selected comparables.
    Calibration/test targets never enter the comparable pool.
    """
    estimates, counts = [], []
    for row in subjects.itertuples():
        pool = training[
            training.verified_category.eq(row.verified_category)
            & training.parcel_id.ne(row.parcel_id)
            & training.acres.between(row.acres / 2, row.acres * 2)
            & (training.sale_date < row.sale_date)
            & (training.sale_date >= row.sale_date - pd.Timedelta(days=max_age_days))
        ].copy()
        lat1, lat2 = np.radians(pool.latitude.to_numpy()), np.radians(row.latitude)
        dlat = lat1 - lat2
        dlon = np.radians(pool.longitude.to_numpy() - row.longitude)
        distance = 6371 * 2 * np.arcsin(np.sqrt(np.clip(
            np.sin(dlat / 2)**2 + np.cos(lat1)*np.cos(lat2)*np.sin(dlon / 2)**2, 0, 1)))
        pool["distance"] = distance
        pool = pool[pool.distance <= max_km].sort_values("distance").drop_duplicates("parcel_id").head(10)
        counts.append(len(pool))
        estimates.append(float((pool.sale_price / pool.acres).median() * row.acres)
                         if len(pool) >= minimum else np.nan)
    return np.asarray(estimates), np.asarray(counts)


def error_metrics(actual, predictions):
    actual, predictions = np.asarray(actual), np.asarray(predictions)
    error = np.abs(actual - predictions)
    return {"rows": len(actual), "mae": float(mean_absolute_error(actual, predictions)),
            "median_absolute_pct_error": float(np.median(error / actual) * 100),
            "p90_absolute_pct_error": float(np.quantile(error / actual, .9) * 100),
            "r2": float(r2_score(actual, predictions)) if len(actual) > 1 else None}


def calibration_radius(residuals, alpha=.1):
    residuals = np.asarray(residuals)
    rank = int(np.ceil((len(residuals) + 1) * (1 - alpha)))
    if not len(residuals) or rank > len(residuals):
        raise ValueError("Insufficient calibration residuals")
    return float(np.sort(residuals)[rank - 1])
