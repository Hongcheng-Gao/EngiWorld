from __future__ import annotations

import math
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path


DESKTOP = Path("/home/user/Desktop")
KICAD_CLI = Path(os.environ.get("KICAD_CLI", "/usr/bin/kicad-cli"))
EXPECTED_BOARD_VERSION = "20260206"
TOL = 1e-4
TAB_TOL = 0.08


class ValidationError(ValueError):
    pass


def _parse_sexp(text: str):
    roots = []
    stack = []
    index = 0
    length = len(text)

    def append(value):
        if stack:
            stack[-1].append(value)
        else:
            roots.append(value)

    while index < length:
        char = text[index]
        if char.isspace():
            index += 1
            continue
        if char == ";":
            newline = text.find("\n", index)
            index = length if newline < 0 else newline + 1
            continue
        if char == "(":
            node = []
            append(node)
            stack.append(node)
            index += 1
            continue
        if char == ")":
            if not stack:
                raise ValidationError("unexpected closing parenthesis")
            stack.pop()
            index += 1
            continue
        if char == '"':
            index += 1
            value = []
            while index < length:
                char = text[index]
                if char == '"':
                    index += 1
                    break
                if char == "\\":
                    index += 1
                    if index >= length:
                        raise ValidationError("unterminated escape")
                    escaped = text[index]
                    value.append({"n": "\n", "r": "\r", "t": "\t"}.get(escaped, escaped))
                    index += 1
                    continue
                value.append(char)
                index += 1
            else:
                raise ValidationError("unterminated string")
            append("".join(value))
            continue

        start = index
        while index < length and not text[index].isspace() and text[index] not in "();":
            index += 1
        if start == index:
            raise ValidationError("invalid token")
        append(text[start:index])

    if stack:
        raise ValidationError("unterminated list")
    if len(roots) != 1 or not isinstance(roots[0], list):
        raise ValidationError("expected one root expression")
    return roots[0]


def _head(node):
    return node[0] if isinstance(node, list) and node else None


def _direct(node, name: str):
    return [
        child
        for child in node[1:]
        if isinstance(child, list) and child and child[0] == name
    ]


def _single_node(node, name: str):
    matches = _direct(node, name)
    if len(matches) != 1:
        raise ValidationError(f"expected one {name} node")
    return matches[0]


def _single_value(node, name: str):
    match = _single_node(node, name)
    if len(match) < 2 or isinstance(match[1], list):
        raise ValidationError(f"invalid {name} value")
    return match[1]


def _numbers(node, name: str, minimum: int = 2):
    match = _single_node(node, name)
    raw = []
    for item in match[1:]:
        if isinstance(item, list):
            break
        raw.append(item)
    if len(raw) < minimum:
        raise ValidationError(f"invalid {name} coordinates")
    try:
        return tuple(float(item) for item in raw)
    except ValueError as exc:
        raise ValidationError(f"non-numeric {name}") from exc


def _property(node, name: str):
    matches = [
        child
        for child in _direct(node, "property")
        if len(child) >= 3 and child[1] == name and not isinstance(child[2], list)
    ]
    if len(matches) != 1:
        raise ValidationError(f"expected one {name} property")
    return matches[0][2]


def _close(left: float, right: float, tolerance: float = TOL) -> bool:
    return abs(left - right) <= tolerance


def _point_close(left, right, tolerance: float = TOL) -> bool:
    return _close(left[0], right[0], tolerance) and _close(left[1], right[1], tolerance)


def _segment_close(left, right, tolerance: float = TOL) -> bool:
    return (
        _point_close(left[0], right[0], tolerance)
        and _point_close(left[1], right[1], tolerance)
    ) or (
        _point_close(left[0], right[1], tolerance)
        and _point_close(left[1], right[0], tolerance)
    )


def _arc_close(left, right, tolerance: float = TOL) -> bool:
    direct = all(_point_close(a, b, tolerance) for a, b in zip(left, right))
    reverse = (
        _point_close(left[0], right[2], tolerance)
        and _point_close(left[1], right[1], tolerance)
        and _point_close(left[2], right[0], tolerance)
    )
    return direct or reverse


