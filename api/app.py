"""
Temporary debug entrypoint — exposes runtime environment info.
"""

import os
import sys
from fastapi import FastAPI

app = FastAPI()

@app.get("/api/debug-env")
def debug_env():
    backend_by_cwd = os.path.join(os.getcwd(), "backend")
    backend_by_file = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))
    return {
        "cwd": os.getcwd(),
        "file": __file__,
        "file_abs": os.path.abspath(__file__),
        "backend_by_cwd": backend_by_cwd,
        "backend_by_file": backend_by_file,
        "backend_cwd_exists": os.path.isdir(backend_by_cwd),
        "backend_file_exists": os.path.isdir(backend_by_file),
        "sys_path": sys.path[:8],
    }
