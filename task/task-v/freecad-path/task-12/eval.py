from __future__ import annotations

import math
import os
import re
from pathlib import Path

RULE = {
    "files": {
        "task-12.nc": {
            "tool_comments": [
                ("TOOL_SPEC", 1, {"TYPE": "ENDMILL", "DIAMETER": (12, "MM"), "CUTTING_EDGE_HEIGHT": (25, "MM"), "LENGTH": (75, "MM"), "SHANK_DIAMETER": (12, "MM")}),
                ("TOOL_CONTROLLER", 1, {"OPERATION": "FACE", "SPINDLE": (6000, "RPM"), "HORIZONTAL_FEED": (600, "MM/MIN"), "VERTICAL_FEED": (180, "MM/MIN")}),
                ("TOOL_SPEC", 2, {"TYPE": "DRILL", "DIAMETER": (6, "MM"), "LENGTH": (80, "MM"), "TIP_ANGLE": (118, "DEG")}),
                ("TOOL_CONTROLLER", 2, {"OPERATION": "DRILLING", "SPINDLE": (5000, "RPM"), "HORIZONTAL_FEED": (180, "MM/MIN"), "VERTICAL_FEED": (180, "MM/MIN")}),
                ("TOOL_SPEC", 3, {"TYPE": "ENDMILL", "DIAMETER": (8, "MM"), "CUTTING_EDGE_HEIGHT": (20, "MM"), "LENGTH": (65, "MM"), "SHANK_DIAMETER": (8, "MM")}),
                ("TOOL_CONTROLLER", 3, {"OPERATION": "PROFILE_ROUGH", "SPINDLE": (7000, "RPM"), "HORIZONTAL_FEED": (500, "MM/MIN"), "VERTICAL_FEED": (150, "MM/MIN")}),
                ("TOOL_SPEC", 4, {"TYPE": "ENDMILL", "DIAMETER": (6, "MM"), "CUTTING_EDGE_HEIGHT": (18, "MM"), "LENGTH": (60, "MM"), "SHANK_DIAMETER": (6, "MM")}),
                ("TOOL_CONTROLLER", 4, {"OPERATION": "PROFILE_FINISH", "SPINDLE": (8000, "RPM"), "HORIZONTAL_FEED": (300, "MM/MIN"), "VERTICAL_FEED": (100, "MM/MIN")}),
            ],
            "operation_controls": [
                {"comment": "OPERATION FACE T1", "tool": 1, "spindle": 6000, "hfeed": 600, "vfeed": 180, "require_horizontal": True, "require_vertical": True},
                {"comment": "OPERATION DRILLING T2", "tool": 2, "spindle": 5000, "hfeed": 180, "vfeed": 180, "require_horizontal": False, "require_vertical": True},
                {"comment": "OPERATION PROFILE_ROUGH T3", "tool": 3, "spindle": 7000, "hfeed": 500, "vfeed": 150, "require_horizontal": True, "require_vertical": True},
                {"comment": "OPERATION PROFILE_FINISH T4", "tool": 4, "spindle": 8000, "hfeed": 300, "vfeed": 100, "require_horizontal": True, "require_vertical": True},
            ],
            "exact_tools": [1, 2, 3, 4],
            "min_motion": 12,
            "min_rapid": 4,
            "face_coverage": {
                "tool": 1,
                "z_range": [17.0, 18.25],
                "part_rect": [-60, -40, 60, 40],
                "tool_radius": 6.0,
                "grid_step": 5.0,
                "sample_step": 1.0,
                "min_coverage": 0.75,
            },
            "hole_sets": [{"tool": 2, "points": [(-30, -20), (30, -20), (30, 20), (-30, 20)], "z_max": -1.0}],
            "profile_envelopes": [
                {"tool": 3, "part_rect": [-60, -40, 60, 40], "part_top": 18.0, "radius": 4.0, "tol": 0.75, "min_side_fraction": 0.70},
                {"tool": 4, "part_rect": [-60, -40, 60, 40], "part_top": 18.0, "radius": 3.0, "tol": 0.75, "min_side_fraction": 0.70},
            ],
            "profile_depth_order": {"rough_tool": 3, "finish_tool": 4, "tolerance": 0.75},
        }
    }
}
DEFAULT_TARGET = '/home/user/Desktop'
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


