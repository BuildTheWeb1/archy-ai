import logging
import shutil
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

import storage
from pipeline.excel_export import export_schedule
from pipeline.orchestrator import run_pipeline
from schemas import (
    PDFInfo,
    PDFStatus,
    ProjectCreate,
    ProjectResponse,
    ProjectStatus,
    ScheduleResponse,
    ScheduleRow,
    ScheduleUpdate,
    UploadPDFResponse,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="ArchyAI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Helpers ────────────────────────────────────────────────────────────────

def _project_response(record: dict) -> ProjectResponse:
    schedule = record.get("schedule")
    schedule_resp = None
    if schedule:
        schedule_resp = ScheduleResponse(
            id=schedule["id"],
            project_id=record["id"],
            status=schedule.get("status", "ready"),
            rows=[ScheduleRow(**r) for r in schedule.get("rows", [])],
            warnings=schedule.get("warnings", []),
            generated_at=schedule.get("generated_at"),
            last_edited_at=schedule.get("last_edited_at"),
        )
    return ProjectResponse(
        id=record["id"],
        name=record["name"],
        project_number=record.get("project_number"),
        beneficiary=record.get("beneficiary"),
        location=record.get("location"),
        status=ProjectStatus(record.get("status", "active")),
        pdfs=[PDFInfo(**p) for p in record.get("pdfs", [])],
        schedule=schedule_resp,
        created_at=record["created_at"],
    )


# ── Projects ───────────────────────────────────────────────────────────────

@app.post("/api/projects", response_model=ProjectResponse, status_code=201)
async def create_project(body: ProjectCreate):
    record = storage.create_project(
        name=body.name,
        project_number=body.project_number,
        beneficiary=body.beneficiary,
        location=body.location,
    )
    return _project_response(record)


@app.get("/api/projects", response_model=list[ProjectResponse])
async def list_projects():
    return [_project_response(r) for r in storage.list_projects()]


@app.get("/api/projects/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str):
    record = storage.load_project(project_id)
    if record is None:
        raise HTTPException(404, "Proiectul nu a fost găsit.")
    return _project_response(record)


@app.delete("/api/projects/{project_id}", status_code=204)
async def delete_project(project_id: str):
    deleted = storage.delete_project(project_id)
    if not deleted:
        raise HTTPException(404, "Proiectul nu a fost găsit.")


# ── PDFs ───────────────────────────────────────────────────────────────────

@app.post("/api/projects/{project_id}/pdfs", response_model=UploadPDFResponse, status_code=201)
async def upload_pdfs(
    project_id: str,
    files: list[UploadFile] = File(...),
):
    record = storage.load_project(project_id)
    if record is None:
        raise HTTPException(404, "Proiectul nu a fost găsit.")

    if len(files) > 10:
        raise HTTPException(400, "Maxim 10 fișiere per încărcare.")

    uploaded: list[PDFInfo] = []
    for file in files:
        filename = file.filename or "upload.pdf"
        if not filename.lower().endswith(".pdf"):
            raise HTTPException(400, f"Doar fișiere PDF sunt acceptate. ({filename})")

        pdf_record = storage.add_pdf(project_id, filename)
        dest = storage.pdf_file_path(project_id, pdf_record["id"])
        with open(dest, "wb") as f:
            shutil.copyfileobj(file.file, f)

        uploaded.append(PDFInfo(**pdf_record))

    return UploadPDFResponse(uploaded=uploaded)


@app.get("/api/projects/{project_id}/pdfs", response_model=list[PDFInfo])
async def list_pdfs(project_id: str):
    record = storage.load_project(project_id)
    if record is None:
        raise HTTPException(404, "Proiectul nu a fost găsit.")
    return [PDFInfo(**p) for p in record.get("pdfs", [])]


# ── Extraction ─────────────────────────────────────────────────────────────

@app.post("/api/projects/{project_id}/extract", status_code=202)
async def trigger_extraction(project_id: str, background_tasks: BackgroundTasks):
    record = storage.load_project(project_id)
    if record is None:
        raise HTTPException(404, "Proiectul nu a fost găsit.")
    if not record.get("pdfs"):
        raise HTTPException(400, "Nu există PDF-uri încărcate pentru acest proiect.")

    storage.set_project_status(project_id, "processing")
    background_tasks.add_task(_extract_task, project_id)
    return {"status": "processing"}


def _extract_task(project_id: str) -> None:
    try:
        record = storage.load_project(project_id)
        if record is None:
            return

        pdf_paths: list[Path] = []
        for pdf in record.get("pdfs", []):
            path = storage.pdf_file_path(project_id, pdf["id"])
            if path.exists():
                pdf_paths.append(path)
                storage.update_pdf_status(project_id, pdf["id"], "processing")

        if not pdf_paths:
            storage.set_project_status(project_id, "error", "Nu s-au găsit fișiere PDF.")
            return

        rows, warnings = run_pipeline(pdf_paths)

        for pdf in record.get("pdfs", []):
            storage.update_pdf_status(project_id, pdf["id"], "ready")

        storage.save_schedule(project_id, rows, warnings, status="ready")
        logger.info("Extraction complete for project %s: %d rows", project_id, len(rows))

    except Exception as exc:
        logger.error("Extraction failed for project %s: %s", project_id, exc, exc_info=True)
        storage.set_project_status(project_id, "error", str(exc))


# ── Schedule ───────────────────────────────────────────────────────────────

@app.get("/api/projects/{project_id}/schedule", response_model=ScheduleResponse)
async def get_schedule(project_id: str):
    record = storage.load_project(project_id)
    if record is None:
        raise HTTPException(404, "Proiectul nu a fost găsit.")

    schedule = record.get("schedule")
    if schedule is None:
        # Return empty schedule with processing status while extraction runs
        return ScheduleResponse(
            id="",
            project_id=project_id,
            status=record.get("status", "active"),
            rows=[],
            warnings=[],
        )

    return ScheduleResponse(
        id=schedule["id"],
        project_id=project_id,
        status=schedule.get("status", "ready"),
        rows=[ScheduleRow(**r) for r in schedule.get("rows", [])],
        warnings=schedule.get("warnings", []),
        generated_at=schedule.get("generated_at"),
        last_edited_at=schedule.get("last_edited_at"),
    )


@app.put("/api/projects/{project_id}/schedule", response_model=ScheduleResponse)
async def update_schedule(project_id: str, body: ScheduleUpdate):
    record = storage.load_project(project_id)
    if record is None:
        raise HTTPException(404, "Proiectul nu a fost găsit.")

    rows = [r.model_dump() for r in body.rows]
    schedule = storage.update_schedule_rows(project_id, rows)
    if schedule is None:
        raise HTTPException(404, "Schedule-ul nu există. Rulați mai întâi extracția.")

    return ScheduleResponse(
        id=schedule["id"],
        project_id=project_id,
        status=schedule.get("status", "ready"),
        rows=[ScheduleRow(**r) for r in schedule.get("rows", [])],
        warnings=schedule.get("warnings", []),
        generated_at=schedule.get("generated_at"),
        last_edited_at=schedule.get("last_edited_at"),
    )


@app.get("/api/projects/{project_id}/schedule/xlsx")
async def export_xlsx(project_id: str):
    record = storage.load_project(project_id)
    if record is None:
        raise HTTPException(404, "Proiectul nu a fost găsit.")

    schedule = record.get("schedule")
    if not schedule or not schedule.get("rows"):
        raise HTTPException(400, "Schedule-ul este gol sau nu a fost generat.")

    output_path = storage.xlsx_path(project_id)
    export_schedule(
        rows=schedule["rows"],
        output_path=output_path,
        project_name=record.get("name", ""),
        project_number=record.get("project_number") or "",
        beneficiary=record.get("beneficiary") or "",
        location=record.get("location") or "",
    )

    safe_name = record["name"].replace(" ", "_")
    return Response(
        content=output_path.read_bytes(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="extras_armare_{safe_name}.xlsx"'},
    )


# ── Health ─────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok"}