def _match_exact(actual, expected, comparator, label: str) -> None:
    if len(actual) != len(expected):
        raise ValidationError(f"wrong {label} count")
    unmatched = list(actual)
    for wanted in expected:
        for index, observed in enumerate(unmatched):
            if comparator(observed, wanted):
                unmatched.pop(index)
                break
        else:
            raise ValidationError(f"missing {label} geometry")
    if unmatched:
        raise ValidationError(f"unexpected {label} geometry")


def _read_board(path: Path):
    if not path.is_file() or path.stat().st_size < 100:
        raise ValidationError(f"missing or empty {path.name}")
    return _parse_sexp(path.read_text(encoding="utf-8"))


def _check_header(root, expected_title: str) -> None:
    if _head(root) != "kicad_pcb":
        raise ValidationError("not a KiCad PCB")
    if _single_value(root, "version") != EXPECTED_BOARD_VERSION:
        raise ValidationError("board is not in the KiCad 10.0.2 format")
    if _single_value(root, "generator") != "pcbnew":
        raise ValidationError("wrong PCB generator")
    if _single_value(root, "generator_version") != "10.0":
        raise ValidationError("wrong PCB generator version")
    general = _single_node(root, "general")
    if not _close(float(_single_value(general, "thickness")), 1.6):
        raise ValidationError("wrong board thickness")
    title_block = _single_node(root, "title_block")
    if _single_value(title_block, "title") != expected_title:
        raise ValidationError("wrong board title")


def _edge_lines(root):
    result = []
    for node in _direct(root, "gr_line"):
        if _single_value(node, "layer") != "Edge.Cuts":
            continue
        result.append((_numbers(node, "start")[:2], _numbers(node, "end")[:2]))
    return result


def _edge_arcs(root):
    result = []
    for node in _direct(root, "gr_arc"):
        if _single_value(node, "layer") != "Edge.Cuts":
            continue
        result.append(
            (
                _numbers(node, "start")[:2],
                _numbers(node, "mid")[:2],
                _numbers(node, "end")[:2],
            )
        )
    return result


def _footprint_at(node):
    values = _numbers(node, "at")
    return values[0], values[1], values[2] if len(values) >= 3 else 0.0


def _pad_at(node):
    matches = _direct(node, "at")
    if not matches:
        return 0.0, 0.0, 0.0
    values = []
    for item in matches[0][1:]:
        if isinstance(item, list):
            break
        values.append(float(item))
    if len(values) < 2:
        raise ValidationError("invalid pad position")
    return values[0], values[1], values[2] if len(values) >= 3 else 0.0


def _world_pad(footprint, pad):
    fx, fy, rotation = _footprint_at(footprint)
    px, py, _ = _pad_at(pad)
    radians = math.radians(rotation)
    return (
        fx + px * math.cos(radians) - py * math.sin(radians),
        fy + px * math.sin(radians) + py * math.cos(radians),
    )


def _pad_net(pad):
    nets = _direct(pad, "net")
    if len(nets) != 1:
        raise ValidationError("pad must have exactly one net")
    scalars = [value for value in nets[0][1:] if not isinstance(value, list)]
    if not scalars:
        raise ValidationError("invalid pad net")
    return scalars[-1]


def _layers(node):
    layer_node = _single_node(node, "layers")
    return {str(value) for value in layer_node[1:] if not isinstance(value, list)}


def _pad_size(pad):
    values = _numbers(pad, "size")
    return values[0], values[1]


def _pad_drill(pad):
    values = _numbers(pad, "drill", minimum=1)
    return values


def _check_testpoint(footprint, expected_reference: str | None = None):
    if len(footprint) < 2 or footprint[1] != "TestPoint:TestPoint_Pad_D1.5mm":
        raise ValidationError("wrong test-point footprint library ID")
    reference = _property(footprint, "Reference")
    if expected_reference is not None and reference != expected_reference:
        raise ValidationError("wrong source reference")
    if _property(footprint, "Value") != "TP":
        raise ValidationError("wrong test-point value")
    pads = _direct(footprint, "pad")
    if len(pads) != 1:
        raise ValidationError("test point must have one pad")
    pad = pads[0]
    if len(pad) < 4 or pad[1:4] != ["1", "thru_hole", "circle"]:
        raise ValidationError("wrong test-point pad type")
    if not _point_close(_pad_at(pad)[:2], (0.0, 0.0)):
        raise ValidationError("test-point pad moved within footprint")
    if not _point_close(_pad_size(pad), (1.5, 1.5)):
        raise ValidationError("wrong test-point pad size")
    drill = _pad_drill(pad)
    if len(drill) != 1 or not _close(drill[0], 0.8):
        raise ValidationError("wrong test-point drill")
    if _layers(pad) != {"*.Cu", "*.Mask"}:
        raise ValidationError("wrong test-point pad layers")
    return reference, _footprint_at(footprint)[:2], _pad_net(pad)


