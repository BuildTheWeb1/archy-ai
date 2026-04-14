"""
Local file-based storage for ArchyAI projects.

Directory structure:
  uploads/
    {project_id}/
      metadata.json        ← project record (name, pdfs list, schedule)
      pdfs/
        {pdf_id}.pdf       ← uploaded PDF files
      exports/
        schedule.xlsx      ← most recent Excel export
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path


UPLOADS_DIR = Path(__file__).parent / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)


# ── IDs ───────────────────────────────────────────────────────────────────

def new_id() -> str:
    return str(uuid.uuid4())


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Directory helpers ─────────────────────────────────────────────────────

def project_dir(project_id: str) -> Path:
    d = UPLOADS_DIR / project_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def pdfs_dir(project_id: str) -> Path:
    d = project_dir(project_id) / "pdfs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def exports_dir(project_id: str) -> Path:
    d = project_dir(project_id) / "exports"
    d.mkdir(parents=True, exist_ok=True)
    return d


def pdf_file_path(project_id: str, pdf_id: str) -> Path:
    return pdfs_dir(project_id) / f"{pdf_id}.pdf"


def xlsx_path(project_id: str) -> Path:
    return exports_dir(project_id) / "schedule.xlsx"


# ── Metadata read/write ───────────────────────────────────────────────────

def _meta_path(project_id: str) -> Path:
    return project_dir(project_id) / "metadata.json"


def save_project(record: dict) -> None:
    _meta_path(record["id"]).write_text(json.dumps(record, indent=2, ensure_ascii=False))


def load_project(project_id: str) -> dict | None:
    path = UPLOADS_DIR / project_id / "metadata.json"
    if not path.exists():
        return None
    return json.loads(path.read_text())


def list_projects() -> list[dict]:
    projects = []
    for meta in UPLOADS_DIR.glob("*/metadata.json"):
        try:
            projects.append(json.loads(meta.read_text()))
        except (json.JSONDecodeError, OSError):
            continue
    projects.sort(key=lambda p: p.get("created_at", ""), reverse=True)
    return projects


def delete_project(project_id: str) -> bool:
    import shutil
    d = UPLOADS_DIR / project_id
    if not d.exists():
        return False
    shutil.rmtree(d)
    return True


# ── Project factory ───────────────────────────────────────────────────────

def create_project(name: str, project_number: str | None, beneficiary: str | None, location: str | None) -> dict:
    record = {
        "id": new_id(),
        "name": name,
        "project_number": project_number,
        "beneficiary": beneficiary,
        "location": location,
        "status": "active",
        "pdfs": [],
        "schedule": None,
        "created_at": _now(),
    }
    save_project(record)
    return record


# ── PDF helpers ───────────────────────────────────────────────────────────

def add_pdf(project_id: str, filename: str) -> dict:
    """Register a PDF in the project's metadata and return the PDF record."""
    record = load_project(project_id)
    if record is None:
        raise ValueError(f"Project {project_id} not found")

    pdf_record = {
        "id": new_id(),
        "filename": filename,
        "status": "uploaded",
        "error": None,
        "uploaded_at": _now(),
    }
    record["pdfs"].append(pdf_record)
    save_project(record)
    return pdf_record


def update_pdf_status(project_id: str, pdf_id: str, status: str, error: str | None = None) -> None:
    record = load_project(project_id)
    if record is None:
        return
    for pdf in record["pdfs"]:
        if pdf["id"] == pdf_id:
            pdf["status"] = status
            if error is not None:
                pdf["error"] = error
            break
    save_project(record)


# ── Schedule helpers ──────────────────────────────────────────────────────

def save_schedule(
    project_id: str,
    rows: list[dict],
    warnings: list[str],
    status: str = "ready",
) -> dict:
    record = load_project(project_id)
    if record is None:
        raise ValueError(f"Project {project_id} not found")

    schedule = {
        "id": new_id(),
        "project_id": project_id,
        "status": status,
        "rows": rows,
        "warnings": warnings,
        "generated_at": _now(),
        "last_edited_at": None,
    }
    record["schedule"] = schedule
    record["status"] = "ready" if status == "ready" else status
    save_project(record)
    return schedule


def update_schedule_rows(project_id: str, rows: list[dict]) -> dict | None:
    record = load_project(project_id)
    if record is None or record.get("schedule") is None:
        return None
    record["schedule"]["rows"] = rows
    record["schedule"]["last_edited_at"] = _now()
    save_project(record)
    return record["schedule"]


def set_project_status(project_id: str, status: str, error: str | None = None) -> None:
    record = load_project(project_id)
    if record is None:
        return
    record["status"] = status
    if error is not None:
        record["error"] = error
    save_project(record)
