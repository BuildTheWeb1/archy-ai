"""Rebar weight constants and schedule row builder."""

import uuid

from pipeline.models import RebarMark, ScheduleRow

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
    28: 4.830,
    32: 6.310,
}


def weight_per_meter(diameter: int) -> float:
    """Return kg/m for a given diameter. Returns 0 if unknown."""
    return REBAR_WEIGHTS_KG_PER_M.get(diameter, 0.0)


def build_schedule_row(
    mark: int | None,
    diameter: int,
    count: int,
    length: float,
    confidence: str = "medium",
    warnings: list[str] | None = None,
) -> ScheduleRow:
    wpm = weight_per_meter(diameter)
    total_length = round(count * length, 3)
    weight = round(total_length * wpm, 3)
    return ScheduleRow(
        id=str(uuid.uuid4()),
        mark=mark,
        diameter=diameter,
        count=count,
        length=length,
        total_length=total_length,
        weight_per_meter=wpm,
        weight=weight,
        confidence=confidence,
        warnings=warnings or [],
    )
