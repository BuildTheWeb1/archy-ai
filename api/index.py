"""
Vercel serverless function entrypoint.
Imports the FastAPI app from backend/main.py so Vercel can run it.
"""

import os
import sys

# Add backend/ to the Python path so its internal imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from main import app  # noqa: E402, F401 — Vercel looks for `app`
