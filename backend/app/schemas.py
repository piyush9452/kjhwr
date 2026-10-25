"""Pydantic response models for the public API."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel

Mode = Literal["decision", "horizon"]


class Health(BaseModel):
    status: Literal["ok"]
    snapshot_version: str
    fetched_at: str
    delivery_start: date
    delivery_end: date


class SeriesPoint(BaseModel):
    start_time: datetime
    actual: float | None
    forecast: float | None
    publish_time: datetime | None
    horizon_h: float | None
    p10: float | None
    p50: float | None
    p90: float | None


class SeriesResponse(BaseModel):
    mode: Mode
    cutoff: str | None
    horizon_h: float | None
    points: list[SeriesPoint]


class Metrics(BaseModel):
    n: int
    mae: float | None = None
    rmse: float | None = None
    bias: float | None = None
    mean_actual: float | None = None
    mae_pct_of_mean_actual: float | None = None
    pct_over: float | None = None
    pct_under: float | None = None
    p50_abs_error: float | None = None
    p90_abs_error: float | None = None
    p99_abs_error: float | None = None
    firm_wind_p10_mean: float | None = None
    firm_wind_p10_min: float | None = None
    forecast_mean: float | None = None


class GroupRow(BaseModel):
    key: int | str
    n: int
    mae: float
    rmse: float
    bias: float
    p90_abs_error: float


class DayRow(GroupRow):
    mean_actual: float


class HistogramBin(BaseModel):
    bin_start: float
    bin_end: float
    count: int


class MetricsResponse(BaseModel):
    mode: Mode
    metrics: Metrics
    by_day: list[DayRow]


class GroupResponse(BaseModel):
    rows: list[GroupRow]


class DistributionResponse(BaseModel):
    bins: list[HistogramBin]
    pct_over: float | None
    pct_under: float | None
    n: int
