"""Fetch January 2026 wind actuals + forecasts from Elexon and write a versioned snapshot.

Usage:
    python scripts/fetch_data.py            # writes data/wind_jan2026_v1.json.gz
    python scripts/fetch_data.py --refresh  # overwrite an existing snapshot
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, time, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app import config
from app.elexon_client import ElexonClient
from app.ingest import build_snapshot, save_snapshot


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="overwrite existing snapshot")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    if config.SNAPSHOT_FILE.exists() and not args.refresh:
        logging.info("Snapshot exists at %s (use --refresh to overwrite)", config.SNAPSHOT_FILE)
        return 0

    window_start = datetime.combine(config.DELIVERY_START, time(0), tzinfo=config.LONDON)
    window_end = datetime.combine(config.DELIVERY_END + timedelta(days=1), time(0), tzinfo=config.LONDON)
    publish_from = (window_start - timedelta(hours=config.FORECAST_BUFFER_HOURS)).astimezone(config.UTC)

    with ElexonClient() as client:
        actuals = client.fuelhh(config.DELIVERY_START, config.DELIVERY_END, config.WIND_FUEL_TYPE)
        forecasts = client.windfor(publish_from, window_end.astimezone(config.UTC))

    path = save_snapshot(build_snapshot(actuals, forecasts))
    logging.info("Wrote %s (%.1f kB)", path, path.stat().st_size / 1024)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
