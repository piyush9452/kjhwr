from __future__ import annotations

from pathlib import Path

from app.ingest import build_snapshot, clean_actuals, clean_forecasts, load_snapshot, save_snapshot, to_hourly


def _fuel(start: str, gen: float, publish: str, fuel: str = "WIND", sp: int = 1) -> dict:
    return {
        "startTime": start,
        "publishTime": publish,
        "settlementDate": start[:10],
        "settlementPeriod": sp,
        "fuelType": fuel,
        "generation": gen,
    }


def test_clean_actuals_filters_wind_and_keeps_latest_duplicate() -> None:
    rows = [
        _fuel("2026-01-02T00:00:00Z", 100, "2026-01-02T00:30:00Z"),
        _fuel("2026-01-02T00:00:00Z", 110, "2026-01-02T01:00:00Z"),  # revised
        _fuel("2026-01-02T00:30:00Z", 120, "2026-01-02T01:00:00Z", sp=2),
        _fuel("2026-01-02T00:00:00Z", 999, "2026-01-02T00:30:00Z", fuel="CCGT"),
    ]
    df, q = clean_actuals(rows)
    assert df["generation"].tolist() == [110.0, 120.0]
    assert q["duplicates_dropped"] == 1
    assert q["missing_half_hours"] == 0


def test_clean_actuals_reports_gaps() -> None:
    rows = [
        _fuel("2026-01-02T00:00:00Z", 1, "x"),
        _fuel("2026-01-02T01:30:00Z", 1, "x"),
    ]
    rows = [{**r, "publishTime": "2026-01-02T02:00:00Z"} for r in rows]
    _, q = clean_actuals(rows)
    assert q["missing_half_hours"] == 2


def test_to_hourly_averages_halves_and_drops_incomplete_hours() -> None:
    rows = [
        _fuel("2026-01-02T00:00:00Z", 100, "2026-01-02T03:00:00Z"),
        _fuel("2026-01-02T00:30:00Z", 200, "2026-01-02T03:00:00Z"),
        _fuel("2026-01-02T01:00:00Z", 300, "2026-01-02T03:00:00Z"),  # missing 01:30
    ]
    df, _ = clean_actuals(rows)
    hourly = to_hourly(df)
    assert hourly["actual"].tolist() == [150.0]


def test_clean_forecasts_drops_out_of_range_horizons() -> None:
    rows = [
        {"startTime": "2026-01-02T00:00:00Z", "publishTime": "2026-01-02T01:00:00Z", "generation": 1},
        {"startTime": "2026-01-02T00:00:00Z", "publishTime": "2026-01-01T00:00:00Z", "generation": 2},
        {"startTime": "2026-01-02T00:00:00Z", "publishTime": "2026-01-01T00:00:00Z", "generation": 2},
    ]
    df, q = clean_forecasts(rows)
    assert df["generation"].tolist() == [2.0]
    assert q["duplicates_dropped"] == 1
    assert q["rows_outside_horizon_dropped"] == 1


def test_snapshot_round_trip(tmp_path: Path) -> None:
    snap = build_snapshot(
        [_fuel("2026-01-02T00:00:00Z", 100, "2026-01-02T00:30:00Z")],
        [{"startTime": "2026-01-02T00:00:00Z", "publishTime": "2026-01-01T07:30:00Z", "generation": 5}],
    )
    path = save_snapshot(snap, tmp_path / "s.json.gz")
    back = load_snapshot(path)
    assert back.forecasts["horizon_h"].tolist() == [16.5]
    assert str(back.actuals["start_time"].dt.tz) == "UTC"


def test_null_generation_is_dropped_and_counted() -> None:
    rows = [
        _fuel("2026-01-02T00:00:00Z", 100, "2026-01-02T00:30:00Z"),
        _fuel("2026-01-02T00:30:00Z", None, "2026-01-02T01:00:00Z", sp=2),
    ]
    df, q = clean_actuals(rows)
    assert df["generation"].tolist() == [100.0]
    assert q["null_values_dropped"] == 1
    assert q["duplicates_dropped"] == 0

    fc, fq = clean_forecasts(
        [
            {"startTime": "2026-01-02T12:00:00Z", "publishTime": "2026-01-02T00:30:00Z", "generation": None},
            {"startTime": "2026-01-02T13:00:00Z", "publishTime": "2026-01-02T00:30:00Z", "generation": 5.0},
        ]
    )
    assert len(fc) == 1
    assert fq["null_values_dropped"] == 1
