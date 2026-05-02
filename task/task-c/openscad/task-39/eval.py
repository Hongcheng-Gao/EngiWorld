from __future__ import annotations

import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

import ezdxf
import trimesh

MESH_SPECS = [{'vertices': 8, 'faces': 12, 'bbox': [80.0, 54.0, 42.0], 'volume': 181440.0, 'area': 19896.0, 'watertight': True, 'path': 'task-039_output.stl'}]
DXF_SPECS = []
THREE_MF_SPECS = []
CSG_SPECS = []
FILE_SPECS = []
BBOX_TOL = 0.05
REL_TOL = 0.01
OUTPUT_ROOT = Path('/home/user/Desktop')


def mesh_summary(path: Path):
    mesh = trimesh.load_mesh(path, force="mesh")
    if not isinstance(mesh, trimesh.Trimesh):
        mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))
    return {
        "vertices": int(len(mesh.vertices)),
        "faces": int(len(mesh.faces)),
        "bbox": [round(float(v), 6) for v in mesh.extents.tolist()],
        "volume": round(float(mesh.volume), 6),
        "area": round(float(mesh.area), 6),
        "watertight": bool(mesh.is_watertight),
    }


def dxf_summary(path: Path):
    doc = ezdxf.readfile(path)
    counts = {}
    layers = set()
    texts = []
    circles = []
    polylines = []
    for entity in doc.modelspace():
        dxftype = entity.dxftype()
        counts[dxftype] = counts.get(dxftype, 0) + 1
        layer = str(getattr(entity.dxf, "layer", "0"))
        layers.add(layer)
        if dxftype == "TEXT":
            texts.append(str(entity.dxf.text))
        elif dxftype == "CIRCLE":
            center = entity.dxf.center
            circles.append((layer, (round(float(center[0]), 4), round(float(center[1]), 4)), round(float(entity.dxf.radius), 4)))
        elif dxftype == "LWPOLYLINE":
            polylines.append((layer, len(entity.get_points("xy"))))
    return {"counts": counts, "layers": sorted(layers), "texts": sorted(texts), "circles": sorted(circles), "polylines": sorted(polylines)}


def three_mf_summary(path: Path):
    with zipfile.ZipFile(path) as archive:
        model_name = next(name for name in archive.namelist() if name.lower().endswith(".model"))
        root = ET.fromstring(archive.read(model_name))
    vertices = []
    triangles = 0
    items = 0
    for elem in root.iter():
        tag = elem.tag.split("}")[-1]
        if tag == "vertex":
            vertices.append((float(elem.attrib["x"]), float(elem.attrib["y"]), float(elem.attrib["z"])))
        elif tag == "triangle":
            triangles += 1
        elif tag == "item":
            items += 1
    xs, ys, zs = zip(*vertices)
    return {"vertices": len(vertices), "triangles": triangles, "items": items, "bbox": [round(max(xs)-min(xs), 6), round(max(ys)-min(ys), 6), round(max(zs)-min(zs), 6)]}


def close_rel(actual, expected):
    return abs(float(actual) - float(expected)) / max(1.0, abs(float(expected))) <= REL_TOL


def evaluate() -> bool:
    gt = OUTPUT_ROOT
    if not gt.exists():
        return False
    for spec in MESH_SPECS:
        path = gt / spec["path"]
        if not path.exists() or path.stat().st_size <= 0:
            return False
        actual = mesh_summary(path)
        if actual["vertices"] != spec["vertices"] or actual["faces"] != spec["faces"] or actual["watertight"] != spec["watertight"]:
            return False
        if any(abs(a - b) > BBOX_TOL for a, b in zip(actual["bbox"], spec["bbox"])):
            return False
        if not close_rel(actual["volume"], spec["volume"]) or not close_rel(actual["area"], spec["area"]):
            return False
    for spec in DXF_SPECS:
        path = gt / spec["path"]
        if not path.exists() or path.stat().st_size <= 0 or dxf_summary(path) != spec["summary"]:
            return False
    for spec in THREE_MF_SPECS:
        path = gt / spec["path"]
        if not path.exists() or path.stat().st_size <= 0 or three_mf_summary(path) != spec["summary"]:
            return False
    for spec in CSG_SPECS:
        path = gt / spec["path"]
        if not path.exists() or path.stat().st_size < int(spec["min_size"]):
            return False
        text = path.read_text(encoding="utf-8")
        if any(token not in text for token in spec["tokens"]):
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
    print(True if ok else False)
