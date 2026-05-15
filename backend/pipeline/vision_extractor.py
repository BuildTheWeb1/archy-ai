"""
Vision-based rebar extraction using Claude API.

Strategy:
  Send all PDF pages to Claude in a single request with a focused prompt
  that prioritises reading an existing "Extras de armătură" table (which
  may be rotated 90° in the drawing) over manual annotation parsing.
"""

import base64
import json
import logging
import os
from pathlib import Path

import anthropic
import fitz  # PyMuPDF

logger = logging.getLogger(__name__)

# ── PDF → image conversion ─────────────────────────────────────────────────

_DPI = 300
_ZOOM = _DPI / 72


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


def _image_to_base64(png_bytes: bytes) -> str:
    return base64.standard_b64encode(png_bytes).decode("ascii")


# ── The single extraction prompt ───────────────────────────────────────────

_SYSTEM_PROMPT = """\
You are an expert at reading Romanian structural engineering drawings \
(planșe de armare) and extracting rebar schedules (extras de armătură).

You will receive images of 1–4 PDF pages from the same construction project. \
One of these pages very likely contains a pre-computed "Extras de armătură" \
table drawn by the structural engineer. This table is the AUTHORITATIVE \
source — if you find it, transcribe its values exactly.

IMPORTANT about the table:
- It is usually in the bottom-right area of one of the pages
- It may be ROTATED 90° (sideways/vertical) — you must still read it
- Column headers are: Marca, Ø [mm], Oțel, Buc., Lung. [m], and then \
  columns for "Lung./Ø [m]" grouped by diameter under "BST500"
- Data rows have: mark number, diameter, steel type "BST500", piece count, \
  bar length, and a total length value in the appropriate diameter column
- Below the data rows there are summary rows: "Lungimi / Ø [m]", \
  "Masa Ø / m [kg/m]", "Masa / Ø [kg]", and "Masa totală [kg]"

YOUR TASK:
1. Scan ALL pages carefully for this table
2. If found: read EVERY data row exactly as written (not summary/total rows)
3. If NOT found: extract rebar data from drawing annotations (circled marks, \
   annotations like "4Ø14 L=2.50", element counts like "23 buc.")

Return ONLY valid JSON, no other text.
"""

_USER_PROMPT = """\
Look at all the attached structural engineering pages. Find the "Extras de \
armătură" table (it may be rotated 90°, usually in the bottom-right of one \
page) and transcribe every data row.

Return this JSON structure:

{
  "table_found": true or false,
  "source_description": "which page/location you found the table",
  "marks": [
    {
      "mark": <Marca number (int)>,
      "diameter": <Ø in mm (int)>,
      "steel_type": "BST500",
      "count": <Buc. — total piece count exactly as in table (int)>,
      "length": <Lung. [m] — bar length exactly as in table (float)>,
      "confidence": "high",
      "source": "table"
    }
  ],
  "warnings": []
}

RULES:
- Copy values EXACTLY from the table. Do not recalculate or round.
- "Buc." is the total count — write the exact number from the table.
- "Lung. [m]" is the per-bar length — write the exact number.
- Include ONLY the numbered mark rows (1, 2, 3...), skip total/summary rows.
- If the table is rotated, read it rotated — the data is still structured.
- If you cannot find a table, set "table_found": false and extract from \
  the drawing annotations instead, using these rules:
  - Circled numbers (①②③) are mark numbers
  - "2x2Ø14 L=8.60" = 4 bars of Ø14, each 8.60m long, per element
  - Count occurrences of each mark across the plan to get total count
  - "etrieri Ø8/15, 9 buc." = 9 stirrups per element
  - Multiply bars_per_element × number_of_elements for total Buc.

Return ONLY the JSON.
"""


# ── Claude API call ────────────────────────────────────────────────────────

def extract_with_vision(
    pdf_paths: list[Path],
) -> tuple[list[dict], list[str]]:
    """
    Send all PDF pages to Claude Vision and extract rebar schedule.
    Returns (marks_list, warnings).
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY nu este setat. "
            "Adaugă-l în fișierul .env din rădăcina proiectului."
        )

    client = anthropic.Anthropic(api_key=api_key)

    # Build image content blocks
    content_blocks: list[dict] = []
    total_pages = 0

    for pdf_path in pdf_paths:
        logger.info("Converting %s to images at %d DPI...", pdf_path.name, _DPI)
        try:
            images = pdf_pages_to_images(pdf_path)
        except Exception as exc:
            logger.error("Failed to convert %s: %s", pdf_path.name, exc)
            continue

        content_blocks.append({
            "type": "text",
            "text": f"--- Page from: {pdf_path.stem} ---",
        })

        for img_bytes in images:
            content_blocks.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": _image_to_base64(img_bytes),
                },
            })
            total_pages += 1

    if total_pages == 0:
        return [], ["Nu s-au putut converti PDF-urile în imagini."]

    content_blocks.append({
        "type": "text",
        "text": _USER_PROMPT,
    })

    logger.info(
        "Sending %d page(s) from %d PDF(s) to Claude Vision...",
        total_pages,
        len(pdf_paths),
    )

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": content_blocks}],
    )

    response_text = ""
    for block in message.content:
        if block.type == "text":
            response_text += block.text

    # Log FULL response for debugging
    logger.info("Claude raw response:\n%s", response_text)

    return _parse_response(response_text)


def _parse_response(text: str) -> tuple[list[dict], list[str]]:
    """Parse Claude's JSON response into marks + warnings."""
    warnings: list[str] = []

    cleaned = text.strip()
    if cleaned.startswith("```"):
        first_newline = cleaned.index("\n")
        cleaned = cleaned[first_newline + 1:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        logger.error("JSON parse failed: %s\nRaw: %s", exc, text[:2000])
        return [], [f"Eroare la parsarea răspunsului AI: {exc}"]

    table_found = data.get("table_found", False)
    source = data.get("source_description", "")
    marks = data.get("marks", [])
    raw_warnings = data.get("warnings", [])

    if table_found:
        warnings.append(
            f"Tabelul extras de armătură a fost găsit ({source}). "
            f"Conține {len(marks)} mărci."
        )
    else:
        warnings.append(
            "Nu s-a găsit tabel extras de armătură — "
            "valorile au fost extrase din adnotările desenului."
        )

    warnings.extend(raw_warnings)

    logger.info(
        "Parsed %d marks (table_found=%s, source=%s)",
        len(marks), table_found, source,
    )

    return marks, warnings
