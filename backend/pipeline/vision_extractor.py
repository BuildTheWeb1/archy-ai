"""
Multi-step vision-based rebar extraction using Claude API.

Pipeline:
  Step 1 — Page Classification (one call per page)
    Determines if each page is: plan | cross_section | detail | non_structural

  Step 2 — Raw Data Extraction (one call per relevant page)
    - plan          → marks with occurrence counts + beam segment dimensions
    - cross_section → stirrup / longitudinal bar specs
    - detail        → element counts + per-element bar specs
"""

import base64
import io
import json
import logging
import os
from pathlib import Path
from typing import Any

import anthropic
import fitz  # PyMuPDF

try:
    from PIL import Image as _PILImage
    _PIL_AVAILABLE = True
except ImportError:
    _PILImage = None
    _PIL_AVAILABLE = False

logger = logging.getLogger(__name__)

_DPI = 300
_ZOOM = _DPI / 72


# ── PDF → images ──────────────────────────────────────────────────────────────

def pdf_pages_to_images(pdf_path: Path) -> list[bytes]:
    """Convert each page of a PDF to a PNG byte buffer at 300 DPI."""
    images: list[bytes] = []
    doc = fitz.open(str(pdf_path))
    try:
        for page in doc:
            mat = fitz.Matrix(_ZOOM, _ZOOM)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            images.append(pix.tobytes("png"))
    finally:
        doc.close()
    return images


def _b64(png_bytes: bytes) -> str:
    return base64.standard_b64encode(png_bytes).decode("ascii")


def _rotate_png(png_bytes: bytes, degrees: int) -> bytes:
    """Rotate a PNG image by the given degrees (90, 180, 270)."""
    if not _PIL_AVAILABLE:
        logger.warning("Pillow not installed — cannot rotate image. Install with: pip install Pillow")
        return png_bytes
    img = _PILImage.open(io.BytesIO(png_bytes))
    rotated = img.rotate(degrees, expand=True)
    buf = io.BytesIO()
    rotated.save(buf, format="PNG")
    return buf.getvalue()


def _image_block(png_bytes: bytes) -> dict:
    return {
        "type": "image",
        "source": {"type": "base64", "media_type": "image/png", "data": _b64(png_bytes)},
    }


def _text_block(text: str) -> dict:
    return {"type": "text", "text": text}


# ── Claude client ─────────────────────────────────────────────────────────────

def _client() -> anthropic.Anthropic:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY nu este setat. Adaugă-l în fișierul .env din rădăcina proiectului."
        )
    return anthropic.Anthropic(api_key=api_key)


_MODEL_CLASSIFY = "claude-haiku-4-5-20251001"   # classification is simple → cheaper
_MODEL_EXTRACT  = "claude-sonnet-4-6"           # extraction needs accuracy


def _call(client: anthropic.Anthropic, system: str, content: list[dict], model: str = _MODEL_EXTRACT) -> str:
    msg = client.messages.create(
        model=model,
        max_tokens=4096,
        system=system,
        messages=[{"role": "user", "content": content}],
    )
    return "".join(b.text for b in msg.content if b.type == "text")


def _parse_json(text: str) -> Any:
    import re
    cleaned = text.strip()
    cleaned = re.sub(r"^```[a-z]*\n?", "", cleaned)
    cleaned = re.sub(r"\n?```$", "", cleaned)
    cleaned = cleaned.strip()
    if not cleaned:
        raise ValueError("Empty response from Claude")
    return json.loads(cleaned)


# ── Step 1: Page Classification ───────────────────────────────────────────────

_CLASSIFY_SYSTEM = """\
You are an expert at reading Romanian structural engineering drawings (planșe de armare).
Return ONLY valid JSON, no other text.
"""

_CLASSIFY_PROMPT = """\
Classify this structural engineering drawing page.

Return this JSON:
{
  "type": "plan" | "cross_section" | "detail" | "non_structural",
  "description": "one sentence describing what this page shows"
}

Types:
- "plan": a top-down foundation plan (Plan fundații / Plan armare) showing the layout of beams, columns, and circled rebar mark numbers
- "cross_section": cross-section or sectional details (Secțiune, Detaliu secțiune) showing rebar arrangement within foundation beams or walls
- "detail": construction detail drawings (Detalii) showing specific elements like columns (stâlpișori), anchoring bars, or connections with explicit element counts
- "non_structural": excavation plans (Plan săpătură), architectural plans, or pages without rebar information

Return ONLY the JSON.
"""


