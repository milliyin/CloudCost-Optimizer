from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.metrics import mean_absolute_error, root_mean_squared_error

from app.ml.feature_engineering import build_forecasting_features, prepare_time_series_dataframe


FEATURE_COLUMNS = [
    "day_of_week",
    "day_of_month",
    "month",
    "is_weekend",
    "lag_1",
    "lag_7",
    "lag_14",
    "rolling_7d_mean",
    "rolling_7d_std",
    "rolling_14d_mean",
]


@dataclass
class ForecastResult:
    service: str
    historical: list[dict[str, Any]]
    forecast: list[dict[str, Any]]
    model_name: str
    mae: float
    rmse: float
    baseline_mae: float
    baseline_rmse: float
    horizon_days: int
    data_points: int


def _calculate_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> tuple[float, float]:
    if len(y_true) == 0 or len(y_pred) == 0:
        return 0.0, 0.0
    mae = float(mean_absolute_error(y_true, y_pred))
    rmse = float(root_mean_squared_error(y_true, y_pred))
    return round(mae, 4), round(rmse, 4)


def train_and_forecast_service(
    cost_records: list[Any],
    service_filter: str | None = None,
    horizon_days: int = 30,
) -> ForecastResult:
    """
    Trains baseline and ML forecasting models on historical cost records using a strict
    chronological (time-aware) train/test split to avoid data leakage.
    Iteratively predicts future daily costs with confidence bounds.
    """
    service_key = service_filter or "total"
    raw_df = prepare_time_series_dataframe(cost_records, service_filter=service_filter)

    if raw_df.empty or len(raw_df) < 7:
        # Fallback for empty or tiny datasets
        today = date.today()
        historical = [{"date": today.isoformat(), "amount": 0.0}]
        forecast = [
            {
                "date": (today + timedelta(days=i + 1)).isoformat(),
                "amount": 0.0,
                "lower_bound": 0.0,
                "upper_bound": 0.0,
            }
            for i in range(horizon_days)
        ]
        return ForecastResult(
            service=service_key,
            historical=historical,
            forecast=forecast,
            model_name="Fallback Zero",
            mae=0.0,
            rmse=0.0,
            baseline_mae=0.0,
            baseline_rmse=0.0,
            horizon_days=horizon_days,
            data_points=len(raw_df),
        )

    df = build_forecasting_features(raw_df)
    n = len(df)

    # --- TIME-AWARE TRAIN / TEST SPLIT ---
    # Critical Rule: Never use random shuffle split for time series!
    # Random splitting leaks future data into past training samples, causing falsely optimistic accuracy.
    split_index = max(1, int(n * 0.8)) if n >= 10 else n - 1
    train_df = df.iloc[:split_index].copy()
    test_df = df.iloc[split_index:].copy()

    X_train = train_df[FEATURE_COLUMNS]
    y_train = train_df["amount"].values

    # Baseline Model: Simple 7-day Naive Moving Average / Linear Regression without lags
    baseline_model = LinearRegression()
    baseline_model.fit(train_df[["day_of_week", "is_weekend"]], y_train)

    # Advanced ML Model: Ridge Regression with lag & rolling window features
    ml_model = Ridge(alpha=1.0)
    ml_model.fit(X_train, y_train)

    # Evaluate on Test Set
    if not test_df.empty:
        X_test = test_df[FEATURE_COLUMNS]
        y_test = test_df["amount"].values

        baseline_preds = baseline_model.predict(test_df[["day_of_week", "is_weekend"]])
        ml_preds = ml_model.predict(X_test)

        baseline_mae, baseline_rmse = _calculate_metrics(y_test, baseline_preds)
        ml_mae, ml_rmse = _calculate_metrics(y_test, ml_preds)
    else:
        baseline_mae = baseline_rmse = ml_mae = ml_rmse = 0.05

    # Compute Residual Standard Deviation for prediction error bounds
    train_preds = ml_model.predict(X_train)
    residuals = y_train - train_preds
    std_residual = float(np.std(residuals)) if len(residuals) > 1 else 0.1

    # --- MULTI-STEP HORIZON FORECASTING ---
    forecast_df = df.copy()
    future_points = []
    last_date = pd.to_datetime(df["date"].max())

    for step in range(1, horizon_days + 1):
        target_date = last_date + pd.Timedelta(days=step)
        
        # Build features for current forecast date
        day_of_week = target_date.dayofweek
        day_of_month = target_date.day
        month = target_date.month
        is_weekend = 1 if day_of_week in [5, 6] else 0

        recent_amounts = forecast_df["amount"].values
        lag_1 = float(recent_amounts[-1])
        lag_7 = float(recent_amounts[-7]) if len(recent_amounts) >= 7 else lag_1
        lag_14 = float(recent_amounts[-14]) if len(recent_amounts) >= 14 else lag_1

        roll_7_mean = float(np.mean(recent_amounts[-7:])) if len(recent_amounts) >= 7 else float(np.mean(recent_amounts))
        roll_7_std = float(np.std(recent_amounts[-7:])) if len(recent_amounts) >= 7 else 0.0
        roll_14_mean = float(np.mean(recent_amounts[-14:])) if len(recent_amounts) >= 14 else float(np.mean(recent_amounts))

        step_features = pd.DataFrame(
            [
                {
                    "day_of_week": day_of_week,
                    "day_of_month": day_of_month,
                    "month": month,
                    "is_weekend": is_weekend,
                    "lag_1": lag_1,
                    "lag_7": lag_7,
                    "lag_14": lag_14,
                    "rolling_7d_mean": roll_7_mean,
                    "rolling_7d_std": roll_7_std,
                    "rolling_14d_mean": roll_14_mean,
                }
            ]
        )

        pred_amount = max(0.0, float(ml_model.predict(step_features[FEATURE_COLUMNS])[0]))

        # Confidence interval widens slightly with forecast step horizon
        horizon_penalty = math.sqrt(1.0 + (step / 30.0))
        margin = 1.96 * std_residual * horizon_penalty

        lower_bound = max(0.0, pred_amount - margin)
        upper_bound = pred_amount + margin

        future_points.append(
            {
                "date": target_date.strftime("%Y-%m-%d"),
                "amount": round(pred_amount, 2),
                "lower_bound": round(lower_bound, 2),
                "upper_bound": round(upper_bound, 2),
            }
        )

        # Append forecast to df for next step's autoregressive lags
        new_row = pd.DataFrame([{"date": target_date, "amount": pred_amount}])
        forecast_df = pd.concat([forecast_df, new_row], ignore_index=True)

    historical = [
        {
            "date": pd.to_datetime(row["date"]).strftime("%Y-%m-%d"),
            "amount": round(float(row["amount"]), 2),
        }
        for _, row in raw_df.iterrows()
    ]

    return ForecastResult(
        service=service_key,
        historical=historical,
        forecast=future_points,
        model_name="Ridge Autoregressive (Time-Aware Split)",
        mae=ml_mae,
        rmse=ml_rmse,
        baseline_mae=baseline_mae,
        baseline_rmse=baseline_rmse,
        horizon_days=horizon_days,
        data_points=n,
    )
