"""Thin HTTP client for the Elexon BMRS stream endpoints.

Stream endpoints return a flat JSON array with no paging cursor, so we
"paginate" by splitting the requested range into fixed-size date windows.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from datetime import date, datetime, timedelta
from typing import Any

import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from . import config

log = logging.getLogger(__name__)

Row = dict[str, Any]


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code == 429 or exc.response.status_code >= 500
    return isinstance(exc, httpx.TransportError)


def date_windows(start: date, end: date, days: int) -> Iterator[tuple[date, date]]:
    """Yield inclusive [from, to] windows of at most `days` days covering start..end."""
    cur = start
    while cur <= end:
        stop = min(cur + timedelta(days=days - 1), end)
        yield cur, stop
        cur = stop + timedelta(days=1)


class ElexonClient:
    def __init__(self, base_url: str = config.ELEXON_BASE_URL, timeout: float = config.HTTP_TIMEOUT_S):
        self._http = httpx.Client(base_url=base_url, timeout=timeout)

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> ElexonClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    @retry(
        retry=retry_if_exception(_is_retryable),
        stop=stop_after_attempt(config.HTTP_MAX_RETRIES),
        wait=wait_exponential(multiplier=1, max=20),
        reraise=True,
    )
    def _get(self, path: str, params: dict[str, Any]) -> list[Row]:
        resp = self._http.get(path, params=params)
        resp.raise_for_status()
        body = resp.json()
        return body["data"] if isinstance(body, dict) else body

    def fuelhh(self, settlement_from: date, settlement_to: date, fuel_type: str) -> list[Row]:
        """Half-hourly outturn for one fuel type, by settlement date (inclusive)."""
        rows: list[Row] = []
        for lo, hi in date_windows(settlement_from, settlement_to, config.FETCH_CHUNK_DAYS):
            params = {
                "settlementDateFrom": lo.isoformat(),
                "settlementDateTo": hi.isoformat(),
                "fuelType": fuel_type,
            }
            chunk = self._get("/datasets/FUELHH/stream", params)
            log.info("FUELHH %s..%s: %d rows", lo, hi, len(chunk))
            rows.extend(chunk)
        return rows

    def windfor(self, publish_from: datetime, publish_to: datetime) -> list[Row]:
        """All wind forecasts published in [publish_from, publish_to)."""
        rows: list[Row] = []
        step = timedelta(days=config.FETCH_CHUNK_DAYS)
        cur = publish_from
        while cur < publish_to:
            nxt = min(cur + step, publish_to)
            params = {
                "publishDateTimeFrom": cur.strftime("%Y-%m-%dT%H:%M:%SZ"),
                # API bound is inclusive; step back a second to avoid double-counting.
                "publishDateTimeTo": (nxt - timedelta(seconds=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
            chunk = self._get("/datasets/WINDFOR/stream", params)
            log.info("WINDFOR %s..%s: %d rows", cur, nxt, len(chunk))
            rows.extend(chunk)
            cur = nxt
        return rows
