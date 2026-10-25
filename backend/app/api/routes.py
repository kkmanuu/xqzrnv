from __future__ import annotations

import logging
from datetime import date

import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from app.config import get_settings
from app.services.elexon_client import ElexonError
from app.services.metrics import compute_metrics
from app.services.selection import cutoff_utc, delivery_date_local, match, select_asof_cutoff, select_latest
from app.services.store import get_dataset

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api")

CUTOFF_RE = r"^([01]\d|2[0-3]):[0-5]\d$"
Mode = Query("asof", pattern="^(asof|latest)$", description="asof = latest forecast published before D-1 cutoff; latest = latest published at all")


def _dataset():
    try:
        return get_dataset()
    except ElexonError as e:
        raise HTTPException(status_code=503, detail=f"Elexon data unavailable: {e}") from e


def _check_range(d_from: date, d_to: date) -> None:
    s = get_settings()
    lo, hi = date.fromisoformat(s.window_start), date.fromisoformat(s.window_end)
    if d_from > d_to:
        raise HTTPException(422, "from must be on or before to")
    if d_from < lo or d_to > hi:
        raise HTTPException(422, f"Dates must be within the pilot window {lo}..{hi}")


def _in_range(df: pd.DataFrame, d_from: date, d_to: date) -> pd.DataFrame:
    if df.empty:
        return df
    d = delivery_date_local(df["start_time"])
    return df[(d >= d_from) & (d <= d_to)]


def _iso(s: pd.Series) -> list[str]:
    return s.dt.strftime("%Y-%m-%dT%H:%M:%SZ").tolist()


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/meta")
def meta():
    ds = _dataset()
    s = get_settings()
    return {
        "window": {"from": s.window_start, "to": s.window_end},
        "default_cutoff_local": s.default_cutoff_local,
        "timezone": "Europe/London",
        "units": "MW",
        "fetched_at": ds.fetched_at,
        "latest_forecast_publish_time": None if ds.forecasts.empty else ds.forecasts["publish_time"].max().isoformat(),
        "latest_actual_start_time": None if ds.actuals.empty else ds.actuals["start_time"].max().isoformat(),
        "counts": {"actuals": len(ds.actuals), "forecasts": len(ds.forecasts)},
        "cutoff_presets": [
            {"label": "EPEX GB hourly day-ahead", "value": "09:20"},
            {"label": "N2EX hourly day-ahead", "value": "09:50"},
            {"label": "EPEX GB half-hourly day-ahead", "value": "15:30"},
        ],
    }


@router.get("/actuals")
def actuals(date_from: date = Query(alias="from"), date_to: date = Query(alias="to")):
    _check_range(date_from, date_to)
    a = _in_range(_dataset().actuals, date_from, date_to)
    return {"unit": "MW", "count": len(a), "data": [
        {"start_time": t, "actual_mw": v} for t, v in zip(_iso(a["start_time"]), a["actual_mw"])] if len(a) else []}


@router.get("/forecast-publications")
def forecast_publications(delivery_date: date = Query(alias="date"), cutoff: str = Query(None, pattern=CUTOFF_RE)):
    """Every publication that covers the delivery day, flagged against the D-1 cutoff."""
    _check_range(delivery_date, delivery_date)
    cutoff = cutoff or get_settings().default_cutoff_local
    f = _in_range(_dataset().forecasts, delivery_date, delivery_date)
    cut = cutoff_utc(delivery_date, cutoff)
    if f.empty:
        return {"delivery_date": delivery_date.isoformat(), "cutoff_utc": cut.isoformat(), "publications": []}
    g = f.groupby("publish_time").size().reset_index(name="periods").sort_values("publish_time")
    before = g[g["publish_time"] <= cut]
    last_before = before["publish_time"].max() if len(before) else None
    g["available_at_cutoff"] = g["publish_time"] <= cut
    g["is_latest_before_cutoff"] = g["publish_time"] == last_before
    g["is_latest_overall"] = g["publish_time"] == g["publish_time"].max()
    return {
        "delivery_date": delivery_date.isoformat(),
        "cutoff_utc": cut.isoformat(),
        "publications": [
            {"publish_time": r.publish_time.isoformat(), "periods": int(r.periods),
             "available_at_cutoff": bool(r.available_at_cutoff),
             "is_latest_before_cutoff": bool(r.is_latest_before_cutoff),
             "is_latest_overall": bool(r.is_latest_overall)} for r in g.itertuples()],
    }


