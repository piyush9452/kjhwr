"""Analytics service: loads the snapshot once and answers API-shaped questions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, time
from functools import lru_cache

import numpy as np
import pandas as pd

from . import analytics as an
from . import config
from .ingest import Snapshot, load_snapshot, to_hourly
from .schemas import Mode


@dataclass(frozen=True)
class Query:
    start: date = config.DELIVERY_START
    end: date = config.DELIVERY_END
    mode: Mode = "decision"
    horizon_h: float = 0.0
    cutoff: time = config.DEFAULT_CUTOFF


class WindService:
    def __init__(self, snap: Snapshot):
        self.snap = snap
        self.actual = to_hourly(snap.actuals)
        self.forecasts = snap.forecasts
        # Every (target, publish) pair with an actual: basis for horizon curve and bands.
        self.pairs = an.align(self.forecasts, self.actual)
        self.qtable = an.error_quantiles_by_horizon(self.pairs)

    def _select(self, q: Query) -> pd.DataFrame:
        if q.mode == "decision":
            return an.select_decision(self.forecasts, q.cutoff)
        return an.select_horizon(self.forecasts, q.horizon_h)

    def selected(self, q: Query) -> pd.DataFrame:
        """Chosen forecast per target, aligned to actuals, within the delivery range."""
        return an.in_delivery_range(an.align(self._select(q), self.actual), q.start, q.end)

    def series(self, q: Query) -> pd.DataFrame:
        sel = self._select(q)
        banded = an.apply_bands(sel.rename(columns={"generation": "forecast"}), self.qtable)
        actual = an.in_delivery_range(self.actual, q.start, q.end)
        out = actual.merge(banded, on="start_time", how="left")
        return out.replace({np.nan: None})

    def metrics(self, q: Query) -> tuple[dict, pd.DataFrame]:
        df = self.selected(q)
        m = an.metrics(df["error"], df["actual"])
        if not df.empty:
            banded = an.apply_bands(df, self.qtable)
            m["firm_wind_p10_mean"] = float(banded["p10"].mean())
            m["firm_wind_p10_min"] = float(banded["p10"].min())
            m["forecast_mean"] = float(df["forecast"].mean())
        return m, an.error_by_day(df) if not df.empty else pd.DataFrame()

    def by_horizon(self, q: Query) -> pd.DataFrame:
        return an.error_by_horizon(an.in_delivery_range(self.pairs, q.start, q.end))

    def by_hour(self, q: Query) -> pd.DataFrame:
        return an.error_by_hour(self.selected(q))

    def distribution(self, q: Query) -> tuple[pd.DataFrame, dict]:
        df = self.selected(q)
        return an.histogram(df["error"]), an.metrics(df["error"], df["actual"])


@lru_cache(maxsize=1)
def get_service() -> WindService:
    return WindService(load_snapshot())
