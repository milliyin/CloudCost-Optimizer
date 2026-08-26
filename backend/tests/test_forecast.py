import pytest
from datetime import date, timedelta
from app.models.cost_record import CostRecord
from app.ml.feature_engineering import prepare_time_series_dataframe, build_forecasting_features
from app.ml.forecaster import should_prefer_baseline, train_and_forecast_service


def test_time_series_feature_engineering():
    records = []
    base_date = date(2026, 5, 1)
    for i in range(60):
        records.append(
            CostRecord(
                organization_id=1,
                account_id="123456789012",
                service="Amazon Elastic Compute Cloud - Compute",
                region="us-east-1",
                amount=100.0 + (i * 0.5),
                currency="USD",
                date=base_date + timedelta(days=i),
            )
        )

    df_raw = prepare_time_series_dataframe(records)
    assert len(df_raw) == 60
    assert "date" in df_raw.columns
    assert "amount" in df_raw.columns

    df_features = build_forecasting_features(df_raw)
    assert "lag_1" in df_features.columns
    assert "lag_7" in df_features.columns
    assert "rolling_7d_mean" in df_features.columns
    assert not df_features.isna().any().any()


def test_train_and_forecast_time_aware_split():
    records = []
    base_date = date(2026, 5, 1)
    for i in range(90):
        records.append(
            CostRecord(
                organization_id=1,
                account_id="123456789012",
                service="Amazon Elastic Compute Cloud - Compute",
                region="us-east-1",
                amount=50.0 + (i * 0.2),
                currency="USD",
                date=base_date + timedelta(days=i),
            )
        )

    result = train_and_forecast_service(records, horizon_days=30)
    assert result.service == "total"
    assert result.horizon_days == 30
    assert len(result.forecast) == 30
    assert len(result.historical) == 90
    assert result.mae >= 0.0
    assert result.rmse >= 0.0
    assert result.baseline_mae >= 0.0

    # Verify forecast points have date, amount, lower_bound, upper_bound
    first_f = result.forecast[0]
    assert "date" in first_f
    assert "amount" in first_f
    assert "lower_bound" in first_f
    assert "upper_bound" in first_f
    assert first_f["lower_bound"] <= first_f["amount"] <= first_f["upper_bound"]


def test_train_and_forecast_short_history_uses_low_history_model():
    records = []
    base_date = date(2026, 8, 20)
    for i in range(6):
        records.append(
            CostRecord(
                organization_id=1,
                account_id="123456789012",
                service="Amazon Elastic Compute Cloud - Compute",
                region="us-east-1",
                amount=2.0 + (i * 0.3),
                currency="USD",
                date=base_date + timedelta(days=i),
            )
        )

    result = train_and_forecast_service(records, horizon_days=14)
    assert result.model_name in {"Ridge Autoregressive (Low-History)", "Naive Baseline (Low-History)"}
    assert result.data_points == 6
    assert len(result.forecast) == 14
    assert result.limited_history_note == "Forecast is based on limited billing history."


def test_should_prefer_baseline_for_low_history_when_baseline_is_better():
    assert should_prefer_baseline(data_points=6, baseline_mae=0.30, ml_mae=1.25) is True
    assert should_prefer_baseline(data_points=20, baseline_mae=0.30, ml_mae=1.25) is False
    assert should_prefer_baseline(data_points=6, baseline_mae=1.25, ml_mae=0.30) is False
