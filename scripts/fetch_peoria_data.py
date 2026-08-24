"""Download public Peoria County parcel/sales records for model research."""

from pathlib import Path

from sources.peoria_county import fetch_parcels_with_sales, fetch_sales_history

OUT_DIR = Path("data/official")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    parcels = fetch_parcels_with_sales()
    parcel_path = OUT_DIR / "peoria_parcel_sales.csv"
    parcels.to_csv(parcel_path, index=False)
    print(f"Saved {len(parcels):,} parcel-sale rows to {parcel_path}")

    history = fetch_sales_history()
    history_path = OUT_DIR / "peoria_sales_history.csv"
    history.to_csv(history_path, index=False)
    print(f"Saved {len(history):,} sales-history rows to {history_path}")


if __name__ == "__main__":
    main()
