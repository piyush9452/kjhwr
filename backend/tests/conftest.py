from __future__ import annotations

import pandas as pd
import pytest

from app.analytics import add_horizon


def ts(s: str) -> pd.Timestamp:
    return pd.Timestamp(s, tz="UTC")


def make_forecasts(rows: list[tuple[str, str, float]]) -> pd.DataFrame:
    """rows: (start_time, publish_time, generation)"""
    df = pd.DataFrame(rows, columns=["start_time", "publish_time", "generation"])
    df["start_time"] = pd.to_datetime(df["start_time"], utc=True)
    df["publish_time"] = pd.to_datetime(df["publish_time"], utc=True)
    return add_horizon(df)


@pytest.fixture
def forecasts() -> pd.DataFrame:
    # Target 2026-01-10 12:00 with four runs; cutoff (D-1 09:00) is 2026-01-09 09:00 UTC.
    return make_forecasts(
        [
            ("2026-01-10T12:00Z", "2026-01-08T18:30Z", 5000.0),  # h=41.5
            ("2026-01-10T12:00Z", "2026-01-09T07:30Z", 6000.0),  # h=28.5, latest before cutoff
            ("2026-01-10T12:00Z", "2026-01-09T09:30Z", 7000.0),  # h=26.5, after cutoff
            ("2026-01-10T12:00Z", "2026-01-10T07:30Z", 8000.0),  # h=4.5, same-day
        ]
    )
