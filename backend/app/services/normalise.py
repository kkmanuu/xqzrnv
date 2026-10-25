"""Validation and normalisation of raw Elexon records into clean DataFrames (all times UTC)."""
from __future__ import annotations

import logging

import pandas as pd

log = logging.getLogger(__name__)


def _to_utc(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s, utc=True, errors="coerce")


def normalise_actuals(rows: list[dict]) -> pd.DataFrame:
    """FUELHH rows -> DataFrame[start_time, actual_mw]; WIND only, de-duplicated, invalid rows dropped."""
    cols = ["start_time", "actual_mw"]
    if not rows:
        return pd.DataFrame(columns=cols)
    df = pd.DataFrame(rows)
    if "fuelType" in df:
        df = df[df["fuelType"].astype(str).str.upper() == "WIND"]
    if not {"startTime", "generation"} <= set(df.columns):
        log.warning("Actuals response missing startTime/generation fields")
        return pd.DataFrame(columns=cols)
    out = pd.DataFrame({
        "start_time": _to_utc(df["startTime"]),
        "actual_mw": pd.to_numeric(df["generation"], errors="coerce"),
        "_pub": _to_utc(df["publishTime"]) if "publishTime" in df else pd.NaT,
    })
    dropped = int(out[["start_time", "actual_mw"]].isna().any(axis=1).sum())
    if dropped:
        log.warning("Dropped %d invalid actuals rows", dropped)
    out = out.dropna(subset=["start_time", "actual_mw"]).sort_values(["start_time", "_pub"])
    out = out.drop_duplicates("start_time", keep="last")  # latest publication wins
    return out[cols].reset_index(drop=True)


def normalise_forecasts(rows: list[dict]) -> pd.DataFrame:
    """WINDFOR rows -> DataFrame[start_time, publish_time, forecast_mw]; duplicates removed."""
    cols = ["start_time", "publish_time", "forecast_mw"]
    if not rows:
        return pd.DataFrame(columns=cols)
    df = pd.DataFrame(rows)
    if not {"startTime", "publishTime", "generation"} <= set(df.columns):
        log.warning("Forecast response missing required fields")
        return pd.DataFrame(columns=cols)
    out = pd.DataFrame({
        "start_time": _to_utc(df["startTime"]),
        "publish_time": _to_utc(df["publishTime"]),
        "forecast_mw": pd.to_numeric(df["generation"], errors="coerce"),
    })
    dropped = int(out.isna().any(axis=1).sum())
    if dropped:
        log.warning("Dropped %d invalid forecast rows", dropped)
    out = out.dropna().drop_duplicates(["start_time", "publish_time"], keep="last")
    return out.sort_values(["start_time", "publish_time"])[cols].reset_index(drop=True)
