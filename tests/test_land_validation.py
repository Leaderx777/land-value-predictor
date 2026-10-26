import pandas as pd
import pytest

from land_validation import REVIEW_COLUMNS, build_verified_cohort


def examples():
    sales = pd.DataFrame([dict(parcel_id="001", sale_date="2024-03-01", sale_price=12000, acres=2)])
    mapping = pd.DataFrame([dict(property_class="010", verified_category="Residential Vacant Land",
                                 verification_source="https://county.example/definitions", definition="Test fixture only")])
    reviews = pd.DataFrame([dict(parcel_id="001", sale_date="2024-03-01", sale_price=12000,
        verified_property_class="010", class_valid_from="2024-01-01", class_valid_to="2024-12-31",
        class_source="https://county.example/historical", land_only_at_sale="true", market_sale="true",
        single_parcel_sale="true", transaction_source="https://county.example/deed",
        verified_acres="1.5", latitude="40.7", longitude="-89.6", geographic_area="A",
        features_as_of="2024-01-01", features_source="https://county.example/features")])
    return sales, mapping, reviews


def test_verified_land_and_string_codes():
    cohort, _, audit = build_verified_cohort(*examples())
    assert len(cohort) == 1
    assert cohort.iloc[0].acres == 1.5
    assert cohort.iloc[0].parcel_id == "001"
    assert audit["investment_suitable"] is False
    assert "total_assessed_value" not in cohort


@pytest.mark.parametrize("column,value,reason", [
    ("verified_property_class", "10", "unverified_or_non_land_class"),
    ("class_valid_from", "2025-01-01", "classification_not_valid_at_sale"),
    ("class_valid_to", "2023-12-31", "classification_not_valid_at_sale"),
    ("features_as_of", "2024-03-02", "features_not_available_at_sale"),
    ("market_sale", "false", "unverified_market_sale"),
    ("single_parcel_sale", "", "unverified_single_parcel_sale"),
    ("land_only_at_sale", "false", "unverified_land_only_at_sale"),
    ("transaction_source", "", "missing_evidence_source"),
    ("latitude", "NaN", "invalid_verified_features"),
    ("geographic_area", "", "missing_geographic_area"),
])
def test_unknown_invalid_or_future_evidence_excludes(column, value, reason):
    sales, mapping, reviews = examples()
    reviews.loc[0, column] = value
    cohort, excluded, audit = build_verified_cohort(sales, mapping, reviews)
    assert cohort.empty
    assert excluded.iloc[0].exclusion_reason == reason
    assert audit["eligible_rows"] + audit["excluded_rows"] == audit["unique_transactions"]


def test_current_improved_category_and_missing_review_cannot_train():
    sales, mapping, reviews = examples()
    mapping.loc[0, "verified_category"] = "Residential"
    assert build_verified_cohort(sales, mapping, reviews)[0].empty
    assert build_verified_cohort(sales, mapping, pd.DataFrame(columns=REVIEW_COLUMNS))[0].empty


@pytest.mark.parametrize("which", ["mapping", "reviews"])
def test_conflicting_duplicate_evidence_aborts(which):
    sales, mapping, reviews = examples()
    if which == "mapping":
        mapping = pd.concat([mapping, mapping])
    else:
        reviews = pd.concat([reviews, reviews])
    with pytest.raises(ValueError, match="unique"):
        build_verified_cohort(sales, mapping, reviews)
