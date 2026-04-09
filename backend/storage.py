"""
Local file-based storage with JSON metadata.

Structure:
  uploads/
    {drawing_id}/
      metadata.json     — DrawingRecord dict
      original.dwg/.dxf — uploaded file
      output.pdf        — converted PDF
"""

import json
import uuid
from pathlib import Path


UPLOADS_DIR = Path(__file__).parent / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)


def new_drawing_id() -> str:
    return str(uuid.uuid4())


def drawing_dir(drawing_id: str) -> Path:
    d = UPLOADS_DIR / drawing_id
    d.mkdir(parents=True, exist_ok=True)
    return d


# ---------------------------------------------------------------------------
# Metadata read/write
# ---------------------------------------------------------------------------

def save_metadata(record: dict) -> None:
    path = drawing_dir(record["id"]) / "metadata.json"
    path.write_text(json.dumps(record, indent=2))


def load_metadata(drawing_id: str) -> dict | None:
    path = UPLOADS_DIR / drawing_id / "metadata.json"
    if not path.exists():
        return None
    return json.loads(path.read_text())


def update_status(drawing_id: str, status: str, error: str | None = None) -> None:
    record = load_metadata(drawing_id)
    if record is None:
        return
    record["status"] = status
    if error is not None:
        record["error"] = error
    save_metadata(record)


# ---------------------------------------------------------------------------
# File paths
# ---------------------------------------------------------------------------

def original_path(drawing_id: str, ext: str = ".dwg") -> Path:
    return drawing_dir(drawing_id) / f"original{ext}"


def pdf_path(drawing_id: str) -> Path:
    return drawing_dir(drawing_id) / "output.pdf"