def normalize_comment(text: str) -> str:
    return " ".join(text.strip().upper().split())


def parse_value(text: str):
    match = re.fullmatch(r"([+-]?\d+(?:\.\d+)?)([A-Z/]+)", text)
    if not match:
        return None
    return float(match.group(1)), match.group(2)


def validate_tool_comments(src: str, expected) -> bool:
    comments = [normalize_comment(text) for text in re.findall(r"\(([^()]*)\)", src)]
    if sum(comment.startswith("TOOL_SPEC ") for comment in comments) != 4:
        return False
    if sum(comment.startswith("TOOL_CONTROLLER ") for comment in comments) != 4:
        return False
    for kind, tool, fields in expected:
        prefix = rf"^{kind}\s+T0*{tool}\b"
        matches = [comment for comment in comments if re.search(prefix, comment)]
        if len(matches) != 1:
            return False
        actual = dict(re.findall(r"([A-Z_]+)=([^\s]+)", matches[0]))
        if set(actual) != set(fields):
            return False
        for name, wanted in fields.items():
            value = actual[name]
            if isinstance(wanted, tuple):
                parsed = parse_value(value)
                if parsed is None or parsed[1] != wanted[1] or not close(parsed[0], wanted[0], 1e-6):
                    return False
            elif value != wanted:
                return False
    return True


def validate_operation_controls(src: str, expected) -> bool:
    lines = [line.strip().upper() for line in src.splitlines() if line.strip()]
    comments = [
        normalize_comment(match.group(1)) if (match := re.fullmatch(r"\(([^()]*)\)", line)) else None
        for line in lines
    ]
    operation_comments = [comment for comment in comments if comment and comment.startswith("OPERATION ")]
    if len(operation_comments) != len(expected):
        return False

    for item in expected:
        marker = normalize_comment(item["comment"])
        indices = [index for index, comment in enumerate(comments) if comment == marker]
        if len(indices) != 1:
            return False
        start = indices[0] + 1
        end = next(
            (
                index
                for index in range(start, len(lines))
                if comments[index] and (
                    comments[index].startswith("FINISH OPERATION")
                    or comments[index].startswith("OPERATION ")
                )
            ),
            len(lines),
        )
        block = lines[start:end]
        changes = []
        for line in block:
            code = strip_code(line)
            match = re.search(r"\bM0?6\b.*\bT0*(\d+)\b|\bT0*(\d+)\b.*\bM0?6\b", code)
            if match:
                changes.append(int(match.group(1) or match.group(2)))
        if changes != [int(item["tool"])]:
            return False
        spindles = [
            float(value)
            for line in block
            if re.search(r"\bM0?3\b", strip_code(line))
            for value in re.findall(r"\bS([+-]?\d+(?:\.\d+)?)", strip_code(line))
        ]
        if not spindles or any(not close(value, item["spindle"], 0.5) for value in spindles):
            return False

        state = {"x": None, "y": None, "z": None, "motion": None, "feed": None}
        horizontal = vertical = 0
        for line in block:
            code = strip_code(line)
            g_codes = [int(value) for value in re.findall(r"\bG0*(\d+)\b", code)]
            explicit_motion = next((value for value in g_codes if value in {0, 1, 2, 3}), None)
            if explicit_motion is not None:
                state["motion"] = explicit_motion
            feed_match = re.search(r"\bF([+-]?\d+(?:\.\d+)?)", code)
            if feed_match:
                state["feed"] = float(feed_match.group(1))
            explicit = {}
            for axis in "XYZ":
                match = re.search(rf"\b{axis}([+-]?\d+(?:\.\d+)?)", code)
                if match:
                    explicit[axis.lower()] = float(match.group(1))
            if not explicit:
                continue
            start_pos = {axis: state[axis] for axis in "xyz"}
            for axis, value in explicit.items():
                state[axis] = value
            if state["motion"] not in {1, 2, 3}:
                continue
            xy_move = any(
                axis in explicit
                and start_pos[axis] is not None
                and not close(start_pos[axis], state[axis], 1e-9)
                for axis in ("x", "y")
            )
            z_move = (
                "z" in explicit
                and start_pos["z"] is not None
                and not close(start_pos["z"], state["z"], 1e-9)
            )
            if xy_move:
                horizontal += 1
                if state["feed"] is None or not close(state["feed"], item["hfeed"], 0.5):
                    return False
            elif z_move:
                vertical += 1
                if state["feed"] is None or not close(state["feed"], item["vfeed"], 0.5):
                    return False
        if item.get("require_horizontal") and horizontal == 0:
            return False
        if item.get("require_vertical") and vertical == 0:
            return False
    return True


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


