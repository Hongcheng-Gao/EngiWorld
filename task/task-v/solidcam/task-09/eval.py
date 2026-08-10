from __future__ import annotations

import math
import os
import re
from pathlib import Path

RULE = {'files': {'task-9.nc': {'terms': [['POCKET', 'ROUGH'], ['REST', 'CLEANUP']], 'min_tools': 2, 'min_motion': 24, 'tool_min_cut': {'1': 8, '2': 8}, 'z_values': [8.0], 'min_cut_groups': 4}}}
DEFAULT_TARGET = 'C:\\Users\\User\\Desktop'
TARGET = Path(os.environ.get("EVAL_TARGET_DIR", os.environ.get("OUTPUT_ROOT", DEFAULT_TARGET)))
TOL = 0.75

FORBIDDEN_EXTENSIONS = {".py", ".pyw", ".ipynb", ".sh", ".bash", ".zsh", ".bat", ".cmd", ".ps1", ".vbs", ".js", ".mjs", ".ts", ".rb", ".lua", ".tcl", ".ahk", ".scr"}


def check_no_gui_bypass(root: Path) -> bool:
    try:
        if not root.exists():
            return True
        for path in root.rglob("*"):
            if path.is_file() and path.name != "eval.py" and path.suffix.lower() in FORBIDDEN_EXTENSIONS:
                return False
    except Exception:
        return False
    return True


def close(a, b, tol=TOL):
    return abs(float(a) - float(b)) <= tol


def strip_code(line: str) -> str:
    line = re.sub(r"\([^)]*\)", " ", line)
    return line.split(";", 1)[0].upper()


def parse_nc(src: str):
    records = []
    state = {"x": None, "y": None, "z": None, "tool": None, "wcs": None, "motion": None}
    tools = []
    axes_seen = set()
    for index, raw in enumerate(src.splitlines()):
        code = strip_code(raw)
        if not code.strip():
            continue
        tool_match = re.search(r"\bT0*(\d+)\b", code)
        if tool_match:
            state["tool"] = int(tool_match.group(1))
            tools.append(state["tool"])
        for wcs in re.findall(r"\bG(5[4-9])\b", code):
            state["wcs"] = "G" + wcs
        g_codes = [int(value) for value in re.findall(r"\bG0*(\d+)\b", code)]
        if 80 in g_codes:
            state["motion"] = None
        explicit_motion = next((g for g in g_codes if g in {0, 1, 2, 3, 81, 82, 83, 84}), None)
        if explicit_motion is not None:
            state["motion"] = explicit_motion
        explicit = {}
        for axis in "XYZABCIJKRF":
            match = re.search(rf"\b{axis}([+-]?\d+(?:\.\d+)?)", code)
            if match:
                explicit[axis.lower()] = float(match.group(1))
                axes_seen.add(axis)
        if state["motion"] is None or not any(axis in explicit for axis in ("x", "y", "z", "a", "b", "c")):
            continue
        start = {axis: state[axis] for axis in ("x", "y", "z")}
        for axis in ("x", "y", "z"):
            if axis in explicit:
                state[axis] = explicit[axis]
        records.append({"index": index, "raw": raw.upper(), "code": state["motion"], "start": start, "end": {axis: state[axis] for axis in ("x", "y", "z")}, "explicit": explicit, "tool": state["tool"], "wcs": state["wcs"]})
    return records, tools, axes_seen


def xy_changed(record):
    s, e = record["start"], record["end"]
    return s["x"] is not None and s["y"] is not None and e["x"] is not None and e["y"] is not None and (not close(s["x"], e["x"], 1e-6) or not close(s["y"], e["y"], 1e-6))


def cut_records(records):
    return [record for record in records if record["code"] in {1, 2, 3} and xy_changed(record)]


def tool_order(tools):
    out = []
    for tool in tools:
        if tool not in out:
            out.append(tool)
    return out


def tool_for_ordinal(tools, ordinal):
    order = tool_order(tools)
    return order[int(ordinal) - 1] if 0 < int(ordinal) <= len(order) else None


def record_z(record):
    return record["end"]["z"]


def at_z(record, z, tol=TOL):
    return record_z(record) is not None and close(record_z(record), z, tol)


def cut_groups(records, z=None):
    groups, current = [], []
    last_index = None
    last_tool = last_wcs = None
    for record in records:
        qualifies = record["code"] in {1, 2, 3} and xy_changed(record) and (z is None or at_z(record, z))
        split = last_index is not None and (record["index"] > last_index + 2 or record["tool"] != last_tool or record["wcs"] != last_wcs)
        if not qualifies or split:
            if current:
                groups.append(current)
                current = []
        if qualifies:
            current.append(record)
            last_tool, last_wcs = record["tool"], record["wcs"]
        last_index = record["index"]
    if current:
        groups.append(current)
    return groups


