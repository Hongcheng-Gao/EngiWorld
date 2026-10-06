from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path


EXPECTED_PADS = {
    "1": (-2.35, 0.25, 0.6, 0.25),
    "2": (-2.35, -0.25, 0.6, 0.25),
    "3": (-0.25, -2.35, 0.25, 0.6),
    "4": (0.25, -2.35, 0.25, 0.6),
    "5": (2.35, -0.25, 0.6, 0.25),
    "6": (2.35, 0.25, 0.6, 0.25),
    "7": (0.25, 2.35, 0.25, 0.6),
    "8": (-0.25, 2.35, 0.25, 0.6),
}


def _parse_float(v: str | None) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except ValueError:
        return None


def evaluate(submission_dir: str) -> bool:
    sub = Path(submission_dir).resolve()
    target = None
    for name in ("qfn8.lbr",):
        cand = sub / name
        if cand.exists():
            target = cand
            break
    if target is None:
        return False

    try:
        root = ET.parse(target).getroot()
    except Exception:
        return False

    packages = list(root.iter("package"))
    if len(packages) != 1:
        return False
    pkg = packages[0]
    if (pkg.get("name") or "") != "QFN-8-0.5":
        return False

    smds = list(pkg.iter("smd"))
    if len(smds) != 8:
        return False
    if {s.get("name") for s in smds} != set(EXPECTED_PADS):
        return False
    center_x = sum(_parse_float(s.get("x")) or 0.0 for s in smds) / len(smds)
    center_y = sum(_parse_float(s.get("y")) or 0.0 for s in smds) / len(smds)
    for smd in smds:
        name = smd.get("name") or ""
        x = _parse_float(smd.get("x"))
        y = _parse_float(smd.get("y"))
        dx = _parse_float(smd.get("dx"))
        dy = _parse_float(smd.get("dy"))
        if None in (x, y, dx, dy):
            return False
        ex, ey, edx, edy = EXPECTED_PADS[name]
        if abs((x - center_x) - ex) > 1e-6 or abs((y - center_y) - ey) > 1e-6:
            return False
        if abs(dx - edx) > 1e-6 or abs(dy - edy) > 1e-6:
            return False

    wires21 = [c for c in pkg if c.tag == "wire" and c.get("layer") == "21"]
    if len(wires21) < 4:
        return False
    markers = [c for c in pkg if c.tag == "circle" and c.get("layer") == "21"]
    if not markers:
        return False
    texts = {t.text or "" for t in pkg.iter("text")}
    if ">NAME" not in texts or ">VALUE" not in texts:
        return False
    if not any(t.get("layer") == "25" for t in pkg.iter("text")):
        return False
    if not any(t.get("layer") == "27" for t in pkg.iter("text")):
        return False
    return True


def main(argv: list[str]) -> int:
    if len(argv) > 2:
        print("usage: python eval.py SUBMISSION_DIR", file=sys.stderr)
        return 2
    submission_dir = argv[1] if len(argv) == 2 else Path(__file__).resolve().parent
    ok = evaluate(submission_dir)
    print("True" if ok else "False")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
