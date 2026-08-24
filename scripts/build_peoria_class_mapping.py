"""Build a reviewable mapping template for Peoria County property classes.

This script does not guess code meanings. It inventories observed class values from the
clean real-sales dataset and creates a CSV that can be manually/independently verified
against official county documentation before any class is used to isolate land-only sales.
"""

from pathlib import Path

import pandas as pd

INPUT = Path("artifacts/real_data/peoria_clean_sales.csv")
OUTPUT = Path("artifacts/real_data/peoria_property_class_mapping.csv")

OFFICIAL_CATEGORIES = [
    "Residential",
    "Residential Vacant Land",
    "Condo",
    "Duplex",
    "Commercial / Industrial",
    "Farm Improved",
    "Farmland Only",
    "Other / Unknown",
]


def build_mapping(df: pd.DataFrame) -> pd.DataFrame:
    if "property_class" not in df.columns:
        raise ValueError("property_class column is required")

    counts = (
        df.groupby("property_class", dropna=False)
        .size()
        .reset_index(name="sales")
        .sort_values("sales", ascending=False)
    )
    counts["verified_category"] = ""
    counts["land_only"] = ""
    counts["verification_source"] = ""
    counts["notes"] = ""
    return counts


def main() -> None:
    if not INPUT.exists():
        raise SystemExit(
            "Clean Peoria sales not found. Run `python scripts/profile_peoria_sales.py` first."
        )

    df = pd.read_csv(INPUT)
    mapping = build_mapping(df)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    mapping.to_csv(OUTPUT, index=False)

    print(f"Wrote {len(mapping):,} observed property classes to {OUTPUT}")
    print("Verify each code/value before marking land_only=true.")
    print("Official county category labels available for review:")
    for category in OFFICIAL_CATEGORIES:
        print(f"- {category}")


if __name__ == "__main__":
    main()
