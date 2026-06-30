from __future__ import annotations

import os
import sys
from pathlib import Path

TASK_ID = "kicad-40"
POSITION_TOLERANCE = 0.1
BOARD_W = 22.86
BOARD_H = 50.80
OTHER_COMPONENTS_INITIAL = {
    "U1": (11.43, 30.0, 0),
    "C1": (5.0, 15.0, 0),
    "C2": (8.0, 15.0, 0),
    "R1": (11.0, 15.0, 0),
    "R2": (14.0, 15.0, 0),
    "J2": (20.32, 22.86, 270),
}


def _parse_atoms(text: str):
    tokens = []
    cur = []
    in_str = False
    esc = False
    for ch in text:
        if in_str:
            if esc:
                cur.append(ch)
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                tokens.append("".join(cur))
                cur = []
                in_str = False
            else:
                cur.append(ch)
            continue
        if ch == '"':
            in_str = True
        elif ch == "(":
            tokens.append("(")
        elif ch == ")":
            if cur:
                tokens.append("".join(cur))
                cur = []
            tokens.append(")")
        elif ch.isspace():
            if cur:
                tokens.append("".join(cur))
                cur = []
        else:
            cur.append(ch)
    if cur:
        tokens.append("".join(cur))
    stack = [[]]
    for tok in tokens:
        if tok == "(":
            node = []
            stack[-1].append(node)
            stack.append(node)
        elif tok == ")":
            stack.pop()
        else:
            stack[-1].append(tok)
    return stack[0]


def _find_all(node, name):
    found = []
    if isinstance(node, list):
        for child in node:
            if isinstance(child, list):
                if child and child[0] == name:
                    found.append(child)
                found.extend(_find_all(child, name))
    return found


def _fp_at(fp):
    for child in fp:
        if isinstance(child, list) and child and child[0] == "at" and len(child) >= 3:
            try:
                return float(child[1]), float(child[2]), float(child[3]) if len(child) >= 4 else 0.0
            except (TypeError, ValueError):
                return 0.0, 0.0, 0.0
    return 0.0, 0.0, 0.0


def extract_footprint_positions(pcb_text: str) -> dict[str, dict]:
    root = _parse_atoms(pcb_text)
    fps = {}
    for fp in _find_all(root, "footprint"):
        ref = None
        for child in fp:
            if isinstance(child, list) and child and child[0] == "fp_text" and len(child) >= 3 and child[1] == "reference":
                ref = child[2]
                break
        if ref:
            x, y, rot = _fp_at(fp)
            fps[ref] = {"x": x, "y": y, "rotation": rot}
    return fps


def _board_bounds(root):
    for item in root:
        if isinstance(item, list) and item and item[0] == "gr_rect":
            start = end = None
            for child in item:
                if isinstance(child, list) and child:
                    if child[0] == "start" and len(child) >= 3:
                        start = (float(child[1]), float(child[2]))
                    elif child[0] == "end" and len(child) >= 3:
                        end = (float(child[1]), float(child[2]))
            if start and end:
                return start[0], start[1], end[0], end[1]
    return 0.0, 0.0, BOARD_W, BOARD_H


def evaluate(path: str):
    result = {"task_id": TASK_ID, "checks": [], "passed": False, "score": 0.0, "total": 0, "error": None}
    if not os.path.exists(path):
        result["error"] = f"output file not found at {path}"
        return result
    try:
        text = Path(path).read_text(encoding="utf-8")
    except Exception as e:
        result["error"] = f"read error: {e}"
        return result

    root = _parse_atoms(text)
    fps = extract_footprint_positions(text)
    checks = []

    checks.append(("usbc_j1_present", "J1" in fps, "J1 in PCB", str(list(fps.keys())), None))
    if "J1" not in fps:
        result["checks"] = checks
        result["total"] = len(checks)
        return result

    bounds = _board_bounds(root)
    board_w = bounds[2] - bounds[0]
    board_h = bounds[3] - bounds[1]
    edge_alignment_possible = abs(board_w - BOARD_W) <= 0.5 and abs(board_h - BOARD_H) <= 0.5
    checks.append(("board_outline_matches_feather", edge_alignment_possible, f"{BOARD_W} x {BOARD_H}", (round(board_w, 3), round(board_h, 3)), None))

    j1 = fps["J1"]
    actual_rot = j1["rotation"] % 360
    target_x = bounds[2]
    target_y = bounds[3]
    checks.append(("j1_centered_on_board_edge", abs(j1["x"] - target_x) <= POSITION_TOLERANCE and abs(j1["y"] - target_y) <= POSITION_TOLERANCE, (round(target_x, 3), round(target_y, 3)), (round(j1["x"], 3), round(j1["y"], 3)), None))
    checks.append(("j1_rotation_face_outward", abs(actual_rot - 180.0) <= 1.0, 180.0, round(actual_rot, 1), None))
    checks.append(("j1_rotation_multiple_of_90", min(actual_rot % 90, 90 - (actual_rot % 90)) <= 1.0, "multiple of 90 deg", round(actual_rot, 1), None))

    moved_refs = []
    for ref, (ex, ey, _) in OTHER_COMPONENTS_INITIAL.items():
        fp = fps.get(ref)
        if fp is None:
            moved_refs.append(f"{ref}:MISSING")
            continue
        if abs(fp["x"] - ex) > POSITION_TOLERANCE or abs(fp["y"] - ey) > POSITION_TOLERANCE:
            moved_refs.append(f"{ref}:moved")
    checks.append(("other_components_unchanged", len(moved_refs) == 0, 0, len(moved_refs), str(moved_refs[:3]) if moved_refs else "all unchanged"))
    checks.append(("component_count_unchanged", len(fps) == 7, 7, len(fps), None))

    result["checks"] = checks
    result["total"] = len(checks)
    result["passed"] = all(item[1] for item in checks)
    result["score"] = 1.0 if result["passed"] else 0.0
    return result


def eval_outputs(output_dir: str = ".") -> dict:
    path = os.path.join(output_dir, "design.kicad_pcb")
    r = evaluate(path)
    return {
        "task_id": r["task_id"],
        "score": r["score"],
        "passed": r["passed"],
        "total": r["total"],
        "error": r["error"],
        "checks": [
            {"name": name, "passed": passed, "expected": expected, "actual": actual, "tolerance": None, "note": note}
            for name, passed, expected, actual, note in r["checks"]
        ],
        "summary": f"{r['passed']} ({r['total']} checks)",
    }


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "design.kicad_pcb"
    print(evaluate(path)["passed"])
