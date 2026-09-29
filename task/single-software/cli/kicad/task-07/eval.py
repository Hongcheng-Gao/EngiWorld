from __future__ import annotations

import json
import math
import os
import re
import sys
from collections import Counter
from pathlib import Path


DESKTOP = Path("/home/user/Desktop")
HERE = Path(__file__).resolve().parent
TASK_ID = "kicad-7"

SLOTS = [
    ("A1", "A.kicad_pcb", (10.0, 10.0), ""),
    ("A2", "A.kicad_pcb", (53.0, 10.0), "_2"),
    ("B1", "B.kicad_pcb", (10.0, 60.0), ""),
    ("B2", "B.kicad_pcb", (53.0, 60.0), "_2"),
    ("B3", "B.kicad_pcb", (96.0, 10.0), "_3"),
    ("B4", "B.kicad_pcb", (96.0, 60.0), "_4"),
]
EXPECTED_RECTS = [
    (0.0, 0.0, 146.0, 110.0),
    (10.0, 10.0, 50.0, 50.0),
    (53.0, 10.0, 93.0, 50.0),
    (10.0, 60.0, 50.0, 100.0),
    (53.0, 60.0, 93.0, 100.0),
    (96.0, 10.0, 136.0, 50.0),
    (96.0, 60.0, 136.0, 100.0),
]
EXPECTED_VSCORE = {
    ((50.0, 10.0), (50.0, 100.0)),
    ((93.0, 10.0), (93.0, 100.0)),
    ((10.0, 55.0), (136.0, 55.0)),
}
EXPECTED_LABELS = {
    "A1": (30.0, 30.0), "A2": (73.0, 30.0),
    "B1": (30.0, 80.0), "B2": (73.0, 80.0),
    "B3": (116.0, 30.0), "B4": (116.0, 80.0),
}
EXPECTED_FID = {"FID1": (5.0, 5.0), "FID2": (141.0, 5.0), "FID3": (5.0, 105.0)}
EXPECTED_TOOL = {"TOOL1": (5.0, 55.0), "TOOL2": (141.0, 55.0),
                 "TOOL3": (73.0, 5.0), "TOOL4": (73.0, 105.0)}


TOKEN_RE = re.compile(r'"(?:\\.|[^"\\])*"|[()]|[^\s()]+')


def parse_sexp(text: str):
    stack = []
    root = None
    for token in TOKEN_RE.findall(text):
        if token == "(":
            node = []
            if stack:
                stack[-1].append(node)
            stack.append(node)
        elif token == ")":
            if not stack:
                raise ValueError("unbalanced closing parenthesis")
            root = stack.pop()
        else:
            if not stack:
                raise ValueError("atom outside list")
            stack[-1].append(json.loads(token) if token.startswith('"') else token)
    if stack or not isinstance(root, list):
        raise ValueError("unbalanced s-expression")
    return root


def direct(node, tag):
    return [child for child in node if isinstance(child, list) and child and child[0] == tag]


def first(node, tag):
    items = direct(node, tag)
    return items[0] if items else None


def number(value):
    return round(float(value), 6)


def point(node):
    return (number(node[1]), number(node[2]))


def norm_edge(a, b):
    return tuple(sorted((a, b)))


def expand_rect(rect):
    start, end = first(rect, "start"), first(rect, "end")
    if not start or not end:
        return []
    x1, y1 = point(start)
    x2, y2 = point(end)
    corners = [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]
    return [norm_edge(corners[i], corners[(i + 1) % 4]) for i in range(4)]


def edges_on_layer(board, layer_name):
    edges = []
    for line in direct(board, "gr_line"):
        layer = first(line, "layer")
        start, end = first(line, "start"), first(line, "end")
        if layer and layer[1] == layer_name and start and end:
            edges.append(norm_edge(point(start), point(end)))
    for rect in direct(board, "gr_rect"):
        layer = first(rect, "layer")
        if layer and layer[1] == layer_name:
            edges.extend(expand_rect(rect))
    return Counter(edges)


def expected_rectangle_edges():
    edges = []
    for x1, y1, x2, y2 in EXPECTED_RECTS:
        corners = [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]
        edges.extend(norm_edge(corners[i], corners[(i + 1) % 4]) for i in range(4))
    return Counter(edges)


def property_value(footprint, name):
    for prop in direct(footprint, "property"):
        if len(prop) >= 3 and prop[1] == name:
            return str(prop[2])
    return ""


def footprint_info(footprint):
    at = first(footprint, "at")
    pads = []
    for pad in direct(footprint, "pad"):
        pad_at, size, layers, net = first(pad, "at"), first(pad, "size"), first(pad, "layers"), first(pad, "net")
        pads.append((
            str(pad[1]), str(pad[2]), str(pad[3]),
            tuple(number(v) for v in pad_at[1:]) if pad_at else (),
            tuple(number(v) for v in size[1:]) if size else (),
            tuple(str(v) for v in layers[1:]) if layers else (),
            str(net[2]) if net and len(net) >= 3 else "",
        ))
    layer = first(footprint, "layer")
    return {
        "library": str(footprint[1]) if len(footprint) >= 2 else "",
        "layer": str(layer[1]) if layer and len(layer) >= 2 else "",
        "at": point(at) if at else (0.0, 0.0),
        "reference": property_value(footprint, "Reference"),
        "value": property_value(footprint, "Value"),
        "pads": Counter(pads),
        "node": footprint,
    }


def source_path(name, output_path):
    beside_output = output_path.parent / name
    return beside_output if beside_output.exists() else HERE / "init_file" / name