def _check_source(root):
    _check_header(root, "PNL02 Board A \u2014 L-shape")
    footprints = _direct(root, "footprint")
    if len(footprints) != 2:
        raise ValidationError("source must contain two footprints")
    observed = {}
    for footprint in footprints:
        reference, position, net = _check_testpoint(footprint)
        if reference in observed:
            raise ValidationError("duplicate source reference")
        observed[reference] = (position, net)
    expected = {
        "TP1": ((15.0, 15.0), "VCC"),
        "TP2": ((15.0, 25.0), "GND"),
    }
    if set(observed) != set(expected):
        raise ValidationError("wrong source references")
    for reference, (position, net) in expected.items():
        actual_position, actual_net = observed[reference]
        if not _point_close(actual_position, position) or actual_net != net:
            raise ValidationError("wrong source test-point data")

    expected_lines = [
        ((0.0, 0.0), (30.0, 0.0)),
        ((30.0, 0.0), (30.0, 20.0)),
        ((30.0, 20.0), (20.0, 20.0)),
        ((20.0, 30.0), (0.0, 30.0)),
        ((0.0, 3.0), (0.0, 30.0)),
    ]
    _match_exact(_edge_lines(root), expected_lines, _segment_close, "source line")
    source_arcs = _edge_arcs(root)
    expected_arcs = [
        ((0.0, 3.0), (-2.244466, 1.5), (0.0, 0.0)),
        ((20.0, 30.0), (17.071, 27.071), (20.0, 20.0)),
    ]
    _match_exact(source_arcs, expected_arcs, _arc_close, "source arc")
    return source_arcs


def _cluster(values, tolerance: float = TOL):
    groups = []
    for value in sorted(values):
        if not groups or abs(value - groups[-1][-1]) > tolerance:
            groups.append([value])
        else:
            groups[-1].append(value)
    return [sum(group) / len(group) for group in groups]


def _nearest_level(value: float, levels):
    distances = [abs(value - level) for level in levels]
    index = min(range(len(levels)), key=distances.__getitem__)
    if distances[index] > TOL:
        raise ValidationError("position is off the panel grid")
    return index


def _panel_origins(root):
    footprints = _direct(root, "footprint")
    testpoints = [
        footprint
        for footprint in footprints
        if len(footprint) >= 2 and footprint[1] == "TestPoint:TestPoint_Pad_D1.5mm"
    ]
    if len(testpoints) != 12:
        raise ValidationError("panel must contain twelve copied test points")

    references = set()
    vcc = []
    gnd = []
    for footprint in testpoints:
        reference, position, net = _check_testpoint(footprint)
        if not re.fullmatch(r"TP[1-9][0-9]*", reference) or reference in references:
            raise ValidationError("test-point references must be unique TP references")
        references.add(reference)
        if net == "VCC":
            vcc.append((position[0] - 15.0, position[1] - 15.0))
        elif net == "GND":
            gnd.append((position[0] - 15.0, position[1] - 25.0))
        else:
            raise ValidationError("copied test point has wrong net")
    if len(vcc) != 6 or len(gnd) != 6:
        raise ValidationError("each board copy needs VCC and GND test points")
    _match_exact(gnd, vcc, _point_close, "test-point origin")

    x_levels = _cluster([point[0] for point in vcc])
    y_levels = _cluster([point[1] for point in vcc])
    if len(x_levels) != 3 or len(y_levels) != 2:
        raise ValidationError("test points do not form a 3x2 grid")
    for left, right in zip(x_levels, x_levels[1:]):
        if not 7.0 <= right - left - 30.0 <= 9.0:
            raise ValidationError("horizontal board spacing is not approximately 8 mm")
    if not 7.0 <= y_levels[1] - y_levels[0] - 30.0 <= 9.0:
        raise ValidationError("vertical board spacing is not approximately 8 mm")

    origins = {}
    for point in vcc:
        col = _nearest_level(point[0], x_levels)
        row = _nearest_level(point[1], y_levels)
        if (row, col) in origins:
            raise ValidationError("duplicate board-copy origin")
        origins[(row, col)] = point
    if set(origins) != {(row, col) for row in range(2) for col in range(3)}:
        raise ValidationError("incomplete 3x2 board grid")
    return origins, x_levels, y_levels


