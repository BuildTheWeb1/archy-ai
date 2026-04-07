import logging
import shutil
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

import converter
import splitter
import storage
from schemas import DrawingSchema, DrawingStatus, LayoutSchema, UploadResponse

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
    if Path(filename).suffix.lower() != ".dwg":
        raise HTTPException(400, "Only .dwg files are supported.")

    drawing_id = storage.new_drawing_id()
    dwg_path = storage.original_dwg_path(drawing_id)

    with open(dwg_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    storage.save_metadata({
        "id": drawing_id,
        "filename": filename,
        "status": DrawingStatus.processing,
        "error": None,
        "layouts": [],
    })

    background_tasks.add_task(_process_drawing, drawing_id)

    return UploadResponse(id=drawing_id, status=DrawingStatus.processing)


def _process_drawing(drawing_id: str) -> None:
    """Background task: convert DWG → per-layout PDFs via CloudConvert."""
    try:
        dwg_path = storage.original_dwg_path(drawing_id)
        layouts_path = storage.layouts_dir(drawing_id)

        logger.info("Converting %s via CloudConvert…", drawing_id)
        layouts = converter.convert_dwg_to_pdfs(str(dwg_path), str(layouts_path))

        storage.update_layouts(drawing_id, layouts)
        storage.update_status(drawing_id, DrawingStatus.ready)
        logger.info("Drawing %s ready — %d layouts", drawing_id, len(layouts))

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
        layouts=[LayoutSchema(**l) for l in record.get("layouts", [])],
    )


# ---------------------------------------------------------------------------
# Layout PDF downloads
# ---------------------------------------------------------------------------

@app.get("/api/drawings/{drawing_id}/layouts/{index}/pdf")
async def download_layout_pdf(drawing_id: str, index: int):
    record = storage.load_metadata(drawing_id)
    if record is None:
        raise HTTPException(404, "Drawing not found.")
    if record["status"] != DrawingStatus.ready:
        raise HTTPException(409, "Drawing is not ready yet.")

    layouts = record.get("layouts", [])
    layout = next((l for l in layouts if l["index"] == index), None)
    if layout is None:
        raise HTTPException(404, f"Layout {index} not found.")

    pdf_path = storage.layout_pdf_path(drawing_id, index)
    if not pdf_path.exists():
        raise HTTPException(500, "Layout PDF missing on disk.")

    safe_name = layout["name"].replace("/", "_").replace("\\", "_")
    filename = f"{index + 1:02d}_{safe_name}.pdf"

    return Response(
        content=pdf_path.read_bytes(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/drawings/{drawing_id}/download")
async def download_all_layouts(drawing_id: str):
    record = storage.load_metadata(drawing_id)
    if record is None:
        raise HTTPException(404, "Drawing not found.")
    if record["status"] != DrawingStatus.ready:
        raise HTTPException(409, "Drawing is not ready yet.")

    layouts = record.get("layouts", [])
    layouts_path = storage.layouts_dir(drawing_id)
    zip_bytes = splitter.build_zip(str(layouts_path), layouts)

    base = Path(record["filename"]).stem
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{base}_layouts.zip"'},
    )


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {"status": "ok"}
