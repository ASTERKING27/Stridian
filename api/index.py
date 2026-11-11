"""Vercel's entry point: the same FastAPI app that runs locally, found in ../backend."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from main import app  # noqa: E402,F401