def group_closed(group):
    if len(group) < 3:
        return False
    start = group[0]["start"]
    end = group[-1]["end"]
    if None in (start["x"], start["y"], end["x"], end["y"]):
        return False
    return close(start["x"], end["x"], 1.0) and close(start["y"], end["y"], 1.0)


def hole_visits(records, tools, rule):
    tool = tool_for_ordinal(tools, rule.get("tool", 1)) if rule.get("tool") else None
    cycle_codes = set(rule.get("cycle", []))
    visits = []
    for record in records:
        if tool is not None and record["tool"] != tool:
            continue
        e, s = record["end"], record["start"]
        if e["x"] is None or e["y"] is None or e["z"] is None or e["z"] > float(rule.get("z_max", 1e9)) + TOL:
            continue
        if cycle_codes:
            if record["code"] in cycle_codes:
                visits.append((e["x"], e["y"]))
        elif record["code"] in {81, 82, 83, 84}:
            visits.append((e["x"], e["y"]))
        elif record["code"] == 1 and s["x"] is not None and s["y"] is not None and s["z"] is not None and close(s["x"], e["x"]) and close(s["y"], e["y"]) and s["z"] - e["z"] > 0.2:
            visits.append((e["x"], e["y"]))
    return visits


def has_all_points(actual, expected):
    return all(any(close(x, ex) and close(y, ey) for x, y in actual) for ex, ey in expected)


def arc_centers(records):
    centers = []
    for record in records:
        if record["code"] not in {2, 3}:
            continue
        s = record["start"]
        ex = record["explicit"]
        if s["x"] is not None and s["y"] is not None and "i" in ex and "j" in ex:
            centers.append((s["x"] + ex["i"], s["y"] + ex["j"]))
    return centers


def circular_centers(records):
    centers = arc_centers(records)
    for group in cut_groups(records):
        if not group_closed(group):
            continue
        pts = [(r["end"]["x"], r["end"]["y"]) for r in group]
        if len(pts) < 6:
            continue
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
        radii = [math.hypot(x - cx, y - cy) for x, y in pts]
        if max(radii) - min(radii) <= 1.5:
            centers.append((cx, cy))
    return centers


def rect_contains(point, rect, margin=0.0):
    x, y = point
    x1, y1, x2, y2 = rect
    return min(x1, x2) - margin <= x <= max(x1, x2) + margin and min(y1, y2) - margin <= y <= max(y1, y2) + margin