def _npth_holes(root):
    holes = []
    all_pads = 0
    for footprint in _direct(root, "footprint"):
        for pad in _direct(footprint, "pad"):
            all_pads += 1
            if len(pad) < 4 or pad[2] != "np_thru_hole":
                continue
            if pad[1] != "" or pad[3] != "circle":
                raise ValidationError("mouse-bite holes must be unnumbered circular NPTH pads")
            if not _point_close(_pad_size(pad), (0.5, 0.5), TAB_TOL):
                raise ValidationError("wrong mouse-bite pad size")
            drill = _pad_drill(pad)
            if len(drill) != 1 or not _close(drill[0], 0.5, TAB_TOL):
                raise ValidationError("wrong mouse-bite drill")
            if _layers(pad) != {"*.Cu", "*.Mask"}:
                raise ValidationError("wrong mouse-bite pad layers")
            if _direct(pad, "net"):
                raise ValidationError("NPTH mouse-bite hole cannot have a net")
            holes.append(_world_pad(footprint, pad))
    if all_pads != 52 or len(holes) != 40:
        raise ValidationError("panel needs exactly twelve board pads and forty NPTH holes")
    if len({(round(x, 4), round(y, 4)) for x, y in holes}) != 40:
        raise ValidationError("mouse-bite holes overlap")
    return holes


def _hole_groups(holes):
    adjacency = {index: set() for index in range(len(holes))}
    for left in range(len(holes)):
        for right in range(left + 1, len(holes)):
            dx = abs(holes[left][0] - holes[right][0])
            dy = abs(holes[left][1] - holes[right][1])
            adjacent = (
                dy <= TAB_TOL and abs(dx - 1.0) <= TAB_TOL
            ) or (
                dx <= TAB_TOL and abs(dy - 1.0) <= TAB_TOL
            )
            if adjacent:
                adjacency[left].add(right)
                adjacency[right].add(left)

    groups = []
    remaining = set(range(len(holes)))
    while remaining:
        seed = next(iter(remaining))
        component = set()
        frontier = [seed]
        while frontier:
            current = frontier.pop()
            if current in component:
                continue
            component.add(current)
            frontier.extend(adjacency[current] - component)
        remaining -= component
        points = [holes[index] for index in component]
        if len(points) != 4:
            raise ValidationError("each mouse-bite array must contain exactly four holes")
        xs = sorted(point[0] for point in points)
        ys = sorted(point[1] for point in points)
        if max(ys) - min(ys) <= TAB_TOL:
            orientation = "horizontal"
            coordinates = xs
        elif max(xs) - min(xs) <= TAB_TOL:
            orientation = "vertical"
            coordinates = ys
        else:
            raise ValidationError("mouse-bite array is not axis aligned")
        if any(abs(right - left - 1.0) > TAB_TOL for left, right in zip(coordinates, coordinates[1:])):
            raise ValidationError("mouse-bite pitch is not 1 mm")
        groups.append(
            {
                "orientation": orientation,
                "center": (
                    sum(point[0] for point in points) / 4.0,
                    sum(point[1] for point in points) / 4.0,
                ),
            }
        )
    if len(groups) != 10:
        raise ValidationError("expected ten mouse-bite arrays")
    return groups


def _take_group(groups, predicate, label: str):
    matches = [index for index, group in enumerate(groups) if predicate(group)]
    if len(matches) != 1:
        raise ValidationError(f"expected exactly one mouse-bite array for {label}")
    return groups.pop(matches[0])


def _horizontal_line(line):
    return _close(line[0][1], line[1][1])


def _vertical_line(line):
    return _close(line[0][0], line[1][0])


