from __future__ import annotations

import math
from datetime import date, time

import pandas as pd
import pytest
from conftest import make_forecasts, ts

from app import analytics as an


def test_horizon_is_start_minus_publish_in_hours(forecasts: pd.DataFrame) -> None:
    assert forecasts["horizon_h"].tolist() == [41.5, 28.5, 26.5, 4.5]


def test_filter_horizon_drops_negative_and_beyond_48h() -> None:
    fc = make_forecasts(
        [
            ("2026-01-10T12:00Z", "2026-01-10T13:00Z", 1.0),  # -1h
            ("2026-01-10T12:00Z", "2026-01-10T12:00Z", 2.0),  # 0h, kept
            ("2026-01-10T12:00Z", "2026-01-08T12:00Z", 3.0),  # 48h, kept
            ("2026-01-10T12:00Z", "2026-01-08T11:00Z", 4.0),  # 49h
        ]
    )
    assert an.filter_horizon(fc, 0, 48)["generation"].tolist() == [2.0, 3.0]


def test_cutoff_utc_winter_and_summer() -> None:
    assert an.cutoff_utc(date(2026, 1, 10), time(9)) == ts("2026-01-09T09:00")
    # BST (UTC+1): 09:00 local on D-1 is 08:00 UTC.
    assert an.cutoff_utc(date(2026, 7, 1), time(9)) == ts("2026-06-30T08:00")


def test_decision_picks_latest_run_before_default_cutoff(forecasts: pd.DataFrame) -> None:
    sel = an.select_decision(forecasts)
    assert len(sel) == 1
    assert sel.iloc[0]["publish_time"] == ts("2026-01-09T07:30")
    assert sel.iloc[0]["generation"] == 6000.0


def test_decision_respects_custom_cutoff(forecasts: pd.DataFrame) -> None:
    assert an.select_decision(forecasts, time(10))["generation"].tolist() == [7000.0]
    assert an.select_decision(forecasts, time(7))["generation"].tolist() == [5000.0]


def test_decision_cutoff_is_inclusive() -> None:
    fc = make_forecasts([("2026-01-10T12:00Z", "2026-01-09T09:00Z", 1.0)])
    assert len(an.select_decision(fc, time(9))) == 1


@pytest.mark.parametrize(
    ("horizon", "expected"),
    [(0, 8000.0), (4.5, 8000.0), (5, 7000.0), (24, 7000.0), (27, 6000.0), (30, 5000.0)],
)
def test_select_horizon(forecasts: pd.DataFrame, horizon: float, expected: float) -> None:
    assert an.select_horizon(forecasts, horizon)["generation"].tolist() == [expected]


def test_select_horizon_empty_when_no_run_old_enough(forecasts: pd.DataFrame) -> None:
    assert an.select_horizon(forecasts, 45).empty


def test_metrics_hand_computed() -> None:
    error = pd.Series([100.0, -100.0, 200.0, 0.0])
    actual = pd.Series([1000.0] * 4)
    m = an.metrics(error, actual)
    assert m["n"] == 4
    assert m["mae"] == 100.0
    assert m["rmse"] == pytest.approx(math.sqrt(15000))
    assert m["bias"] == 50.0
    assert m["mae_pct_of_mean_actual"] == 10.0
    assert m["pct_over"] == 50.0
    assert m["pct_under"] == 25.0
    assert m["p50_abs_error"] == 100.0


def test_metrics_empty() -> None:
    assert an.metrics(pd.Series(dtype=float), pd.Series(dtype=float)) == {"n": 0}


def test_align_computes_forecast_minus_actual(forecasts: pd.DataFrame) -> None:
    actual = pd.DataFrame({"start_time": [ts("2026-01-10T12:00")], "actual": [6500.0]})
    merged = an.align(an.select_decision(forecasts), actual)
    assert merged["error"].tolist() == [-500.0]


def test_bands_use_flipped_error_quantiles_and_floor_at_zero() -> None:
    qtable = pd.DataFrame({"hbin": [24], "q10": [-1000.0], "q50": [0.0], "q90": [2000.0]})
    sel = pd.DataFrame({"forecast": [5000.0, 1000.0], "horizon_h": [28.5, 25.0]})
    out = an.apply_bands(sel, qtable, width=6)
    assert out["p10"].tolist() == [3000.0, 0.0]  # forecast - q90, floored
    assert out["p50"].tolist() == [5000.0, 1000.0]
    assert out["p90"].tolist() == [6000.0, 2000.0]  # forecast - q10


def test_error_quantiles_by_horizon_bins() -> None:
    pairs = pd.DataFrame({"horizon_h": [1.0, 2.0, 7.0], "error": [0.0, 10.0, 5.0]})
    table = an.error_quantiles_by_horizon(pairs, quantiles=(0.5,), width=6)
    assert table.to_dict("list") == {"hbin": [0, 6], "q50": [5.0, 5.0]}


def test_histogram_counts_sum_to_n() -> None:
    error = pd.Series([-600.0, -10.0, 10.0, 499.0, 501.0])
    h = an.histogram(error, bin_mw=500)
    assert h["count"].sum() == 5
    assert h["bin_start"].iloc[0] == -1000.0


def test_error_by_hour_uses_local_hour() -> None:
    df = pd.DataFrame(
        {"start_time": [ts("2026-01-10T12:00"), ts("2026-01-10T12:00")], "error": [1.0, -3.0], "actual": [1.0, 1.0]}
    )
    out = an.error_by_hour(df)
    assert out["hour"].tolist() == [12]
    assert out["mae"].tolist() == [2.0]
    assert out["bias"].tolist() == [-1.0]
