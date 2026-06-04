"""
Vercel entrypoint — lives in api/ so Vercel picks it up as a serverless function.
Adds backend/ to sys.path so internal imports resolve correctly.

Per Vercel docs, the working directory is always the project root.
We use os.getcwd() instead of __file__-relative paths for reliability.
"""

import os
import sys

# Vercel cwd = project root; backend/ is a direct subdirectory
_backend_path = os.path.join(os.getcwd(), "backend")
if _backend_path not in sys.path:
    sys.path.insert(0, _backend_path)

from main import app  # noqa: E402, F401
