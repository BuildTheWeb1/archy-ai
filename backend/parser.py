"""
Rebar notation parser — Phase 2.

Parses Romanian structural rebar annotation strings into structured data.
Both Latin Ø and Cyrillic Ф are treated as equivalent diameter symbols.

This module is a stub. Implementation happens in Phase 2 after the
layout splitter (Feature 1) is validated end-to-end.
"""

import re
from dataclasses import dataclass


# Normalise both Ø (U+00D8) and Ф (U+0424) to a single token for matching
_DIA_RE = re.compile(r"[ØФ]")


@dataclass
class RebarMark:
    mark: int | None
    count: int
    diameter: int
    length: float | None
    spacing: int | None        # cm — for stirrups / slab bars
    steel: str = "BST500"
    pattern_name: str = ""


def parse_rebar_label(text: str) -> RebarMark | None:
    """
    Parse a single text entity into a RebarMark.
    Returns None if the text does not match any known rebar pattern.

    Phase 2: implement full grammar here.
    """
    # Stub — will be implemented in Phase 2
    return None
