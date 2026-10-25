"""Thin Elexon Insights API client.

Verified against the published OpenAPI collection (base https://data.elexon.co.uk/bmrs/api/v1):
  - WINDFOR/stream : publishDateTimeFrom, publishDateTimeTo
  - FUELHH/stream  : settlementDateFrom, settlementDateTo, fuelType
No API key is required. Stream endpoints return a plain JSON array.
NOT yet verified against live responses (sandbox could not reach Elexon): per-request
window limits and exact field casing; the normaliser tolerates both.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import get_settings

log = logging.getLogger(__name__)


class ElexonError(RuntimeError):
    """Raised when Elexon cannot be reached or returns an unusable response."""


def _iso_z(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")


class ElexonClient:
    def __init__(self, client: httpx.Client | None = None):
        self._s = get_settings()
        self._client = client or httpx.Client(base_url=self._s.elexon_base_url, timeout=self._s.http_timeout_s)

    def _get(self, path: str, params: dict) -> list[dict]:
        @retry(
            reraise=True,
            stop=stop_after_attempt(self._s.http_retries),
            wait=wait_exponential(multiplier=1, min=1, max=8),
            retry=retry_if_exception_type(httpx.TransportError),
        )
        def call() -> httpx.Response:
            r = self._client.get(path, params=params)
            if r.status_code >= 500 or r.status_code == 429:
                raise httpx.TransportError(f"retryable status {r.status_code}")
            return r

        try:
            r = call()
            r.raise_for_status()
            data = r.json()
        except (httpx.HTTPError, ValueError) as e:
            log.error("Elexon request failed: %s %s (%s)", path, params, e)
            raise ElexonError(f"Elexon request failed for {path}: {e}") from e
        if isinstance(data, dict):
            data = data.get("data", [])
        if not isinstance(data, list):
            raise ElexonError(f"Unexpected response shape from {path}")
        return data

    def fetch_wind_actuals(self, start: date, end: date) -> list[dict]:
        """FUELHH wind actuals for settlement dates start..end inclusive, chunked."""
        rows: list[dict] = []
        cur, step = start, timedelta(days=self._s.chunk_days)
        while cur <= end:
            to = min(cur + step - timedelta(days=1), end)
            rows += self._get(
                "/datasets/FUELHH/stream",
                {"settlementDateFrom": cur.isoformat(), "settlementDateTo": to.isoformat(), "fuelType": "WIND"},
            )
            cur = to + timedelta(days=1)
        return rows

    def fetch_wind_forecasts(self, publish_from: datetime, publish_to: datetime) -> list[dict]:
        """WINDFOR records with publishTime in [publish_from, publish_to], chunked."""
        rows: list[dict] = []
        cur, step = publish_from, timedelta(days=self._s.chunk_days)
        while cur < publish_to:
            to = min(cur + step, publish_to)
            rows += self._get(
                "/datasets/WINDFOR/stream",
                {"publishDateTimeFrom": _iso_z(cur), "publishDateTimeTo": _iso_z(to)},
            )
            cur = to
        return rows
