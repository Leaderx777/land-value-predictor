"""Read public Peoria County parcel/sales data from the official ArcGIS services.

The connector deliberately excludes owner names and mailing addresses. It retrieves
only fields useful for valuation research and model development.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pandas as pd
import requests

PARCEL_QUERY_URL = (
    "https://gis.peoriacounty.gov/arcgis/rest/services/DP/Cadastral/FeatureServer/1/query"
)
SALES_QUERY_URL = (
    "https://gis.peoriacounty.gov/arcgis/rest/services/Query_Layers/MapServer/3/query"
)

PARCEL_FIELDS = [
    "PIN",
    "PropClass",
    "CITY",
    "PZIP",
    "land_lot_value",
    "total_assessed_value",
    "Acres",
    "NET_SELLING_PRICE",
    "SALES_DATE",
]

SALES_FIELDS = ["parcel_number", "net_selling_price", "date_of_sale"]


def _query_all(
    url: str,
    fields: list[str],
    where: str = "1=1",
    page_size: int = 2000,
    timeout: int = 30,
) -> list[dict[str, Any]]:
    """Page through an ArcGIS query endpoint and return attribute dictionaries."""
    rows: list[dict[str, Any]] = []
    offset = 0

    while True:
        response = requests.get(
            url,
            params={
                "f": "json",
                "where": where,
                "outFields": ",".join(fields),
                "returnGeometry": "false",
                "resultOffset": offset,
                "resultRecordCount": page_size,
                "orderByFields": fields[0],
            },
            timeout=timeout,
        )
        response.raise_for_status()
        payload = response.json()
        if "error" in payload:
            raise RuntimeError(f"Peoria County ArcGIS error: {payload['error']}")

        features = payload.get("features", [])
        rows.extend(feature.get("attributes", {}) for feature in features)

        if len(features) < page_size:
            break
        offset += page_size

    return rows


def fetch_parcels_with_sales(min_acres: float = 0.1) -> pd.DataFrame:
    """Fetch parcel records that contain acreage and a recorded sale price."""
    where = (
        f"Acres >= {float(min_acres)} AND NET_SELLING_PRICE > 0 "
        "AND SALES_DATE IS NOT NULL"
    )
    rows = _query_all(PARCEL_QUERY_URL, PARCEL_FIELDS, where=where, page_size=5000)
    df = pd.DataFrame(rows)
    if df.empty:
        return df

    df = df.rename(
        columns={
            "PIN": "parcel_id",
            "PropClass": "property_class",
            "CITY": "city",
            "PZIP": "zip_code",
            "Acres": "acres",
            "NET_SELLING_PRICE": "sale_price",
            "SALES_DATE": "sale_date",
        }
    )
    df["county"] = "Peoria"
    df["state"] = "IL"
    df["source"] = "Peoria County GIS"
    df["retrieved_at_utc"] = datetime.now(timezone.utc).isoformat()
    if "sale_date" in df.columns:
        df["sale_date"] = pd.to_datetime(df["sale_date"], unit="ms", errors="coerce", utc=True)
    return df


def fetch_sales_history() -> pd.DataFrame:
    """Fetch the public Peoria County sales-history table."""
    rows = _query_all(SALES_QUERY_URL, SALES_FIELDS, page_size=2000)
    df = pd.DataFrame(rows)
    if df.empty:
        return df

    df = df.rename(
        columns={
            "parcel_number": "parcel_id",
            "net_selling_price": "sale_price",
            "date_of_sale": "sale_date",
        }
    )
    df["county"] = "Peoria"
    df["state"] = "IL"
    df["source"] = "Peoria County GIS Sales History"
    df["retrieved_at_utc"] = datetime.now(timezone.utc).isoformat()
    if "sale_date" in df.columns:
        df["sale_date"] = pd.to_datetime(df["sale_date"], unit="ms", errors="coerce", utc=True)
    return df
