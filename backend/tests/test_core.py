from datetime import date

import pandas as pd
import pytest

from app.services.metrics import compute_metrics
from app.services.normalise import normalise_actuals, normalise_forecasts
from app.services.selection import cutoff_utc, match, select_asof_cutoff, select_latest


def ts(s):
    return pd.Timestamp(s, tz="UTC")


def test_actuals_filter_wind_dedupe_and_drop_invalid():
    rows = [
        {"fuelType": "WIND", "startTime": "2026-01-02T00:00:00Z", "generation": 100, "publishTime": "2026-01-02T00:30:00Z"},
        {"fuelType": "WIND", "startTime": "2026-01-02T00:00:00Z", "generation": 120, "publishTime": "2026-01-02T01:00:00Z"},
        {"fuelType": "CCGT", "startTime": "2026-01-02T00:00:00Z", "generation": 9999},
        {"fuelType": "WIND", "startTime": "2026-01-02T00:30:00Z", "generation": None},
    ]
    df = normalise_actuals(rows)
    assert list(df["actual_mw"]) == [120.0]


def test_forecast_dedupe_and_missing_fields():
    rows = [
        {"startTime": "2026-01-02T00:00Z", "publishTime": "2026-01-01T06:00Z", "generation": 1},
        {"startTime": "2026-01-02T00:00Z", "publishTime": "2026-01-01T06:00Z", "generation": 2},
        {"startTime": "bad", "publishTime": "2026-01-01T06:00Z", "generation": 3},
    ]
    df = normalise_forecasts(rows)
    assert len(df) == 1 and df.iloc[0]["forecast_mw"] == 2
    assert normalise_forecasts([{"foo": 1}]).empty


def test_cutoff_winter_and_dst():
    assert cutoff_utc(date(2026, 1, 15), "09:20") == ts("2026-01-14T09:20")  # GMT
    # Clocks go forward 29 Mar 2026 (01:00 UTC). D-1 = 28 Mar is still GMT; D-1 = 29 Mar is BST.
    assert cutoff_utc(date(2026, 3, 29), "09:20") == ts("2026-03-28T09:20")
    assert cutoff_utc(date(2026, 3, 30), "09:20") == ts("2026-03-29T08:20")  # BST: 09:20 local = 08:20 UTC


def test_asof_cutoff_never_uses_later_publication():
    fc = pd.DataFrame({
        "start_time": [ts("2026-01-15T12:00")] * 3,
        "publish_time": [ts("2026-01-14T06:00"), ts("2026-01-14T09:20"), ts("2026-01-14T09:21")],
        "forecast_mw": [10.0, 20.0, 30.0],
    })
    sel = select_asof_cutoff(fc, "09:20")
    assert len(sel) == 1 and sel.iloc[0]["forecast_mw"] == 20.0  # boundary inclusive, 09:21 excluded
    assert select_latest(fc).iloc[0]["forecast_mw"] == 30.0
    assert select_asof_cutoff(fc, "05:00").empty  # nothing was available yet


def test_match_and_metrics():
    fc = pd.DataFrame({"start_time": [ts("2026-01-15T00:00"), ts("2026-01-15T00:30"), ts("2026-01-15T01:00")],
                       "publish_time": [ts("2026-01-14T09:00")] * 3, "forecast_mw": [110.0, 90.0, 50.0]})
    ac = pd.DataFrame({"start_time": [ts("2026-01-15T00:00"), ts("2026-01-15T00:30")], "actual_mw": [100.0, 100.0]})
    m = match(fc, ac)
    assert len(m) == 2  # unmatched forecast period excluded
    r = compute_metrics(m)
    assert r["mae_mw"] == 10 and r["rmse_mw"] == 10 and r["bias_mw"] == 0
    assert r["mape_pct"] == pytest.approx(10.0)


def test_mape_excludes_near_zero_actuals():
    m = pd.DataFrame({"error_mw": [5.0, 50.0], "actual_mw": [0.0, 200.0]})
    r = compute_metrics(m)
    assert r["mape_n"] == 1 and r["mape_pct"] == pytest.approx(25.0)
    assert compute_metrics(pd.DataFrame({"error_mw": [1.0], "actual_mw": [0.0]}))["mape_pct"] is None


def test_empty_metrics():
    assert compute_metrics(match(pd.DataFrame(), pd.DataFrame()))["n"] == 0
