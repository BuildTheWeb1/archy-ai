import logging
import shutil
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from fastapi import BackgroundTasks, FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

import converter
import storage
from schemas import DrawingSchema, DrawingStatus, UploadResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="ArchyAI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Upload & process
# ---------------------------------------------------------------------------

@app.post("/api/drawings/upload", response_model=UploadResponse)
async def upload_drawing(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    filename = file.filename or ""
    ext = Path(filename).suffix.lower()
    if ext not in (".dwg", ".dxf", ".pdf"):
        raise HTTPException(400, "Only .dwg, .dxf, and .pdf files are supported.")

    drawing_id = storage.new_drawing_id()
    file_path  = storage.original_path(drawing_id, ext)

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    storage.save_metadata({
        "id":       drawing_id,
        "filename": filename,
        "status":   DrawingStatus.processing,
        "error":    None,
    })

    if ext == ".pdf":
        background_tasks.add_task(_process_pdf, drawing_id)
    else:
        background_tasks.add_task(_process_drawing, drawing_id)

    return UploadResponse(id=drawing_id, status=DrawingStatus.processing)


def _process_pdf(drawing_id: str) -> None:
    """Background task: use the uploaded PDF directly as output."""
    try:
        src = storage.original_path(drawing_id, ".pdf")
        dst = storage.pdf_path(drawing_id)
        shutil.copy2(src, dst)
        storage.update_status(drawing_id, DrawingStatus.ready)
        logger.info("Drawing %s ready (PDF passthrough)", drawing_id)
    except Exception as exc:
        logger.error("PDF passthrough failed for %s: %s", drawing_id, exc)
        storage.update_status(drawing_id, DrawingStatus.error, str(exc))


def _process_drawing(drawing_id: str) -> None:
    """Background task: convert DWG/DXF → PDF via APS."""
    try:
        record  = storage.load_metadata(drawing_id)
        ext     = Path(record["filename"]).suffix.lower()
        dwg     = storage.original_path(drawing_id, ext)
        out_dir = storage.drawing_dir(drawing_id)

        logger.info("Converting %s…", record["filename"])
        pdf = converter.convert_dwg_to_pdf(str(dwg), str(out_dir))

        # Ensure the output lands at the canonical pdf_path location
        canonical = storage.pdf_path(drawing_id)
        if pdf != canonical:
            shutil.move(str(pdf), str(canonical))

        storage.update_status(drawing_id, DrawingStatus.ready)
        logger.info("Drawing %s ready", drawing_id)

    except Exception as exc:
        logger.error("Processing failed for %s: %s", drawing_id, exc)
        storage.update_status(drawing_id, DrawingStatus.error, str(exc))


# ---------------------------------------------------------------------------
# Drawing status
# ---------------------------------------------------------------------------

@app.get("/api/drawings/{drawing_id}", response_model=DrawingSchema)
async def get_drawing(drawing_id: str):
    record = storage.load_metadata(drawing_id)
    if record is None:
        raise HTTPException(404, "Drawing not found.")
    return DrawingSchema(
        id=record["id"],
        filename=record["filename"],
        status=record["status"],
        error=record.get("error"),
    )


# ---------------------------------------------------------------------------
# PDF download
# ---------------------------------------------------------------------------

@app.get("/api/drawings/{drawing_id}/pdf")
async def get_drawing_pdf(drawing_id: str):
    record = storage.load_metadata(drawing_id)
    if record is None:
        raise HTTPException(404, "Drawing not found.")
    if record["status"] != DrawingStatus.ready:
        raise HTTPException(409, "Drawing is not ready yet.")

    path = storage.pdf_path(drawing_id)
    if not path.exists():
        raise HTTPException(500, "PDF missing on disk.")

    stem     = Path(record["filename"]).stem
    filename = f"{stem}.pdf"

    return Response(
        content=path.read_bytes(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {"status": "ok"}
