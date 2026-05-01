from __future__ import annotations

from pathlib import Path

import ezdxf

DXF_SPECS = [{'path': 'gui20_fixture_edit_completed.dxf', 'summary': {'counts': {'LWPOLYLINE': 1, 'CIRCLE': 4, 'LINE': 8, 'TEXT': 1}, 'layers': ['CENTER', 'HOLE', 'OUTLINE', 'TEXT'], 'texts': ['TASK-20'], 'circles': [('HOLE', (20.0, 20.0), 5.0), ('HOLE', (20.0, 50.0), 5.0), ('HOLE', (100.0, 20.0), 5.0), ('HOLE', (100.0, 50.0), 5.0)], 'lines': [('CENTER', (10.0, 20.0), (30.0, 20.0)), ('CENTER', (10.0, 50.0), (30.0, 50.0)), ('CENTER', (20.0, 10.0), (20.0, 30.0)), ('CENTER', (20.0, 40.0), (20.0, 60.0)), ('CENTER', (90.0, 20.0), (110.0, 20.0)), ('CENTER', (90.0, 50.0), (110.0, 50.0)), ('CENTER', (100.0, 10.0), (100.0, 30.0)), ('CENTER', (100.0, 40.0), (100.0, 60.0))], 'arcs': [], 'polylines': [('OUTLINE', [(0.0, 0.0), (120.0, 0.0), (120.0, 70.0), (0.0, 70.0), (0.0, 0.0)])], 'inserts': []}}]
FILE_SPECS = []
OUTPUT_ROOT = Path("/home/user/Desktop")


def round_pair(point):
    return (round(float(point[0]), 4), round(float(point[1]), 4))


def summarize_dxf(path: Path):
    doc = ezdxf.readfile(path)
    counts = {}
    layers = set()
    texts = []
    circles = []
    lines = []
    arcs = []
    polylines = []
    inserts = []
    for entity in doc.modelspace():
        dxftype = entity.dxftype()
        counts[dxftype] = counts.get(dxftype, 0) + 1
        layer = str(getattr(entity.dxf, "layer", "0"))
        layers.add(layer)
        if dxftype == "TEXT":
            texts.append(str(entity.dxf.text))
        elif dxftype == "CIRCLE":
            circles.append((layer, round_pair(entity.dxf.center), round(float(entity.dxf.radius), 4)))
        elif dxftype == "LINE":
            lines.append((layer, round_pair(entity.dxf.start), round_pair(entity.dxf.end)))
        elif dxftype == "ARC":
            arcs.append((layer, round_pair(entity.dxf.center), round(float(entity.dxf.radius), 4), round(float(entity.dxf.start_angle), 4), round(float(entity.dxf.end_angle), 4)))
        elif dxftype == "LWPOLYLINE":
            polylines.append((layer, [round_pair((p[0], p[1])) for p in entity.get_points("xy")]))
        elif dxftype == "INSERT":
            inserts.append((layer, str(entity.dxf.name), round_pair(entity.dxf.insert)))
    return {
        "counts": counts,
        "layers": sorted(layers),
        "texts": sorted(texts),
        "circles": sorted(circles),
        "lines": sorted(lines),
        "arcs": sorted(arcs),
        "polylines": sorted(polylines),
        "inserts": sorted(inserts),
    }


def evaluate() -> bool:
    gt = OUTPUT_ROOT
    if not gt.exists():
        return False
    for spec in DXF_SPECS:
        path = gt / spec["path"]
        if not path.exists() or path.stat().st_size <= 0:
            return False
        if summarize_dxf(path) != spec["summary"]:
            return False
    for spec in FILE_SPECS:
        path = gt / spec["path"]
        if not path.exists() or path.stat().st_size < int(spec["min_size"]):
            return False
    return True


if __name__ == "__main__":
    try:
        ok = evaluate()
    except Exception:
        ok = False
    print("true" if ok else "false")