def classify_page(client: anthropic.Anthropic, image_bytes: bytes, page_label: str) -> dict:
    """Classify a single PDF page. Returns {type, description}."""
    logger.info("Classifying page: %s", page_label)
    raw = _call(client, _CLASSIFY_SYSTEM, [_image_block(image_bytes), _text_block(_CLASSIFY_PROMPT)], model=_MODEL_CLASSIFY)
    logger.info("Classification for %s: %s", page_label, raw[:200])
    try:
        result = _parse_json(raw)
        result["label"] = page_label
        return result
    except Exception as exc:
        logger.warning("Classification parse failed for %s: %s", page_label, exc)
        return {"type": "non_structural", "description": "parse error", "label": page_label}


# ── Step 2a: Plan page extraction ─────────────────────────────────────────────

_PLAN_SYSTEM = """\
You are an expert at reading Romanian structural engineering foundation plan drawings.
Extract rebar mark data exactly as annotated. Return ONLY valid JSON.
"""

_PLAN_PROMPT = """\
This is a foundation plan drawing (Plan fundații / Plan armare).

Extract ALL rebar marks and beam dimensions. Return this JSON:

{
  "marks": [
    {
      "mark": <circled number (int)>,
      "annotation": "<full annotation text, e.g. '2x2Ø14 L=8.60'>",
      "diameter": <mm (int)>,
      "bars_per_occurrence": <total bars in one placement, e.g. 2x2=4 (int)>,
      "length": <bar length in meters (float)>,
      "occurrences_on_plan": <how many times this circled mark appears on this plan (int)>,
      "confidence": "high" | "medium" | "low"
    }
  ],
  "beam_segments": [
    {
      "from": "<grid point label>",
      "to": "<grid point label>",
      "length_cm": <length in cm (float)>,
      "type": "horizontal" | "vertical"
    }
  ],
  "warnings": []
}

RULES:
- Circled numbers (①②③ or numbers in circles) are mark numbers
- ANNOTATION PARSING — multiply both numbers for bars_per_occurrence:
    "2x2Ø14" → 2 × 2 = 4 bars per occurrence → bars_per_occurrence = 4
    "3x2Ø12" → 3 × 2 = 6 bars per occurrence → bars_per_occurrence = 6
    "2Ø14"   → 2 bars per occurrence → bars_per_occurrence = 2
    "4Ø14"   → 4 bars per occurrence → bars_per_occurrence = 4
  Do NOT use just the first number. Multiply ALL multipliers together.
- Count CAREFULLY how many times each circled mark number appears on the plan
- beam_segments: read ALL dimension annotations showing lengths (e.g. "243.8", "891")
  Include ONLY foundation beam lengths, not column or wall dimensions
- If you cannot determine occurrences confidently, set confidence "low"
- Return ONLY the JSON
"""


def extract_plan_data(client: anthropic.Anthropic, image_bytes: bytes, label: str) -> dict:
    logger.info("Extracting plan data from: %s", label)
    raw = _call(client, _PLAN_SYSTEM, [_image_block(image_bytes), _text_block(_PLAN_PROMPT)])
    logger.info("Plan extraction for %s: %s", label, raw[:300])
    try:
        data = _parse_json(raw)
        data["source"] = label
        data["page_type"] = "plan"
        return data
    except Exception as exc:
        logger.warning("Plan parse failed for %s: %s", label, exc)
        return {"marks": [], "beam_segments": [], "warnings": [str(exc)], "source": label, "page_type": "plan"}


# ── Step 2b: Cross-section extraction ─────────────────────────────────────────

_SECTION_SYSTEM = """\
You are an expert at reading Romanian structural engineering cross-section drawings.
Extract rebar specifications exactly as annotated. Return ONLY valid JSON.
"""

