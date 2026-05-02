from __future__ import annotations

import csv
import json
from pathlib import Path

import cadquery as cq

STEP_SPECS = [{'solid_count': 4, 'bbox': [349.0, 50.0, 20.0], 'volume': 173000.0, 'path': 'task-26_output.step'}]
JSON_SPECS = []
CSV_SPECS = []
TEXT_SPECS = []
FILE_SPECS = []
BBOX_TOL = 0.05
VOLUME_REL_TOL = 0.01
NUM_TOL = 0.05


def summarize_step(path: Path):
    wp = cq.importers.importStep(str(path))
    solids = wp.solids().vals()
    if not solids or any(not solid.isValid() for solid in solids):
        raise ValueError("invalid step")
    xs, ys, zs = [], [], []
    volume = 0.0
    for solid in solids:
        bb = solid.BoundingBox()
        xs.extend([bb.xmin, bb.xmax])
        ys.extend([bb.ymin, bb.ymax])
        zs.extend([bb.zmin, bb.zmax])
        volume += solid.Volume()
    return len(solids), [max(xs)-min(xs), max(ys)-min(ys), max(zs)-min(zs)], volume


def json_matches(actual, expected):
    if isinstance(expected, dict):
        return isinstance(actual, dict) and all(key in actual and json_matches(actual[key], value) for key, value in expected.items())
    if isinstance(expected, list):
        return isinstance(actual, list) and len(actual) == len(expected) and all(json_matches(a, e) for a, e in zip(actual, expected))
    if isinstance(expected, (int, float)):
        try:
            return abs(float(actual) - float(expected)) <= NUM_TOL
        except Exception:
            return False
    return actual == expected


def read_csv(path: Path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def evaluate() -> bool:
    gt = Path(r"C:\Users\Administrator\Desktop")
    if not gt.exists():
        return False
    for spec in STEP_SPECS:
        path = gt / spec["path"]
        if not path.exists() or path.stat().st_size <= 0:
            return False
        solid_count, bbox, volume = summarize_step(path)
        if solid_count != spec["solid_count"]:
            return False
        if any(abs(float(a) - float(b)) > BBOX_TOL for a, b in zip(bbox, spec["bbox"])):
            return False
        if abs(volume - float(spec["volume"])) / max(1.0, abs(float(spec["volume"]))) > VOLUME_REL_TOL:
            return False
    for spec in JSON_SPECS:
        path = gt / spec["path"]
        if not path.exists() or path.stat().st_size <= 0:
            return False
        if not json_matches(json.loads(path.read_text(encoding="utf-8")), spec["expected"]):
            return False
    for spec in CSV_SPECS:
        path = gt / spec["path"]
        if not path.exists() or path.stat().st_size <= 0 or read_csv(path) != spec["expected"]:
            return False
    for spec in TEXT_SPECS:
        path = gt / spec["path"]
        if not path.exists() or path.read_text(encoding="utf-8") != spec["expected"]:
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
    raise SystemExit(0)
