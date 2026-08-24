from train import FEATURES, load_data, train_model


def test_sample_data_has_required_columns():
    df = load_data()
    for column in FEATURES + ["price"]:
        assert column in df.columns
    assert len(df) >= 20


def test_training_returns_metrics():
    df = load_data()
    model, metrics = train_model(df)
    assert hasattr(model, "predict")
    assert "mae" in metrics
    assert "r2" in metrics
    assert metrics["rows"] == len(df)
