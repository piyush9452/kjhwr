"""Pure forecast-selection and accuracy functions (no I/O).

Conventions:
- frames carry tz-aware UTC `start_time` / `publish_time`
- horizon_h = (start_time - publish_time) in hours
- error = forecast - actual (positive = over-forecast)
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime, time, timedelta

import numpy as np
import pandas as pd

from . import config

# --- Horizon & selection -----------------------------------------------------------


def add_horizon(fc: pd.DataFrame) -> pd.DataFrame:
    out = fc.copy()
    out["horizon_h"] = (out["start_time"] - out["publish_time"]).dt.total_seconds() / 3600
    return out


def filter_horizon(fc: pd.DataFrame, lo: float, hi: float) -> pd.DataFrame:
    return fc[(fc["horizon_h"] >= lo) & (fc["horizon_h"] <= hi)]


def delivery_date(ts: pd.Series) -> pd.Series:
    """Local (Europe/London) calendar date a UTC timestamp is delivered on."""
    return ts.dt.tz_convert(config.LONDON).dt.date


def cutoff_utc(delivery_day: date, cutoff: time = config.DEFAULT_CUTOFF) -> datetime:
    """Decision cutoff for a delivery day: `cutoff` local time on D-1, in UTC."""
    local = datetime.combine(delivery_day - timedelta(days=1), cutoff, tzinfo=config.LONDON)
    return local.astimezone(config.UTC)


def _latest_per_target(fc: pd.DataFrame) -> pd.DataFrame:
    if fc.empty:
        return fc
    idx = fc.groupby("start_time")["publish_time"].idxmax()
    return fc.loc[idx].sort_values("start_time").reset_index(drop=True)


def select_decision(fc: pd.DataFrame, cutoff: time = config.DEFAULT_CUTOFF) -> pd.DataFrame:
    """Latest forecast per target published at or before that target's D-1 cutoff."""
    days = delivery_date(fc["start_time"])
    cutoffs = pd.to_datetime(days.map(lambda d: cutoff_utc(d, cutoff)), utc=True)
    return _latest_per_target(fc[fc["publish_time"] <= cutoffs])


def select_horizon(fc: pd.DataFrame, horizon_h: float) -> pd.DataFrame:
    """Latest forecast per target published at least `horizon_h` hours before it."""
    return _latest_per_target(fc[fc["horizon_h"] >= horizon_h])


def align(selected: pd.DataFrame, actual: pd.DataFrame) -> pd.DataFrame:
    """Inner-join forecasts to hourly actuals and compute error."""
    merged = selected.rename(columns={"generation": "forecast"}).merge(actual, on="start_time", how="inner")
    merged["error"] = merged["forecast"] - merged["actual"]
    return merged


def in_delivery_range(df: pd.DataFrame, start: date, end: date) -> pd.DataFrame:
    d = delivery_date(df["start_time"])
    return df[(d >= start) & (d <= end)]


# --- Metrics -------------------------------------------------------------------


def metrics(error: pd.Series, actual: pd.Series) -> dict[str, float | int | None]:
    n = int(error.size)
    if n == 0:
        return {"n": 0}
    abs_err = error.abs()
    mean_actual = float(actual.mean())
    out: dict[str, float | int | None] = {
        "n": n,
        "mae": float(abs_err.mean()),
        "rmse": float(np.sqrt((error**2).mean())),
        "bias": float(error.mean()),
        "mean_actual": mean_actual,
        "mae_pct_of_mean_actual": float(abs_err.mean() / mean_actual * 100) if mean_actual else None,
        "pct_over": float((error > 0).mean() * 100),
        "pct_under": float((error < 0).mean() * 100),
    }
    for p in config.ABS_ERROR_PERCENTILES:
        out[f"p{p}_abs_error"] = float(np.percentile(abs_err, p))
    return out


def _grouped_metrics(df: pd.DataFrame, key: pd.Series, name: str) -> pd.DataFrame:
    g = df.assign(**{name: key, "abs_error": df["error"].abs(), "sq": df["error"] ** 2}).groupby(name)
    out = pd.DataFrame(
        {
            "n": g.size(),
            "mae": g["abs_error"].mean(),
            "rmse": np.sqrt(g["sq"].mean()),
            "bias": g["error"].mean(),
            "p90_abs_error": g["abs_error"].quantile(0.9),
        }
    )
    return out.reset_index()


def error_by_horizon(pairs: pd.DataFrame) -> pd.DataFrame:
    """Metrics per whole-hour horizon (0..48) across every forecast/actual pair."""
    return _grouped_metrics(pairs, np.floor(pairs["horizon_h"]).astype(int), "horizon_h")


def error_by_hour(df: pd.DataFrame) -> pd.DataFrame:
    """Metrics per local hour of day of delivery."""
    hour = df["start_time"].dt.tz_convert(config.LONDON).dt.hour
    return _grouped_metrics(df, hour, "hour")


def error_by_day(df: pd.DataFrame) -> pd.DataFrame:
    out = _grouped_metrics(df, delivery_date(df["start_time"]), "delivery_date")
    out["mean_actual"] = df.groupby(delivery_date(df["start_time"]))["actual"].mean().values
    return out


def histogram(error: pd.Series, bin_mw: float = config.HISTOGRAM_BIN_MW) -> pd.DataFrame:
    if error.empty:
        return pd.DataFrame(columns=["bin_start", "bin_end", "count"])
    lo = np.floor(error.min() / bin_mw) * bin_mw
    hi = np.ceil(error.max() / bin_mw) * bin_mw + bin_mw
    counts, edges = np.histogram(error, bins=np.arange(lo, hi + 1e-9, bin_mw))
    return pd.DataFrame({"bin_start": edges[:-1], "bin_end": edges[1:], "count": counts})


# --- Reliability bands -----------------------------------------------------------


def horizon_bin(horizon_h: pd.Series, width: int = config.BAND_HORIZON_BIN_H) -> pd.Series:
    return (np.floor(horizon_h / width) * width).astype(int)


def error_quantiles_by_horizon(
    pairs: pd.DataFrame,
    quantiles: Sequence[float] = config.BAND_QUANTILES,
    width: int = config.BAND_HORIZON_BIN_H,
) -> pd.DataFrame:
    """Empirical error quantiles per horizon bucket, columns q10/q50/q90 etc."""
    g = pairs.assign(hbin=horizon_bin(pairs["horizon_h"], width)).groupby("hbin")["error"]
    table = g.quantile(list(quantiles)).unstack()
    table.columns = [f"q{round(q * 100)}" for q in quantiles]
    return table.reset_index()


def apply_bands(selected: pd.DataFrame, qtable: pd.DataFrame, width: int = config.BAND_HORIZON_BIN_H) -> pd.DataFrame:
    """Add P10/P50/P90 bands of *actual* generation around the forecast.

    actual = forecast - error, so the P10 of actual uses the q90 of error.
    Bands are floored at zero since wind output cannot be negative.
    """
    out = selected.assign(hbin=horizon_bin(selected["horizon_h"], width)).merge(qtable, on="hbin", how="left")
    out["p10"] = (out["forecast"] - out["q90"]).clip(lower=0)
    out["p50"] = (out["forecast"] - out["q50"]).clip(lower=0)
    out["p90"] = (out["forecast"] - out["q10"]).clip(lower=0)
    return out.drop(columns=["hbin", "q10", "q50", "q90"])
