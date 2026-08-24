import pandas as pd

from real_data import prepare_peoria_sales, property_class_profile


def test_prepare_peoria_sales_filters_and_derives_features():
    raw = pd.DataFrame(
        [
            {
                "parcel_id": "A",
                "property_class": "X",
                "city": "Peoria",
                "zip_code": "61614",
                "acres": 5.0,
                "sale_price": 50000,
                "sale_date": "2024-01-01",
                "land_lot_value": 12000,
                "total_assessed_value": 18000,
            },
            {
                "parcel_id": "B",
                "property_class": "Y",
                "city": "Peoria",
                "zip_code": "61615",
                "acres": 0.0,
                "sale_price": 100,
                "sale_date": "2024-01-02",
                "land_lot_value": 1000,
                "total_assessed_value": 1000,
            },
        ]
    )

    clean = prepare_peoria_sales(raw)

    assert len(clean) == 1
    assert clean.loc[0, "parcel_id"] == "A"
    assert clean.loc[0, "sale_price_per_acre"] == 10000
    assert clean.loc[0, "sale_year"] == 2024

    profile = property_class_profile(clean)
    assert profile.loc[0, "sales"] == 1
