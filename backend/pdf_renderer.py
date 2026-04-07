"""
PDF sheet management.

When CloudConvert converts a DWG it produces a multi-page PDF — one page per
AutoCAD layout/sheet. This module splits that PDF into individual pages and
packages them for download.

Fallback: if only a DXF is available (local ODA converter), ezdxf + matplotlib
renders the model space as a single A3 PDF (lower quality).
"""

import io
import zipfile
from pathlib import Path

from pypdf import PdfReader, PdfWriter


# ---------------------------------------------------------------------------
# PDF-based workflow (CloudConvert path)
# ---------------------------------------------------------------------------

def get_sheets_from_pdf(pdf_path: str) -> list[dict]:
    """Return one entry per page in the PDF."""
    reader = PdfReader(pdf_path)
    sheets = []
    for i, page in enumerate(reader.pages):
        # Use page labels if present, otherwise just number them
        sheets.append({
            "name": f"Sheet {i + 1}",
            "page_index": i,
            "is_paperspace": True,
            "entity_count": None,
        })
    return sheets


def extract_page_as_pdf(pdf_path: str, page_index: int) -> bytes:
    """Extract a single page from the multi-page PDF and return its bytes."""
    reader = PdfReader(pdf_path)
    if page_index < 0 or page_index >= len(reader.pages):
        raise ValueError(f"Page index {page_index} out of range (0-{len(reader.pages)-1})")

    writer = PdfWriter()
    writer.add_page(reader.pages[page_index])

    buf = io.BytesIO()
    writer.write(buf)
    buf.seek(0)
    return buf.read()


def extract_all_pages_as_zip(pdf_path: str) -> bytes:
    """Bundle every page of the PDF as its own PDF inside a zip archive."""
    reader = PdfReader(pdf_path)
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for i, _ in enumerate(reader.pages):
            pdf_bytes = extract_page_as_pdf(pdf_path, i)
            zf.writestr(f"Sheet_{i + 1}.pdf", pdf_bytes)
    zip_buf.seek(0)
    return zip_buf.read()


# ---------------------------------------------------------------------------
# DXF fallback (local ODA converter path)
# ---------------------------------------------------------------------------

def get_sheets_from_dxf(dxf_path: str) -> list[dict]:
    import ezdxf
    from ezdxf.layouts import Modelspace

    doc = ezdxf.readfile(dxf_path)
    sheets = []
    for layout in doc.layouts:
        sheets.append({
            "name": layout.name,
            "page_index": None,
            "is_paperspace": not isinstance(layout, Modelspace),
            "entity_count": len(list(layout)),
        })
    sheets.sort(key=lambda s: (not s["is_paperspace"], s["name"]))
    return sheets


def render_dxf_layout_to_pdf(dxf_path: str, layout_name: str) -> bytes:
    import ezdxf
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from ezdxf.layouts import Modelspace
    from ezdxf.addons.drawing import RenderContext, Frontend
    from ezdxf.addons.drawing.matplotlib import MatplotlibBackend

    A3_W_IN, A3_H_IN = 420 / 25.4, 297 / 25.4

    doc = ezdxf.readfile(dxf_path)
    layout = doc.modelspace() if layout_name == "Model" else doc.layouts.get(layout_name)
    if layout is None:
        raise ValueError(f"Layout '{layout_name}' not found")

    fig = plt.figure(figsize=(A3_W_IN, A3_H_IN))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_axis_off()

    ctx = RenderContext(doc)
    backend = MatplotlibBackend(ax)
    Frontend(ctx, backend).draw_layout(layout, finalize=True)

    buf = io.BytesIO()
    fig.savefig(buf, format="pdf", dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def render_all_dxf_layouts_to_zip(dxf_path: str) -> bytes:
    sheets = get_sheets_from_dxf(dxf_path)
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for sheet in sheets:
            try:
                pdf_bytes = render_dxf_layout_to_pdf(dxf_path, sheet["name"])
                safe = sheet["name"].replace("/", "_").replace("\\", "_")
                zf.writestr(f"{safe}.pdf", pdf_bytes)
            except Exception:
                pass
    zip_buf.seek(0)
    return zip_buf.read()
