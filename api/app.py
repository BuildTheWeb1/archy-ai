"""
Vercel entrypoint — lives in api/ so Vercel picks it up as a serverless function.
Adds backend/ to sys.path so internal imports resolve correctly.
"""

import os
import sys

# __file__ is api/app.py; backend/ is one level up
_backend_path = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))
sys.path.insert(0, _backend_path)

from main import app  # noqa: E402, F401
