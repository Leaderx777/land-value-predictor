"""Profile official Peoria County parcel-sale data before model training."""

from pathlib import Path

import pandas as pd

from real_data import prepare_peoria_sales, property_class_profile

INPUT = Path("data/official/peoria_parcel_sales.csv")
OUT_DIR = Path("artifacts/real_data")


def main() -> None:
    if not INPUT.exists():
        raise SystemExit(
            "Official Peoria data not found. Run `python scripts/fetch_peoria_data.py` first."
        )

    raw = pd.read_csv(INPUT)
    clean = prepare_peoria_sales(raw)
    profile = property_class_profile(clean)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    clean.to_csv(OUT_DIR / "peoria_clean_sales.csv", index=False)
    profile.to_csv(OUT_DIR / "peoria_property_class_profile.csv", index=False)

    print(f"Raw rows: {len(raw):,}")
    print(f"Clean sale rows: {len(clean):,}")
    print(f"Property classes: {profile['property_class'].nunique(dropna=False):,}")
    if len(clean):
        print(f"Sale years: {clean['sale_year'].min()}-{clean['sale_year'].max()}")
        print(f"Median acres: {clean['acres'].median():,.2f}")
        print(f"Median sale price: ${clean['sale_price'].median():,.0f}")
        print(f"Median price/acre: ${clean['sale_price_per_acre'].median():,.0f}")


if __name__ == "__main__":
    main()