_SECTION_PROMPT = """\
This is a cross-section detail drawing (Detalii fundații / Secțiuni).

Extract ALL rebar and stirrup specifications. Return this JSON:

{
  "sections": [
    {
      "name": "<section name, e.g. 'Secțiune fundație pereți ext.'>",
      "stirrups": [
        {
          "mark": <mark number (int) or null>,
          "diameter": <mm (int)>,
          "spacing_cm": <spacing in cm (float)>,
          "length": <bar length in meters (float)>,
          "annotation": "<full annotation, e.g. 'Ø8/15 L=1.25'>"
        }
      ],
      "special_bars": [
        {
          "mark": <mark number (int) or null>,
          "diameter": <mm (int)>,
          "count_per_set": <bars per individual placement (int)>,
          "set_count": <how many sets/placements total, if readable (int) or null>,
          "total_count": <total bars if stated explicitly (int) or null>,
          "length": <bar length in meters (float)>,
          "annotation": "<full annotation, e.g. '2Ø10/15 L=2.10'>",
          "description": "<what these bars are, e.g. 'Mustăți scară'>"
        }
      ],
      "longitudinal_bars": [
        {
          "mark": <mark number (int) or null>,
          "diameter": <mm (int)>,
          "bars": <count (int)>,
          "annotation": "<e.g. '2x2Ø14'>",
          "description": "<e.g. 'Armare centură'>"
        }
      ]
    }
  ],
  "warnings": []
}

RULES:
- "Ø8/15" means Ø8mm stirrups at 15cm spacing → diameter=8, spacing_cm=15
- "2Ø10/15 L=2.10" means 2 bars of Ø10, spacing 15cm, length 2.10m → special bar
- Extract mark numbers from annotations or labels
- If a value is unclear, note it in warnings
- Return ONLY the JSON
"""


def extract_section_data(client: anthropic.Anthropic, image_bytes: bytes, label: str) -> dict:
    logger.info("Extracting cross-section data from: %s", label)
    raw = _call(client, _SECTION_SYSTEM, [_image_block(image_bytes), _text_block(_SECTION_PROMPT)])
    logger.info("Section extraction for %s: %s", label, raw[:300])
    try:
        data = _parse_json(raw)
        data["source"] = label
        data["page_type"] = "cross_section"
        return data
    except Exception as exc:
        logger.warning("Section parse failed for %s: %s", label, exc)
        return {"sections": [], "warnings": [str(exc)], "source": label, "page_type": "cross_section"}


# ── Step 2c: Detail page extraction ───────────────────────────────────────────

_DETAIL_SYSTEM = """\
You are an expert at reading Romanian structural engineering construction detail drawings.
Extract element counts and rebar specifications exactly as annotated. Return ONLY valid JSON.
"""

_DETAIL_PROMPT = """\
This is a construction detail drawing (Detalii fundații II / Detalii stâlpișori etc.).

Extract ALL elements with their rebar specifications. Return this JSON:

{
  "elements": [
    {
      "name": "<element name, e.g. 'Mustăți stâlpișori 25/25'>",
      "count": <total number of this element (int), from annotations like '23 buc.'>",
      "marks": [
        {
          "mark": <mark number (int) or null>,
          "diameter": <mm (int)>,
          "bars_per_element": <bars per single element (int)>,
          "stirrups_per_element": <if stirrups: count per element (int) or null>,
          "length": <bar length in meters (float)>,
          "annotation": "<full annotation, e.g. '4Ø14 L=2.50'>",
          "is_stirrup": <true if etrieri/stirrups, false otherwise (bool)>
        }
      ]
    }
  ],
  "anchor_bars": [
    {
      "mark": <mark number (int) or null>,
      "diameter": <mm (int)>,
      "bars_per_junction": <total bars per junction (int)>,
      "length": <bar length in meters (float)>,
      "junction_count": <number of junctions, if readable (int) or null>,
      "annotation": "<full annotation, e.g. '2x3Ø14 L=1.70'>"
    }
  ],
  "warnings": []
}

RULES:
- Look for explicit element counts like "23 buc.", "Mustăți stâlpișori 25/25, 23 buc."
- "4Ø14 L=2.50" = 4 bars of Ø14, 2.50m long per element → bars_per_element=4, length=2.50
- "etrieri Ø8/15, 9 buc., L=0.95" = 9 stirrups per element → stirrups_per_element=9, length=0.95, is_stirrup=true
- Mark numbers for stirrups WITHIN elements: read from the mark label next to the annotation (e.g. a circled ⑩ next to "etrieri Ø8/15 9 buc." means mark=10)
- ANNOTATION PARSING for bars_per_junction:
    "2x3Ø14 L=1.70" → 2 × 3 = 6 bars per junction → bars_per_junction=6, length=1.70
    "4Ø14 L=1.70"   → 4 bars per junction → bars_per_junction=4, length=1.70
  Use the LENGTH stated next to the anchor bar annotation, not any other length.
- anchor_bars: bars at corners or beam intersections/junctions — look for annotations like "2x3Ø14 L=..." or "nxmØd L=..."
- junction_count: count how many corner/intersection locations this bar appears at on the plan or detail
- Return ONLY the JSON
"""


