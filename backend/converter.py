"""
DWG → per-layout PDFs via CloudConvert.

CloudConvert uses a native CAD engine to render the DWG. With all_layouts=True
it produces one PDF file per AutoCAD Paper Space layout.

Requires CLOUDCONVERT_API_KEY in the environment.
"""

import logging
import os
import time
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

_CC_BASE = "https://api.cloudconvert.com/v2"
_TIMEOUT_SECONDS = 300  # 5 minutes


def convert_dwg_to_pdfs(dwg_path: str, layouts_dir: str) -> list[dict]:
    """
    Convert a DWG file to individual layout PDFs.

    CloudConvert may return one file per layout when all_layouts=True.
    Downloads all output files into layouts_dir as 0.pdf, 1.pdf, etc.

    Returns list of {"index": int, "name": str} for each layout.
    Raises RuntimeError on failure.
    """
    api_key = os.environ.get("CLOUDCONVERT_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "CLOUDCONVERT_API_KEY is not set. "
            "Add it to your .env file to enable DWG conversion."
        )

    headers = {"Authorization": f"Bearer {api_key}"}
    dwg = Path(dwg_path)
    out = Path(layouts_dir)
    out.mkdir(parents=True, exist_ok=True)

    # 1. Create job: upload → convert → export
    job_resp = requests.post(
        f"{_CC_BASE}/jobs",
        headers=headers,
        json={
            "tasks": {
                "upload-dwg": {"operation": "import/upload"},
                "convert-to-pdf": {
                    "operation": "convert",
                    "input": "upload-dwg",
                    "input_format": "dwg",
                    "output_format": "pdf",
                    "engine": "cadconverter",
                    "all_layouts": True,
                },
                "export-pdf": {
                    "operation": "export/url",
                    "input": "convert-to-pdf",
                },
            }
        },
        timeout=30,
    )
    job_resp.raise_for_status()
    job = job_resp.json()["data"]

    # 2. Upload the DWG
    upload_task = next(t for t in job["tasks"] if t["name"] == "upload-dwg")
    form = upload_task["result"]["form"]
    with open(dwg_path, "rb") as f:
        upload_resp = requests.post(
            form["url"],
            data=form["parameters"],
            files={"file": (dwg.name, f)},
            timeout=120,
        )
    upload_resp.raise_for_status()

    # 3. Poll until finished
    job_id = job["id"]
    deadline = time.time() + _TIMEOUT_SECONDS
    while time.time() < deadline:
        time.sleep(4)
        status_resp = requests.get(
            f"{_CC_BASE}/jobs/{job_id}", headers=headers, timeout=30
        )
        status_resp.raise_for_status()
        data = status_resp.json()["data"]

        if data["status"] == "finished":
            break
        if data["status"] == "error":
            tasks = data.get("tasks", [])
            failed = next((t for t in tasks if t["status"] == "error"), None)
            msg = failed.get("message", "Unknown error") if failed else "Conversion failed"
            raise RuntimeError(f"CloudConvert error: {msg}")
    else:
        raise RuntimeError("CloudConvert timed out after 5 minutes.")

    # 4. Download ALL output files
    tasks = status_resp.json()["data"]["tasks"]
    export_task = next(t for t in tasks if t["name"] == "export-pdf")
    files = export_task["result"]["files"]

    logger.info(
        "CloudConvert produced %d output file(s): %s",
        len(files),
        [f.get("filename", "?") for f in files],
    )

    layouts = []
    for i, file_info in enumerate(files):
        url = file_info["url"]
        filename = file_info.get("filename", f"layout_{i}.pdf")
        name = _layout_name_from_filename(filename, i)

        pdf_resp = requests.get(url, timeout=120)
        pdf_resp.raise_for_status()

        pdf_path = out / f"{i}.pdf"
        pdf_path.write_bytes(pdf_resp.content)

        logger.info(
            "  Layout %d: %s (%d bytes)", i, name, len(pdf_resp.content)
        )
        layouts.append({"index": i, "name": name})

    if not layouts:
        raise RuntimeError("CloudConvert returned no output files.")

    return layouts


def _layout_name_from_filename(filename: str, index: int) -> str:
    """Extract a human-friendly layout name from the CloudConvert output filename."""
    stem = Path(filename).stem
    # CloudConvert often names files like "drawing_Layout1.pdf" or "drawing.pdf"
    # Try to extract the layout part after the last underscore or hyphen
    for sep in ("_", "-"):
        if sep in stem:
            parts = stem.split(sep)
            # The layout name is usually the last segment
            candidate = parts[-1].strip()
            if candidate:
                return candidate
    return stem if stem else f"Layout_{index + 1}"
