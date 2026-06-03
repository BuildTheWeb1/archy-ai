"""
Export a rebar schedule to .xlsx in the Romanian "Extras de armătură" format.

Layout matches the standard structural engineering table:
  • Two-row header: fixed columns (Marca, Ø, Oțel, Buc., Lung.) +
    dynamic sub-columns under "Lung./Ø [m]" — one per distinct diameter.
  • Data rows: each row's total length appears under its matching diameter column.
  • Footer rows:
      - Lungimi / Ø [m]   — total length per diameter
      - Masa Ø / m [kg/m]  — weight constant per diameter
      - Masa / Ø [kg]      — total weight per diameter
      - Masa totală [kg]   — grand total across all diameters
"""

from __future__ import annotations

import logging
from collections import defaultdict
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from pipeline.weights import REBAR_WEIGHTS_KG_PER_M

logger = logging.getLogger(__name__)

# ── Styling helpers ────────────────────────────────────────────────────────

_THIN = Side(style="thin")
_BORDER = Border(left=_THIN, right=_THIN, top=_THIN, bottom=_THIN)
_HEADER_FILL = PatternFill("solid", fgColor="1F4E79")
_SUBHEADER_FILL = PatternFill("solid", fgColor="2E75B6")
_SUMMARY_FILL = PatternFill("solid", fgColor="D6E4F0")
_TOTAL_FILL = PatternFill("solid", fgColor="BDD7EE")


def _style_cell(cell, bold=False, fill=None, align="center", color=None):
    font_kwargs = {"bold": bold, "size": 10}
    if color:
        font_kwargs["color"] = color
    cell.font = Font(**font_kwargs)
    cell.alignment = Alignment(horizontal=align, vertical="center", wrap_text=True)
    cell.border = _BORDER
    if fill:
        cell.fill = fill


def _num_fmt(cell):
    """Apply number format (1 decimal place, matching the reference table)."""
    cell.number_format = "#,##0.0"


# ── Fixed column definitions ──────────────────────────────────────────────

_FIXED_COLS = [
    ("Marca", 8),
    ("Ø [mm]", 8),
    ("Oțel", 9),
    ("Buc.", 7),
    ("Lung. [m]", 10),
]


