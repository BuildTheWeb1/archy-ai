"""
Standard rebar weight constants (kg/m) by diameter.
Physical constants: steel density × cross-sectional area.
Never hardcode these elsewhere — always import from here.
"""

REBAR_WEIGHTS_KG_PER_M: dict[int, float] = {
    6: 0.222,
    8: 0.395,
    10: 0.617,
    12: 0.888,
    14: 1.210,
    16: 1.580,
    18: 2.000,
    20: 2.470,
    22: 2.984,
    25: 3.853,
}


def weight_for_diameter(diameter_mm: int) -> float:
    """Return kg/m for a given diameter. Raises KeyError if not in table."""
    return REBAR_WEIGHTS_KG_PER_M[diameter_mm]
