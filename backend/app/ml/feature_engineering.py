from __future__ import annotations

from typing import Any
import pandas as pd
import numpy as np


def prepare_time_series_dataframe(records: list[Any], service_filter: str | None = None) -> pd.DataFrame:
    """
    Extracts CostRecord data, groups by date, reindexes missing dates with 0.0,
    and returns a clean, continuous daily pandas DataFrame.
    """
    if not records:
        return pd.DataFrame(columns=["date", "amount"])

    filtered_records = []
    for r in records:
        service_name = getattr(r, "service", None)
        record_date = getattr(r, "date", None)
        amount = float(getattr(r, "amount", 0.0))

        if service_filter and service_filter != "total" and service_name != service_filter:
            continue
        if record_date is not None:
            filtered_records.append({"date": pd.to_datetime(record_date), "amount": amount})

    if not filtered_records:
        return pd.DataFrame(columns=["date", "amount"])

    df = pd.DataFrame(filtered_records)
    df = df.groupby("date", as_index=False)["amount"].sum()
    df = df.sort_values("date").reset_index(drop=True)

    # Reindex to complete continuous daily date range
    min_date = df["date"].min()
    max_date = df["date"].max()
    full_range = pd.date_range(start=min_date, end=max_date, freq="D")
    df = df.set_index("date").reindex(full_range, fill_value=0.0).rename_axis("date").reset_index()
    return df


def build_forecasting_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Engineers time-based, lag, and rolling window features for time-series ML models.
    """
    if df.empty or len(df) < 3:
        return df.copy()

    data = df.copy()
    data["date"] = pd.to_datetime(data["date"])

    # Time features
    data["day_of_week"] = data["date"].dt.dayofweek
    data["day_of_month"] = data["date"].dt.day
    data["month"] = data["date"].dt.month
    data["is_weekend"] = data["day_of_week"].isin([5, 6]).astype(int)

    # Multi-frequency Fourier seasonal harmonics (7D weekly, 14D biweekly, 30D monthly)
    data["sin_7"] = np.sin(2 * np.pi * data["day_of_week"] / 7.0)
    data["cos_7"] = np.cos(2 * np.pi * data["day_of_week"] / 7.0)
    data["sin_14"] = np.sin(2 * np.pi * (data["date"].dt.dayofyear % 14) / 14.0)
    data["cos_14"] = np.cos(2 * np.pi * (data["date"].dt.dayofyear % 14) / 14.0)
    data["sin_30"] = np.sin(2 * np.pi * data["day_of_month"] / 30.0)
    data["cos_30"] = np.cos(2 * np.pi * data["day_of_month"] / 30.0)

    # Autoregressive lag features (shift by 1+ to prevent future data leakage)
    data["lag_1"] = data["amount"].shift(1)
    data["lag_7"] = data["amount"].shift(7)
    data["lag_14"] = data["amount"].shift(14)
    data["lag_30"] = data["amount"].shift(30)

    # Rolling window features
    data["rolling_7d_mean"] = data["amount"].shift(1).rolling(window=7, min_periods=1).mean()
    data["rolling_7d_std"] = data["amount"].shift(1).rolling(window=7, min_periods=1).std()
    data["rolling_14d_mean"] = data["amount"].shift(1).rolling(window=14, min_periods=1).mean()

    # Fill NaNs from shifting
    data["lag_1"] = data["lag_1"].bfill().fillna(0.0)
    data["lag_7"] = data["lag_7"].bfill().fillna(0.0)
    data["lag_14"] = data["lag_14"].bfill().fillna(0.0)
    data["lag_30"] = data["lag_30"].bfill().fillna(0.0)
    data["rolling_7d_mean"] = data["rolling_7d_mean"].bfill().fillna(0.0)
    data["rolling_7d_std"] = data["rolling_7d_std"].fillna(0.0)
    data["rolling_14d_mean"] = data["rolling_14d_mean"].bfill().fillna(0.0)

    return data
