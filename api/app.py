"""
Vercel entrypoint — lives in api/ so Vercel picks it up as a serverless function.
Adds backend/ to sys.path so internal imports resolve correctly.
"""

import os
import sys

# __file__ is api/app.py; backend/ is one level up
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from main import app  # noqa: E402, F401
