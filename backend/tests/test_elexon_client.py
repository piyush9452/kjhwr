from __future__ import annotations

from datetime import UTC, date, datetime

import httpx
import pytest
from tenacity import wait_none

from app import config
from app.elexon_client import ElexonClient, date_windows


@pytest.fixture(autouse=True)
def _no_backoff(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ElexonClient._get.retry, "wait", wait_none())


def _client(handler) -> tuple[ElexonClient, list[httpx.Request]]:
    seen: list[httpx.Request] = []

    def record(req: httpx.Request) -> httpx.Response:
        seen.append(req)
        return handler(req, len(seen))

    c = ElexonClient()
    c._http = httpx.Client(base_url=config.ELEXON_BASE_URL, transport=httpx.MockTransport(record))
    return c, seen


def test_default_timeout_is_configured() -> None:
    with ElexonClient() as c:
        assert c._http.timeout.read == config.HTTP_TIMEOUT_S


def test_date_windows_cover_range_without_overlap() -> None:
    w = list(date_windows(date(2026, 1, 2), date(2026, 1, 16), 7))
    assert w == [
        (date(2026, 1, 2), date(2026, 1, 8)),
        (date(2026, 1, 9), date(2026, 1, 15)),
        (date(2026, 1, 16), date(2026, 1, 16)),
    ]


def test_fuelhh_paginates_by_settlement_date_and_passes_fuel_type() -> None:
    c, seen = _client(lambda req, n: httpx.Response(200, json=[{"n": n}]))
    rows = c.fuelhh(date(2026, 1, 2), date(2026, 1, 16), "WIND")
    assert rows == [{"n": 1}, {"n": 2}, {"n": 3}]
    assert [r.url.params["settlementDateFrom"] for r in seen] == ["2026-01-02", "2026-01-09", "2026-01-16"]
    assert {r.url.params["fuelType"] for r in seen} == {"WIND"}
    assert seen[0].url.path.endswith("/datasets/FUELHH/stream")


def test_windfor_windows_are_contiguous_and_unwrap_data_key() -> None:
    c, seen = _client(lambda req, n: httpx.Response(200, json={"data": [{"n": n}]}))
    rows = c.windfor(datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 1, 10, tzinfo=UTC))
    assert rows == [{"n": 1}, {"n": 2}]
    assert [(r.url.params["publishDateTimeFrom"], r.url.params["publishDateTimeTo"]) for r in seen] == [
        ("2026-01-01T00:00:00Z", "2026-01-07T23:59:59Z"),
        ("2026-01-08T00:00:00Z", "2026-01-09T23:59:59Z"),
    ]


@pytest.mark.parametrize("status", [429, 500, 503])
def test_retries_transient_errors_then_succeeds(status: int) -> None:
    c, seen = _client(lambda req, n: httpx.Response(status) if n < 3 else httpx.Response(200, json=[]))
    assert c.fuelhh(date(2026, 1, 2), date(2026, 1, 2), "WIND") == []
    assert len(seen) == 3


def test_retries_transport_errors() -> None:
    def handler(req: httpx.Request, n: int) -> httpx.Response:
        if n == 1:
            raise httpx.ReadTimeout("slow", request=req)
        return httpx.Response(200, json=[])

    c, seen = _client(handler)
    c.fuelhh(date(2026, 1, 2), date(2026, 1, 2), "WIND")
    assert len(seen) == 2


def test_gives_up_after_max_retries() -> None:
    c, seen = _client(lambda req, n: httpx.Response(502))
    with pytest.raises(httpx.HTTPStatusError):
        c.fuelhh(date(2026, 1, 2), date(2026, 1, 2), "WIND")
    assert len(seen) == config.HTTP_MAX_RETRIES


def test_client_errors_are_not_retried() -> None:
    c, seen = _client(lambda req, n: httpx.Response(400))
    with pytest.raises(httpx.HTTPStatusError):
        c.fuelhh(date(2026, 1, 2), date(2026, 1, 2), "WIND")
    assert len(seen) == 1
