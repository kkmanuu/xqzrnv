import httpx
import pandas as pd
import pytest
import respx
from fastapi.testclient import TestClient

from app.main import app
from app.services import store
from app.services.elexon_client import ElexonClient, ElexonError


def ts(s):
    return pd.Timestamp(s, tz="UTC")


@pytest.fixture
def client(monkeypatch):
    # Synthetic fixtures for tests ONLY; never shipped as deployed data.
    fc = pd.DataFrame({
        "start_time": [ts("2026-01-15T12:00")] * 3, "publish_time": [ts("2026-01-14T06:00"), ts("2026-01-14T09:20"), ts("2026-01-14T12:00")],
        "forecast_mw": [10.0, 20.0, 30.0]})
    ac = pd.DataFrame({"start_time": [ts("2026-01-15T12:00")], "actual_mw": [25.0]})
    monkeypatch.setattr(store, "_mem", store.Dataset(ac, fc, "2026-01-16T00:00:00+00:00"))
    return TestClient(app)


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_analysis_asof_vs_latest(client):
    a = client.get("/api/analysis", params={"from": "2026-01-15", "to": "2026-01-15"}).json()
    assert a["metrics"]["bias_mw"] == -5.0 and a["rows"][0]["forecast_mw"] == 20.0
    l = client.get("/api/analysis", params={"from": "2026-01-15", "to": "2026-01-15", "mode": "latest"}).json()
    assert l["metrics"]["bias_mw"] == 5.0


def test_publications_flags(client):
    p = client.get("/api/forecast-publications", params={"date": "2026-01-15"}).json()["publications"]
    assert [x["is_latest_before_cutoff"] for x in p] == [False, True, False]
    assert [x["is_latest_overall"] for x in p] == [False, False, True]


def test_validation(client):
    assert client.get("/api/analysis", params={"from": "2026-02-01", "to": "2026-02-02"}).status_code == 422
    assert client.get("/api/analysis", params={"from": "2026-01-16", "to": "2026-01-15"}).status_code == 422
    assert client.get("/api/forecasts", params={"date": "2026-01-15", "cutoff": "25:99"}).status_code == 422


def test_empty_day_has_warnings_not_error(client):
    r = client.get("/api/analysis", params={"from": "2026-01-20", "to": "2026-01-20"}).json()
    assert r["metrics"]["n"] == 0 and r["warnings"]


@respx.mock
def test_elexon_failure_raises(monkeypatch):
    monkeypatch.setenv("HTTP_RETRIES", "1")
    from app.config import get_settings
    get_settings.cache_clear()
    respx.get(url__regex=r".*/datasets/WINDFOR/stream.*").mock(return_value=httpx.Response(500))
    c = ElexonClient(httpx.Client(base_url="https://data.elexon.co.uk/bmrs/api/v1"))
    with pytest.raises(ElexonError):
        c.fetch_wind_forecasts(ts("2026-01-01"), ts("2026-01-02"))
    get_settings.cache_clear()


@respx.mock
def test_elexon_params_and_parse():
    route = respx.get(url__regex=r".*/datasets/FUELHH/stream.*").mock(
        return_value=httpx.Response(200, json=[{"fuelType": "WIND", "startTime": "2026-01-01T00:00:00Z", "generation": 5}]))
    c = ElexonClient(httpx.Client(base_url="https://data.elexon.co.uk/bmrs/api/v1"))
    rows = c.fetch_wind_actuals(pd.Timestamp("2026-01-01").date(), pd.Timestamp("2026-01-01").date())
    assert rows[0]["generation"] == 5
    assert route.calls[0].request.url.params["fuelType"] == "WIND"
