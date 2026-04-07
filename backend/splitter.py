"""
Split a multi-page PDF into individual per-layout PDFs.

AutoCAD's PDF output (and CloudConvert's) includes bookmarks where each
top-level entry corresponds to a layout name. We use those when available,
falling back to page labels, then "Layout N".
"""

import io
import zipfile
from pathlib import Path

from pypdf import PdfReader, PdfWriter


def get_layout_names(pdf_path: str) -> list[str]:
    """
    Extract layout names from the PDF bookmarks/outline.
    Returns a list of names, one per page, in page order.
    """
    reader = PdfReader(pdf_path)
    page_count = len(reader.pages)

    # Try outline (bookmarks) first
    names = _names_from_outline(reader, page_count)
    if names:
        return names

    # Try page labels
    labels = _names_from_page_labels(reader, page_count)
    if labels:
        return labels

    # Fall back to generic names
    return [f"Layout_{i + 1}" for i in range(page_count)]


def split_pdf(pdf_path: str, out_dir: str) -> list[dict]:
    """
    Split pdf_path into individual PDFs saved in out_dir.
    Returns list of {"index": int, "name": str} in page order.
    """
    reader = PdfReader(pdf_path)
    names = get_layout_names(pdf_path)
    layouts = []

    for i, page in enumerate(reader.pages):
        writer = PdfWriter()
        writer.add_page(page)

        buf = io.BytesIO()
        writer.write(buf)
        buf.seek(0)

        out_path = Path(out_dir) / f"{i}.pdf"
        out_path.write_bytes(buf.read())

        layouts.append({"index": i, "name": names[i]})

    return layouts


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


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _names_from_outline(reader: PdfReader, page_count: int) -> list[str]:
    """Extract one name per page from the PDF outline (bookmarks)."""
    try:
        outline = reader.outline
        if not outline:
            return []

        # Flatten only top-level entries (each = one layout in AutoCAD PDFs)
        page_names: dict[int, str] = {}
        pages = reader.pages

        for item in outline:
            if isinstance(item, list):
                continue  # skip nested
            try:
                page_num = pages.index(reader.get_destination_page_number(item))
                title = item.title.strip() if item.title else ""
                if title and page_num not in page_names:
                    page_names[page_num] = title
            except Exception:
                continue

        if len(page_names) == page_count:
            return [page_names[i] for i in range(page_count)]
    except Exception:
        pass
    return []


def _names_from_page_labels(reader: PdfReader, page_count: int) -> list[str]:
    """Try to get names from PDF page labels."""
    try:
        labels = []
        for i in range(page_count):
            label = reader.page_labels[i] if reader.page_labels else None
            if label:
                labels.append(str(label).strip())
            else:
                return []
        if all(labels):
            return labels
    except Exception:
        pass
    return []


def _safe_filename(name: str) -> str:
    """Turn a layout name into a safe filename component."""
    safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in name)
    return safe[:60]  # cap length
