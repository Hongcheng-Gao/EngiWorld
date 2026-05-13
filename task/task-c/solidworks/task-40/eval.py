from __future__ import annotations

import re
from pathlib import Path

import cadquery as cq


OUTPUT_ROOT = Path(r"C:\Users\User\Desktop")
STEP_NAME = "cli_040_ap242_quality_out.step"
REPORT_NAME = "cli_040_quality_report.txt"
TOL = 0.08


PART_BBOXES = [
    (-25.0, 25.0, -20.0, 20.0, 0.0, 20.0),
    (35.0, 75.0, -17.5, 17.5, 0.0, 18.0),
    (85.0, 115.0, -12.5, 12.5, 0.0, 16.0),
    (121.0, 149.0, -11.0, 11.0, 0.0, 14.0),
    (156.0, 180.0, -10.0, 10.0, 0.0, 12.0),
    (187.0, 207.0, -8.0, 8.0, 0.0, 10.0),
]
ASSEMBLY_BBOX = (-25.0, 207.0, -20.0, 20.0, 0.0, 20.0)


def load_solids(path: Path):
    if not path.exists() or path.stat().st_size <= 0:
        raise FileNotFoundError(path)
    solids = cq.importers.importStep(str(path)).solids().vals()
    if len(solids) != 6 or any(not solid.isValid() for solid in solids):
        raise ValueError("expected six valid solids")
    return solids


def bbox_tuple(solid):
    bb = solid.BoundingBox()
    return (bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax)


def close_tuple(actual, expected) -> bool:
    return all(abs(float(a) - float(e)) <= TOL for a, e in zip(actual, expected))


def check_geometry(solids) -> bool:
    unmatched = [bbox_tuple(solid) for solid in solids]
    for expected in PART_BBOXES:
        match = None
        for actual in unmatched:
            if close_tuple(actual, expected):
                match = actual
                break
        if match is None:
            return False
        unmatched.remove(match)
    total_volume = sum(solid.Volume() for solid in solids)
    return abs(total_volume - 94784.0) <= 80.0


def report_has_numbers(text: str, values) -> bool:
    numbers = [float(value) for value in re.findall(r"-?\d+(?:\.\d+)?", text)]
    for expected in values:
        if not any(abs(number - expected) <= 0.1 for number in numbers):
            return False
    return True


def check_report(path: Path) -> bool:
    if not path.exists() or path.stat().st_size <= 0:
        return False
    text = path.read_text(encoding="utf-8", errors="ignore").lower()
    if "solid_count" not in text and "part count" not in text:
        return False
    if "6" not in text or "bbox" not in text:
        return False
    if "ap242" not in text or "millimeter" not in text:
        return False
    for bbox in PART_BBOXES:
        if not report_has_numbers(text, bbox):
            return False
    return report_has_numbers(text, ASSEMBLY_BBOX)


def evaluate() -> bool:
    solids = load_solids(OUTPUT_ROOT / STEP_NAME)
    return check_geometry(solids) and check_report(OUTPUT_ROOT / REPORT_NAME)


if __name__ == "__main__":
    try:
        print(True if evaluate() else False)
    except Exception:
        print(False)
