"""
Vercel entrypoint — lives in api/ so Vercel picks it up as a serverless function.
Adds backend/ to sys.path so internal imports resolve correctly.
"""

import os
import sys
import traceback

# __file__ is api/app.py; backend/ is one level up
_backend_path = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))
sys.path.insert(0, _backend_path)

try:
    from main import app  # noqa: E402, F401
except Exception:
    _tb = traceback.format_exc()
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse
    app = FastAPI()

    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
    async def _import_error(path: str = ""):
        return JSONResponse(status_code=500, content={"import_error": _tb, "backend_path": _backend_path})
