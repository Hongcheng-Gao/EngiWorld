from __future__ import annotations

import os
import sys
from collections import defaultdict
from pathlib import Path

TASK_ID = "kicad-37"
RF_REFS = ["U1", "U2", "U3", "U4", "U5", "U6", "U7", "U8"]
MIN_SPACING_MM = 6.0
Y_TOLERANCE_MM = 0.5


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
            continue
        if ch == "(":
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


def extract_footprints(pcb_text: str):
    root = _parse_atoms(pcb_text)
    footprints = {}
    for fp in _find_all(root, "footprint"):
        ref = None
        x = y = rot = 0.0
        pad_nets = {}
        for child in fp:
            if not isinstance(child, list) or not child:
                continue
            if child[0] == "fp_text" and len(child) >= 3 and child[1] == "reference":
                ref = child[2]
            elif child[0] == "at" and len(child) >= 3:
                try:
                    x = float(child[1])
                    y = float(child[2])
                    rot = float(child[3]) if len(child) >= 4 else 0.0
                except (TypeError, ValueError):
                    pass
            elif child[0] == "pad" and len(child) >= 4:
                pad_name = child[1]
                net_name = None
                for item in child[4:]:
                    if isinstance(item, list) and item and item[0] == "net" and len(item) >= 3:
                        net_name = item[2]
                        break
                if net_name is not None:
                    pad_nets[pad_name] = net_name
        if ref:
            footprints[ref] = {"x": x, "y": y, "rotation": rot, "pads": pad_nets}
    return footprints


def _chain_order_by_nets(footprints: dict[str, dict]) -> list[str] | None:
    net_to_refs = defaultdict(set)
    for ref in RF_REFS:
        for net in footprints.get(ref, {}).get("pads", {}).values():
            net_to_refs[net].add(ref)

    graph = {ref: set() for ref in RF_REFS}
    for refs in net_to_refs.values():
        if len(refs) != 2:
            continue
        a, b = sorted(refs)
        graph[a].add(b)
        graph[b].add(a)

    degree_one = [ref for ref in RF_REFS if len(graph[ref]) == 1]
    if len(degree_one) != 2:
        return None
    start = next((ref for ref in degree_one if "RF_IN" in footprints[ref]["pads"].values()), degree_one[0])

    order = [start]
    prev = None
    cur = start
    while True:
        nxt = [n for n in graph[cur] if n != prev]
        if not nxt:
            break
        if len(nxt) != 1:
            return None
        nxt = nxt[0]
        if nxt in order:
            return None
        order.append(nxt)
        prev, cur = cur, nxt
    return order if len(order) == len(RF_REFS) else None


def _summary(passed: bool, checks: int) -> str:
    return f"{passed} ({checks} checks)"


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

    fps = extract_footprints(text)
    checks = []

    missing = [ref for ref in RF_REFS if ref not in fps]
    checks.append(("all_8_rf_components_present", len(missing) == 0, 0, len(missing), str(missing) if missing else "all present"))
    if missing:
        result["checks"] = checks
        result["total"] = len(checks)
        result["passed"] = False
        return result

    order = _chain_order_by_nets(fps)
    checks.append(("rf_chain_derivable_from_nets", order is not None, "unique chain from RF_IN to RF_OUT", order, None))
    if order is None:
        result["checks"] = checks
        result["total"] = len(checks)
        result["passed"] = False
        return result

    positions = [fps[ref] for ref in order]
    ys = [p["y"] for p in positions]
    mean_y = sum(ys) / len(ys)
    max_y_dev = max(abs(y - mean_y) for y in ys)
    checks.append(("all_components_on_horizontal_line", max_y_dev <= Y_TOLERANCE_MM, f"max Y deviation <= {Y_TOLERANCE_MM}mm", round(max_y_dev, 3), None))

    xs = [p["x"] for p in positions]
    checks.append(("x_values_strictly_increasing", all(xs[i] < xs[i + 1] for i in range(len(xs) - 1)), "strictly increasing X in inferred chain order", [round(x, 2) for x in xs], None))

    spacings = [xs[i + 1] - xs[i] for i in range(len(xs) - 1)]
    checks.append(("adjacent_spacing_at_least_6mm", min(spacings) >= MIN_SPACING_MM, f">={MIN_SPACING_MM}mm", round(min(spacings), 3), str([round(s, 2) for s in spacings])))

    rots = [p["rotation"] % 360 for p in positions]
    bad_rots = [rot for rot in rots if min(rot % 90, 90 - (rot % 90)) > 1.0]
    checks.append(("rotations_multiples_of_90", len(bad_rots) == 0, "all rotations multiples of 90 deg", [round(rot, 1) for rot in rots], str(bad_rots) if bad_rots else "all ok"))

    rot_180 = [ref for ref in order if abs(fps[ref]["rotation"] % 360 - 180) < 1.0]
    checks.append(("no_component_rotated_180", len(rot_180) == 0, 0, len(rot_180), str(rot_180) if rot_180 else "no 180 deg rotations"))

    checks.append(("x_span_within_board", (max(xs) - min(xs)) >= MIN_SPACING_MM * 7 and max(xs) <= 300, f">={MIN_SPACING_MM * 7:.0f}mm and <=300mm", round(max(xs) - min(xs), 2), None))
    far = [ref for ref, p in zip(order, positions) if abs(p["y"] - mean_y) > 3.0]
    checks.append(("no_component_far_from_line", len(far) == 0, 0, len(far), str(far) if far else "all within 3mm of mean Y"))

    passed = all(item[1] for item in checks)
    result["checks"] = checks
    result["total"] = len(checks)
    result["passed"] = passed
    result["score"] = 1.0 if passed else 0.0
    return result


def eval_outputs(output_dir: str = ".") -> dict:
    path = os.path.join(output_dir, "answer.kicad_pcb")
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
        "summary": _summary(r["passed"], r["total"]),
    }


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else str(Path("/home/user/Desktop") / "answer.kicad_pcb")
    print(evaluate(path)["passed"])
