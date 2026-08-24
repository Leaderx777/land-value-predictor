import pandas as pd

from scripts.build_peoria_class_mapping import build_mapping


def test_build_mapping_preserves_unknown_codes_for_verification():
    df = pd.DataFrame({"property_class": ["100", "100", "400", None]})
    mapping = build_mapping(df)

    assert set(mapping.columns) == {
        "property_class",
        "sales",
        "verified_category",
        "land_only",
        "verification_source",
        "notes",
    }
    assert mapping.loc[mapping["property_class"] == "100", "sales"].iloc[0] == 2
    assert mapping["verified_category"].eq("").all()
    assert mapping["land_only"].eq("").all()
