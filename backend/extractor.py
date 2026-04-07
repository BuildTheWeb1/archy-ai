import ezdxf
from pathlib import Path


def extract_from_dxf(filepath: str) -> dict:
    """Parse a DXF file and return structured extraction data."""
    doc = ezdxf.readfile(filepath)
    msp = doc.modelspace()

    layers: dict[str, dict] = {}

    for entity in msp:
        layer_name = entity.dxf.layer
        if layer_name not in layers:
            layers[layer_name] = {"entities": [], "entity_types": set()}

        entity_data = _extract_entity(entity)
        if entity_data:
            layers[layer_name]["entities"].append(entity_data)
            layers[layer_name]["entity_types"].add(entity_data["type"])

    # Convert sets to sorted lists for JSON serialisation
    for layer in layers.values():
        layer["entity_types"] = sorted(layer["entity_types"])

    return {
        "filename": Path(filepath).name,
        "dxf_version": doc.dxfversion,
        "layer_count": len(layers),
        "total_entities": sum(len(l["entities"]) for l in layers.values()),
        "layers": layers,
    }


def _extract_entity(entity) -> dict | None:
    etype = entity.dxftype()

    if etype == "TEXT":
        return {
            "type": "TEXT",
            "text": entity.dxf.text,
            "insertion": list(entity.dxf.insert)[:2],
            "height": getattr(entity.dxf, "height", 0),
        }

    if etype == "MTEXT":
        return {
            "type": "MTEXT",
            "text": entity.plain_text(),
            "insertion": list(entity.dxf.insert)[:2],
        }

    if etype == "DIMENSION":
        return {
            "type": "DIMENSION",
            "measurement": round(entity.dxf.get("actual_measurement", 0), 4),
            "text_override": entity.dxf.get("text", ""),
        }

    if etype == "INSERT":
        attribs = {}
        for attrib in entity.attribs:
            attribs[attrib.dxf.tag] = attrib.dxf.text
        return {
            "type": "INSERT",
            "block_name": entity.dxf.name,
            "insertion": list(entity.dxf.insert)[:2],
            "attributes": attribs,
        }

    if etype == "LWPOLYLINE":
        points = list(entity.get_points(format="xy"))
        return {
            "type": "LWPOLYLINE",
            "point_count": len(points),
            "is_closed": entity.closed,
            "points": [list(p) for p in points[:10]],
        }

    if etype == "LINE":
        return {
            "type": "LINE",
            "start": list(entity.dxf.start)[:2],
            "end": list(entity.dxf.end)[:2],
        }

    if etype == "CIRCLE":
        return {
            "type": "CIRCLE",
            "center": list(entity.dxf.center)[:2],
            "radius": round(entity.dxf.radius, 4),
        }

    if etype == "ARC":
        return {
            "type": "ARC",
            "center": list(entity.dxf.center)[:2],
            "radius": round(entity.dxf.radius, 4),
            "start_angle": round(entity.dxf.start_angle, 2),
            "end_angle": round(entity.dxf.end_angle, 2),
        }

    return None
