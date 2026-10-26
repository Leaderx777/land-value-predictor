import numpy as np
import pandas as pd
import pytest

from research_evaluation import chronological_partitions, comparable_estimates, calibration_radius
from train_peoria_baseline import evaluate


def sample(n=150):
    return pd.DataFrame({"parcel_id": [str(i) for i in range(n)],
        "sale_date": pd.date_range("2023-01-01", periods=n, tz="UTC"),
        "sale_price": np.arange(n) * 10 + 12000., "acres": 1.,
        "latitude": 40.7, "longitude": -89.6,
        "verified_category": "Residential Vacant Land",
        "geographic_area": ["A" if i % 2 else "B" for i in range(n)]})


def test_date_ties_and_repeat_parcels_never_cross_partitions():
    frame = sample()
    frame.loc[90, "parcel_id"] = frame.loc[0, "parcel_id"]
    frame.loc[89, "sale_date"] = frame.loc[90, "sale_date"]
    train, calibration, test = chronological_partitions(frame)
    assert train.sale_date.max() < calibration.sale_date.min()
    assert calibration.sale_date.max() < test.sale_date.min()
    assert not set(train.parcel_id) & set(calibration.parcel_id)
    assert not set(train.parcel_id) & set(test.parcel_id)
    assert not set(calibration.parcel_id) & set(test.parcel_id)


def test_comparables_exclude_future_same_parcel_distant_and_other_categories():
    training, subjects = sample(10).iloc[:9].copy(), sample(10).iloc[9:].copy()
    training.loc[0, "sale_date"] = subjects.sale_date.iloc[0]
    training.loc[1, "parcel_id"] = subjects.parcel_id.iloc[0]
    training.loc[2, "latitude"] = 50.
    training.loc[3, "verified_category"] = "Farmland Only"
    training.loc[4, "acres"] = 10.
    training.loc[5, "sale_date"] = pd.Timestamp("2010-01-01", tz="UTC")
    predictions, counts = comparable_estimates(training, subjects)
    assert counts[0] == 3
    assert np.isfinite(predictions[0])
    assert np.isnan(comparable_estimates(training.iloc[:6], subjects)[0][0])


def test_calibration_uses_finite_sample_rank():
    assert calibration_radius(np.arange(20)) == 18
    with pytest.raises(ValueError):
        calibration_radius([])


def test_evaluation_reports_abstention_and_geographic_checks_without_promotion():
    _, report, output = evaluate(sample())
    assert report["investment_suitable"] is False
    assert set(report["geographic_holdouts"]) == {"A", "B"}
    assert report["supported_rows"] == len(output)
    assert report["interval"]["calibration_rows"] >= 20
    distant = sample()
    distant.loc[120:, "latitude"] = 50.
    _, report, output = evaluate(distant)
    assert report["abstained_rows"] == 30
    assert output.estimated_value.isna().all()


def test_blocked_run_removes_stale_model_and_records_reason(tmp_path, monkeypatch):
    import json
    import train_peoria_baseline as trainer
    from land_validation import sha256
    source = tmp_path / "sales.csv"
    sample(0).to_csv(source, index=False)
    (tmp_path / "audit.json").write_text(json.dumps({"cohort_sha256": sha256(source), "eligible_rows": 0}))
    output = tmp_path / "output"
    output.mkdir()
    model = output / "model.joblib"
    model.write_bytes(b"stale")
    monkeypatch.setattr(trainer, "INPUT", source)
    monkeypatch.setattr(trainer, "OUT_DIR", output)
    monkeypatch.setattr(trainer, "MODEL_PATH", model)
    monkeypatch.setattr(trainer, "METRICS_PATH", output / "metrics.json")
    with pytest.raises(SystemExit) as error:
        trainer.main()
    assert error.value.code == 2
    assert not model.exists()
    report = json.loads((output / "metrics.json").read_text())
    assert report["investment_suitable"] is False
    assert "No verified" in report["reason"]
