"""Vercel serverless entrypoint: exposes the FastAPI ASGI app."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.main import app

__all__ = ["app"]