def _find_rail(lines, origins, x_levels, y_levels):
    minimum_y = min(point[1] for line in lines for point in line)
    board_left = min(point[0] for point in origins.values()) - 2.244466
    board_right = max(point[0] for point in origins.values()) + 30.0
    top_candidates = []
    for segment in lines:
        if not _horizontal_line(segment):
            continue
        start, end = sorted((segment[0][0], segment[1][0]))
        if _close(segment[0][1], minimum_y) and start <= board_left + TOL and end >= board_right - TOL:
            top_candidates.append((segment, start, end))
    if len(top_candidates) != 1:
        raise ValidationError("expected one full-width top rail edge")
    _, rail_left, rail_right = top_candidates[0]

    def side_bottom(x):
        candidates = []
        for segment in lines:
            if not _vertical_line(segment) or not _close(segment[0][0], x):
                continue
            ys = sorted((segment[0][1], segment[1][1]))
            if _close(ys[0], minimum_y) and ys[1] > minimum_y + TOL:
                candidates.append(ys[1])
        if len(candidates) != 1:
            raise ValidationError("rail must have two unambiguous side edges")
        return candidates[0]

    left_bottom = side_bottom(rail_left)
    right_bottom = side_bottom(rail_right)
    if not _close(left_bottom, right_bottom):
        raise ValidationError("rail side edges have different heights")
    rail_bottom = (left_bottom + right_bottom) / 2.0
    if not 0.5 <= rail_bottom - minimum_y <= 10.0:
        raise ValidationError("invalid rail-strip depth")
    if not 7.0 <= y_levels[0] - rail_bottom <= 9.0:
        raise ValidationError("rail-to-board spacing is not approximately 8 mm")
    if rail_right - rail_left > 180.0 + TOL:
        raise ValidationError("rail exceeds maximum panel width")
    return rail_left, rail_right, minimum_y, rail_bottom


def _split_interval(start: float, end: float, gaps):
    low, high = sorted((start, end))
    normalized = sorted((max(low, a), min(high, b)) for a, b in gaps)
    cursor = low
    pieces = []
    for gap_start, gap_end in normalized:
        if gap_start < cursor - TOL or gap_end <= gap_start + TOL or gap_end > high + TOL:
            raise ValidationError("invalid or overlapping tab opening")
        if gap_start > cursor + TOL:
            pieces.append((cursor, gap_start))
        cursor = gap_end
    if cursor < high - TOL:
        pieces.append((cursor, high))
    return pieces


def _append_horizontal(expected, start: float, end: float, y: float, gaps=()):
    expected.extend((((left, y), (right, y))) for left, right in _split_interval(start, end, gaps))


def _append_vertical(expected, x: float, start: float, end: float, gaps=()):
    expected.extend((((x, low), (x, high))) for low, high in _split_interval(start, end, gaps))


