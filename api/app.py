"""
Vercel entrypoint — lives in api/ so Vercel picks it up as a serverless function.
Adds backend/ to sys.path so internal imports resolve correctly.
"""

import os
import sys

# Derive project root from this file's location: api/app.py -> api/ -> root
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_backend_path = os.path.join(_root, "backend")
if _backend_path not in sys.path:
    sys.path.insert(0, _backend_path)

from main import app  # noqa: E402, F401
