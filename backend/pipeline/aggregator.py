"""
Aggregate parsed RebarMark objects across multiple PDFs/pages into schedule rows.

Strategy:
  - Marks with a mark number: group by (mark, diameter).
    Same mark + different diameter or length → inconsistency warning.
    Count is taken as the maximum seen (drawing sheets repeat the same bar).
  - Marks without a mark number (slab, stirrup, mesh): kept individually,
    assigned synthetic negative IDs so they don't collide with real marks.
"""

import logging
from collections import defaultdict

from pipeline.models import RebarMark
from pipeline.weights import build_schedule_row

logger = logging.getLogger(__name__)


def aggregate_marks(
    parsed_marks: list[RebarMark],
) -> tuple[list[dict], list[str]]:
    """
    Aggregate a flat list of RebarMark objects into schedule row dicts.

    Returns (rows, warnings).
    """
    warnings: list[str] = []

    # Separate numbered vs unnamed marks
    numbered: dict[int, list[RebarMark]] = defaultdict(list)
    unnamed: list[RebarMark] = []

    for m in parsed_marks:
        if m.mark is not None:
            numbered[m.mark].append(m)
        else:
            unnamed.append(m)

    rows: list[dict] = []

    # ── Numbered marks ──────────────────────────────────────────────
    for mark_no in sorted(numbered.keys()):
        marks = numbered[mark_no]

        diameters = {m.diameter for m in marks}
        lengths = {m.length for m in marks if m.length is not None}
        counts = [m.count for m in marks if m.count is not None]

        row_warnings: list[str] = []

        if len(diameters) > 1:
            msg = f"Marca {mark_no}: diametre inconsistente {sorted(diameters)}"
            warnings.append(msg)
            row_warnings.append(msg)

        if len(lengths) > 1:
            msg = f"Marca {mark_no}: lungimi inconsistente {sorted(lengths)}"
            warnings.append(msg)
            row_warnings.append(msg)

        diameter = next(iter(diameters))  # best-effort: take first
        length = max(lengths) if lengths else 0.0
        count = max(counts) if counts else 1

        confidence = "medium" if not row_warnings else "low"
        # Upgrade to high only if set by embedded-schedule parser upstream
        has_high = any(m.confidence == "high" for m in marks)
        if has_high and not row_warnings:
            confidence = "high"

        if length <= 0:
            row_warnings.append(f"Marca {mark_no}: lungime lipsă")
            confidence = "low"

        row = build_schedule_row(
            mark=mark_no,
            diameter=diameter,
            count=count,
            length=length,
            confidence=confidence,
            warnings=row_warnings,
        )
        rows.append(row.to_dict())

    # ── Unnamed marks (slab, stirrup, mesh) ─────────────────────────
    for m in unnamed:
        length = m.length or 0.0
        count = m.count or 1
        row_warnings: list[str] = []

        if length <= 0:
            row_warnings.append("Lungime lipsă — necesită verificare manuală")

        row = build_schedule_row(
            mark=None,
            diameter=m.diameter,
            count=count,
            length=length,
            confidence="low",
            warnings=row_warnings,
        )
        rows.append(row.to_dict())

    logger.info(
        "Aggregated %d numbered + %d unnamed marks → %d schedule rows, %d warnings",
        len(numbered),
        len(unnamed),
        len(rows),
        len(warnings),
    )
    return rows, warnings
