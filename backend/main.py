import shutil
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel

from dwg_converter import convert_dwg
from extractor import extract_from_dxf
from exporter import export_to_xlsx
from pdf_renderer import (
    get_sheets_from_pdf,
    extract_page_as_pdf,
    extract_all_pages_as_zip,
    get_sheets_from_dxf,
    render_dxf_layout_to_pdf,
    render_all_dxf_layouts_to_zip,
)

app = FastAPI(title="Archy AI — CAD Extract Demo")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# In-memory store: file_id → metadata dict
#   pdf_path  — set when CloudConvert was used (primary)
#   dxf_path  — set when local ODA converter was used (fallback)
extractions: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------

@app.post("/api/upload")
async def upload_drawing(file: UploadFile = File(...)):
    filename = file.filename or ""
    ext = Path(filename).suffix.lower()

    if ext not in {".dxf", ".dwg"}:
        raise HTTPException(400, "Only .dxf and .dwg files are supported.")

    file_id = str(uuid.uuid4())
    saved_path = UPLOAD_DIR / f"{file_id}{ext}"

    with open(saved_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    pdf_path: str | None = None
    dxf_path: str | None = None

    if ext == ".dwg":
        try:
            result = convert_dwg(str(saved_path))
            pdf_path = result["pdf_path"]
            dxf_path = result["dxf_path"]
        except RuntimeError as exc:
            raise HTTPException(422, str(exc))
    else:
        # DXF uploaded directly
        dxf_path = str(saved_path)

    # Extract layer metadata when a DXF is available
    extraction_meta: dict = {"id": file_id, "original_filename": filename}
    if dxf_path:
        try:
            meta = extract_from_dxf(dxf_path)
            extraction_meta.update(meta)
        except Exception:
            pass  # metadata extraction is best-effort

    extraction_meta["pdf_path"] = pdf_path
    extraction_meta["dxf_path"] = dxf_path
    extractions[file_id] = extraction_meta

    return {
        "id": file_id,
        "filename": filename,
        "dxf_version": extraction_meta.get("dxf_version", "n/a"),
        "layer_count": extraction_meta.get("layer_count", 0),
        "total_entities": extraction_meta.get("total_entities", 0),
    }


@app.get("/api/extractions/{file_id}")
async def get_extraction(file_id: str):
    _require(file_id)
    return extractions[file_id]


@app.get("/api/extractions/{file_id}/layers")
async def get_layers(file_id: str):
    _require(file_id)
    layers = extractions[file_id].get("layers", {})
    return {
        name: {
            "entity_types": layer["entity_types"],
            "entity_count": len(layer["entities"]),
        }
        for name, layer in layers.items()
    }


@app.get("/api/extractions/{file_id}/entities/{layer_name}")
async def get_layer_entities(file_id: str, layer_name: str):
    _require(file_id)
    layers = extractions[file_id].get("layers", {})
    if layer_name not in layers:
        raise HTTPException(404, f"Layer '{layer_name}' not found")
    entities = layers[layer_name]["entities"]
    return {"layer": layer_name, "entities": entities[:50], "total": len(entities)}


# ---------------------------------------------------------------------------
# Sheet (layout) PDF export — core functionality
# ---------------------------------------------------------------------------

@app.get("/api/extractions/{file_id}/sheets")
async def list_sheets(file_id: str):
    _require(file_id)
    rec = extractions[file_id]

    try:
        if rec.get("pdf_path"):
            sheets = get_sheets_from_pdf(rec["pdf_path"])
        elif rec.get("dxf_path"):
            sheets = get_sheets_from_dxf(rec["dxf_path"])
        else:
            raise HTTPException(422, "No converted file available for sheet listing.")
    except Exception as exc:
        raise HTTPException(500, f"Failed to read sheets: {exc}")

    return {"sheets": sheets}


@app.get("/api/extractions/{file_id}/sheets/{sheet_index}/pdf")
async def export_sheet_pdf(file_id: str, sheet_index: int):
    """Download a single sheet as PDF by its zero-based index."""
    _require(file_id)
    rec = extractions[file_id]

    try:
        if rec.get("pdf_path"):
            pdf_bytes = extract_page_as_pdf(rec["pdf_path"], sheet_index)
        elif rec.get("dxf_path"):
            sheets = get_sheets_from_dxf(rec["dxf_path"])
            if sheet_index < 0 or sheet_index >= len(sheets):
                raise ValueError(f"Sheet index {sheet_index} out of range")
            pdf_bytes = render_dxf_layout_to_pdf(rec["dxf_path"], sheets[sheet_index]["name"])
        else:
            raise HTTPException(422, "No converted file available.")
    except ValueError as exc:
        raise HTTPException(404, str(exc))
    except Exception as exc:
        raise HTTPException(500, f"Render failed: {exc}")

    filename = f"Sheet_{sheet_index + 1}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(pdf_bytes)),
        },
    )


@app.get("/api/extractions/{file_id}/sheets-zip")
async def export_all_sheets_zip(file_id: str):
    """Download all sheets as individual PDFs in a zip archive."""
    _require(file_id)
    rec = extractions[file_id]
    base = Path(rec.get("original_filename", "drawing")).stem

    try:
        if rec.get("pdf_path"):
            zip_bytes = extract_all_pages_as_zip(rec["pdf_path"])
        elif rec.get("dxf_path"):
            zip_bytes = render_all_dxf_layouts_to_zip(rec["dxf_path"])
        else:
            raise HTTPException(422, "No converted file available.")
    except Exception as exc:
        raise HTTPException(500, f"Zip export failed: {exc}")

    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{base}_sheets.zip"',
            "Content-Length": str(len(zip_bytes)),
        },
    )


# ---------------------------------------------------------------------------
# Excel export (legacy)
# ---------------------------------------------------------------------------

class MappingItem(BaseModel):
    layer: str
    entity_type: str
    field: str
    column_name: str


class ExportRequest(BaseModel):
    mappings: list[MappingItem]


@app.post("/api/extractions/{file_id}/export")
async def export_extraction(file_id: str, req: ExportRequest):
    _require(file_id)
    if not req.mappings:
        raise HTTPException(400, "No mappings provided.")
    if not extractions[file_id].get("dxf_path"):
        raise HTTPException(422, "Excel export requires DXF data (not available in cloud-converted files).")

    output_path = UPLOAD_DIR / f"{file_id}_export.xlsx"
    try:
        export_to_xlsx(
            extractions[file_id],
            [m.model_dump() for m in req.mappings],
            str(output_path),
        )
    except Exception as exc:
        raise HTTPException(500, f"Export failed: {exc}")

    return FileResponse(
        output_path,
        filename="cad_extract.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {"status": "ok"}


def _require(file_id: str) -> None:
    if file_id not in extractions:
        raise HTTPException(404, "Extraction not found. Upload a file first.")