def _check_panel_geometry(root, source_arcs):
    origins, x_levels, y_levels = _panel_origins(root)
    actual_lines = _edge_lines(root)
    actual_arcs = _edge_arcs(root)
    expected_arcs = []
    for origin in origins.values():
        for source_arc in source_arcs:
            expected_arcs.append(
                tuple((point[0] + origin[0], point[1] + origin[1]) for point in source_arc)
            )
    _match_exact(actual_arcs, expected_arcs, _arc_close, "copied arc")

    holes = _npth_holes(root)
    groups = _hole_groups(holes)
    rail_left, rail_right, rail_top, rail_bottom = _find_rail(
        actual_lines, origins, x_levels, y_levels
    )

    horizontal_tabs = {}
    for row in range(2):
        for col in range(2):
            left = origins[(row, col)]
            right = origins[(row, col + 1)]
            gap_center = (left[0] + 30.0 + right[0]) / 2.0
            low = max(left[1], right[1] + 3.0) + 1.0
            high = min(left[1] + 20.0, right[1] + 30.0) - 1.0
            horizontal_tabs[(row, col)] = _take_group(
                groups,
                lambda group, center=gap_center, low=low, high=high: (
                    group["orientation"] == "horizontal"
                    and _close(group["center"][0], center, TAB_TOL)
                    and low - TAB_TOL <= group["center"][1] <= high + TAB_TOL
                ),
                f"horizontal interface {row},{col}",
            )

    vertical_tabs = {}
    for col in range(3):
        top = origins[(0, col)]
        bottom = origins[(1, col)]
        gap_center = (top[1] + 30.0 + bottom[1]) / 2.0
        vertical_tabs[col] = _take_group(
            groups,
            lambda group, left=top[0] + 1.0, right=top[0] + 19.0, center=gap_center: (
                group["orientation"] == "vertical"
                and _close(group["center"][1], center, TAB_TOL)
                and left - TAB_TOL <= group["center"][0] <= right + TAB_TOL
            ),
            f"vertical interface {col}",
        )

    rail_tabs = {}
    rail_gap_center = (rail_bottom + y_levels[0]) / 2.0
    for col in range(3):
        origin = origins[(0, col)]
        rail_tabs[col] = _take_group(
            groups,
            lambda group, left=origin[0] + 1.0, right=origin[0] + 29.0: (
                group["orientation"] == "vertical"
                and _close(group["center"][1], rail_gap_center, TAB_TOL)
                and left - TAB_TOL <= group["center"][0] <= right + TAB_TOL
            ),
            f"rail interface {col}",
        )
    if groups:
        raise ValidationError("unassigned mouse-bite arrays")

    expected_lines = []
    for row in range(2):
        for col in range(3):
            ox, oy = origins[(row, col)]
            top_tab = rail_tabs[col] if row == 0 else vertical_tabs[col]
            top_x = top_tab["center"][0]
            _append_horizontal(expected_lines, ox, ox + 30.0, oy, [(top_x - 1.0, top_x + 1.0)])

            if col < 2:
                tab_y = horizontal_tabs[(row, col)]["center"][1]
                _append_vertical(expected_lines, ox + 30.0, oy, oy + 20.0, [(tab_y - 1.0, tab_y + 1.0)])
            else:
                _append_vertical(expected_lines, ox + 30.0, oy, oy + 20.0)
            _append_horizontal(expected_lines, ox + 20.0, ox + 30.0, oy + 20.0)

            if row == 0:
                tab_x = vertical_tabs[col]["center"][0]
                _append_horizontal(expected_lines, ox, ox + 20.0, oy + 30.0, [(tab_x - 1.0, tab_x + 1.0)])
            else:
                _append_horizontal(expected_lines, ox, ox + 20.0, oy + 30.0)

            if col > 0:
                tab_y = horizontal_tabs[(row, col - 1)]["center"][1]
                _append_vertical(expected_lines, ox, oy + 3.0, oy + 30.0, [(tab_y - 1.0, tab_y + 1.0)])
            else:
                _append_vertical(expected_lines, ox, oy + 3.0, oy + 30.0)

    for row in range(2):
        for col in range(2):
            left = origins[(row, col)]
            right = origins[(row, col + 1)]
            center = horizontal_tabs[(row, col)]["center"]
            _append_horizontal(expected_lines, left[0] + 30.0, right[0], center[1] - 1.0)
            _append_horizontal(expected_lines, left[0] + 30.0, right[0], center[1] + 1.0)

    for col in range(3):
        top = origins[(0, col)]
        bottom = origins[(1, col)]
        center = vertical_tabs[col]["center"]
        _append_vertical(expected_lines, center[0] - 1.0, top[1] + 30.0, bottom[1])
        _append_vertical(expected_lines, center[0] + 1.0, top[1] + 30.0, bottom[1])

    _append_horizontal(expected_lines, rail_left, rail_right, rail_top)
    _append_vertical(expected_lines, rail_left, rail_top, rail_bottom)
    _append_vertical(expected_lines, rail_right, rail_top, rail_bottom)
    rail_gaps = []
    for col in range(3):
        center = rail_tabs[col]["center"]
        rail_gaps.append((center[0] - 1.0, center[0] + 1.0))
        _append_vertical(expected_lines, center[0] - 1.0, rail_bottom, y_levels[0])
        _append_vertical(expected_lines, center[0] + 1.0, rail_bottom, y_levels[0])
    _append_horizontal(expected_lines, rail_left, rail_right, rail_bottom, rail_gaps)

    _match_exact(actual_lines, expected_lines, _segment_close, "Edge.Cuts line")

    points = [point for segment in actual_lines for point in segment]
    points.extend(point for arc_item in actual_arcs for point in arc_item)
    points.extend(holes)
    width = max(point[0] for point in points) - min(point[0] for point in points)
    height = max(point[1] for point in points) - min(point[1] for point in points)
    if width > 180.0 + TOL or height > 120.0 + TOL:
        raise ValidationError("panel exceeds 180x120 mm")


