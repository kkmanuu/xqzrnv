"""Forecast publication selection and forecast/actual matching.

Key rule: for each delivery period, the forecast a trader could have used is the LATEST WINDFOR
record with publishTime <= the day-ahead cutoff on D-1 (UK local time, DST-aware), where D is the
UK local delivery date of the period.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pandas as pd

LONDON = ZoneInfo("Europe/London")


def parse_hhmm(value: str) -> time:
    try:
        h, m = value.split(":")
        return time(int(h), int(m))
    except Exception as e:  # noqa: BLE001
        raise ValueError(f"cutoff must be HH:MM, got {value!r}") from e


def cutoff_utc(delivery_date: date, cutoff_local: str) -> pd.Timestamp:
    """UTC instant of cutoff_local on D-1 in Europe/London. Built from local wall-clock so DST is right."""
    d1 = delivery_date - timedelta(days=1)
    local = datetime.combine(d1, parse_hhmm(cutoff_local), tzinfo=LONDON)
    return pd.Timestamp(local).tz_convert("UTC")


def delivery_date_local(start_time: pd.Series) -> pd.Series:
    return start_time.dt.tz_convert(LONDON).dt.date


def select_asof_cutoff(fc: pd.DataFrame, cutoff_local: str) -> pd.DataFrame:
    """Latest forecast per start_time published at or before that period's D-1 cutoff."""
    if fc.empty:
        return fc.assign(delivery_date=pd.Series(dtype=object), cutoff_utc=pd.Series(dtype="datetime64[ns, UTC]"))
    df = fc.copy()
    df["delivery_date"] = delivery_date_local(df["start_time"])
    cmap = {d: cutoff_utc(d, cutoff_local) for d in df["delivery_date"].unique()}
    df["cutoff_utc"] = df["delivery_date"].map(cmap)
    df = df[df["publish_time"] <= df["cutoff_utc"]]
    df = df.sort_values(["start_time", "publish_time"]).drop_duplicates("start_time", keep="last")
    return df.reset_index(drop=True)


def select_latest(fc: pd.DataFrame) -> pd.DataFrame:
    """Latest forecast per start_time regardless of cutoff (what is available 'now')."""
    if fc.empty:
        return fc
    df = fc.sort_values(["start_time", "publish_time"]).drop_duplicates("start_time", keep="last")
    return df.reset_index(drop=True)


def match(forecast: pd.DataFrame, actuals: pd.DataFrame) -> pd.DataFrame:
    """Inner-join forecasts to actuals on start_time; error = forecast - actual (MW)."""
    cols = ["start_time", "publish_time", "forecast_mw", "actual_mw", "error_mw", "horizon_h"]
    if forecast.empty or actuals.empty:
        return pd.DataFrame(columns=cols)
    m = forecast.merge(actuals, on="start_time", how="inner")
    m["error_mw"] = m["forecast_mw"] - m["actual_mw"]
    m["horizon_h"] = (m["start_time"] - m["publish_time"]).dt.total_seconds() / 3600.0
    return m.sort_values("start_time").reset_index(drop=True)[cols + [c for c in m.columns if c not in cols]]
