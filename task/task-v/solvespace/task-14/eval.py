import argparse
import csv
import json
from pathlib import Path
import ezdxf

DXF_SPECS = [{'path': 'final_ss_gui_14.dxf', 'summary': {'counts': {'LWPOLYLINE': 1, 'CIRCLE': 2, 'LINE': 1, 'TEXT': 1}, 'layers': ['AUX', 'CENTER', 'HOLE', 'OUTER'], 'texts': ['task-14']}}]
JSON_SPECS = []
CSV_SPECS = []
TEXT_SPECS = []
NUM_TOL = 0.05

def _cmp(actual, expected):
    if isinstance(expected, dict):
        return isinstance(actual, dict) and all(k in actual and _cmp(actual[k], v) for k, v in expected.items())
    if isinstance(expected, list):
        return isinstance(actual, list) and len(actual) == len(expected) and all(_cmp(a, e) for a, e in zip(actual, expected))
    if isinstance(expected, (int, float)):
        try:
            return abs(float(actual) - float(expected)) <= NUM_TOL
        except Exception:
            return False
    return actual == expected

def _summarize_dxf(path):
    doc = ezdxf.readfile(path)
    counts = {}
    layers = set()
    texts = []
    for entity in doc.modelspace():
        dxftype = entity.dxftype()
        counts[dxftype] = counts.get(dxftype, 0) + 1
        if hasattr(entity.dxf, "layer"):
            layers.add(entity.dxf.layer)
        if dxftype == "TEXT":
            texts.append(entity.dxf.text)
    return {"counts": counts, "layers": sorted(layers), "texts": sorted(texts)}

OUTPUT_ROOT = Path('/home/user/Desktop')

def evaluate():
    gt = OUTPUT_ROOT
    if not gt.exists():
        return False
    for spec in DXF_SPECS:
        path = gt / spec["path"]
        if not path.exists() or path.stat().st_size <= 0:
            return False
        if _summarize_dxf(path) != spec["summary"]:
            return False
    for spec in JSON_SPECS:
        path = gt / spec["path"]
        if not path.exists() or path.stat().st_size <= 0:
            return False
        if not _cmp(json.loads(path.read_text(encoding="utf-8")), spec["expected"]):
            return False
    for spec in CSV_SPECS:
        path = gt / spec["path"]
        if not path.exists() or path.stat().st_size <= 0:
            return False
        with open(path, newline="", encoding="utf-8") as handle:
            if list(csv.DictReader(handle)) != spec["expected"]:
                return False
    for spec in TEXT_SPECS:
        path = gt / spec["path"]
        if not path.exists() or path.stat().st_size < spec["min_size"]:
            return False
    return True

if __name__ == "__main__":
    try:
        ok = evaluate()
    except Exception:
        ok = False
    print("True" if ok else "False")
