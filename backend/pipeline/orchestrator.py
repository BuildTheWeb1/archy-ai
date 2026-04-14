"""
Pipeline orchestrator: runs all extraction steps for a list of PDF files
and returns schedule rows + warnings.

Steps:
  1. Extract text / tables / rotated chars from each PDF (extractor.py)
  2. If an embedded schedule table is found, use it (parser.py)
  3. Otherwise parse rebar labels from upright text (parser.py)
  4. If >50% of chars on a page are rotated, also parse rotated lines (rotated.py)
  5. Aggregate all marks across PDFs (aggregator.py)
"""

import logging
from pathlib import Path

from pipeline.aggregator import aggregate_marks
from pipeline.extractor import extract_pdf
from pipeline.models import RebarMark
from pipeline.parser import parse_embedded_schedule, parse_rebar_label
from pipeline.rotated import reconstruct_rotated_text

logger = logging.getLogger(__name__)


def run_pipeline(pdf_paths: list[Path]) -> tuple[list[dict], list[str]]:
    """
    Run the full extraction pipeline over *pdf_paths*.

    Returns:
        (rows, warnings) where rows is a list of schedule row dicts
        ready to be stored in metadata.json.
    """
    all_marks: list[RebarMark] = []
    global_warnings: list[str] = []

    for pdf_path in pdf_paths:
        logger.info("Processing %s", pdf_path.name)

        try:
            extracted = extract_pdf(pdf_path)
        except Exception as exc:
            msg = f"{pdf_path.name}: eroare la extracție — {exc}"
            logger.error(msg)
            global_warnings.append(msg)
            continue

        # ── Step 2: embedded schedule ─────────────────────────────────
        if extracted["has_embedded_schedule"] and extracted["tables"]:
            embedded_rows = parse_embedded_schedule(extracted["tables"])
            if embedded_rows:
                logger.info(
                    "Using embedded schedule from %s (%d rows)",
                    pdf_path.name,
                    len(embedded_rows),
                )
                # Embedded schedules are authoritative — return immediately
                _, agg_warnings = aggregate_marks([])
                return embedded_rows, agg_warnings

        # ── Step 3: parse upright text ────────────────────────────────
        upright_text = extracted["upright_text"]
        for line in upright_text.splitlines():
            mark = parse_rebar_label(line.strip())
            if mark:
                all_marks.append(mark)

        # ── Step 4: rotated text ──────────────────────────────────────
        rotated_chars = extracted["rotated_chars"]
        all_chars_estimate = len(upright_text)
        if rotated_chars and all_chars_estimate > 0:
            rotated_ratio = len(rotated_chars) / max(all_chars_estimate, 1)
        else:
            rotated_ratio = 0.0

        if rotated_chars and (rotated_ratio > 0.1 or len(rotated_chars) > 50):
            rotated_lines = reconstruct_rotated_text(rotated_chars)
            added = 0
            for line in rotated_lines:
                mark = parse_rebar_label(line.strip())
                if mark:
                    mark.confidence = "low"
                    all_marks.append(mark)
                    added += 1
            if added:
                logger.info("Added %d marks from rotated text in %s", added, pdf_path.name)

    if not all_marks:
        global_warnings.append(
            "Nu s-au găsit etichete de armare în PDF-urile încărcate. "
            "Verificați că PDF-urile conțin text (nu sunt scanate)."
        )
        return [], global_warnings

    # ── Step 5: aggregate ─────────────────────────────────────────────
    rows, agg_warnings = aggregate_marks(all_marks)
    global_warnings.extend(agg_warnings)

    logger.info("Pipeline complete: %d rows, %d warnings", len(rows), len(global_warnings))
    return rows, global_warnings
