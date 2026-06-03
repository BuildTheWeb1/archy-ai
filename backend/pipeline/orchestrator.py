"""
Pipeline orchestrator: combines multi-step vision extraction results
and computes the rebar schedule via code (not AI).

Tier system (from extraction-pipeline-plan.md):
  Tier 1 — Explicit element count  → Buc = bars_per_element × element_count      (high confidence)
  Tier 2 — Occurrences on plan     → Buc = bars_per_occurrence × occurrences      (medium confidence)
  Tier 3 — Stirrup + spacing       → Buc = ceil(total_beam_length / spacing)      (low confidence)
"""

import logging
import math
from pathlib import Path

from pipeline.vision_extractor import extract_all
from pipeline.weights import build_schedule_row

logger = logging.getLogger(__name__)


def run_pipeline(pdf_paths: list[Path]) -> tuple[list[dict], list[str]]:
    """
    Run the full extraction pipeline over *pdf_paths*.

    Returns:
        (rows, warnings) where rows is a list of schedule row dicts.
    """
    global_warnings: list[str] = []

    # ── Steps 1 + 2: Vision extraction ───────────────────────────────
    try:
        page_data, vision_warnings = extract_all(pdf_paths)
        global_warnings.extend(vision_warnings)
        logger.info("Vision extraction returned %d classified pages", len(page_data))
    except Exception as exc:
        msg = f"Eroare la extracția cu AI: {exc}"
        logger.error(msg, exc_info=True)
        return [], [msg]

    if not page_data:
        global_warnings.append(
            "Nu s-au găsit pagini structurale relevante în PDF-urile încărcate. "
            "Verificați că PDF-urile conțin planșe de armare lizibile."
        )
        return [], global_warnings

    # ── Check if the Extras table was found (Step 0 shortcut) ────────
    table_pages = [p for p in page_data if p.get("page_type") == "extras_table"]
    if table_pages:
        logger.info("Using Extras table data directly")
        rows = _rows_from_table_marks(table_pages[0]["marks"], global_warnings)
        return rows, global_warnings

    # ── Separate pages by type ────────────────────────────────────────
    plan_pages = [p for p in page_data if p.get("page_type") == "plan"]
    section_pages = [p for p in page_data if p.get("page_type") == "cross_section"]
    detail_pages = [p for p in page_data if p.get("page_type") == "detail"]

    logger.info(
        "Pages: %d plan, %d cross_section, %d detail",
        len(plan_pages), len(section_pages), len(detail_pages),
    )

    # ── Compute total beam length from plan pages (for Tier 3) ────────
    total_beam_length_cm = _sum_beam_lengths(plan_pages)
    logger.info("Total beam length from plans: %.1f cm", total_beam_length_cm)

    # ── Step 3: Calculate schedule rows ──────────────────────────────
    raw_marks: list[dict] = []  # {mark, diameter, count, length, confidence, source_desc}

    # --- Tier 2: Plan marks (occurrences on plan) ---
    for page in plan_pages:
        for m in page.get("marks", []):
            mark_no = _int(m.get("mark"))
            diameter = _int(m.get("diameter"))
            bars_per = _int(m.get("bars_per_occurrence"))
            occurrences = _int(m.get("occurrences_on_plan"))
            length = _float(m.get("length"))
            confidence = m.get("confidence", "medium")

            if diameter is None or bars_per is None:
                global_warnings.append(
                    f"Marcă din plan ignorată (date lipsă): {m.get('annotation', m)}"
                )
                continue

            buc = (bars_per * occurrences) if occurrences is not None else bars_per
            if occurrences is None:
                confidence = "low"
                global_warnings.append(
                    f"Marca {mark_no}: numărul de apariții pe plan nu a putut fi determinat."
                )

            raw_marks.append({
                "mark": mark_no,
                "diameter": diameter,
                "count": buc,
                "length": length or 0.0,
                "confidence": confidence,
                "tier": 2,
                "source": page.get("source", "plan"),
            })

    # --- Tier 1 & 3: Detail marks (explicit element counts) ---
    for page in detail_pages:
        for element in page.get("elements", []):
            element_count = _int(element.get("count"))
            for m in element.get("marks", []):
                mark_no = _int(m.get("mark"))
                diameter = _int(m.get("diameter"))
                length = _float(m.get("length"))
                bars_per = _int(m.get("bars_per_element"))
                stirrups_per = _int(m.get("stirrups_per_element"))
                is_stirrup = bool(m.get("is_stirrup", False))

                if diameter is None:
                    global_warnings.append(
                        f"Marcă din detaliu ignorată (diametru lipsă): {m.get('annotation', m)}"
                    )
                    continue

                if is_stirrup and stirrups_per is not None and element_count is not None:
                    buc = stirrups_per * element_count
                    confidence = "high"
                    tier = 1
                elif bars_per is not None and element_count is not None:
                    buc = bars_per * element_count
                    confidence = "high"
                    tier = 1
                else:
                    buc = bars_per or 1
                    confidence = "low"
                    tier = 3  # fallback — don't override valid Tier 2 plan entries
                    global_warnings.append(
                        f"Marca {mark_no}: numărul de elemente neclar — valoare estimată."
                    )

                raw_marks.append({
                    "mark": mark_no,
                    "diameter": diameter,
                    "count": buc,
                    "length": length or 0.0,
                    "confidence": confidence,
                    "tier": tier,
                    "source": page.get("source", "detail"),
                })

        # Anchor bars
        for ab in page.get("anchor_bars", []):
            mark_no = _int(ab.get("mark"))
            diameter = _int(ab.get("diameter"))
            bars_per_junc = _int(ab.get("bars_per_junction"))
            junction_count = _int(ab.get("junction_count"))
            length = _float(ab.get("length"))

            if diameter is None:
                continue

            if bars_per_junc is not None and junction_count is not None:
                buc = bars_per_junc * junction_count
                confidence = "high"
            elif bars_per_junc is not None:
                buc = bars_per_junc
                confidence = "low"
                global_warnings.append(
                    f"Marca {mark_no} (bare ancorare): numărul de joncțiuni neclar — valoare estimată."
                )
            else:
                continue

            raw_marks.append({
                "mark": mark_no,
                "diameter": diameter,
                "count": buc,
                "length": length or 0.0,
                "confidence": confidence,
                "tier": 1,
                "source": page.get("source", "detail"),
            })

    # --- Tier 3: Cross-section stirrups (spacing-based) ---
    for page in section_pages:
        for section in page.get("sections", []):
            for st in section.get("stirrups", []):
                mark_no = _int(st.get("mark"))
                diameter = _int(st.get("diameter"))
                spacing_cm = _float(st.get("spacing_cm"))
                length = _float(st.get("length"))

                if diameter is None or spacing_cm is None or spacing_cm <= 0:
                    global_warnings.append(
                        f"Etrier ignorat (date lipsă): {st.get('annotation', st)}"
                    )
                    continue

                if total_beam_length_cm > 0:
                    buc = math.ceil(total_beam_length_cm / spacing_cm)
                    confidence = "low"
                    tier = 3
                    global_warnings.append(
                        f"Marca {mark_no} (etrier Ø{diameter}/{spacing_cm:.0f}cm): "
                        f"calculat din lungimea totală a tuturor grinzilor ({total_beam_length_cm:.0f} cm). "
                        f"Verificați dacă etrierul se aplică doar unei porțiuni din fundație."
                    )
                else:
                    buc = 0
                    confidence = "low"
                    tier = 3
                    global_warnings.append(
                        f"Marca {mark_no}: lungimea totală a grinzilor nu a putut fi determinată "
                        f"din plan — numărul de etrieri este 0."
                    )

                raw_marks.append({
                    "mark": mark_no,
                    "diameter": diameter,
                    "count": buc,
                    "length": length or 0.0,
                    "confidence": confidence,
                    "tier": tier,
                    "source": page.get("source", "cross_section"),
                })

            # Special bars from sections (e.g., mustăți scară)
            for sb in section.get("special_bars", []):
                mark_no = _int(sb.get("mark"))
                diameter = _int(sb.get("diameter"))
                count_per_set = _int(sb.get("count_per_set"))
                set_count = _int(sb.get("set_count"))
                total_count = _int(sb.get("total_count"))
                length = _float(sb.get("length"))

                if diameter is None:
                    continue

                if total_count is not None:
                    buc = total_count
                    confidence = "medium"
                elif count_per_set is not None and set_count is not None:
                    buc = count_per_set * set_count
                    confidence = "medium"
                elif count_per_set is not None:
                    buc = count_per_set
                    confidence = "low"
                    global_warnings.append(
                        f"Marca {mark_no}: numărul de seturi de bare speciale neclar — valoare estimată."
                    )
                else:
                    continue

                raw_marks.append({
                    "mark": mark_no,
                    "diameter": diameter,
                    "count": buc,
                    "length": length or 0.0,
                    "confidence": confidence,
                    "tier": 3,
                    "source": page.get("source", "cross_section"),
                })

            # Longitudinal bars from sections — add only if not already covered by plan
            for lb in section.get("longitudinal_bars", []):
                mark_no = _int(lb.get("mark"))
                diameter = _int(lb.get("diameter"))
                bars = _int(lb.get("bars"))
                length = _float(lb.get("length"))

                if diameter is None or bars is None or mark_no is None:
                    continue
                # Will be deduplicated below if plan page already has this mark
                raw_marks.append({
                    "mark": mark_no,
                    "diameter": diameter,
                    "count": bars,
                    "length": length or 0.0,
                    "confidence": "low",
                    "tier": 3,  # lower priority than plan occurrences
                    "source": page.get("source", "cross_section"),
                })

    # ── Deduplicate and build rows ─────────────────────────────────────
    rows: list[dict] = []
    seen_marks: dict[int, int] = {}  # mark_no → index in rows (for dedup by tier priority)

    for m in raw_marks:
        mark_no = m.get("mark")
        diameter = m["diameter"]
        count = int(m["count"])
        length = float(m["length"])
        confidence = m["confidence"]
        tier = m.get("tier", 2)

        row_warnings: list[str] = []
        if length <= 0:
            row_warnings.append(f"Marca {mark_no or '?'}: lungime lipsă — necesită verificare")
            confidence = "low"

        # Prefer higher-tier (lower tier number = higher priority) when duplicate mark
        if mark_no is not None and mark_no in seen_marks:
            existing_idx = seen_marks[mark_no]
            existing_tier = rows[existing_idx].get("_tier", 99)
            if tier >= existing_tier:
                # existing is better or equal — skip this one
                continue
            else:
                # this one is better — replace
                rows.pop(existing_idx)
                seen_marks = {
                    m2: (i if i < existing_idx else i - 1)
                    for m2, i in seen_marks.items()
                    if m2 != mark_no
                }

        row = build_schedule_row(
            mark=mark_no,
            diameter=diameter,
            count=count,
            length=length,
            confidence=confidence,
            warnings=row_warnings,
        )
        row_dict = row.to_dict()
        row_dict["_tier"] = tier  # internal, stripped before saving

        if mark_no is not None:
            seen_marks[mark_no] = len(rows)
        rows.append(row_dict)

    # Strip internal _tier field
    for r in rows:
        r.pop("_tier", None)

    # Sort by mark number (None marks go to end)
    rows.sort(key=lambda r: (r["mark"] is None, r["mark"] or 0))

    logger.info("Pipeline complete: %d rows, %d warnings", len(rows), len(global_warnings))
    return rows, global_warnings