def expected_copies(output_path):
    parsed_sources = {}
    result = {}
    for _, filename, origin, suffix in SLOTS:
        if filename not in parsed_sources:
            source_board = parse_sexp(source_path(filename, output_path).read_text(encoding="utf-8"))
            parsed_sources[filename] = [footprint_info(fp) for fp in direct(source_board, "footprint")]
        for source in parsed_sources[filename]:
            expected_ref = source["reference"] + suffix
            result[expected_ref] = {
                **source,
                "at": (round(source["at"][0] + origin[0], 6),
                       round(source["at"][1] + origin[1], 6)),
                "reference": expected_ref,
            }
    return result


def same_copy(actual, expected, tol=0.01):
    return (
        actual["library"] == expected["library"]
        and actual["layer"] == expected["layer"]
        and actual["value"] == expected["value"]
        and actual["pads"] == expected["pads"]
        and math.dist(actual["at"], expected["at"]) <= tol
    )


def feature_position_ok(info, expected, tol=0.01):
    return info is not None and math.dist(info["at"], expected) <= tol


def evaluate(path: str):
    checks = []
    output_path = Path(path)
    if not output_path.exists():
        return False, [("file_exists", False)]
    try:
        board = parse_sexp(output_path.read_text(encoding="utf-8"))
        if not board or board[0] != "kicad_pcb":
            raise ValueError("root is not kicad_pcb")
    except Exception:
        return False, [("valid_kicad_pcb", False)]
    checks.append(("valid_kicad_pcb", True))

    actual_edges = edges_on_layer(board, "Edge.Cuts")
    expected_edges = expected_rectangle_edges()
    checks.append(("outer_and_slot_geometry", all(actual_edges[e] >= count for e, count in expected_edges.items())))
    edge_points = [point for edge in actual_edges for point in edge]
    checks.append(("edge_cuts_inside_panel", all(0 <= x <= 146 and 0 <= y <= 110 for x, y in edge_points)))

    vscore_edges = edges_on_layer(board, "Dwgs.User")
    checks.append(("vscore_guides", all(vscore_edges[edge] >= 1 for edge in EXPECTED_VSCORE)))

    label_positions = {}
    for label in direct(board, "gr_text"):
        layer, at = first(label, "layer"), first(label, "at")
        if len(label) >= 2 and layer and layer[1] in {"F.Silkscreen", "F.SilkS"} and at:
            label_positions.setdefault(str(label[1]), []).append(point(at))
    labels_ok = all(
        name in label_positions and any(math.dist(pos, center) <= 5.0 for pos in label_positions[name])
        for name, center in EXPECTED_LABELS.items()
    )
    checks.append(("copy_labels_near_centers", labels_ok))

    footprints = [footprint_info(fp) for fp in direct(board, "footprint")]
    by_ref = {}
    for info in footprints:
        by_ref.setdefault(info["reference"], []).append(info)
    expected = expected_copies(output_path)
    copies_ok = all(
        len(by_ref.get(ref, [])) == 1 and same_copy(by_ref[ref][0], expected_info)
        for ref, expected_info in expected.items()
    )
    checks.append(("all_source_footprints_faithfully_copied", copies_ok))

    fid_ok = True
    for ref, pos in EXPECTED_FID.items():
        info = by_ref.get(ref, [None])[0] if len(by_ref.get(ref, [])) == 1 else None
        has_copper_pad = bool(info and any(pad[1] == "smd" and "F.Cu" in pad[5] for pad in direct_pad_signatures(info)))
        fid_ok = fid_ok and feature_position_ok(info, pos) and has_copper_pad
    checks.append(("fiducials", fid_ok))

    tool_ok = True
    for ref, pos in EXPECTED_TOOL.items():
        info = by_ref.get(ref, [None])[0] if len(by_ref.get(ref, [])) == 1 else None
        valid_hole = False
        if info:
            for pad in direct(info["node"], "pad"):
                drill = first(pad, "drill")
                if len(pad) >= 3 and pad[2] == "np_thru_hole" and drill and len(drill) >= 2:
                    try:
                        valid_hole = abs(float(drill[1]) - 3.0) <= 0.01
                    except (TypeError, ValueError):
                        pass
        tool_ok = tool_ok and feature_position_ok(info, pos) and valid_hole
    checks.append(("tooling_holes_3mm_npth", tool_ok))

    expected_refs = set(expected) | set(EXPECTED_FID) | set(EXPECTED_TOOL)
    checks.append(("reference_set_exact", set(by_ref) == expected_refs and all(len(items) == 1 for items in by_ref.values())))
    checks.append(("all_footprint_centers_inside_panel", all(0 <= info["at"][0] <= 146 and 0 <= info["at"][1] <= 110 for info in footprints)))
    return all(value for _, value in checks), checks


def direct_pad_signatures(info):
    return list(info["pads"].elements())


def eval_outputs(output_dir: str = "."):
    passed, checks = evaluate(os.path.join(output_dir, "panel.kicad_pcb"))
    return {
        "task_id": TASK_ID,
        "passed": passed,
        "score": 1.0 if passed else 0.0,
        "total": len(checks),
        "error": None,
        "checks": [{"name": name, "passed": value, "expected": True, "actual": value}
                   for name, value in checks],
        "summary": f"{sum(value for _, value in checks)}/{len(checks)}",
    }


if __name__ == "__main__":
    passed, _ = evaluate(sys.argv[1] if len(sys.argv) > 1 else "panel.kicad_pcb")
    print("True" if passed else "False")