def validate_file(path: Path, rule: dict) -> bool:
    if not path.exists() or path.stat().st_size <= 0:
        return False
    src = path.read_text(encoding="utf-8", errors="ignore").upper()
    code_src = "\n".join(strip_code(line) for line in src.splitlines())
    if "G21" not in code_src or "G90" not in code_src or "M30" not in code_src:
        return False
    records, tools, axes_seen = parse_nc(src)
    cuts = cut_records(records)
    if len(tool_order(tools)) < int(rule.get("min_tools", 1)) or len(records) < int(rule.get("min_motion", 1)):
        return False
    if sum(1 for record in records if record["code"] == 0) < int(rule.get("min_rapid", 0)):
        return False
    for group in rule.get("terms", []):
        if not any(str(term).upper() in src for term in group):
            return False
    if any(axis.upper() in axes_seen for axis in rule.get("forbid_axes", [])):
        return False
    for expected_z in rule.get("z_values", []):
        if not any(at_z(record, expected_z) for record in records):
            return False
    z_values = sorted({round(record_z(record), 3) for record in cuts if record_z(record) is not None})
    if len(z_values) < int(rule.get("min_z_levels", 0)):
        return False
    if "face_grid" in rule:
        item = rule["face_grid"]
        candidates = [record for record in cuts if "z" not in item or at_z(record, item["z"])]
        horizontal, vertical = set(), set()
        span = float(item.get("span", 20.0))
        for record in candidates:
            s, e = record["start"], record["end"]
            if abs(e["x"] - s["x"]) >= span and close(e["y"], s["y"], 0.2):
                horizontal.add(round((e["y"] + s["y"]) / 2, 1))
            if abs(e["y"] - s["y"]) >= span and close(e["x"], s["x"], 0.2):
                vertical.add(round((e["x"] + s["x"]) / 2, 1))
        if max(len(horizontal), len(vertical)) < int(item["min_tracks"]):
            return False
    if "closed" in rule:
        item = rule["closed"]
        groups = cut_groups(records, item.get("z"))
        if sum(group_closed(group) for group in groups) < int(item["min"]):
            return False
    if len(cut_groups(records)) < int(rule.get("min_cut_groups", 0)):
        return False
    for item in rule.get("hole_sets", []):
        if not has_all_points(hole_visits(records, tools, item), item["points"]):
            return False
    if "any_holes" in rule:
        item = rule["any_holes"]
        visits = hole_visits(records, tools, {"tool": item.get("tool"), "z_max": item.get("z_max", 1e9)})
        unique = []
        for point in visits:
            if not any(close(point[0], p[0]) and close(point[1], p[1]) for p in unique):
                unique.append(point)
        if len(unique) < int(item["min"]):
            return False
    all_visits = hole_visits(records, tools, {"z_max": 1e9})
    if any(any(close(x, fx) and close(y, fy) for x, y in all_visits) for fx, fy in rule.get("forbidden_holes", [])):
        return False
    if "circle_centers" in rule:
        item = rule["circle_centers"]
        centers = circular_centers(records)
        if not has_all_points(centers, item["points"]) or len(centers) < int(item["min"]):
            return False
    if sum(1 for record in records if record["code"] in {2, 3}) < int(rule.get("min_arcs", 0)):
        return False
    if "region" in rule:
        item = rule["region"]
        if sum(rect_contains((r["end"]["x"], r["end"]["y"]), item["rect"]) for r in cuts) < int(item["min"]):
            return False
    for item in rule.get("regions", []):
        if sum(rect_contains((r["end"]["x"], r["end"]["y"]), item["rect"]) for r in cuts) < int(item["min"]):
            return False
    for ordinal, minimum in rule.get("tool_min_cut", {}).items():
        tool = tool_for_ordinal(tools, int(ordinal))
        if tool is None or sum(record["tool"] == tool for record in cuts) < int(minimum):
            return False
    for ordinal, minimum in rule.get("tool_z_levels", {}).items():
        tool = tool_for_ordinal(tools, int(ordinal))
        levels = {round(record_z(record), 3) for record in cuts if record["tool"] == tool and record_z(record) is not None}
        if len(levels) < int(minimum):
            return False
    if "z_levels" in rule:
        item = rule["z_levels"]
        levels = sorted({round(record_z(r), 3) for r in cuts if record_z(r) is not None and record_z(r) >= float(item["floor"]) - TOL})
        if len(levels) < int(item["min"]) or not any(close(level, item["floor"]) for level in levels):
            return False
        if any(b - a > float(item["max_step"]) + TOL for a, b in zip(levels, levels[1:])):
            return False
    for wcs, minimum in rule.get("wcs_motion", {}).items():
        if sum(record["wcs"] == wcs for record in cuts) < int(minimum):
            return False
    if rule.get("avoid_rects"):
        margin = float(rule.get("avoid_clearance", 0.0))
        below = float(rule.get("avoid_below", 1e9))
        for record in cuts:
            e = record["end"]
            if e["z"] is not None and e["z"] < below and any(rect_contains((e["x"], e["y"]), rect, margin) for rect in rule["avoid_rects"]):
                return False
    if "engrave" in rule:
        item = rule["engrave"]
        xs = [r["end"]["x"] for r in cuts]
        ys = [r["end"]["y"] for r in cuts]
        if not xs or max(xs) - min(xs) < float(item["min_x_span"]) or max(ys) - min(ys) < float(item["min_y_span"]):
            return False
        if "max_y_center_abs" in item and abs((min(ys) + max(ys)) / 2) > float(item["max_y_center_abs"]):
            return False
    if "tags" in rule:
        item = rule["tags"]
        tag_z = float(item["bottom"]) + float(item["height"])
        tag_moves = sum(record["code"] == 1 and xy_changed(record) and at_z(record, tag_z, 0.35) for record in records)
        if tag_moves < int(item["min"]):
            return False
    for slot in rule.get("slots", []):
        found = False
        for record in cuts:
            s, e = record["start"], record["end"]
            if record_z(record) is not None and record_z(record) <= float(slot["z_max"]) + TOL and close(s["y"], slot["y"]) and close(e["y"], slot["y"]) and min(s["x"], e["x"]) <= float(slot["xmin"]) + TOL and max(s["x"], e["x"]) >= float(slot["xmax"]) - TOL:
                found = True
        if not found:
            return False
    if rule.get("turning") and ("X" not in axes_seen or "Z" not in axes_seen):
        return False
    if "center_drill" in rule:
        item = rule["center_drill"]
        if not any(r["end"]["x"] is not None and r["end"]["z"] is not None and close(r["end"]["x"], item["x"]) and r["end"]["z"] <= float(item["z_max"]) + TOL for r in records):
            return False
    if rule.get("outer_last"):
        groups = [g for g in cut_groups(records) if group_closed(g)]
        if len(groups) < 2:
            return False
        def area(group):
            xs = [r["end"]["x"] for r in group]; ys = [r["end"]["y"] for r in group]
            return (max(xs) - min(xs)) * (max(ys) - min(ys))
        if area(groups[-1]) + 1e-6 < max(area(group) for group in groups[:-1]):
            return False
    return True


def evaluate() -> bool:
    if not check_no_gui_bypass(TARGET):
        return False
    return all(validate_file(TARGET / name, file_rule) for name, file_rule in RULE["files"].items())


if __name__ == "__main__":
    try:
        ok = evaluate()
    except Exception:
        ok = False
    print("True" if ok else "False")
