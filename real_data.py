"""Prepare a first Peoria County real-sales dataset for baseline modeling.

This module intentionally works only with public valuation fields already normalized by
`sources.peoria_county`. It does not use owner names or mailing addresses.
"""

from __future__ import annotations

import pandas as pd

MIN_SALE_PRICE = 1000.0
MIN_ACRES = 0.1
MAX_ACRES = 1000.0


def prepare_peoria_sales(parcels: pd.DataFrame) -> pd.DataFrame:
    """Clean parcel-sale rows and derive safe baseline features.

    This is deliberately conservative. Property-class codes are retained as a feature
    for profiling but are not yet used to assert that a parcel is vacant land or
    farmland until county code meanings are verified.
    """
    required = {
        "parcel_id",
        "property_class",
        "city",
        "zip_code",
        "acres",
        "sale_price",
        "sale_date",
        "land_lot_value",
        "total_assessed_value",
    }
    missing = required.difference(parcels.columns)
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")

    df = parcels.copy()
    df["acres"] = pd.to_numeric(df["acres"], errors="coerce")
    df["sale_price"] = pd.to_numeric(df["sale_price"], errors="coerce")
    df["land_lot_value"] = pd.to_numeric(df["land_lot_value"], errors="coerce")
    df["total_assessed_value"] = pd.to_numeric(df["total_assessed_value"], errors="coerce")
    df["sale_date"] = pd.to_datetime(df["sale_date"], errors="coerce", utc=True)

    df = df.dropna(subset=["parcel_id", "acres", "sale_price", "sale_date"])
    df = df[
        df["acres"].between(MIN_ACRES, MAX_ACRES)
        & (df["sale_price"] >= MIN_SALE_PRICE)
    ].copy()

    df["sale_year"] = df["sale_date"].dt.year.astype(int)
    df["sale_price_per_acre"] = df["sale_price"] / df["acres"]
    df["assessment_to_sale_ratio"] = df["total_assessed_value"] / df["sale_price"]
    df.replace([float("inf"), float("-inf")], pd.NA, inplace=True)

    # Remove exact duplicate parcel/date/price records while preserving repeat sales.
    df = df.drop_duplicates(subset=["parcel_id", "sale_date", "sale_price"])

    return df.sort_values("sale_date").reset_index(drop=True)


def property_class_profile(df: pd.DataFrame) -> pd.DataFrame:
    """Summarize recorded property-class codes without assuming their meaning."""
    grouped = (
        df.groupby("property_class", dropna=False)
        .agg(
            sales=("parcel_id", "count"),
            median_acres=("acres", "median"),
            median_sale_price=("sale_price", "median"),
            median_price_per_acre=("sale_price_per_acre", "median"),
        )
        .reset_index()
        .sort_values("sales", ascending=False)
    )
    return grouped
