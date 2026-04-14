"""
Split a combined PDF (from APS Model Derivative) into one PDF per page.

Each page in the combined output corresponds to one Paper Space layout from
the original DWG/DXF. PDF page labels carry the layout name when present.
"""

import logging
from pathlib import Path

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


def split_pdf(combined_pdf: Path, layouts_dir: Path) -> list[dict]:
    """
    Split combined_pdf into one file per page under layouts_dir/{n}.pdf.
    Returns list of {index: int, name: str} dicts ordered by page.
    """
    layouts_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(str(combined_pdf))
    label_rules = doc.get_page_labels()

    layouts = []
    for i in range(len(doc)):
        out = fitz.open()
        out.insert_pdf(doc, from_page=i, to_page=i)
        page_path = layouts_dir / f"{i}.pdf"
        out.save(str(page_path))
        out.close()

        name = _resolve_label(label_rules, i) or f"Layout {i + 1}"
        layouts.append({"index": i, "name": name})
        logger.info("Split layout %d: %s", i, name)

    doc.close()
    return layouts


def _resolve_label(rules: list[dict], page_index: int) -> str | None:
    """
    Resolve the PDF page label for a 0-based page index using the label rules
    stored in the PDF's /PageLabels dict. Returns None when no useful label exists.

    DWG → PDF exports from APS typically set prefix=<layout name>, style="" (no
    numbering), making the prefix the full label.
    """
    if not rules:
        return None

    # Find the applicable rule: highest startpage that is still <= page_index
    applicable: dict | None = None
    for rule in rules:
        if rule.get("startpage", 0) <= page_index:
            applicable = rule

    if applicable is None:
        return None

    prefix = applicable.get("prefix", "")
    style = applicable.get("style", "")

    if not style:
        return prefix.strip() or None

    first = applicable.get("firstpagenum", 1)
    offset = page_index - applicable.get("startpage", 0)
    num = first + offset

    if style == "D":
        suffix = str(num)
    elif style == "R":
        suffix = _to_roman(num).upper()
    elif style == "r":
        suffix = _to_roman(num).lower()
    elif style in ("A", "a"):
        letters: list[str] = []
        n = num
        while n > 0:
            n, r = divmod(n - 1, 26)
            letters.append(chr(65 + r))
        suffix = "".join(reversed(letters))
        if style == "a":
            suffix = suffix.lower()
    else:
        suffix = str(num)

    return (prefix + suffix).strip() or None


def _to_roman(n: int) -> str:
    result = ""
    for value, numeral in (
        (1000, "M"), (900, "CM"), (500, "D"), (400, "CD"),
        (100, "C"), (90, "XC"), (50, "L"), (40, "XL"),
        (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I"),
    ):
        while n >= value:
            result += numeral
            n -= value
    return result
