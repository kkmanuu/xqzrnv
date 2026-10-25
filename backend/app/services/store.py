"""Data store: loads normalised Elexon data from an on-disk cache, fetching from Elexon only when absent.

Historical January 2026 data is immutable enough to cache; this avoids hitting Elexon on every request.
"""
from __future__ import annotations

import json
import logging
import threading
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from app.config import get_settings
from app.services.elexon_client import ElexonClient
from app.services.normalise import normalise_actuals, normalise_forecasts

log = logging.getLogger(__name__)
_lock = threading.Lock()


@dataclass
class Dataset:
    actuals: pd.DataFrame
    forecasts: pd.DataFrame
    fetched_at: str | None


_mem: Dataset | None = None


def _paths() -> tuple[Path, Path, Path]:
    d = Path(get_settings().cache_dir)
    return d / "actuals.csv", d / "forecasts.csv", d / "meta.json"


def build_cache(client: ElexonClient | None = None) -> Dataset:
    """Fetch the pilot window from Elexon, normalise, and write the cache."""
    s = get_settings()
    client = client or ElexonClient()
    start, end = date.fromisoformat(s.window_start), date.fromisoformat(s.window_end)
    # Forecasts for early-Jan delivery are published before 1 Jan, so look back a few days.
    pub_from = datetime.combine(start - timedelta(days=3), datetime.min.time(), tzinfo=timezone.utc)
    pub_to = datetime.combine(end + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc)
    actuals = normalise_actuals(client.fetch_wind_actuals(start, end))
    forecasts = normalise_forecasts(client.fetch_wind_forecasts(pub_from, pub_to))
    fetched_at = datetime.now(timezone.utc).isoformat()
    a, f, m = _paths()
    a.parent.mkdir(parents=True, exist_ok=True)
    actuals.to_csv(a, index=False)
    forecasts.to_csv(f, index=False)
    m.write_text(json.dumps({"fetched_at": fetched_at}))
    log.info("Cache built: %d actuals, %d forecasts", len(actuals), len(forecasts))
    return Dataset(actuals, forecasts, fetched_at)


def _load_cache() -> Dataset | None:
    a, f, m = _paths()
    if not (a.exists() and f.exists()):
        return None
    actuals = pd.read_csv(a, parse_dates=["start_time"])
    forecasts = pd.read_csv(f, parse_dates=["start_time", "publish_time"])
    for df, cols in ((actuals, ["start_time"]), (forecasts, ["start_time", "publish_time"])):
        for c in cols:
            df[c] = pd.to_datetime(df[c], utc=True)
    fetched = json.loads(m.read_text()).get("fetched_at") if m.exists() else None
    return Dataset(actuals, forecasts, fetched)


def get_dataset() -> Dataset:
    global _mem
    with _lock:
        if _mem is None:
            _mem = _load_cache() or build_cache()
        return _mem


def reset_memory() -> None:
    global _mem
    _mem = None
