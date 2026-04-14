"""Shared data models for the rebar extraction pipeline."""

from dataclasses import dataclass, field


@dataclass
class RebarMark:
    """A single parsed rebar annotation from a drawing."""

    diameter: int
    mark: int | None = None
    count: int | None = None
    length: float | None = None
    spacing: int | None = None   # spacing in mm (slab / stirrup)
    mesh_gx: int | None = None   # mesh grid x [mm]
    mesh_gy: int | None = None   # mesh grid y [mm]
    confidence: str = "medium"   # high | medium | low
    raw: str = ""


@dataclass
class ScheduleRow:
    """One row in the final rebar schedule."""

    id: str
    diameter: int
    count: int
    length: float               # length per bar [m]
    total_length: float         # count * length [m]
    weight_per_meter: float     # kg/m
    weight: float               # total_length * weight_per_meter [kg]
    mark: int | None = None
    steel_type: str = "BST500"
    confidence: str = "medium"  # high | medium | low
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "mark": self.mark,
            "diameter": self.diameter,
            "steel_type": self.steel_type,
            "count": self.count,
            "length": self.length,
            "total_length": self.total_length,
            "weight_per_meter": self.weight_per_meter,
            "weight": self.weight,
            "confidence": self.confidence,
            "warnings": self.warnings,
        }
