"""Fetch the January 2026 pilot window from Elexon and write the on-disk cache.

Run from backend/:  python -m scripts.snapshot
Needs outbound HTTPS access to data.elexon.co.uk (no API key).
"""
from app.config import configure_logging
from app.services.store import build_cache

if __name__ == "__main__":
    configure_logging()
    ds = build_cache()
    print(f"actuals={len(ds.actuals)} forecasts={len(ds.forecasts)} fetched_at={ds.fetched_at}")
