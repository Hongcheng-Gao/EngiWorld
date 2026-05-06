from __future__ import annotations

import math
import os
from pathlib import Path

import ezdxf

OUTPUT_ROOT = Path(os.environ.get("OUTPUT_ROOT", r"C:\Users\Administrator\Desktop"))
SPEC = {'target': 'autocad_result.dxf', 'segments': [{'start': [0, 0], 'end': [220, 0], 'layer': 'OUTLINE'}, {'start': [220, 0], 'end': [220, 45], 'layer': 'OUTLINE'}, {'start': [220, 45], 'end': [0, 45], 'layer': 'OUTLINE'}, {'start': [0, 45], 'end': [0, 0], 'layer': 'OUTLINE'}, {'start': [80, 55], 'end': [140, 55], 'layer': 'OUTLINE'}, {'start': [140, 55], 'end': [140, 95], 'layer': 'OUTLINE'}, {'start': [140, 95], 'end': [80, 95], 'layer': 'OUTLINE'}, {'start': [80, 95], 'end': [80, 55], 'layer': 'OUTLINE'}, {'start': [45, 55], 'end': [65, 55], 'layer': 'OUTLINE'}, {'start': [65, 55], 'end': [65, 95], 'layer': 'OUTLINE'}, {'start': [65, 95], 'end': [45, 95], 'layer': 'OUTLINE'}, {'start': [45, 95], 'end': [45, 55], 'layer': 'OUTLINE'}, {'start': [155, 55], 'end': [175, 55], 'layer': 'OUTLINE'}, {'start': [175, 55], 'end': [175, 95], 'layer': 'OUTLINE'}, {'start': [175, 95], 'end': [155, 95], 'layer': 'OUTLINE'}, {'start': [155, 95], 'end': [155, 55], 'layer': 'OUTLINE'}, {'start': [55, 75], 'end': [165, 75], 'layer': 'CENTER'}], 'circles': [{'center': [110, 75], 'radius': 7, 'layer': 'HOLE'}], 'arcs': [], 'texts': [{'text': 'ACAD-38', 'layer': 'ANNOTATION'}]}
TOL = 0.75
ANGLE_TOL = 2.0


def _close(a, b, tol=TOL):
    return abs(float(a) - float(b)) <= tol


def _angle_close(a, b, tol=ANGLE_TOL):
    return abs(((float(a) - float(b) + 180.0) % 360.0) - 180.0) <= tol


def _point_close(a, b, tol=TOL):
    return _close(a[0], b[0], tol) and _close(a[1], b[1], tol)


def _layer_ok(actual, expected):
    return expected is None or str(actual).upper() == str(expected).upper()


def _segments(doc):
    out = []
    for entity in doc.modelspace():
        layer = getattr(entity.dxf, "layer", "")
        if entity.dxftype() == "LINE":
            s, e = entity.dxf.start, entity.dxf.end
            out.append(((float(s.x), float(s.y)), (float(e.x), float(e.y)), layer))
        elif entity.dxftype() == "LWPOLYLINE":
            pts = [(float(p[0]), float(p[1])) for p in entity.get_points("xy")]
            for start, end in zip(pts, pts[1:]):
                out.append((start, end, layer))
            if entity.closed and len(pts) > 2:
                out.append((pts[-1], pts[0], layer))
    return out


def _has_segment(segments, start, end, layer=None):
    start = tuple(start)
    end = tuple(end)
    for a, b, actual_layer in segments:
        if not _layer_ok(actual_layer, layer):
            continue
        if (_point_close(a, start) and _point_close(b, end)) or (_point_close(a, end) and _point_close(b, start)):
            return True
    return False


def _has_circle(doc, center, radius, layer=None):
    center = tuple(center)
    for entity in doc.modelspace():
        if entity.dxftype() != "CIRCLE":
            continue
        if not _layer_ok(getattr(entity.dxf, "layer", ""), layer):
            continue
        c = entity.dxf.center
        if _point_close((c.x, c.y), center) and _close(entity.dxf.radius, radius):
            return True
    return False


def _has_arc(doc, center, radius, start_angle, end_angle, layer=None):
    center = tuple(center)
    for entity in doc.modelspace():
        if entity.dxftype() != "ARC":
            continue
        if not _layer_ok(getattr(entity.dxf, "layer", ""), layer):
            continue
        c = entity.dxf.center
        if (_point_close((c.x, c.y), center)
                and _close(entity.dxf.radius, radius)
                and _angle_close(entity.dxf.start_angle, start_angle)
                and _angle_close(entity.dxf.end_angle, end_angle)):
            return True
    return False


def _has_text(doc, value, layer=None):
    for entity in doc.modelspace():
        if entity.dxftype() == "TEXT":
            txt = str(entity.dxf.text)
        elif entity.dxftype() == "MTEXT":
            txt = str(entity.text)
        else:
            continue
        if not _layer_ok(getattr(entity.dxf, "layer", ""), layer):
            continue
        if txt.strip() == str(value):
            return True
    return False


def evaluate() -> bool:
    path = OUTPUT_ROOT / SPEC["target"]
    if not path.exists() or path.stat().st_size <= 0:
        return False
    doc = ezdxf.readfile(path)
    segments = _segments(doc)
    for item in SPEC["segments"]:
        if not _has_segment(segments, item["start"], item["end"], item.get("layer")):
            return False
    for item in SPEC["circles"]:
        if not _has_circle(doc, item["center"], item["radius"], item.get("layer")):
            return False
    for item in SPEC["arcs"]:
        if not _has_arc(doc, item["center"], item["radius"], item["start_angle"], item["end_angle"], item.get("layer")):
            return False
    for item in SPEC["texts"]:
        if not _has_text(doc, item["text"], item.get("layer")):
            return False
    return True


if __name__ == "__main__":
    try:
        ok = evaluate()
    except Exception:
        ok = False
    print("True" if ok else "False")
