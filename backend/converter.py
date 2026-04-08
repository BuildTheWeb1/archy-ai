"""
DWG → per-layout A3 PDFs via ODA File Converter + ezdxf rendering.

Pipeline:
  1. ODA File Converter reads the .dwg natively (via ezdxf.addons.odafc)
  2. ezdxf enumerates all Paper Space layouts
  3. Each layout is rendered to an A3 PDF with black lines on white background
     (print-ready) using ezdxf's drawing add-on + matplotlib

Requires ODA File Converter installed. On macOS set ODA_FILE_CONVERTER env var
to the binary path (e.g. /Applications/ODAFileConverter.app/Contents/MacOS/ODAFileConverter).
"""

import logging
import os
import time
from pathlib import Path

import ezdxf
from ezdxf.addons.drawing import Frontend, RenderContext
from ezdxf.addons.drawing import matplotlib as mpl_backend
from ezdxf.addons.drawing.config import (
    BackgroundPolicy,
    ColorPolicy,
    Configuration,
)

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

logger = logging.getLogger(__name__)

# A3 landscape: 420 × 297 mm  →  inches for matplotlib
_A3_WIDTH_IN = 420 / 25.4  # ≈ 16.535
_A3_HEIGHT_IN = 297 / 25.4  # ≈ 11.693

# Print-ready config: all entities rendered in black on white
_RENDER_CONFIG = Configuration(
    color_policy=ColorPolicy.BLACK,
    background_policy=BackgroundPolicy.WHITE,
)


def _ensure_oda() -> None:
    """Configure and verify ODA File Converter is available."""
    oda_path = os.environ.get("ODA_FILE_CONVERTER", "").strip()
    if oda_path:
        ezdxf.options.set("odafc-addon", "unix_exec_path", oda_path)

    from ezdxf.addons import odafc

    if not odafc.is_installed():
        raise RuntimeError(
            "ODA File Converter is not installed or not found. "
            "Set ODA_FILE_CONVERTER to the binary path."
        )


def convert_dwg_to_pdfs(dwg_path: str, layouts_dir: str) -> list[dict]:
    """
    Convert a DWG file to individual layout PDFs.

    Reads the DWG via ODA File Converter, then renders each Paper Space
    layout to an A3 PDF with black lines on white background.

    Returns list of {"index": int, "name": str} for each layout.
    Raises RuntimeError on failure.
    """
    dwg = Path(dwg_path)
    out = Path(layouts_dir)
    out.mkdir(parents=True, exist_ok=True)

    if not dwg.exists():
        raise RuntimeError(f"DWG file not found: {dwg}")

    suffix = dwg.suffix.lower()
    if suffix == ".dxf":
        doc = _read_dxf(dwg)
    elif suffix == ".dwg":
        doc = _read_dwg(dwg)
    else:
        raise RuntimeError(f"Unsupported file format: {suffix}")

    # Collect non-empty Paper Space layouts
    paper_layouts = []
    for layout in doc.layouts:
        if layout.is_modelspace:
            continue
        if not list(layout):
            logger.info("Skipping empty layout: %s", layout.name)
            continue
        paper_layouts.append(layout)

    if not paper_layouts:
        raise RuntimeError(
            "No Paper Space layouts with content found in the drawing."
        )

    logger.info(
        "Found %d paper space layout(s): %s",
        len(paper_layouts),
        [l.name for l in paper_layouts],
    )

    # Render each layout to A3 PDF
    ctx = RenderContext(doc)
    results = []
    for i, layout in enumerate(paper_layouts):
        start = time.time()
        pdf_path = out / f"{i}.pdf"
        _render_layout(doc, ctx, layout, pdf_path)
        elapsed = time.time() - start

        logger.info(
            "  Layout %d: %s (%d bytes, %.1fs)",
            i,
            layout.name,
            pdf_path.stat().st_size,
            elapsed,
        )
        results.append({"index": i, "name": layout.name})

    return results


def _read_dwg(dwg_path: Path) -> ezdxf.document.Drawing:
    """Read a DWG file using ODA File Converter."""
    _ensure_oda()
    from ezdxf.addons import odafc

    logger.info("Reading DWG via ODA: %s", dwg_path.name)
    return odafc.readfile(str(dwg_path))


def _read_dxf(dxf_path: Path) -> ezdxf.document.Drawing:
    """Read a DXF file directly with ezdxf."""
    logger.info("Reading DXF: %s", dxf_path.name)
    return ezdxf.readfile(str(dxf_path))


def _render_layout(
    doc: ezdxf.document.Drawing,
    ctx: RenderContext,
    layout: ezdxf.layouts.BaseLayout,
    pdf_path: Path,
) -> None:
    """Render a single layout to an A3 landscape PDF (black on white)."""
    fig = plt.figure(figsize=(_A3_WIDTH_IN, _A3_HEIGHT_IN))
    ax = fig.add_axes([0, 0, 1, 1])

    backend = mpl_backend.MatplotlibBackend(ax)
    Frontend(ctx, backend, config=_RENDER_CONFIG).draw_layout(layout)

    ax.set_facecolor("white")
    fig.patch.set_facecolor("white")
    ax.set_axis_off()

    fig.savefig(str(pdf_path), facecolor="white")
    plt.close(fig)
