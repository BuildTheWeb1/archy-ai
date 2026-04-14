"""PDF text and table extraction using pdfplumber."""

import logging
from pathlib import Path

import pdfplumber

logger = logging.getLogger(__name__)

_SCHEDULE_KWS = {"BST500", "Marca", "Extras de armatura", "Extras de armătură", "armatura"}


def extract_pdf(pdf_path: Path) -> dict:
    """
    Extract text, rotated chars, and tables from a PDF.

    Returns:
        {
            "page_count": int,
            "upright_text": str,           # joined text from all pages
            "rotated_chars": list[dict],   # pdfplumber char dicts where upright==False
            "tables": list[list[list]],    # raw table cells per table
            "has_embedded_schedule": bool,
        }
    """
    result: dict = {
        "page_count": 0,
        "upright_text": "",
        "rotated_chars": [],
        "tables": [],
        "has_embedded_schedule": False,
    }

    with pdfplumber.open(str(pdf_path)) as pdf:
        result["page_count"] = len(pdf.pages)
        text_parts: list[str] = []
        all_rotated: list[dict] = []

        for page in pdf.pages:
            text = page.extract_text() or ""
            text_parts.append(text)

            # Collect rotated chars (upright == False)
            for char in page.chars:
                if not char.get("upright", True):
                    all_rotated.append(char)

            # Tables
            tables = page.extract_tables()
            if tables:
                result["tables"].extend(tables)

        result["upright_text"] = "\n".join(text_parts)
        result["rotated_chars"] = all_rotated

        combined = result["upright_text"]
        result["has_embedded_schedule"] = any(kw in combined for kw in _SCHEDULE_KWS)

    logger.debug(
        "Extracted %d pages, %d rotated chars, %d tables from %s",
        result["page_count"],
        len(all_rotated),
        len(result["tables"]),
        pdf_path.name,
    )
    return result
