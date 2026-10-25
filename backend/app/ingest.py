"""Turn raw BMRS rows into clean, typed frames and a versioned on-disk snapshot.

All timestamps are kept as tz-aware UTC. Local (Europe/London) dates are only
derived when grouping by delivery day, so DST transitions are handled in one place.
"""

from __future__ import annotations

import gzip
import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from . import config
from .analytics import add_horizon, filter_horizon

log = logging.getLogger(__name__)


@dataclass
class Snapshot:
    actuals: pd.DataFrame  # start_time, generation (half-hourly, MW)
    forecasts: pd.DataFrame  # start_time, publish_time, generation, horizon_h
    quality: dict[str, Any]
    fetched_at: str
    version: str = config.SNAPSHOT_VERSION


def _to_utc(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s, utc=True)


def clean_actuals(rows: list[dict[str, Any]]) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Filter to wind, de-duplicate on startTime (keep latest publish) and report gaps."""
    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(columns=["start_time", "generation"]), {"rows_raw": 0}
    df = df[df["fuelType"] == config.WIND_FUEL_TYPE].copy()
    df["start_time"] = _to_utc(df["startTime"])
    df["publish_time"] = _to_utc(df["publishTime"])
    n_raw = len(df)
    n_null = int(df["generation"].isna().sum())
    df = df.dropna(subset=["generation"])
    df = df.sort_values("publish_time").drop_duplicates("start_time", keep="last")
    df = df.sort_values("start_time").reset_index(drop=True)

    expected = pd.date_range(df["start_time"].min(), df["start_time"].max(), freq=f"{config.ACTUAL_RESOLUTION_MIN}min")
    missing = expected.difference(pd.DatetimeIndex(df["start_time"]))
    periods_per_day = df.groupby("settlementDate")["settlementPeriod"].nunique()
    quality = {
        "rows_raw": n_raw,
        "null_values_dropped": n_null,
        "duplicates_dropped": n_raw - n_null - len(df),
        "rows_clean": len(df),
        "missing_half_hours": len(missing),
        "missing_examples": [t.isoformat() for t in missing[:5]],
        "negative_values": int((df["generation"] < 0).sum()),
        # 46/50 periods would indicate a DST change day; January should be all 48.
        "days_not_48_periods": periods_per_day[periods_per_day != 48].to_dict(),
        "first": df["start_time"].min().isoformat(),
        "last": df["start_time"].max().isoformat(),
    }
    return df[["start_time", "generation"]].astype({"generation": float}), quality


def clean_forecasts(rows: list[dict[str, Any]]) -> tuple[pd.DataFrame, dict[str, Any]]:
    """De-duplicate forecasts, compute horizon and drop horizons outside [0, 48] h."""
    df = pd.DataFrame(rows)
    if df.empty:
        cols = ["start_time", "publish_time", "generation", "horizon_h"]
        return pd.DataFrame(columns=cols), {"rows_raw": 0}
    df["start_time"] = _to_utc(df["startTime"])
    df["publish_time"] = _to_utc(df["publishTime"])
    n_raw = len(df)
    n_null = int(df["generation"].isna().sum())
    df = df.dropna(subset=["generation"])
    df = df.drop_duplicates(["start_time", "publish_time"], keep="last")
    n_dedup = len(df)
    df = add_horizon(df)
    in_range = filter_horizon(df, config.MIN_HORIZON_H, config.MAX_HORIZON_H)
    publishes = df["publish_time"].drop_duplicates().sort_values()
    gaps_h = publishes.diff().dt.total_seconds().div(3600).dropna()
    quality = {
        "rows_raw": n_raw,
        "null_values_dropped": n_null,
        "duplicates_dropped": n_raw - n_null - n_dedup,
        "rows_outside_horizon_dropped": n_dedup - len(in_range),
        "rows_clean": len(in_range),
        "publish_runs": int(publishes.size),
        "max_gap_between_runs_h": float(gaps_h.max()) if not gaps_h.empty else None,
        "median_gap_between_runs_h": float(gaps_h.median()) if not gaps_h.empty else None,
        "non_hourly_start_times": int((df["start_time"].dt.minute != 0).sum()),
        "negative_values": int((df["generation"] < 0).sum()),
    }
    clean = in_range[["start_time", "publish_time", "generation", "horizon_h"]]
    return clean.astype({"generation": float}).reset_index(drop=True), quality


def to_hourly(actuals: pd.DataFrame) -> pd.DataFrame:
    """Average half-hourly MW to hourly MW to match WINDFOR resolution.

    Hours missing either half-hour are dropped rather than half-filled.
    """
    s = actuals.set_index("start_time")["generation"]
    grouped = s.resample(config.FORECAST_RESOLUTION)
    hourly = grouped.mean()[grouped.count() == 60 // config.ACTUAL_RESOLUTION_MIN]
    return hourly.rename("actual").reset_index()


# --- Snapshot persistence ---------------------------------------------------------


def _frame_to_columns(df: pd.DataFrame) -> dict[str, list[Any]]:
    out: dict[str, list[Any]] = {}
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            out[col] = df[col].dt.strftime("%Y-%m-%dT%H:%M:%SZ").tolist()
        else:
            out[col] = df[col].tolist()
    return out


def _columns_to_frame(cols: dict[str, list[Any]], time_cols: list[str]) -> pd.DataFrame:
    df = pd.DataFrame(cols)
    for c in time_cols:
        df[c] = _to_utc(df[c])
    return df


def save_snapshot(snap: Snapshot, path: Path = config.SNAPSHOT_FILE) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": snap.version,
        "fetched_at": snap.fetched_at,
        "quality": snap.quality,
        "actuals": _frame_to_columns(snap.actuals),
        "forecasts": _frame_to_columns(snap.forecasts),
    }
    with gzip.open(path, "wt", encoding="utf-8") as f:
        json.dump(payload, f, default=str)
    return path


def load_snapshot(path: Path = config.SNAPSHOT_FILE) -> Snapshot:
    with gzip.open(path, "rt", encoding="utf-8") as f:
        payload = json.load(f)
    return Snapshot(
        actuals=_columns_to_frame(payload["actuals"], ["start_time"]),
        forecasts=_columns_to_frame(payload["forecasts"], ["start_time", "publish_time"]),
        quality=payload["quality"],
        fetched_at=payload["fetched_at"],
        version=payload["version"],
    )


def build_snapshot(actual_rows: list[dict[str, Any]], forecast_rows: list[dict[str, Any]]) -> Snapshot:
    actuals, aq = clean_actuals(actual_rows)
    forecasts, fq = clean_forecasts(forecast_rows)
    hourly = to_hourly(actuals)
    quality = {
        "actuals": aq,
        "forecasts": fq,
        "hourly_actuals": len(hourly),
        "alignment": "half-hourly actuals averaged to hourly (both halves required)",
    }
    log.info("Data quality: %s", json.dumps(quality, indent=2, default=str))
    return Snapshot(actuals, forecasts, quality, datetime.now(UTC).isoformat(timespec="seconds"))