# ── Helpers ───────────────────────────────────────────────────────────────────

def _int(val) -> int | None:
    if val is None:
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


def _float(val) -> float | None:
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _rows_from_table_marks(marks: list[dict], warnings: list[str]) -> list[dict]:
    """Build schedule rows directly from a transcribed Extras table (high confidence)."""
    rows: list[dict] = []
    for m in marks:
        mark_no = _int(m.get("mark"))
        diameter = _int(m.get("diameter"))
        count = _int(m.get("count"))
        length = _float(m.get("length"))

        if diameter is None or count is None or length is None:
            warnings.append(f"Marcă din tabel ignorată (date lipsă): {m}")
            continue

        row = build_schedule_row(
            mark=mark_no,
            diameter=diameter,
            count=count,
            length=length,
            confidence="high",
            warnings=[],
        )
        rows.append(row.to_dict())

    rows.sort(key=lambda r: (r["mark"] is None, r["mark"] or 0))
    return rows


def _sum_beam_lengths(plan_pages: list[dict]) -> float:
    """Sum all beam segment lengths (in cm) from plan pages."""
    total = 0.0
    for page in plan_pages:
        for seg in page.get("beam_segments", []):
            length = _float(seg.get("length_cm"))
            if length and length > 0:
                total += length
    return total