def extract_detail_data(client: anthropic.Anthropic, image_bytes: bytes, label: str) -> dict:
    logger.info("Extracting detail data from: %s", label)
    raw = _call(client, _DETAIL_SYSTEM, [_image_block(image_bytes), _text_block(_DETAIL_PROMPT)])
    logger.info("Detail extraction for %s: %s", label, raw[:300])
    try:
        data = _parse_json(raw)
        data["source"] = label
        data["page_type"] = "detail"
        return data
    except Exception as exc:
        logger.warning("Detail parse failed for %s: %s", label, exc)
        return {"elements": [], "anchor_bars": [], "warnings": [str(exc)], "source": label, "page_type": "detail"}


# ── Step 0: Find the Extras de armătură table ────────────────────────────────

_DETECT_TABLE_SYSTEM = """\
You are an expert at reading Romanian structural engineering drawings.
Return ONLY valid JSON, no other text.
"""

_DETECT_TABLE_PROMPT = """\
Scan ALL attached pages for an "Extras de armătură" table.

This table has columns: Marca, Ø [mm], Oțel, Buc., Lung. [m], and total-length columns.
It may be rotated 90° on the page (readable when tilting your head right or left).

Return:
{
  "table_found": true or false,
  "page_label": "<the label of the page that contains the table, exactly as given>",
  "rotation": 0 or 90 or 270
}

rotation:
  0   = table is upright (readable normally)
  90  = table is rotated 90° clockwise (tilt head right to read it)
  270 = table is rotated 90° counter-clockwise (tilt head left to read it)

If not found: {"table_found": false, "page_label": null, "rotation": 0}
Return ONLY the JSON.
"""

_EXTRACT_TABLE_SYSTEM = """\
You are an expert at reading Romanian structural engineering drawings.
The image shows an "Extras de armătură" table in its correct upright orientation.
Return ONLY valid JSON, no other text.
"""

_EXTRACT_TABLE_PROMPT = """\
Read EVERY data row from the "Extras de armătură" table in this image.

The table columns are: Marca | Ø [mm] | Oțel | Buc. | Lung. [m] | (total length columns per diameter)

Return:
{
  "marks": [
    {
      "mark": <Marca number (int)>,
      "diameter": <Ø in mm (int)>,
      "steel_type": "BST500",
      "count": <Buc. — exact integer from the Buc. column>,
      "length": <Lung. [m] — exact decimal from the Lung. column>
    }
  ]
}

RULES:
- The table is now UPRIGHT — read left-to-right, top-to-bottom normally.
- Copy values EXACTLY as printed. Do NOT recalculate or round.
- Include ONLY numbered mark rows (1, 2, 3...). Skip summary rows (Lungimi, Masa, Total).
- Buc. is the total piece count column — it contains integers like 40, 8, 620.
- Lung. [m] is the per-bar length — it contains decimals like 8.60, 3.30, 1.25.
- Return ONLY the JSON.
"""


def find_extras_table(
    client: anthropic.Anthropic,
    all_images: list[tuple[str, bytes]],  # [(label, png_bytes), ...]
) -> tuple[bool, list[dict], list[str]]:
    """
    Two-pass table extraction:
    Pass 1 (Haiku) — detect which page has the table and its rotation.
    Pass 2 (Sonnet) — extract from that page with the image already rotated upright.

    Returns: (found, marks, warnings)
    """
    # Pass 1: detect
    detect_content: list[dict] = []
    for label, img_bytes in all_images:
        detect_content.append(_text_block(f"--- {label} ---"))
        detect_content.append(_image_block(img_bytes))
    detect_content.append(_text_block(_DETECT_TABLE_PROMPT))

    logger.info("Step 0a: detecting Extras table across %d pages...", len(all_images))
    try:
        raw = _call(client, _DETECT_TABLE_SYSTEM, detect_content, model=_MODEL_CLASSIFY)
        data = _parse_json(raw)
    except Exception as exc:
        logger.warning("Table detection failed: %s", exc)
        return False, [], []

    if not data.get("table_found"):
        logger.info("No Extras table detected")
        return False, [], []

    page_label = data.get("page_label", "")
    rotation = int(data.get("rotation", 0))
    logger.info("Table detected on '%s', rotation=%d°", page_label, rotation)

    # Find the image for that page (strip any decoration Claude may have added)
    clean_label = page_label.strip().lstrip("-").rstrip("-").strip()
    img_bytes_for_page: bytes | None = None
    for label, img_bytes in all_images:
        if label == clean_label or label == page_label:
            img_bytes_for_page = img_bytes
            break

    if img_bytes_for_page is None:
        # Fallback: use the last image
        logger.warning("Could not find image for label '%s', using last page", page_label)
        img_bytes_for_page = all_images[-1][1]

    # Rotate image to upright before extraction
    if rotation == 90:
        # Table rotated 90° CW → rotate CCW (270°) to make it upright
        img_bytes_for_page = _rotate_png(img_bytes_for_page, 90)
        logger.info("Rotated image 90° CCW to make table upright")
    elif rotation == 270:
        # Table rotated 90° CCW → rotate CW (90°) to make it upright
        img_bytes_for_page = _rotate_png(img_bytes_for_page, 270)
        logger.info("Rotated image 90° CW to make table upright")

    # Pass 2: extract from upright image
    logger.info("Step 0b: extracting table values from upright image...")
    extract_content = [_image_block(img_bytes_for_page), _text_block(_EXTRACT_TABLE_PROMPT)]
    try:
        raw2 = _call(client, _EXTRACT_TABLE_SYSTEM, extract_content, model=_MODEL_EXTRACT)
        logger.info("Table extraction response: %s", raw2[:400])
        data2 = _parse_json(raw2)
    except Exception as exc:
        logger.warning("Table extraction failed: %s", exc)
        return False, [], [f"Extragerea tabelului a eșuat: {exc}"]

    marks = data2.get("marks", [])
    if not marks:
        logger.info("Table detected but no marks extracted")
        return False, [], []

    logger.info("Extras table extracted: %d marks from '%s'", len(marks), page_label)
    return True, marks, [
        f"Tabel 'Extras de armătură' găsit ({page_label}, rotație {rotation}°). "
        f"{len(marks)} mărci transcrise direct din tabel."
    ]


