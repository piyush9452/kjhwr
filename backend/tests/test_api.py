from __future__ import annotations

from collections.abc import Iterator

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.ingest import Snapshot, clean_forecasts
from app.main import app
from app.service import WindService, get_service


def _synthetic_service() -> WindService:
    """Two delivery days, flat 10 GW actual; every run over-forecasts by 1 GW."""
    half_hours = pd.date_range("2026-01-02", "2026-01-03T23:30", freq="30min", tz="UTC")
    actuals = pd.DataFrame({"start_time": half_hours, "generation": 10_000.0})
    runs = pd.date_range("2026-01-01T01:30", "2026-01-03T22:30", freq="3h", tz="UTC")
    targets = pd.date_range("2026-01-02", "2026-01-03T23:00", freq="1h", tz="UTC")
    rows = [
        {"startTime": t.isoformat(), "publishTime": p.isoformat(), "generation": 11_000.0}
        for p in runs
        for t in targets
    ]
    forecasts, _ = clean_forecasts(rows)
    return WindService(Snapshot(actuals, forecasts, {}, "2026-01-01T00:00:00+00:00"))


@pytest.fixture
def client() -> Iterator[TestClient]:
    svc = _synthetic_service()
    app.dependency_overrides[get_service] = lambda: svc
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_health(client: TestClient) -> None:
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert body["delivery_start"] == "2026-01-02"


def test_series_decision_mode(client: TestClient) -> None:
    r = client.get("/api/series", params={"start": "2026-01-02", "end": "2026-01-02"})
    assert r.status_code == 200
    points = r.json()["points"]
    assert len(points) == 24
    first = points[0]
    assert first["forecast"] == 11_000.0 and first["actual"] == 10_000.0
    # Latest run at or before 2026-01-01 09:00 is the 07:30 run.
    assert first["publish_time"].startswith("2026-01-01T07:30")
    # Every error is +1000, so the band collapses to forecast - 1000.
    assert first["p10"] == first["p90"] == 10_000.0


def test_metrics_horizon_mode(client: TestClient) -> None:
    r = client.get("/api/metrics", params={"mode": "horizon", "horizon": 6})
    m = r.json()["metrics"]
    assert m["mae"] == 1000.0 and m["bias"] == 1000.0 and m["pct_over"] == 100.0
    assert m["firm_wind_p10_mean"] == 10_000.0


def test_accuracy_endpoints(client: TestClient) -> None:
    assert client.get("/api/accuracy/by-horizon").json()["rows"][0]["mae"] == 1000.0
    hours = client.get("/api/accuracy/by-hour").json()["rows"]
    assert {r["key"] for r in hours} == set(range(24))
    dist = client.get("/api/accuracy/distribution").json()
    assert sum(b["count"] for b in dist["bins"]) == dist["n"]


@pytest.mark.parametrize(
    ("params", "fragment"),
    [
        ({"start": "2025-12-31"}, "within 2026-01-02..2026-02-01"),
        ({"start": "2026-01-10", "end": "2026-01-05"}, "start must be on or before end"),
        ({"cutoff": "9am"}, "cutoff must be HH:MM"),
        ({"cutoff": "09:00+05:00"}, "cutoff must be HH:MM"),
        ({"cutoff": "24:00"}, "cutoff must be HH:MM"),
        ({"cutoff": "T09"}, "cutoff must be HH:MM"),
    ],
)
def test_validation_errors(client: TestClient, params: dict, fragment: str) -> None:
    r = client.get("/api/series", params=params)
    assert r.status_code == 422
    assert fragment in r.json()["detail"]


def test_horizon_out_of_range(client: TestClient) -> None:
    assert client.get("/api/metrics", params={"mode": "horizon", "horizon": 49}).status_code == 422


@pytest.mark.parametrize("horizon", ["-1", "49", "abc"])
def test_bad_horizon_is_422(client: TestClient, horizon: str) -> None:
    assert client.get("/api/series", params={"mode": "horizon", "horizon": horizon}).status_code == 422


def test_range_past_window_is_422(client: TestClient) -> None:
    r = client.get("/api/metrics", params={"start": "2026-01-30", "end": "2026-02-05"})
    assert r.status_code == 422


def test_unreachable_horizon_returns_empty_not_error(client: TestClient) -> None:
    # WINDFOR runs publish at :30, so no forecast is a full 48h ahead.
    r = client.get("/api/metrics", params={"mode": "horizon", "horizon": 48})
    assert r.status_code == 200
    assert r.json()["metrics"]["n"] == 0
