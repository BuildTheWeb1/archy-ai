"""Reconstruct text from rotated PDF characters (pdfplumber char objects)."""

import logging

logger = logging.getLogger(__name__)

# Group rotated chars into "columns" by x-position (bucket width in pt)
_BUCKET_WIDTH = 10


def reconstruct_rotated_text(chars: list[dict]) -> list[str]:
    """
    Group rotated chars by x-position bucket, sort each bucket by y-position
    (top-to-bottom reading order), and return reconstructed line strings.

    pdfplumber char dict keys used: x0, top, text
    """
    if not chars:
        return []

    buckets: dict[int, list[dict]] = {}
    for char in chars:
        x0 = char.get("x0", 0.0)
        key = int(x0 // _BUCKET_WIDTH)
        buckets.setdefault(key, []).append(char)

    lines: list[str] = []
    for key in sorted(buckets):
        bucket_chars = sorted(buckets[key], key=lambda c: c.get("top", 0.0))
        text = "".join(c.get("text", "") for c in bucket_chars).strip()
        if text:
            lines.append(text)

    logger.debug("Reconstructed %d rotated lines from %d chars", len(lines), len(chars))
    return lines
