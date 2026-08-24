from sources import peoria_county


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_fetch_parcels_with_sales_normalizes_public_fields(monkeypatch):
    payload = {
        "features": [
            {
                "attributes": {
                    "PIN": "01-01-100-001",
                    "PropClass": "V",
                    "CITY": "Peoria",
                    "PZIP": "61614",
                    "land_lot_value": 12000.0,
                    "total_assessed_value": 12000.0,
                    "Acres": 5.25,
                    "NET_SELLING_PRICE": 45000.0,
                    "SALES_DATE": 1704067200000,
                }
            }
        ]
    }

    monkeypatch.setattr(
        peoria_county.requests,
        "get",
        lambda *args, **kwargs: FakeResponse(payload),
    )

    df = peoria_county.fetch_parcels_with_sales()

    assert len(df) == 1
    assert df.loc[0, "parcel_id"] == "01-01-100-001"
    assert df.loc[0, "county"] == "Peoria"
    assert df.loc[0, "state"] == "IL"
    assert df.loc[0, "acres"] == 5.25
    assert df.loc[0, "sale_price"] == 45000.0
    assert "owner_name" not in df.columns
