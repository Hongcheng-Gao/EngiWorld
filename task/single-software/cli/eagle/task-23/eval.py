from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path


EXPECTED_PREFIXES = ["A1", "A2", "A3", "B1", "B2", "B3"]
SPACING_X = 15.0
SPACING_Y = 15.0


def _parse_float(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _element_key(e: ET.Element) -> tuple[str, str, str]:
    return (
        e.get("library") or "",
        e.get("package") or "",
        e.get("value") or "",
    )


def _wire_key(w: ET.Element) -> tuple[float, float, float, float, float, str]:
    def f(name: str) -> float:
        raw = w.get(name)
        if raw is None:
            return float("nan")
        return float(raw)

    return (f("x1"), f("y1"), f("x2"), f("y2"), f("width"), w.get("layer") or "")


def evaluate(submission_dir: str) -> bool:
    sub = Path(submission_dir).resolve()
    target = None
    for name in ("coin_panel.brd",):
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

    eval_dir = Path(__file__).resolve().parent
    starter_path = next(
        (path for path in (eval_dir / "coin.brd", eval_dir / "init_file" / "coin.brd") if path.exists()),
        eval_dir / "coin.brd",
    )
    orig = ET.parse(starter_path).getroot()
    orig_elems = list(orig.findall(".//element"))
    board = root.find(".//board")
    if board is None:
        return False
    elements = list(board.findall(".//element"))
    if len(elements) != 6 * len(orig_elems):
        return False

    groups: dict[str, list[ET.Element]] = defaultdict(list)
    for e in elements:
        name = e.get("name") or ""
        m = re.match(r"^([A-Z]\d+)_([^_]+)$", name)
        if not m:
            return False
        groups[m.group(1)].append(e)
    if sorted(groups) != EXPECTED_PREFIXES:
        return False
    if any(len(groups[p]) != len(orig_elems) for p in EXPECTED_PREFIXES):
        return False
    if len({e.get("name") for e in elements}) != len(elements):
        return False

    orig_by_key: dict[tuple[str, str, str], list[ET.Element]] = defaultdict(list)
    for e in orig_elems:
        orig_by_key[_element_key(e)].append(e)

    for prefix in EXPECTED_PREFIXES:
        row = 0 if prefix.startswith("A") else 1
        col = int(prefix[1]) - 1
        dx_expected = col * SPACING_X
        dy_expected = row * SPACING_Y
        for e in groups[prefix]:
            base = e.get("name", "").split("_", 1)[1]
            # Match against original by library/package/value and original refdes.
            candidates = [o for o in orig_elems if o.get("name") == base]
            if len(candidates) != 1:
                return False
            orig_e = candidates[0]
            x = _parse_float(e.get("x"))
            y = _parse_float(e.get("y"))
            ox = _parse_float(orig_e.get("x"))
            oy = _parse_float(orig_e.get("y"))
            if None in (x, y, ox, oy):
                return False
            if abs((x - ox) - dx_expected) > 1e-6:
                return False
            if abs((y - oy) - dy_expected) > 1e-6:
                return False
            for attr in ("library", "package", "value", "rot"):
                if (e.get(attr) or "") != (orig_e.get(attr) or ""):
                    return False

    plain = board.find("plain")
    if plain is None:
        return False
    wires = list(plain.findall("wire"))
    if len(wires) != 4:
        return False
    expected_outline = {
        (0.0, 0.0, 40.0, 0.0, 0.1, "20"),
        (40.0, 0.0, 40.0, 25.0, 0.1, "20"),
        (40.0, 25.0, 0.0, 25.0, 0.1, "20"),
        (0.0, 25.0, 0.0, 0.0, 0.1, "20"),
    }
    got_wires = Counter(_wire_key(w) for w in wires)
    if got_wires != Counter(expected_outline):
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
