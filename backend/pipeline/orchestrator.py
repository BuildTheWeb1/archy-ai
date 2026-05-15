"""
Pipeline orchestrator: runs vision-based extraction for a list of PDF files
and returns schedule rows + warnings.

Steps:
  1. Convert PDF pages to images (PyMuPDF)
  2. Send all images to Claude Vision API with specialised prompt
  3. Parse structured JSON response into marks
  4. Build schedule rows with weight calculations
"""

import logging
from pathlib import Path

from pipeline.vision_extractor import extract_with_vision
from pipeline.weights import build_schedule_row

logger = logging.getLogger(__name__)


def run_pipeline(pdf_paths: list[Path]) -> tuple[list[dict], list[str]]:
    """
    Run the vision extraction pipeline over *pdf_paths*.

    Returns:
        (rows, warnings) where rows is a list of schedule row dicts
        ready to be stored in metadata.json.
    """
    global_warnings: list[str] = []

    # ── Step 1-2: Vision extraction ──────────────────────────────────
    try:
        marks, vision_warnings = extract_with_vision(pdf_paths)
        global_warnings.extend(vision_warnings)
        logger.info("Vision extraction returned %d marks:", len(marks))
        for m in marks:
            logger.info("  Mark %s: Ø%s, %s buc, L=%s, conf=%s, src=%s",
                        m.get("mark"), m.get("diameter"), m.get("count"),
                        m.get("length"), m.get("confidence"), m.get("source"))
    except Exception as exc:
        msg = f"Eroare la extracția cu AI: {exc}"
        logger.error(msg, exc_info=True)
        return [], [msg]

    if not marks:
        global_warnings.append(
            "Nu s-au găsit date de armare în PDF-urile încărcate. "
            "Verificați că PDF-urile conțin planșe de armare lizibile."
        )
        return [], global_warnings

    # ── Step 3: Build schedule rows ──────────────────────────────────
    rows: list[dict] = []
    seen_marks: set[int] = set()

    for m in marks:
        mark_no = m.get("mark")
        diameter = m.get("diameter")
        count = m.get("count", 1)
        length = m.get("length", 0.0)
        confidence = m.get("confidence", "medium")

        if diameter is None:
            global_warnings.append(
                f"Marcă ignorată (diametru lipsă): {m}"
            )
            continue

        # Validate types
        try:
            diameter = int(diameter)
            count = int(count) if count else 1
            length = float(length) if length else 0.0
            if mark_no is not None:
                mark_no = int(mark_no)
        except (ValueError, TypeError) as exc:
            global_warnings.append(
                f"Valori invalide pentru marca {mark_no}: {exc}"
            )
            continue

        row_warnings: list[str] = []

        if length <= 0:
            row_warnings.append(
                f"Marca {mark_no or '?'}: lungime lipsă — necesită verificare"
            )
            confidence = "low"

        # Deduplicate: if same mark appears from both table and drawing,
        # prefer the table source
        if mark_no is not None and mark_no in seen_marks:
            # Skip duplicate — the first one (from table if available) wins
            continue
        if mark_no is not None:
            seen_marks.add(mark_no)

        row = build_schedule_row(
            mark=mark_no,
            diameter=diameter,
            count=count,
            length=length,
            confidence=confidence,
            warnings=row_warnings,
        )
        rows.append(row.to_dict())

    # Sort by mark number (None marks go to end)
    rows.sort(key=lambda r: (r["mark"] is None, r["mark"] or 0))

    logger.info(
        "Pipeline complete: %d rows, %d warnings",
        len(rows),
        len(global_warnings),
    )
    return rows, global_warnings
