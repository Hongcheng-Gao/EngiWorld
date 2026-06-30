from __future__ import annotations

import os
import re
import sys
from pathlib import Path


DESKTOP = Path("/home/user/Desktop")
TASK_ID = "kicad-7"

EXPECTED_LABELS = {"A1", "A2", "B1", "B2", "B3", "B4"}
EXPECTED_FRAMES = {
    "a1": (10.0, 10.0, 50.0, 50.0),
    "a2": (53.0, 10.0, 93.0, 50.0),
    "b1": (10.0, 60.0, 50.0, 100.0),
    "b2": (53.0, 60.0, 93.0, 100.0),
    "b3": (96.0, 10.0, 136.0, 50.0),
    "b4": (96.0, 60.0, 136.0, 100.0),
}
EXPECTED_OUTER = (0.0, 0.0, 146.0, 110.0)
EXPECTED_VSCORE = [
    ("x", 50.0, 10.0, 100.0),
    ("x", 93.0, 10.0, 100.0),
    ("y", 55.0, 10.0, 136.0),
]
EXPECTED_FID = {"FID1": (5.0, 5.0), "FID2": (141.0, 5.0), "FID3": (5.0, 105.0)}
EXPECTED_TOOL = {"TOOL1": (5.0, 55.0), "TOOL2": (141.0, 55.0), "TOOL3": (73.0, 5.0), "TOOL4": (73.0, 105.0)}
EXPECTED_FOOTPRINTS = {
    "UA1": (25.0, 25.0), "UA2": (35.0, 25.0), "UA3": (45.0, 25.0),
    "UA1_2": (68.0, 25.0), "UA2_2": (78.0, 25.0), "UA3_2": (88.0, 25.0),
    "UB1": (25.0, 75.0), "UB2": (35.0, 75.0), "UB3": (45.0, 75.0), "UB4": (30.0, 90.0),
    "UB1_2": (68.0, 75.0), "UB2_2": (78.0, 75.0), "UB3_2": (88.0, 75.0), "UB4_2": (73.0, 90.0),
    "UB1_3": (111.0, 25.0), "UB2_3": (121.0, 25.0), "UB3_3": (131.0, 25.0), "UB4_3": (116.0, 40.0),
    "UB1_4": (111.0, 75.0), "UB2_4": (121.0, 75.0), "UB3_4": (131.0, 75.0), "UB4_4": (116.0, 90.0),
}


def _load(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _find_all(pattern: str, text: str):
    return re.finditer(pattern, text, flags=re.M)


def _label_positions(text: str):
    found = set()
    for m in re.finditer(r'\(gr_text\s+"([^"]+)"\s+\(at\s+([-.0-9]+)\s+([-.0-9]+)\)\s+\(layer\s+"F\.Silkscreen"\)', text):
        label = m.group(1)
        if label in EXPECTED_LABELS:
            found.add(label)
    return found


def _frame_bbox(text: str, prefix: str):
    coords = []
    for side in ("top", "right", "bottom", "left"):
        m = re.search(rf'\(gr_line\s+\(start\s+([-.0-9]+)\s+([-.0-9]+)\)\s+\(end\s+([-.0-9]+)\s+([-.0-9]+)\)\s+\(layer\s+"Edge\.Cuts"\)\s+\(width\s+0\.05\)\s+\(uuid\s+"{prefix}-{side}"\)\)', text)
        if not m:
            return None
        coords.extend([float(m.group(1)), float(m.group(2)), float(m.group(3)), float(m.group(4))])
    xs = coords[0::2]
    ys = coords[1::2]
    return min(xs), min(ys), max(xs), max(ys)


def _fp_positions(text: str):
    found = {}
    for m in re.finditer(r'\(footprint\s+"[^"]+"\s+\(layer\s+"F\.Cu"\)\s+\(uuid\s+"[^"]+"\)\s+\(at\s+([-.0-9]+)\s+([-.0-9]+)\)\s+\(property\s+"Reference"\s+"([^"]+)"', text):
        found[m.group(3)] = (float(m.group(1)), float(m.group(2)))
    return found


def _point_ok(actual, expected, tol=0.01):
    return abs(actual[0] - expected[0]) <= tol and abs(actual[1] - expected[1]) <= tol


def _bbox_ok(actual, expected, tol=0.01):
    return all(abs(a - e) <= tol for a, e in zip(actual, expected))


def _vscore_ok(text: str):
    seen = set()
    for m in re.finditer(r'\(gr_line\s+\(start\s+([-.0-9]+)\s+([-.0-9]+)\)\s+\(end\s+([-.0-9]+)\s+([-.0-9]+)\)\s+\(layer\s+"Dwgs\.User"\)\s+\(width\s+0\.12\)\s+\(uuid\s+"([^"]+)"\)\)', text):
        x1, y1, x2, y2 = map(float, m.group(1, 2, 3, 4))
        if abs(x1 - x2) < 1e-6:
            seen.add(("x", round(x1, 3), round(min(y1, y2), 3), round(max(y1, y2), 3)))
        elif abs(y1 - y2) < 1e-6:
            seen.add(("y", round(y1, 3), round(min(x1, x2), 3), round(max(x1, x2), 3)))
    expected = {(kind, round(axis, 3), round(a, 3), round(b, 3)) for kind, axis, a, b in EXPECTED_VSCORE}
    return expected.issubset(seen)


def evaluate(path: str):
    out = []
    text = _load(Path(path))
    out.append(("file_exists", Path(path).exists()))
    out.append(("outer_frame", _bbox_ok(_frame_bbox(text, "pan-outer"), EXPECTED_OUTER)))
    out.append(("labels", _label_positions(text) == EXPECTED_LABELS))
    for key, bbox in EXPECTED_FRAMES.items():
        out.append((f"frame_{key}", _bbox_ok(_frame_bbox(text, key), bbox)))
    out.append(("vscore_guides", _vscore_ok(text)))
    fps = _fp_positions(text)
    for ref, pos in EXPECTED_FOOTPRINTS.items():
        out.append((f"fp_{ref}", _point_ok(fps.get(ref, (9999.0, 9999.0)), pos)))
    for ref, pos in EXPECTED_FID.items():
        out.append((f"fid_{ref}", _point_ok(fps.get(ref, (9999.0, 9999.0)), pos)))
    for ref, pos in EXPECTED_TOOL.items():
        out.append((f"tool_{ref}", _point_ok(fps.get(ref, (9999.0, 9999.0)), pos)))
    passed = all(v for _, v in out)
    return passed, out


def eval_outputs(output_dir: str = "."):
    path = os.path.join(output_dir, "panel.kicad_pcb")
    passed, checks = evaluate(path)
    return {
        "task_id": TASK_ID,
        "passed": passed,
        "score": 1.0 if passed else 0.0,
        "total": len(checks),
        "error": None,
        "checks": [{"name": n, "passed": b, "expected": True, "actual": b} for n, b in checks],
        "summary": f"{sum(b for _, b in checks)}/{len(checks)}",
    }


if __name__ == "__main__":
    passed, _ = evaluate(sys.argv[1] if len(sys.argv) > 1 else "panel.kicad_pcb")
    print("True" if passed else "False")
