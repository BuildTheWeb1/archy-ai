"""
Vercel entrypoint — one of the auto-detected FastAPI entrypoint paths.
Adds backend/ to sys.path so internal imports resolve correctly.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from main import app  # noqa: E402, F401
