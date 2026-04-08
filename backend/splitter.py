"""
Bundle per-layout PDFs into a downloadable ZIP.
"""

import io
import zipfile
from pathlib import Path


def build_zip(pdf_dir: str, layouts: list[dict]) -> bytes:
    """Bundle all layout PDFs into a single ZIP."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for layout in layouts:
            pdf_path = Path(pdf_dir) / f"{layout['index']}.pdf"
            if pdf_path.exists():
                safe_name = _safe_filename(layout["name"])
                zf.writestr(f"{layout['index'] + 1:02d}_{safe_name}.pdf", pdf_path.read_bytes())
    buf.seek(0)
    return buf.read()


def _safe_filename(name: str) -> str:
    """Turn a layout name into a safe filename component."""
    safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in name)
    return safe[:60]
