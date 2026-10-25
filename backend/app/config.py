"""Single source of truth for constants and environment-driven settings."""

from __future__ import annotations

import os
from datetime import date, time
from pathlib import Path
from zoneinfo import ZoneInfo

# --- Time zones ---------------------------------------------------------------
UTC = ZoneInfo("UTC")
LONDON = ZoneInfo("Europe/London")

# --- Analysis window ------------------------------------------------------------
DECISION_START = date(2026, 1, 1)  # first D-1 decision day
DECISION_END = date(2026, 1, 31)  # last D-1 decision day
DELIVERY_START = date(2026, 1, 2)  # = DECISION_START + 1 day
DELIVERY_END = date(2026, 2, 1)  # = DECISION_END + 1 day
FORECAST_BUFFER_HOURS = 48  # fetch forecasts published this long before the window

# --- Forecast selection ---------------------------------------------------------
DEFAULT_CUTOFF = time(9, 0)  # D-1 local London time
MIN_HORIZON_H = 0.0
MAX_HORIZON_H = 48.0
FORECAST_RESOLUTION = "1h"  # WINDFOR native resolution; actuals are averaged to this
ACTUAL_RESOLUTION_MIN = 30
WIND_FUEL_TYPE = "WIND"

# --- Analytics ------------------------------------------------------------------
BAND_QUANTILES = (0.10, 0.50, 0.90)
ABS_ERROR_PERCENTILES = (50, 90, 99)
BAND_HORIZON_BIN_H = 6  # horizon bucket width for empirical error quantiles
HISTOGRAM_BIN_MW = 500

# --- Elexon client --------------------------------------------------------------
ELEXON_BASE_URL = os.getenv("ELEXON_BASE_URL", "https://data.elexon.co.uk/bmrs/api/v1")
HTTP_TIMEOUT_S = float(os.getenv("HTTP_TIMEOUT_S", "60"))
HTTP_MAX_RETRIES = int(os.getenv("HTTP_MAX_RETRIES", "4"))
FETCH_CHUNK_DAYS = int(os.getenv("FETCH_CHUNK_DAYS", "7"))

# --- Storage --------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.getenv("DATA_DIR", REPO_ROOT / "data"))
SNAPSHOT_VERSION = "v1"
SNAPSHOT_FILE = DATA_DIR / f"wind_jan2026_{SNAPSHOT_VERSION}.json.gz"

# --- API ------------------------------------------------------------------------
# Comma-separated. Empty by default: every deployment (Vercel, nginx, Vite proxy) serves the UI and
# /api from the same origin, so cross-origin access is only needed if the frontend is hosted elsewhere.
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]