@router.get("/forecasts")
def forecasts(delivery_date: date = Query(alias="date"), mode: str = Mode,
              cutoff: str = Query(None, pattern=CUTOFF_RE), publish_time: str | None = None):
    """Forecast for a delivery day: as-of cutoff, latest, or one specific publication (publish_time, ISO UTC)."""
    _check_range(delivery_date, delivery_date)
    cutoff = cutoff or get_settings().default_cutoff_local
    f = _in_range(_dataset().forecasts, delivery_date, delivery_date)
    if publish_time:
        try:
            pt = pd.Timestamp(publish_time).tz_convert("UTC") if pd.Timestamp(publish_time).tzinfo else pd.Timestamp(publish_time, tz="UTC")
        except ValueError as e:
            raise HTTPException(422, "publish_time must be an ISO timestamp") from e
        sel, label = f[f["publish_time"] == pt], "publication"
    elif mode == "latest":
        sel, label = select_latest(f), "latest"
    else:
        sel, label = select_asof_cutoff(f, cutoff), "asof"
    sel = sel.sort_values("start_time") if len(sel) else sel
    return {"unit": "MW", "delivery_date": delivery_date.isoformat(), "selection": label,
            "cutoff_local": cutoff, "cutoff_utc": cutoff_utc(delivery_date, cutoff).isoformat(), "count": len(sel),
            "data": [{"start_time": s, "publish_time": p, "forecast_mw": v} for s, p, v in zip(
                _iso(sel["start_time"]), _iso(sel["publish_time"]), sel["forecast_mw"])] if len(sel) else []}


@router.get("/analysis")
def analysis(date_from: date = Query(alias="from"), date_to: date = Query(alias="to"),
             mode: str = Mode, cutoff: str = Query(None, pattern=CUTOFF_RE)):
    _check_range(date_from, date_to)
    cutoff = cutoff or get_settings().default_cutoff_local
    ds = _dataset()
    f = _in_range(ds.forecasts, date_from, date_to)
    a = _in_range(ds.actuals, date_from, date_to)
    sel = select_latest(f) if mode == "latest" else select_asof_cutoff(f, cutoff)
    m = match(sel, a)
    warnings = []
    if f.empty:
        warnings.append("No forecast records available for the selected range.")
    if a.empty:
        warnings.append("No actual generation records available for the selected range.")
    n_unmatched = int(len(sel) - len(m)) if len(sel) else 0
    if n_unmatched:
        warnings.append(f"{n_unmatched} forecast periods have no matching actual yet and are excluded from metrics.")
    by_hour, by_day = [], []
    if len(m):
        loc = m["start_time"].dt.tz_convert("Europe/London")
        for h, grp in m.groupby(loc.dt.hour):
            by_hour.append({"hour": int(h), **{k: v for k, v in compute_metrics(grp).items() if k in ("n", "mae_mw", "rmse_mw", "bias_mw")}})
        for d, grp in m.groupby(loc.dt.date):
            by_day.append({"date": d.isoformat(), **{k: v for k, v in compute_metrics(grp).items() if k in ("n", "mae_mw", "rmse_mw", "bias_mw")}})
    rows = [{"start_time": s, "publish_time": p, "forecast_mw": fv, "actual_mw": av, "error_mw": ev, "horizon_h": hv}
            for s, p, fv, av, ev, hv in zip(_iso(m["start_time"]), _iso(m["publish_time"]), m["forecast_mw"],
                                            m["actual_mw"], m["error_mw"], m["horizon_h"])] if len(m) else []
    return {"unit": "MW", "mode": mode, "cutoff_local": cutoff, "from": date_from.isoformat(), "to": date_to.isoformat(),
            "metrics": compute_metrics(m), "by_hour": by_hour, "by_day": by_day, "rows": rows, "warnings": warnings}