def record_sample_points(record, step=1.0):
    start, end = record["start"], record["end"]
    if None in (start["x"], start["y"], end["x"], end["y"]):
        return []
    sx, sy, ex, ey = start["x"], start["y"], end["x"], end["y"]
    explicit = record["explicit"]
    if record["code"] in {2, 3} and "i" in explicit and "j" in explicit:
        cx, cy = sx + explicit["i"], sy + explicit["j"]
        radius = math.hypot(sx - cx, sy - cy)
        if radius > 1e-9:
            start_angle = math.atan2(sy - cy, sx - cx)
            end_angle = math.atan2(ey - cy, ex - cx)
            sweep = (start_angle - end_angle) % (2 * math.pi) if record["code"] == 2 else (end_angle - start_angle) % (2 * math.pi)
            if sweep < 1e-9 and close(sx, ex, 1e-6) and close(sy, ey, 1e-6):
                sweep = 2 * math.pi
            count = max(1, int(math.ceil(radius * sweep / max(float(step), 1e-6))))
            direction = -1.0 if record["code"] == 2 else 1.0
            return [
                (cx + radius * math.cos(start_angle + direction * sweep * index / count),
                 cy + radius * math.sin(start_angle + direction * sweep * index / count))
                for index in range(count + 1)
            ]
    length = math.hypot(ex - sx, ey - sy)
    count = max(1, int(math.ceil(length / max(float(step), 1e-6))))
    return [(sx + (ex - sx) * index / count, sy + (ey - sy) * index / count) for index in range(count + 1)]


def validate_face_coverage(records, item):
    tool = int(item["tool"])
    z_min, z_max = map(float, item["z_range"])
    candidates = [
        record for record in records
        if record["tool"] == tool and record["code"] in {1, 2, 3} and xy_changed(record)
        and record_z(record) is not None and z_min - TOL <= record_z(record) <= z_max + TOL
    ]
    samples = [point for record in candidates for point in record_sample_points(record, item.get("sample_step", 1.0))]
    if not samples:
        return False
    x1, y1, x2, y2 = map(float, item["part_rect"])
    x1, x2, y1, y2 = min(x1, x2), max(x1, x2), min(y1, y2), max(y1, y2)
    step = float(item.get("grid_step", 5.0))
    nx = max(1, int(math.ceil((x2 - x1) / step)))
    ny = max(1, int(math.ceil((y2 - y1) / step)))
    grid = [(x1 + (ix + 0.5) * (x2 - x1) / nx, y1 + (iy + 0.5) * (y2 - y1) / ny) for ix in range(nx) for iy in range(ny)]
    reach = float(item["tool_radius"]) + float(item.get("sample_step", 1.0))
    covered = sum(any(math.hypot(x - px, y - py) <= reach for px, py in samples) for x, y in grid)
    return covered / len(grid) >= float(item["min_coverage"])


