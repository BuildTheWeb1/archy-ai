"""
Regex-based rebar label parser for Romanian AutoCAD drawings.

Both Ø (U+00D8, Latin) and Ф (U+0424, Cyrillic) are treated as diameter symbols,
as are their lowercase variants ø (U+00F8) and ф (U+0444).
"""

import logging
import re

from pipeline.models import RebarMark

logger = logging.getLogger(__name__)

# Diameter symbol — matches all four common variants
_D = r"[ØøФф]"

# ─── Compiled patterns (ordered: most-specific first) ────────────────────────

# 1. NxM grouped bars with length:  "1 2x3Ф14 L=8.60"
_PAT_NXM = re.compile(
    rf"(?:(?P<mark>\d{{1,2}})\s+)?(?P<n1>\d+)[xX×](?P<n2>\d+){_D}(?P<dia>\d+)\s*L=(?P<length>[\d.,]+)",
    re.IGNORECASE,
)

# 2. N bars with length:  "1 3Ф14 L=8.60"  or  "3Ф14 L=8.60"
_PAT_N = re.compile(
    rf"(?:(?P<mark>\d{{1,2}})\s+)?(?P<count>\d+){_D}(?P<dia>\d+)\s*L=(?P<length>[\d.,]+)",
    re.IGNORECASE,
)

# 3. Slab / distribution bar with length:  "1 Ф10/15 L=8.80"  or  "Ф10/15 L=8.80"
_PAT_SLAB = re.compile(
    rf"(?:(?P<mark>\d{{1,2}})\s+)?{_D}(?P<dia>\d+)/(?P<spacing>\d+)\s*L=(?P<length>[\d.,]+)",
    re.IGNORECASE,
)

# 4. Welded mesh:  "Ø6/10/10"
_PAT_MESH = re.compile(
    rf"{_D}(?P<dia>\d+)/(?P<gx>\d+)/(?P<gy>\d+)",
    re.IGNORECASE,
)

# 5. Stirrup / transverse bar (no length):  "etrieri Ф8/15"  or  "Ф8/15"
_PAT_STIRRUP = re.compile(
    rf"(?:etrieri\s+)?{_D}(?P<dia>\d+)/(?P<spacing>\d+)",
    re.IGNORECASE,
)


def _parse_float(s: str) -> float:
    return float(s.replace(",", "."))


def parse_rebar_label(text: str) -> RebarMark | None:
    """
    Try to extract a RebarMark from a raw text string.
    Returns None if no recognised pattern matches.
    """
    stripped = text.strip()

    # 1. NxM
    m = _PAT_NXM.search(stripped)
    if m:
        count = int(m.group("n1")) * int(m.group("n2"))
        mark_raw = m.group("mark")
        return RebarMark(
            mark=int(mark_raw) if mark_raw else None,
            diameter=int(m.group("dia")),
            count=count,
            length=_parse_float(m.group("length")),
            confidence="medium" if mark_raw else "low",
            raw=stripped,
        )

    # 2. N bars with length
    m = _PAT_N.search(stripped)
    if m:
        mark_raw = m.group("mark")
        return RebarMark(
            mark=int(mark_raw) if mark_raw else None,
            diameter=int(m.group("dia")),
            count=int(m.group("count")),
            length=_parse_float(m.group("length")),
            confidence="medium" if mark_raw else "low",
            raw=stripped,
        )

    # 3. Slab bar
    m = _PAT_SLAB.search(stripped)
    if m:
        mark_raw = m.group("mark")
        return RebarMark(
            mark=int(mark_raw) if mark_raw else None,
            diameter=int(m.group("dia")),
            count=None,
            length=_parse_float(m.group("length")),
            spacing=int(m.group("spacing")),
            confidence="low",
            raw=stripped,
        )

    # 4. Mesh
    m = _PAT_MESH.search(stripped)
    if m:
        return RebarMark(
            mark=None,
            diameter=int(m.group("dia")),
            count=None,
            length=None,
            mesh_gx=int(m.group("gx")),
            mesh_gy=int(m.group("gy")),
            confidence="low",
            raw=stripped,
        )

    # 5. Stirrup
    m = _PAT_STIRRUP.search(stripped)
    if m:
        return RebarMark(
            mark=None,
            diameter=int(m.group("dia")),
            count=None,
            length=None,
            spacing=int(m.group("spacing")),
            confidence="low",
            raw=stripped,
        )

    return None


# ─── Embedded schedule table parser ──────────────────────────────────────────

_SCHEDULE_HEADER_KWS = {"MARCA", "BST500", "BUC", "LUNG", "MASA", "OTEL", "OȚEL"}


def parse_embedded_schedule(tables: list[list[list]]) -> list[dict] | None:
    """
    Scan pdfplumber table output for a pre-drawn schedule table.
    Returns a list of raw row dicts (mark, diameter, count, length, confidence="high"),
    or None if no embedded schedule is found.
    """
    from pipeline.weights import build_schedule_row

    for table in tables:
        if not table or len(table) < 2:
            continue

        header_row: list | None = None
        header_idx = 0
        for i, row in enumerate(table):
            if not row:
                continue
            row_text = " ".join(str(c or "").upper() for c in row)
            if sum(1 for kw in _SCHEDULE_HEADER_KWS if kw in row_text) >= 2:
                header_row = row
                header_idx = i
                break

        if header_row is None:
            continue

        # Map column names → indices
        col: dict[str, int] = {}
        for j, cell in enumerate(header_row):
            upper = str(cell or "").upper()
            if "MARCA" in upper and "mark" not in col:
                col["mark"] = j
            elif ("Ø" in upper or "MM" in upper or "DIAM" in upper) and "diameter" not in col:
                col["diameter"] = j
            elif "BUC" in upper and "count" not in col:
                col["count"] = j
            elif "LUNG" in upper and "length" not in col and "TOTAL" not in upper:
                col["length"] = j

        if len(col) < 2:
            continue

        rows: list[dict] = []
        for row in table[header_idx + 1 :]:
            if not row or all(c is None or str(c).strip() == "" for c in row):
                continue
            try:
                def _cell(key: str):
                    idx = col.get(key)
                    return row[idx] if idx is not None and idx < len(row) else None

                mark_raw = _cell("mark")
                dia_raw = _cell("diameter")
                count_raw = _cell("count")
                length_raw = _cell("length")

                if dia_raw is None:
                    continue

                dia_str = re.sub(r"[ØøФфmm ]", "", str(dia_raw), flags=re.IGNORECASE)
                diameter = int(dia_str)
                mark = int(str(mark_raw).strip()) if mark_raw and str(mark_raw).strip().isdigit() else None
                count = int(str(count_raw).strip()) if count_raw and str(count_raw).strip().isdigit() else 1
                length = _parse_float(str(length_raw)) if length_raw and str(length_raw).strip() else 0.0

                if length <= 0:
                    continue

                sr = build_schedule_row(mark, diameter, count, length, confidence="high")
                rows.append(sr.to_dict())
            except (ValueError, TypeError, IndexError):
                continue

        if rows:
            logger.info("Found embedded schedule with %d rows", len(rows))
            return rows

    return None