def _run(command, timeout=60):
    completed = subprocess.run(
        [str(item) for item in command],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout,
        check=False,
    )
    if completed.returncode != 0:
        raise ValidationError(completed.stderr or completed.stdout or "KiCad command failed")
    return completed.stdout


def _normalize_svg(text: str):
    if "<desc>Image generated by PCBNEW </desc>" not in text:
        raise ValidationError("SVG is not a native PCBNEW export")
    normalized, count = re.subn(
        r"<title>SVG Image created as edgecuts\.svg date [^<]+</title>",
        "<title>SVG Image created as edgecuts.svg date TIMESTAMP </title>",
        text,
    )
    if count != 1:
        raise ValidationError("invalid native SVG title")
    return normalized.replace("\r\n", "\n")


def _normalize_drill(text: str):
    if "; #@! TF.GenerationSoftware,Kicad,Pcbnew,10.0.2-10.0.2~ubuntu24.04.1" not in text:
        raise ValidationError("drill file was not generated by snapshot KiCad 10.0.2")
    text, header_count = re.subn(
        r"(?m)^(; DRILL file KiCad 10\.0\.2-10\.0\.2~ubuntu24\.04\.1 date )[^\r\n]+$",
        r"\1TIMESTAMP",
        text,
    )
    text, creation_count = re.subn(
        r"(?m)^(; #@! TF\.CreationDate,)[^\r\n]+$",
        r"\1TIMESTAMP",
        text,
    )
    if header_count != 1 or creation_count != 1:
        raise ValidationError("invalid native drill metadata")
    return text.replace("\r\n", "\n")


def _native_validate(panel_path: Path, svg_path: Path, drill_path: Path) -> None:
    if not KICAD_CLI.is_file() or not os.access(KICAD_CLI, os.X_OK):
        raise ValidationError("KiCad CLI is unavailable")
    version = _run([KICAD_CLI, "version", "--format", "about"])
    if "Version: 10.0.2-10.0.2~ubuntu24.04.1" not in version:
        raise ValidationError("wrong KiCad CLI build")
    with tempfile.TemporaryDirectory(prefix="engiworld-kicad-task-20-") as temporary:
        root = Path(temporary)
        native_panel = root / "panel.kicad_pcb"
        shutil.copy2(panel_path, native_panel)
        _run([KICAD_CLI, "pcb", "upgrade", "--force", native_panel])

        native_svg = root / "edgecuts.svg"
        _run(
            [
                KICAD_CLI,
                "pcb",
                "export",
                "svg",
                "--layers",
                "Edge.Cuts",
                "--exclude-drawing-sheet",
                "--page-size-mode",
                "2",
                "--drill-shape-opt",
                "2",
                "--black-and-white",
                "--mode-single",
                "--output",
                native_svg,
                native_panel,
            ]
        )
        _run([KICAD_CLI, "pcb", "export", "drill", "--output", root, native_panel])
        native_drill = root / "panel.drl"
        if not native_svg.is_file() or not native_drill.is_file():
            raise ValidationError("KiCad did not create required native exports")
        if _normalize_svg(svg_path.read_text(encoding="utf-8")) != _normalize_svg(
            native_svg.read_text(encoding="utf-8")
        ):
            raise ValidationError("edgecuts.svg does not match the native export")
        if _normalize_drill(drill_path.read_text(encoding="utf-8")) != _normalize_drill(
            native_drill.read_text(encoding="utf-8")
        ):
            raise ValidationError("panel.drl does not match the native export")


def evaluate(desktop: Path = DESKTOP) -> bool:
    source_path = desktop / "A.kicad_pcb"
    panel_path = desktop / "panel.kicad_pcb"
    svg_path = desktop / "edgecuts.svg"
    drill_path = desktop / "panel.drl"
    source = _read_board(source_path)
    panel = _read_board(panel_path)
    source_arcs = _check_source(source)
    _check_header(panel, "PNL02 Panel 3x2 of Board A")
    _check_panel_geometry(panel, source_arcs)
    _native_validate(panel_path, svg_path, drill_path)
    return True


if __name__ == "__main__":
    try:
        result = evaluate()
    except Exception:
        result = False
    print("True" if result else "False")