def profile_side_depths(records, item):
    tool = int(item["tool"])
    radius = float(item["radius"])
    tol = float(item.get("tol", 0.75))
    fraction = float(item.get("min_side_fraction", 0.70))
    x1, y1, x2, y2 = map(float, item["part_rect"])
    expected = (min(x1, x2) - radius, min(y1, y2) - radius, max(x1, x2) + radius, max(y1, y2) + radius)
    xmin, ymin, xmax, ymax = expected
    part_top = float(item.get("part_top", 1e9))
    candidates = [
        record for record in records
        if record["tool"] == tool and record["code"] in {1, 2, 3} and xy_changed(record)
        and record_z(record) is not None and record_z(record) <= part_top + TOL
    ]
    points = []
    for record in candidates:
        z = record_z(record)
        if z is None:
            continue
        for x, y in record_sample_points(record, 1.0):
            points.append((x, y, z))
    if not points:
        return []

    def distance_to_part(x, y):
        dx = max(min(x1, x2) - x, 0.0, x - max(x1, x2))
        dy = max(min(y1, y2) - y, 0.0, y - max(y1, y2))
        return math.hypot(dx, dy)

    if any(distance_to_part(x, y) < radius - tol for x, y, _ in points):
        return []

    bottom = [(x, z) for x, y, z in points if abs(y - ymin) <= tol]
    top = [(x, z) for x, y, z in points if abs(y - ymax) <= tol]
    left = [(y, z) for x, y, z in points if abs(x - xmin) <= tol]
    right = [(y, z) for x, y, z in points if abs(x - xmax) <= tol]
    sides = (bottom, top, left, right)
    required_spans = ((xmax - xmin) * fraction, (xmax - xmin) * fraction, (ymax - ymin) * fraction, (ymax - ymin) * fraction)
    if any(not side or max(value for value, _ in side) - min(value for value, _ in side) < required for side, required in zip(sides, required_spans)):
        return []
    return [z for side in sides for _, z in side]


def validate_profile_envelopes(records, rules, depth_order=None):
    depths = {}
    for item in rules:
        item_depths = profile_side_depths(records, item)
        if not item_depths:
            return False
        depths[int(item["tool"])] = item_depths
    if depth_order:
        rough = depths.get(int(depth_order["rough_tool"]))
        finish = depths.get(int(depth_order["finish_tool"]))
        if not rough or not finish or min(finish) > min(rough) + float(depth_order.get("tolerance", TOL)):
            return False
    return True


def validate_file(path: Path, rule: dict) -> bool:
    if not path.exists() or path.stat().st_size <= 0:
        return False
    src = path.read_text(encoding="utf-8", errors="ignore").upper()
    code_src = "\n".join(strip_code(line) for line in src.splitlines())
    if "G21" not in code_src or "G90" not in code_src or not re.search(r"\bM(?:2|30)\b", code_src):
        return False
    if not validate_tool_comments(src, rule.get("tool_comments", [])):
        return False
    if not validate_operation_controls(src, rule.get("operation_controls", [])):
        return False
    records, tools, axes_seen = parse_nc(src)
    cuts = cut_records(records)
    if len(tool_order(tools)) < int(rule.get("min_tools", 1)) or len(records) < int(rule.get("min_motion", 1)):
        return False
    if "exact_tools" in rule and tool_order(tools) != [int(tool) for tool in rule["exact_tools"]]:
        return False
    if sum(1 for record in records if record["code"] == 0) < int(rule.get("min_rapid", 0)):
        return False
    if "face_coverage" in rule and not validate_face_coverage(records, rule["face_coverage"]):
        return False
    if not validate_profile_envelopes(records, rule.get("profile_envelopes", []), rule.get("profile_depth_order")):
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
