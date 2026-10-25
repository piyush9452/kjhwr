"""FastAPI routes. Thin layer: validate inputs, call the service, shape responses."""

from __future__ import annotations

import logging
import re
from datetime import date, time
from typing import Annotated

import pandas as pd
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from . import config
from .schemas import (
    DayRow,
    DistributionResponse,
    GroupResponse,
    GroupRow,
    Health,
    HistogramBin,
    Metrics,
    MetricsResponse,
    Mode,
    SeriesPoint,
    SeriesResponse,
)
from .service import Query as SvcQuery
from .service import WindService, get_service

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Wind Forecast Desk API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=config.CORS_ORIGINS, allow_methods=["GET"])

Svc = Annotated[WindService, Depends(get_service)]


_CUTOFF_RE = re.compile(r"([01]\d|2[0-3]):([0-5]\d)")


def _parse_cutoff(value: str) -> time:
    # Strict HH:MM: time.fromisoformat would also accept offsets ("09:00+05:00") we'd silently ignore.
    m = _CUTOFF_RE.fullmatch(value)
    if not m:
        raise HTTPException(422, f"cutoff must be HH:MM (24h, Europe/London), got '{value}'")
    return time(int(m[1]), int(m[2]))


def build_query(
    start: date = Query(config.DELIVERY_START, description="First delivery date (inclusive)"),
    end: date = Query(config.DELIVERY_END, description="Last delivery date (inclusive)"),
    mode: Mode = Query("decision"),
    horizon: float = Query(0.0, ge=config.MIN_HORIZON_H, le=config.MAX_HORIZON_H),
    cutoff: str = Query(config.DEFAULT_CUTOFF.strftime("%H:%M"), description="D-1 cutoff, HH:MM London"),
) -> SvcQuery:
    lo, hi = config.DELIVERY_START, config.DELIVERY_END
    if not (lo <= start <= hi and lo <= end <= hi):
        raise HTTPException(422, f"Delivery dates must be within {lo}..{hi} (decisions made in January 2026)")
    if start > end:
        raise HTTPException(422, "start must be on or before end")
    return SvcQuery(start=start, end=end, mode=mode, horizon_h=horizon, cutoff=_parse_cutoff(cutoff))


Q = Annotated[SvcQuery, Depends(build_query)]


def _group_rows(df: pd.DataFrame, key: str) -> list[GroupRow]:
    return [
        GroupRow(key=r[key], **{k: r[k] for k in GroupRow.model_fields if k != "key"}) for r in df.to_dict("records")
    ]


@app.get("/api/health", response_model=Health)
def health(svc: Svc) -> Health:
    return Health(
        status="ok",
        snapshot_version=svc.snap.version,
        fetched_at=svc.snap.fetched_at,
        delivery_start=config.DELIVERY_START,
        delivery_end=config.DELIVERY_END,
    )


@app.get("/api/series", response_model=SeriesResponse)
def series(svc: Svc, q: Q) -> SeriesResponse:
    df = svc.series(q)
    points = [SeriesPoint(**{k: r.get(k) for k in SeriesPoint.model_fields}) for r in df.to_dict("records")]
    return SeriesResponse(
        mode=q.mode,
        cutoff=q.cutoff.strftime("%H:%M") if q.mode == "decision" else None,
        horizon_h=q.horizon_h if q.mode == "horizon" else None,
        points=points,
    )


@app.get("/api/metrics", response_model=MetricsResponse)
def metrics(svc: Svc, q: Q) -> MetricsResponse:
    m, by_day = svc.metrics(q)
    days = [
        DayRow(key=str(r["delivery_date"]), **{k: r[k] for k in DayRow.model_fields if k != "key"})
        for r in by_day.to_dict("records")
    ]
    return MetricsResponse(mode=q.mode, metrics=Metrics(**m), by_day=days)


@app.get("/api/accuracy/by-horizon", response_model=GroupResponse)
def by_horizon(svc: Svc, q: Q) -> GroupResponse:
    return GroupResponse(rows=_group_rows(svc.by_horizon(q), "horizon_h"))


@app.get("/api/accuracy/by-hour", response_model=GroupResponse)
def by_hour(svc: Svc, q: Q) -> GroupResponse:
    return GroupResponse(rows=_group_rows(svc.by_hour(q), "hour"))


@app.get("/api/accuracy/distribution", response_model=DistributionResponse)
def distribution(svc: Svc, q: Q) -> DistributionResponse:
    hist, m = svc.distribution(q)
    return DistributionResponse(
        bins=[HistogramBin(**r) for r in hist.to_dict("records")],
        pct_over=m.get("pct_over"),
        pct_under=m.get("pct_under"),
        n=m["n"],
    )
