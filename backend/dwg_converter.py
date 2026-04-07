"""
DWG → PDF conversion via CloudConvert (or local fallback via DXF).

CloudConvert renders the DWG natively using its own CAD engine, producing a
correct multi-page PDF (one page per AutoCAD layout/sheet). This is far more
reliable than going through DXF + ezdxf rendering.

Priority:
  1. CloudConvert API  — if CLOUDCONVERT_API_KEY env var is set
  2. Local ODA File Converter — fallback, produces DXF (lower quality rendering)
"""

import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

import requests


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def convert_dwg(dwg_path: str) -> dict:
    """
    Convert a DWG file.
    Returns a dict:
      { "pdf_path": str, "dxf_path": str | None }

    pdf_path is always set (used for sheet rendering).
    dxf_path is set only when a local converter is available (used for metadata).
    """
    api_key = os.environ.get("CLOUDCONVERT_API_KEY", "").strip()

    if api_key:
        pdf_path = _convert_via_cloudconvert(dwg_path, api_key)
        return {"pdf_path": pdf_path, "dxf_path": None}

    converter = _find_local_converter()
    if converter:
        dxf_path = _convert_locally(dwg_path, converter)
        return {"pdf_path": None, "dxf_path": dxf_path}

    raise RuntimeError(
        "No DWG converter available. "
        "Set the CLOUDCONVERT_API_KEY environment variable to enable cloud conversion, "
        "or install ODA File Converter from opendesign.com."
    )


# Keep this for backwards compatibility with extractor.py
def convert_dwg_to_dxf(dwg_path: str) -> str:
    result = convert_dwg(dwg_path)
    if result["dxf_path"]:
        return result["dxf_path"]
    raise RuntimeError(
        "DXF conversion requires a local ODA File Converter. "
        "Cloud conversion produces PDF only."
    )


# ---------------------------------------------------------------------------
# CloudConvert — DWG → PDF
# ---------------------------------------------------------------------------

_CC_BASE = "https://api.cloudconvert.com/v2"


def _convert_via_cloudconvert(dwg_path: str, api_key: str) -> str:
    headers = {"Authorization": f"Bearer {api_key}"}
    dwg = Path(dwg_path)
    out_pdf = dwg.with_suffix(".pdf")

    # 1. Create job: upload → convert DWG→PDF → export
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

    # 3. Poll until finished (max 5 minutes)
    job_id = job["id"]
    for _ in range(60):
        time.sleep(5)
        status_resp = requests.get(
            f"{_CC_BASE}/jobs/{job_id}", headers=headers, timeout=30
        )
        status_resp.raise_for_status()
        data = status_resp.json()["data"]

        if data["status"] == "finished":
            break
        if data["status"] == "error":
            raise RuntimeError(
                "CloudConvert conversion failed — check your API key and file."
            )
    else:
        raise RuntimeError("CloudConvert timed out after 5 minutes.")

    # 4. Download the PDF
    tasks = status_resp.json()["data"]["tasks"]
    export_task = next(t for t in tasks if t["name"] == "export-pdf")
    download_url = export_task["result"]["files"][0]["url"]

    pdf_resp = requests.get(download_url, timeout=120)
    pdf_resp.raise_for_status()
    out_pdf.write_bytes(pdf_resp.content)

    return str(out_pdf)


# ---------------------------------------------------------------------------
# Local converters — DWG → DXF (offline fallback)
# ---------------------------------------------------------------------------

def _find_local_converter() -> str | None:
    candidates = [
        "ODAFileConverter",
        "/Applications/ODAFileConverter/ODAFileConverter",
        "dwg2dxf",
        "/opt/homebrew/bin/dwg2dxf",
        "/usr/local/bin/dwg2dxf",
    ]
    for c in candidates:
        if shutil.which(c) or Path(c).exists():
            return c
    return None


def _convert_locally(dwg_path: str, converter: str) -> str:
    dwg = Path(dwg_path)
    out_dxf = dwg.with_suffix(".dxf")

    if "dwg2dxf" in converter:
        _run_libredwg(converter, dwg, out_dxf)
    else:
        _run_oda(converter, dwg, out_dxf)

    if not out_dxf.exists():
        raise RuntimeError(f"Local conversion produced no output for {dwg.name}")
    return str(out_dxf)


def _run_libredwg(binary: str, dwg: Path, out_dxf: Path) -> None:
    result = subprocess.run(
        [binary, "-o", str(out_dxf), str(dwg)],
        capture_output=True, text=True, timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(f"dwg2dxf failed: {result.stderr.strip()}")


def _run_oda(binary: str, dwg: Path, out_dxf: Path) -> None:
    with tempfile.TemporaryDirectory() as tmp_in, tempfile.TemporaryDirectory() as tmp_out:
        tmp_dwg = Path(tmp_in) / dwg.name
        shutil.copy(dwg, tmp_dwg)
        result = subprocess.run(
            [binary, tmp_in, tmp_out, "ACAD2018", "DXF", "0", "1"],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode != 0:
            raise RuntimeError(f"ODAFileConverter failed: {result.stderr.strip()}")
        converted = list(Path(tmp_out).glob("*.dxf"))
        if not converted:
            raise RuntimeError("ODAFileConverter produced no .dxf output")
        shutil.move(str(converted[0]), str(out_dxf))
