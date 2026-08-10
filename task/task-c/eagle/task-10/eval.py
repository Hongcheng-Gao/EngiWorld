from __future__ import annotations

import math
import xml.etree.ElementTree as ET
from pathlib import Path


TASK_ID = "c-eagle-task-10-ubuntu"
EVAL_DIR = Path(__file__).resolve().parent
INIT_FILE = next(
    (path for path in (EVAL_DIR / "qfn_board.brd", EVAL_DIR / "init_file" / "qfn_board.brd") if path.exists()),
    EVAL_DIR / "qfn_board.brd",
)
TARGET_PADS = ("1", "3", "5", "7")
PAD_TOL = 0.8
VIA_TOL = 1e-3


def _sig(elem: ET.Element) -> tuple[tuple[str, str], ...]:
    return tuple(sorted(elem.attrib.items()))


def _element_position(root: ET.Element, name: str) -> tuple[float, float]:
    el = root.find(f".//elements/element[@name='{name}']")
    if el is None:
        raise ValueError(f"missing element {name}")
    return float(el.get("x", "0")), float(el.get("y", "0"))


def _pad_centers(root: ET.Element) -> dict[str, tuple[float, float]]:
    pkg = root.find(".//packages/package[@name='QFN8']")
    if pkg is None:
        raise ValueError("missing QFN8 package")
    ux, uy = _element_position(root, "U1")
    pads: dict[str, tuple[float, float]] = {}
    for smd in pkg.findall("smd"):
        name = smd.get("name")
        if not name:
            continue
        pads[name] = (ux + float(smd.get("x", "0")), uy + float(smd.get("y", "0")))
    return pads


def _nearest_pad(point: tuple[float, float], pads: dict[str, tuple[float, float]]) -> tuple[str, float]:
    best_name = ""
    best_dist = float("inf")
    px, py = point
    for name, (x, y) in pads.items():
        dist = math.hypot(px - x, py - y)
        if dist < best_dist:
            best_name = name
            best_dist = dist
    return best_name, best_dist


def _nearest_point(
    point: tuple[float, float],
    points: dict[tuple[float, float], str],
) -> tuple[str, float]:
    best_name = ""
    best_dist = float("inf")
    px, py = point
    for (x, y), name in points.items():
        dist = math.hypot(px - x, py - y)
        if dist < best_dist:
            best_name = name
            best_dist = dist
    return best_name, best_dist


def _wire_match(
    wire: ET.Element,
    pads: dict[str, tuple[float, float]],
    vias: dict[tuple[float, float], str],
) -> tuple[str, str] | None:
    p1 = (float(wire.get("x1", "nan")), float(wire.get("y1", "nan")))
    p2 = (float(wire.get("x2", "nan")), float(wire.get("y2", "nan")))
    candidates = []
    for near, far in ((p1, p2), (p2, p1)):
        pad, pad_dist = _nearest_pad(near, pads)
        via_name, via_dist = _nearest_point(far, vias)
        if pad in TARGET_PADS and pad_dist <= PAD_TOL and via_dist <= VIA_TOL:
            candidates.append((pad, via_name))
    if len(candidates) != 1:
        return None
    return candidates[0]


def evaluate(submission_dir: str) -> bool:
    sub = Path(submission_dir).resolve()
    target = None
    for name in ("fanout.brd", "answer.brd"):
        p = sub / name
        if p.exists():
            target = p
            break
    if target is None or not INIT_FILE.exists():
        return False

    try:
        starter = ET.parse(INIT_FILE).getroot()
        result = ET.parse(target).getroot()
    except Exception:
        return False

    if not any(
        el.get("name") == "U1" and el.get("package") == "QFN8"
        for el in result.findall(".//element")
    ):
        return False

    if len(result.findall(".//element")) != len(starter.findall(".//element")):
        return False

    orig_wire_sigs = {_sig(node) for node in starter.findall(".//wire")}
    orig_via_sigs = {_sig(node) for node in starter.findall(".//via")}
    added_wires = [node for node in result.findall(".//wire") if _sig(node) not in orig_wire_sigs]
    added_vias = [node for node in result.findall(".//via") if _sig(node) not in orig_via_sigs]
    if len(added_wires) != 4 or len(added_vias) != 4:
        return False

    pads = _pad_centers(result)
    via_points: dict[tuple[float, float], str] = {}
    for via in added_vias:
        point = (float(via.get("x", "nan")), float(via.get("y", "nan")))
        via_points[point] = via.get("id") or via.get("name") or f"{point[0]},{point[1]}"

    used_pads: set[str] = set()
    used_vias: set[str] = set()
    for wire in added_wires:
        match = _wire_match(wire, pads, via_points)
        if match is None:
            return False
        pad, via_name = match
        if pad in used_pads or via_name in used_vias:
            return False
        used_pads.add(pad)
        used_vias.add(via_name)

    return used_pads == set(TARGET_PADS) and len(used_vias) == 4


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 2:
        print("usage: python eval.py SUBMISSION_DIR", file=sys.stderr)
        sys.exit(2)
    submission_dir = sys.argv[1] if len(sys.argv) == 2 else Path(__file__).resolve().parent
    print("True" if evaluate(submission_dir) else "False")