# ── Main entry point ──────────────────────────────────────────────────────────

def extract_all(pdf_paths: list[Path]) -> tuple[list[dict], list[str]]:
    """
    Run the full pipeline over all PDF paths.

    Strategy:
      Step 0 — Search all pages for an existing Extras de armătură table.
               If found, return those marks directly (authoritative source, high confidence).
      Steps 1-2 — If no table found, classify each page and extract raw data per type.

    Returns:
        (page_data_list, warnings)
        If table found: page_data_list contains one synthetic "table" entry.
        Otherwise: one dict per classified page with extracted structured data.
    """
    client = _client()
    warnings: list[str] = []

    # Collect all page images first (needed for Step 0 and Steps 1-2)
    all_images: list[tuple[str, bytes]] = []  # [(label, png_bytes)]
    for pdf_path in pdf_paths:
        logger.info("Converting %s to images...", pdf_path.name)
        try:
            images = pdf_pages_to_images(pdf_path)
        except Exception as exc:
            msg = f"Nu s-a putut converti {pdf_path.name}: {exc}"
            logger.error(msg)
            warnings.append(msg)
            continue
        for page_idx, img_bytes in enumerate(images):
            label = f"{pdf_path.stem} (pag. {page_idx + 1})"
            all_images.append((label, img_bytes))

    if not all_images:
        return [], warnings + ["Nu s-au putut converti PDF-urile în imagini."]

    # ── Step 0: Look for the Extras table ────────────────────────────
    table_found, table_marks, table_warnings = find_extras_table(client, all_images)
    warnings.extend(table_warnings)

    if table_found and len(table_marks) >= 3:
        # Return as a synthetic page_data entry so orchestrator can handle it uniformly
        return [{"page_type": "extras_table", "marks": table_marks, "source": "Extras table"}], warnings

    logger.info("Falling back to multi-step pipeline...")

    # ── Steps 1-2: Multi-step extraction ─────────────────────────────
    page_data: list[dict] = []

    for label, img_bytes in all_images:

            # Step 1: Classify
            classification = classify_page(client, img_bytes, label)
            page_type = classification.get("type", "non_structural")
            logger.info("Page %s classified as: %s", label, page_type)

            if page_type == "non_structural":
                logger.info("Skipping non-structural page: %s", label)
                warnings.append(f"Pagina ignorată (non-structurală): {label} — {classification.get('description', '')}")
                continue

            # Step 2: Extract per type
            if page_type == "plan":
                data = extract_plan_data(client, img_bytes, label)
            elif page_type == "cross_section":
                data = extract_section_data(client, img_bytes, label)
            elif page_type == "detail":
                data = extract_detail_data(client, img_bytes, label)
            else:
                logger.warning("Unknown page type '%s' for %s, skipping", page_type, label)
                continue

            data["classification"] = classification
            page_data.append(data)

            if data.get("warnings"):
                warnings.extend(data["warnings"])

    return page_data, warnings