def export_schedule(
    rows: list[dict],
    output_path: Path,
    project_name: str = "",
    project_number: str = "",
    beneficiary: str = "",
    location: str = "",
) -> None:
    """Write *rows* to an .xlsx file at *output_path*."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Extras armătură"

    # Determine distinct diameters from data
    diameters = sorted({r["diameter"] for r in rows})
    num_dia = len(diameters)
    dia_col_start = len(_FIXED_COLS) + 1  # first diameter column (1-based)

    current_row = 1

    # ── Project info header ───────────────────────────────────────────
    if any([project_name, project_number, beneficiary, location]):
        info_lines = [
            ("Proiect:", project_name or "—"),
            ("Nr. proiect:", project_number or "—"),
            ("Beneficiar:", beneficiary or "—"),
            ("Locație:", location or "—"),
        ]
        for label, value in info_lines:
            ws.cell(current_row, 1, label).font = Font(bold=True, size=10)
            ws.cell(current_row, 2, value).font = Font(size=10)
            current_row += 1
        current_row += 1  # blank row

    # ── Header row 1: fixed columns + merged "Lung./Ø [m]" ──────────
    header_row1 = current_row
    header_row2 = current_row + 1

    # Fixed columns span both header rows
    for col_idx, (title, width) in enumerate(_FIXED_COLS, start=1):
        cell = ws.cell(header_row1, col_idx, title)
        _style_cell(cell, bold=True, fill=_HEADER_FILL, color="FFFFFF")
        ws.merge_cells(
            start_row=header_row1, start_column=col_idx,
            end_row=header_row2, end_column=col_idx,
        )
        # Style the merged bottom cell too
        _style_cell(ws.cell(header_row2, col_idx), bold=True, fill=_HEADER_FILL, color="FFFFFF")
        ws.column_dimensions[get_column_letter(col_idx)].width = width

    # "Lung./Ø [m]" grouped header spanning all diameter columns
    if num_dia > 0:
        group_cell = ws.cell(header_row1, dia_col_start, "Lung./Ø [m]")
        _style_cell(group_cell, bold=True, fill=_HEADER_FILL, color="FFFFFF")
        if num_dia > 1:
            ws.merge_cells(
                start_row=header_row1, start_column=dia_col_start,
                end_row=header_row1, end_column=dia_col_start + num_dia - 1,
            )
        # Style merged cells
        for i in range(1, num_dia):
            _style_cell(
                ws.cell(header_row1, dia_col_start + i),
                bold=True, fill=_HEADER_FILL, color="FFFFFF",
            )

    # ── Header row 2: diameter sub-headers ────────────────────────────
    for i, dia in enumerate(diameters):
        col = dia_col_start + i
        cell = ws.cell(header_row2, col, dia)
        _style_cell(cell, bold=True, fill=_SUBHEADER_FILL, color="FFFFFF")
        ws.column_dimensions[get_column_letter(col)].width = 10

    ws.row_dimensions[header_row1].height = 24
    ws.row_dimensions[header_row2].height = 20
    current_row = header_row2 + 1

    # ── Data rows ─────────────────────────────────────────────────────
    for r in rows:
        mark_val = r.get("mark") or ""
        diameter = r["diameter"]
        values = [
            mark_val,
            diameter,
            r.get("steel_type", "BST500"),
            r.get("count", 0),
            r.get("length", 0.0),
        ]
        # Fixed columns
        for col_idx, val in enumerate(values, start=1):
            cell = ws.cell(current_row, col_idx, val)
            _style_cell(cell)
            if isinstance(val, float):
                _num_fmt(cell)

        # Diameter columns — value only in matching column
        total_length = r.get("total_length", 0.0)
        for i, dia in enumerate(diameters):
            col = dia_col_start + i
            if dia == diameter:
                cell = ws.cell(current_row, col, total_length)
                _num_fmt(cell)
            else:
                cell = ws.cell(current_row, col, "")
            _style_cell(cell)

        current_row += 1

    # ── Summary rows ──────────────────────────────────────────────────

    # Pre-compute per-diameter totals
    length_per_dia: dict[int, float] = defaultdict(float)
    for r in rows:
        length_per_dia[r["diameter"]] += r.get("total_length", 0.0)

    weight_per_dia: dict[int, float] = {}
    for dia in diameters:
        length_per_dia[dia] = round(length_per_dia[dia], 1)
        wpm = REBAR_WEIGHTS_KG_PER_M.get(dia, 0.0)
        weight_per_dia[dia] = round(length_per_dia[dia] * wpm, 1)

    grand_total = round(sum(weight_per_dia.values()), 1)

    def _write_summary_row(label: str, values_by_dia: dict[int, float | str], fill, bold=True):
        nonlocal current_row
        # Merge fixed columns for label
        label_cell = ws.cell(current_row, 1, label)
        _style_cell(label_cell, bold=bold, fill=fill)
        ws.merge_cells(
            start_row=current_row, start_column=1,
            end_row=current_row, end_column=len(_FIXED_COLS),
        )
        label_cell.alignment = Alignment(horizontal="right", vertical="center")
        # Style merged cells
        for c in range(2, len(_FIXED_COLS) + 1):
            _style_cell(ws.cell(current_row, c), bold=bold, fill=fill)

        # Diameter values
        for i, dia in enumerate(diameters):
            col = dia_col_start + i
            val = values_by_dia.get(dia, "")
            cell = ws.cell(current_row, col, val)
            _style_cell(cell, bold=bold, fill=fill)
            if isinstance(val, (int, float)):
                _num_fmt(cell)
        current_row += 1

    # Lungimi / Ø [m]
    _write_summary_row("Lungimi / Ø [m]", length_per_dia, _SUMMARY_FILL)

    # Masa Ø / m [kg/m]
    wpm_values = {dia: REBAR_WEIGHTS_KG_PER_M.get(dia, 0.0) for dia in diameters}
    _write_summary_row("Masa Ø / m [kg/m]", wpm_values, _SUMMARY_FILL, bold=False)

    # Masa / Ø [kg]
    _write_summary_row("Masa / Ø [kg]", weight_per_dia, _SUMMARY_FILL)

    # Masa totală [kg] — merged across diameter columns
    total_label = ws.cell(current_row, 1, "Masa totală [kg]")
    _style_cell(total_label, bold=True, fill=_TOTAL_FILL)
    ws.merge_cells(
        start_row=current_row, start_column=1,
        end_row=current_row, end_column=len(_FIXED_COLS),
    )
    total_label.alignment = Alignment(horizontal="right", vertical="center")
    for c in range(2, len(_FIXED_COLS) + 1):
        _style_cell(ws.cell(current_row, c), bold=True, fill=_TOTAL_FILL)

    # Grand total value merged across all diameter columns
    total_val_cell = ws.cell(current_row, dia_col_start, grand_total)
    _style_cell(total_val_cell, bold=True, fill=_TOTAL_FILL)
    _num_fmt(total_val_cell)
    if num_dia > 1:
        ws.merge_cells(
            start_row=current_row, start_column=dia_col_start,
            end_row=current_row, end_column=dia_col_start + num_dia - 1,
        )
        for i in range(1, num_dia):
            _style_cell(ws.cell(current_row, dia_col_start + i), bold=True, fill=_TOTAL_FILL)
    total_val_cell.alignment = Alignment(horizontal="center", vertical="center")

    # Freeze below header rows
    ws.freeze_panes = ws.cell(header_row2 + 1, 1)

    wb.save(str(output_path))
    logger.info("Exported schedule (%d rows) to %s", len(rows), output_path)
