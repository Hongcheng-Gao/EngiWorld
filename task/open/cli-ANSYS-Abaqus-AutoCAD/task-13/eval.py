# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
from collections import defaultdict, deque
from pathlib import Path


TASK_ID = "c-open-abaqus-ansys-autocad-task-13-windows"
ABAQUS_COMMAND = r"C:\SIMULIA\Commands\abaqus.bat"
ANSYS_EXEC = r"C:\Program Files\ANSYS Inc\v261\ansys\bin\winx64\ANSYS261.exe"
ANSYS_PYTHON_SITE = Path(r"C:\Users\user\AppData\Roaming\Python\Python311\site-packages")
ANSYS_RST_HEADER_SIZE = 128
DESKTOP_CANDIDATES = [
    Path(os.environ.get("USERPROFILE", r"C:\Users\user")) / "Desktop",
    Path(r"C:\Users\user\Desktop"),
    Path(r"C:\Users\User\Desktop"),
]

DETAILS: list[str] = []


def log(message: object) -> None:
    DETAILS.append(str(message))


def desktop_dir() -> Path:
    for candidate in DESKTOP_CANDIDATES:
        if candidate.exists():
            return candidate
    return DESKTOP_CANDIDATES[1]


def is_nonempty(path: Path) -> bool:
    try:
        return path.is_file() and path.stat().st_size > 0
    except OSError:
        return False


def finite_number(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def close(actual: float, expected: float, rel: float = 0.02, abs_tol: float = 1.0e-8) -> bool:
    return math.isclose(float(actual), float(expected), rel_tol=rel, abs_tol=abs_tol)


def read_metrics(root: Path) -> dict[str, float] | None:
    path = root / "metrics.json"
    if not is_nonempty(path):
        log("metrics.json is missing")
        return None
    try:
        def reject_duplicate_keys(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError("duplicate JSON key: %s" % key)
                result[key] = value
            return result

        payload = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=reject_duplicate_keys,
        )
    except Exception as exc:
        log("metrics.json is invalid JSON: %s" % exc)
        return None
    if not isinstance(payload, dict):
        log("metrics.json must contain an object")
        return None
    names = ("max_stress", "stress_concentration_proxy")
    if set(payload) != set(names):
        log("metrics.json must contain exactly max_stress and stress_concentration_proxy, with no extra keys")
        return None
    if any(not finite_number(payload[name]) for name in names):
        log("metrics.json values must be finite numbers")
        return None
    values = {name: float(payload[name]) for name in names}
    if not (15.0 <= values["max_stress"] <= 50.0):
        log("reported max_stress is outside the physical screening range")
        return None
    if not (1.5 <= values["stress_concentration_proxy"] <= 5.0):
        log("reported stress_concentration_proxy is outside the physical screening range")
        return None
    if not close(
        values["stress_concentration_proxy"],
        values["max_stress"] / 10.0,
        rel=0.015,
        abs_tol=0.02,
    ):
        log("metrics.json does not satisfy stress_concentration_proxy=max_stress/10 MPa")
        return None
    return values


def metrics_match(reported: dict[str, float], extracted: dict[str, float]) -> bool:
    if not close(reported["max_stress"], extracted["max_stress"], rel=0.02, abs_tol=0.15):
        log(
            "reported max_stress %.9g does not match native result %.9g"
            % (reported["max_stress"], extracted["max_stress"])
        )
        return False
    if not close(
        reported["stress_concentration_proxy"],
        extracted["stress_concentration_proxy"],
        rel=0.02,
        abs_tol=0.02,
    ):
        log(
            "reported stress_concentration_proxy %.9g does not match native result %.9g"
            % (
                reported["stress_concentration_proxy"],
                extracted["stress_concentration_proxy"],
            )
        )
        return False
    return True


def files(root: Path, suffix: str) -> list[Path]:
    try:
        return sorted(
            [path for path in root.iterdir() if path.is_file() and path.suffix.lower() == suffix],
            key=lambda path: path.name.lower(),
        )
    except OSError:
        return []


def unique_native_pair(root: Path) -> tuple[str, Path, Path] | None:
    abaqus_models = files(root, ".cae")
    abaqus_results = files(root, ".odb")
    ansys_models = files(root, ".db")
    ansys_results = files(root, ".rst")
    has_abaqus = bool(abaqus_models or abaqus_results)
    has_ansys = bool(ansys_models or ansys_results)
    if has_abaqus and has_ansys:
        log("Abaqus and ANSYS native artifacts coexist; solver selection is ambiguous")
        return None
    if has_abaqus:
        if len(abaqus_models) != 1 or len(abaqus_results) != 1:
            log(
                "expected exactly one Abaqus CAE and one ODB, got %d CAE and %d ODB"
                % (len(abaqus_models), len(abaqus_results))
            )
            return None
        if not is_nonempty(abaqus_models[0]) or not is_nonempty(abaqus_results[0]):
            log("the unique Abaqus CAE/ODB pair must contain two nonempty files")
            return None
        return "abaqus", abaqus_models[0], abaqus_results[0]
    if has_ansys:
        if len(ansys_models) != 1 or len(ansys_results) != 1:
            log(
                "expected exactly one ANSYS DB and one RST, got %d DB and %d RST"
                % (len(ansys_models), len(ansys_results))
            )
            return None
        if not is_nonempty(ansys_models[0]) or not is_nonempty(ansys_results[0]):
            log("the unique ANSYS DB/RST pair must contain two nonempty files")
            return None
        return "ansys", ansys_models[0], ansys_results[0]
    log("no complete native Abaqus CAE/ODB or ANSYS DB/RST pair found")
    return None


def mesh_digest(nodes: dict[int, tuple[float, float, float]], elements: list[dict[str, object]]) -> str:
    rows = []
    for label in sorted(nodes):
        xyz = nodes[label]
        rows.append("N:%d:%.10g,%.10g,%.10g" % (label, xyz[0], xyz[1], xyz[2]))
    for element in sorted(elements, key=lambda item: int(item["label"])):
        rows.append(
            "E:%d:%s:%s"
            % (
                int(element["label"]),
                str(element["type"]),
                ",".join(str(int(value)) for value in element["connectivity"]),
            )
        )
    return hashlib.sha256("\n".join(rows).encode("ascii")).hexdigest()


def edge_sequences(element_type: str, connectivity: list[int]) -> list[list[int]]:
    etype = element_type.upper()
    if etype in {"CPS3", "PLANE182_TRI3"}:
        return [
            [connectivity[0], connectivity[1]],
            [connectivity[1], connectivity[2]],
            [connectivity[2], connectivity[0]],
        ]
    if etype in {"CPS6", "CPS6M", "PLANE183_TRI6"}:
        return [
            [connectivity[0], connectivity[3], connectivity[1]],
            [connectivity[1], connectivity[4], connectivity[2]],
            [connectivity[2], connectivity[5], connectivity[0]],
        ]
    if etype.startswith("CPS4") or etype == "PLANE182":
        return [
            [connectivity[0], connectivity[1]],
            [connectivity[1], connectivity[2]],
            [connectivity[2], connectivity[3]],
            [connectivity[3], connectivity[0]],
        ]
    if etype.startswith("CPS8") or etype == "PLANE183":
        return [
            [connectivity[0], connectivity[4], connectivity[1]],
            [connectivity[1], connectivity[5], connectivity[2]],
            [connectivity[2], connectivity[6], connectivity[3]],
            [connectivity[3], connectivity[7], connectivity[0]],
        ]
    raise ValueError("unsupported element type %s" % element_type)


def corner_labels(element_type: str, connectivity: list[int]) -> list[int]:
    etype = element_type.upper()
    if etype in {"CPS3", "CPS6", "CPS6M", "PLANE182_TRI3", "PLANE183_TRI6"}:
        return connectivity[:3]
    return connectivity[:4]


def polyline_length(sequence: list[int], nodes: dict[int, tuple[float, float, float]]) -> float:
    return sum(
        math.hypot(
            nodes[sequence[index + 1]][0] - nodes[sequence[index]][0],
            nodes[sequence[index + 1]][1] - nodes[sequence[index]][1],
        )
        for index in range(len(sequence) - 1)
    )


def matrix_rank(rows: list[list[float]], tolerance: float = 1.0e-9) -> int:
    work = [list(map(float, row)) for row in rows]
    if not work:
        return 0
    rank = 0
    column = 0
    while rank < len(work) and column < len(work[0]):
        pivot = max(range(rank, len(work)), key=lambda row: abs(work[row][column]))
        if abs(work[pivot][column]) <= tolerance:
            column += 1
            continue
        work[rank], work[pivot] = work[pivot], work[rank]
        divisor = work[rank][column]
        work[rank] = [value / divisor for value in work[rank]]
        for row in range(len(work)):
            if row == rank:
                continue
            factor = work[row][column]
            work[row] = [
                work[row][index] - factor * work[rank][index]
                for index in range(len(work[row]))
            ]
        rank += 1
        column += 1
    return rank


def validate_minimal_constraints(
    constraints: list[tuple[int, int, float]],
    nodes: dict[int, tuple[float, float, float]],
) -> tuple[bool, str]:
    unique: dict[tuple[int, int], float] = {}
    for node, dof, value in constraints:
        key = (int(node), int(dof))
        if key in unique and not close(unique[key], value, rel=0.0, abs_tol=1.0e-10):
            return False, "conflicting displacement constraints"
        unique[key] = float(value)
    if len(unique) != 3:
        return False, "expected exactly three constrained in-plane node DOFs, got %d" % len(unique)
    rows = []
    constrained_nodes = set()
    for (node, dof), value in sorted(unique.items()):
        if node not in nodes or dof not in (1, 2) or abs(value) > 1.0e-10:
            return False, "constraints must be zero UX/UY values on plate nodes"
        x, y, _ = nodes[node]
        constrained_nodes.add(node)
        rows.append([1.0, 0.0, -y] if dof == 1 else [0.0, 1.0, x])
    if len(constrained_nodes) != 2:
        return False, "minimum support must use exactly two reference nodes"
    if matrix_rank(rows) != 3:
        return False, "support constraints do not remove all three 2D rigid-body modes"
    return True, ""


def validate_topology(
    nodes: dict[int, tuple[float, float, float]],
    elements: list[dict[str, object]],
) -> dict[str, object]:
    if len(nodes) < 100 or len(elements) < 100:
        raise ValueError("mesh is too small for the requested 5/1 mm refinement")
    xs = [point[0] for point in nodes.values()]
    ys = [point[1] for point in nodes.values()]
    zs = [point[2] for point in nodes.values()]
    for actual, expected, label in (
        (min(xs), 0.0, "xmin"),
        (max(xs), 100.0, "xmax"),
        (min(ys), 0.0, "ymin"),
        (max(ys), 200.0, "ymax"),
    ):
        if not close(actual, expected, rel=0.0, abs_tol=0.02):
            raise ValueError("geometry %s is %.9g instead of %.9g mm" % (label, actual, expected))
    if max(abs(value) for value in zs) > 0.02:
        raise ValueError("mesh is not two-dimensional in the global XY plane")

    used_nodes: set[int] = set()
    node_to_elements: dict[int, list[int]] = defaultdict(list)
    edge_occurrences: dict[tuple[int, int], list[tuple[int, int, list[int]]]] = defaultdict(list)
    area = 0.0
    element_by_label: dict[int, dict[str, object]] = {}
    for element in elements:
        label = int(element["label"])
        connectivity = [int(value) for value in element["connectivity"]]
        etype = str(element["type"])
        if any(node not in nodes for node in connectivity):
            raise ValueError("element connectivity references missing nodes")
        element_by_label[label] = element
        used_nodes.update(connectivity)
        for node in connectivity:
            node_to_elements[node].append(label)
        corners = corner_labels(etype, connectivity)
        polygon = [nodes[node] for node in corners]
        signed_twice_area = sum(
            polygon[index][0] * polygon[(index + 1) % len(polygon)][1]
            - polygon[(index + 1) % len(polygon)][0] * polygon[index][1]
            for index in range(len(polygon))
        )
        area += abs(signed_twice_area) * 0.5
        for face, sequence in enumerate(edge_sequences(etype, connectivity), start=1):
            key = tuple(sorted((int(sequence[0]), int(sequence[-1]))))
            edge_occurrences[key].append((label, face, sequence))
    if used_nodes != set(nodes):
        raise ValueError("mesh contains unused or disconnected dummy nodes")
    if not close(area, 20000.0 - math.pi * 25.0, rel=0.012, abs_tol=2.0):
        raise ValueError("meshed plate area %.9g is inconsistent with the central radius-5 hole" % area)

    remaining = set(element_by_label)
    queue = deque([next(iter(remaining))])
    visited: set[int] = set()
    while queue:
        current = queue.popleft()
        if current in visited:
            continue
        visited.add(current)
        element = element_by_label[current]
        for node in element["connectivity"]:
            queue.extend(node_to_elements[int(node)])
    if visited != remaining:
        raise ValueError("plate mesh has multiple disconnected element components")

    boundary: dict[str, list[tuple[tuple[int, int], int, int, list[int], float]]] = {
        "left": [],
        "right": [],
        "bottom": [],
        "top": [],
        "hole": [],
    }
    for key, occurrences in edge_occurrences.items():
        if len(occurrences) == 2:
            continue
        if len(occurrences) != 1:
            raise ValueError("non-manifold mesh edge detected")
        label, face, sequence = occurrences[0]
        points = [nodes[node] for node in sequence]
        radii = [math.hypot(point[0] - 50.0, point[1] - 100.0) for point in points]
        if all(abs(point[0]) <= 0.02 for point in points):
            group = "left"
        elif all(abs(point[0] - 100.0) <= 0.02 for point in points):
            group = "right"
        elif all(abs(point[1]) <= 0.02 for point in points):
            group = "bottom"
        elif all(abs(point[1] - 200.0) <= 0.02 for point in points):
            group = "top"
        elif all(abs(radius - 5.0) <= 0.08 for radius in radii):
            group = "hole"
        else:
            raise ValueError("mesh has an unexpected free boundary that is not the plate or hole boundary")
        boundary[group].append((key, label, face, sequence, polyline_length(sequence, nodes)))

    expected_lengths = {"left": 200.0, "right": 200.0, "bottom": 100.0, "top": 100.0}
    for group, expected in expected_lengths.items():
        observed = sum(item[4] for item in boundary[group])
        if not close(observed, expected, rel=0.005, abs_tol=0.1):
            raise ValueError("%s plate boundary length is %.9g mm" % (group, observed))
    hole_length = sum(item[4] for item in boundary["hole"])
    if len(boundary["hole"]) < 16 or not close(hole_length, 2.0 * math.pi * 5.0, rel=0.025, abs_tol=0.15):
        raise ValueError("central hole is not a sufficiently resolved radius-5 circular free boundary")
    if any(math.hypot(x - 50.0, y - 100.0) < 4.92 for x, y, _ in nodes.values()):
        raise ValueError("mesh nodes occupy the central hole")

    outer_sizes = [item[4] for group in ("left", "right", "bottom", "top") for item in boundary[group]]
    hole_sizes = [item[4] for item in boundary["hole"]]
    far_field_sizes = []
    for occurrences in edge_occurrences.values():
        sequence = occurrences[0][2]
        first = nodes[sequence[0]]
        last = nodes[sequence[-1]]
        midpoint_x = 0.5 * (first[0] + last[0])
        midpoint_y = 0.5 * (first[1] + last[1])
        if (
            5.0 <= midpoint_x <= 95.0
            and 5.0 <= midpoint_y <= 195.0
            and math.hypot(midpoint_x - 50.0, midpoint_y - 100.0) >= 25.0
        ):
            far_field_sizes.append(polyline_length(sequence, nodes))
    outer_median = statistics.median(outer_sizes)
    hole_median = statistics.median(hole_sizes)
    if not far_field_sizes:
        raise ValueError("mesh has no auditable far-field internal edges")
    far_field_median = statistics.median(far_field_sizes)
    if not (3.5 <= outer_median <= 6.5):
        raise ValueError("outer/global representative edge size %.9g is not approximately 5 mm" % outer_median)
    if not (0.65 <= hole_median <= 1.35):
        raise ValueError("hole-boundary representative edge size %.9g is not approximately 1 mm" % hole_median)
    if not (3.5 <= far_field_median <= 7.5):
        raise ValueError("far-field representative edge size %.9g is not compatible with global size 5 mm" % far_field_median)
    if min(outer_median, far_field_median) / hole_median < 2.5:
        raise ValueError("mesh does not demonstrate distinct global and local refinement scales")

    return {
        "boundary": boundary,
        "edge_occurrences": edge_occurrences,
        "element_by_label": element_by_label,
        "mesh_sha256": mesh_digest(nodes, elements),
        "outer_median": outer_median,
        "far_field_median": far_field_median,
        "hole_median": hole_median,
        "area": area,
    }


def float_tokens(text: str) -> list[float]:
    return [
        float(token.replace("D", "E").replace("d", "e"))
        for token in re.findall(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[EeDd][-+]?\d+)?", text)
    ]


def parse_ansys_cdb(path: Path) -> dict[str, object]:
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    nodes: dict[int, tuple[float, float, float]] = {}
    elements: list[dict[str, object]] = []
    element_types: dict[int, tuple[int, list[int]]] = {}
    real_constants: dict[int, list[float]] = {}
    materials: dict[tuple[int, str], float] = {}
    constraints: list[tuple[int, int, float]] = []
    surface_loads: list[dict[str, object]] = []
    mode = ""
    surface_label = ""
    for line in lines:
        upper = line.upper()
        if upper.startswith("ETBLOCK"):
            mode = "et"
            continue
        if upper.startswith("NBLOCK"):
            mode = "node"
            continue
        if upper.startswith("EBLOCK"):
            mode = "elem"
            continue
        if upper.startswith("RLBLOCK"):
            mode = "real"
            continue
        if upper.startswith("DBLOCK"):
            mode = "constraint"
            continue
        if upper.startswith("SFEBLOCK"):
            fields = [value.strip().upper() for value in line.split(",")]
            surface_label = fields[2] if len(fields) > 2 else ""
            mode = "surface"
            continue
        if line.startswith("("):
            continue
        stripped = line.lstrip()
        if mode and stripped and (stripped[0].isalpha() or stripped[0] in "/*"):
            mode = ""
        if mode and (line.strip() == "-1" or upper.startswith(("N,UNBL", "CMBLOCK", "MPTEMP", "MPDATA", "EXTOPT"))):
            mode = ""
        if mode == "et" and line.strip():
            values = [int(value) for value in re.findall(r"-?\d+", line)]
            if len(values) >= 5 and values[0] > 0:
                element_types[values[0]] = (values[1], values[2:])
            continue
        if mode == "node" and line.strip():
            try:
                label = int(line[:9])
                coordinates = float_tokens(line[27:])
                coordinates += [0.0] * (3 - len(coordinates))
                nodes[label] = tuple(coordinates[:3])
            except Exception:
                pass
            continue
        if mode == "elem" and line.strip():
            values = [int(value) for value in re.findall(r"-?\d+", line)]
            if len(values) >= 12:
                material_id, type_id, real_id = values[0], values[1], values[2]
                node_count = values[8]
                label = values[10]
                connectivity = values[11 : 11 + node_count]
                type_number = element_types.get(type_id, (0, []))[0]
                if type_number == 182 and len(set(connectivity[:4])) == 3:
                    normalized_type = "PLANE182_TRI3"
                    connectivity = list(dict.fromkeys(connectivity[:4]))
                elif type_number == 183 and len(set(connectivity[:4])) == 3:
                    normalized_type = "PLANE183_TRI6"
                    connectivity = list(dict.fromkeys(connectivity))[:6]
                else:
                    normalized_type = "PLANE%d" % type_number
                elements.append(
                    {
                        "label": label,
                        "type": normalized_type,
                        "type_id": type_id,
                        "material_id": material_id,
                        "real_id": real_id,
                        "connectivity": connectivity,
                    }
                )
            continue
        if mode == "real" and line.strip():
            values = float_tokens(line)
            if len(values) >= 3:
                real_constants[int(values[0])] = values[2:]
            continue
        if mode == "constraint" and line.strip():
            match = re.match(r"\s*(\d+)\s+(UX|UY)\s+([-+0-9.EeDd]+)", line, re.I)
            if match:
                constraints.append(
                    (int(match.group(1)), 1 if match.group(2).upper() == "UX" else 2, float(match.group(3).replace("D", "E")))
                )
            continue
        if mode == "surface" and line.strip():
            values = float_tokens(line)
            if len(values) >= 4:
                surface_loads.append(
                    {
                        "label": surface_label,
                        "element": int(values[0]),
                        "face": int(values[1]),
                        "kval": int(values[2]),
                        "values": values[3:],
                    }
                )
            continue
        match = re.match(
            r"MPDATA,[^,]*,\s*(\d+)\s*,\s*(EX|PRXY)\s*,[^,]*,[^,]*,\s*([-+0-9.EeDd]+)",
            line,
            re.I,
        )
        if match:
            materials[(int(match.group(1)), match.group(2).upper())] = float(match.group(3).replace("D", "E"))

    if not nodes or not elements:
        raise ValueError("CDWRITE output does not contain a readable MAPDL mesh")
    return {
        "text": "\n".join(lines),
        "nodes": nodes,
        "elements": elements,
        "element_types": element_types,
        "real_constants": real_constants,
        "materials": materials,
        "constraints": constraints,
        "surface_loads": surface_loads,
    }


def validate_ansys_model(parsed: dict[str, object]) -> dict[str, object]:
    nodes = parsed["nodes"]
    elements = parsed["elements"]
    topology = validate_topology(nodes, elements)
    used_type_ids = {int(element["type_id"]) for element in elements}
    used_material_ids = {int(element["material_id"]) for element in elements}
    used_real_ids = {int(element["real_id"]) for element in elements}
    element_types = parsed["element_types"]
    for type_id in used_type_ids:
        number, keyopts = element_types.get(type_id, (0, []))
        if number not in (182, 183):
            raise ValueError("all active MAPDL elements must be PLANE182/PLANE183")
        keyopt3 = keyopts[2] if len(keyopts) >= 3 else 0
        if keyopt3 != 3:
            raise ValueError("active PLANE182/183 type %d is not plane stress with thickness KEYOPT(3)=3" % type_id)
    materials = parsed["materials"]
    for material_id in used_material_ids:
        young = materials.get((material_id, "EX"))
        poisson = materials.get((material_id, "PRXY"))
        if young is None or poisson is None or not close(young, 210000.0, rel=0.002) or not close(poisson, 0.3, rel=0.002):
            raise ValueError("active MAPDL material %d is not E=210000 MPa, nu=0.3" % material_id)
    real_constants = parsed["real_constants"]
    for real_id in used_real_ids:
        values = real_constants.get(real_id, [])
        if not values or not close(values[0], 1.0, rel=0.002, abs_tol=0.002):
            raise ValueError("active MAPDL real set %d does not specify thickness 1 mm" % real_id)

    valid, reason = validate_minimal_constraints(parsed["constraints"], nodes)
    if not valid:
        raise ValueError(reason)
    text_upper = str(parsed["text"]).upper()
    # CDWRITE does not reliably serialize ANTYPE from a solved database.  The
    # result branch below proves the procedure by forcing a new static solve
    # and comparing its response signature with the submitted RST.
    if re.search(r"^\s*(?:FBLOCK|BFBLOCK)", text_upper, re.M):
        raise ValueError("unexpected nodal/body loads are present")

    boundary = topology["boundary"]
    boundary_keys = {
        group: {item[0] for item in entries}
        for group, entries in boundary.items()
    }
    element_face_to_key = {
        (item[1], item[2]): item[0]
        for entries in boundary.values()
        for item in entries
    }
    real_loads: dict[tuple[int, int], list[float]] = defaultdict(list)
    imaginary_loads: dict[tuple[int, int], list[float]] = defaultdict(list)
    for load in parsed["surface_loads"]:
        if str(load["label"]).upper() != "PRES":
            raise ValueError("only uniform pressure traction is permitted on plate edges")
        key = (int(load["element"]), int(load["face"]))
        values = [float(value) for value in load["values"]]
        if int(load["kval"]) in (0, 1):
            real_loads[key].extend(values)
        elif int(load["kval"]) == 2:
            imaginary_loads[key].extend(values)
        elif any(abs(value) > 1.0e-10 for value in values):
            raise ValueError("unsupported nonzero SFEBLOCK KVAL")
    if any(abs(value) > 1.0e-10 for values in imaginary_loads.values() for value in values):
        raise ValueError("complex pressure components are not valid for this static task")
    classified: dict[str, set[tuple[int, int]]] = defaultdict(set)
    for element_face, values in real_loads.items():
        edge_key = element_face_to_key.get(element_face)
        if edge_key is None:
            raise ValueError("pressure is applied to an internal or unrecognized element face")
        group = next(name for name, keys in boundary_keys.items() if edge_key in keys)
        if group not in ("left", "right"):
            raise ValueError("pressure is applied to %s rather than a vertical tensile edge" % group)
        nonzero = [value for value in values if abs(value) > 1.0e-10]
        if not nonzero or any(not close(value, -10.0, rel=0.005, abs_tol=0.02) for value in nonzero):
            raise ValueError("MAPDL edge pressure must be uniform outward 10 MPa")
        classified[group].add(edge_key)
    for group in ("left", "right"):
        if classified[group] != boundary_keys[group]:
            raise ValueError("MAPDL pressure does not cover the complete %s edge" % group)
        resultant = sum(item[4] for item in boundary[group]) * 10.0
        if not close(resultant, 2000.0, rel=0.005, abs_tol=1.0):
            raise ValueError("%s edge traction resultant is not 2000 N" % group)
    return topology


def _safe_run(mapdl, command: str) -> str:
    value = mapdl.run(command)
    return "" if value is None else str(value)


def _try_get(mapdl, *args):
    try:
        return float(mapdl.get_value(*args))
    except Exception:
        return None


def select_nodes(mapdl, labels: list[int]) -> None:
    mapdl.run("NSEL,NONE")
    for index, label in enumerate(labels):
        mapdl.run("NSEL,%s,NODE,,%d" % ("S" if index == 0 else "A", int(label)))


def extract_ansys_result(mapdl, parsed: dict[str, object]) -> dict[str, float]:
    nodes = parsed["nodes"]
    nnum = [int(value) for value in mapdl.mesh.nnum]
    ux = [float(value) for value in mapdl.post_processing.nodal_displacement("X")]
    sx = [float(value) for value in mapdl.post_processing.nodal_component_stress("X")]
    sy = [float(value) for value in mapdl.post_processing.nodal_component_stress("Y")]
    sxy = [float(value) for value in mapdl.post_processing.nodal_component_stress("XY")]
    if not nnum or not (len(nnum) == len(ux) == len(sx) == len(sy) == len(sxy)):
        raise ValueError("MAPDL result arrays do not match the resumed database mesh")
    if set(nnum) != set(nodes):
        raise ValueError("MAPDL result node labels do not match the resumed database mesh")
    if any(not math.isfinite(value) for array in (ux, sx, sy, sxy) for value in array):
        raise ValueError("MAPDL result contains non-finite values")
    stress_indices = [
        index
        for index in range(len(nnum))
        if abs(sx[index]) + abs(sy[index]) + abs(sxy[index]) > 1.0e-8
    ]
    if len(stress_indices) < max(20, int(0.2 * len(nnum))):
        raise ValueError("MAPDL nodal stress recovery covers too few result-bearing nodes")
    far_sx = [
        sx[index]
        for index in stress_indices
        for label in (nnum[index],)
        if math.hypot(nodes[label][0] - 50.0, nodes[label][1] - 100.0) >= 25.0
        and 10.0 <= nodes[label][0] <= 90.0
    ]
    if not far_sx:
        raise ValueError("cannot extract MAPDL far-field stress signature")
    constrained_nodes = sorted({int(row[0]) for row in parsed["constraints"]})
    mapdl.run("ALLSEL,ALL")
    select_nodes(mapdl, constrained_nodes)
    _safe_run(mapdl, "FSUM")
    reaction_x = _try_get(mapdl, "FSUM", 0, "ITEM", "FX")
    reaction_y = _try_get(mapdl, "FSUM", 0, "ITEM", "FY")
    mapdl.run("ALLSEL,ALL")
    result_time = _try_get(mapdl, "ACTIVE", 0, "SET", "TIME")
    if reaction_x is None or reaction_y is None or result_time is None:
        raise ValueError("cannot extract MAPDL reaction/time result signature")
    return {
        "max_stress": max(sx),
        "stress_concentration_proxy": max(sx) / 10.0,
        "ux_min": min(ux),
        "ux_max": max(ux),
        "ux_span": max(ux) - min(ux),
        "far_sx_median": statistics.median(far_sx),
        "far_stress_node_count": float(len(far_sx)),
        "stress_node_count": float(len(stress_indices)),
        "stress_total_node_count": float(len(nnum)),
        "sy_median": statistics.median(sy[index] for index in stress_indices),
        "sxy_abs_median": statistics.median(abs(sxy[index]) for index in stress_indices),
        "reaction_x": reaction_x,
        "reaction_y": reaction_y,
        "result_time": result_time,
    }


def validate_physics(result: dict[str, float], solver: str) -> None:
    if not (20.0 <= result["max_stress"] <= 42.0):
        raise ValueError("%s maximum X stress is outside the plate-with-hole range" % solver)
    if not (2.0 <= result["stress_concentration_proxy"] <= 4.2):
        raise ValueError("%s stress concentration signature is implausible" % solver)
    if not (0.003 <= result["ux_span"] <= 0.007):
        raise ValueError("%s relative X extension is inconsistent with E=210000 MPa and 10 MPa" % solver)
    if not (7.0 <= result["far_sx_median"] <= 13.0):
        raise ValueError("%s far-field X stress is not approximately 10 MPa" % solver)
    if abs(result["sy_median"]) > 3.0 or result["sxy_abs_median"] > 3.0:
        raise ValueError("%s result does not exhibit a predominantly uniaxial far field" % solver)
    if abs(result["reaction_x"]) > 5.0 or abs(result["reaction_y"]) > 5.0:
        raise ValueError("%s support reactions contradict the balanced two-sided traction" % solver)
    if result["result_time"] <= 0.0:
        raise ValueError("%s result has no completed positive-time load step" % solver)


def compare_native_results(saved: dict[str, float], fresh: dict[str, float], solver: str) -> None:
    for name, rel, abs_tol in (
        ("max_stress", 0.025, 0.25),
        ("ux_span", 0.025, 2.0e-5),
        ("far_sx_median", 0.04, 0.2),
    ):
        if not close(saved[name], fresh[name], rel=rel, abs_tol=abs_tol):
            raise ValueError(
                "%s saved result is stale or mismatched: %s saved=%.9g fresh=%.9g"
                % (solver, name, saved[name], fresh[name])
            )


def ansys_rst_preflight(result_path: Path) -> bool:
    try:
        if not result_path.is_file() or result_path.is_symlink():
            log("ANSYS RST preflight requires a regular, non-symlink result file")
            return False
        size = result_path.stat().st_size
        if size < ANSYS_RST_HEADER_SIZE:
            log("ANSYS RST preflight rejected a truncated header: %d bytes" % size)
            return False
        with result_path.open("rb") as stream:
            header = stream.read(ANSYS_RST_HEADER_SIZE)
    except Exception as exc:
        log("ANSYS RST preflight could not inspect the submitted result: %s" % exc)
        return False
    declared_words = int.from_bytes(header[112:116], "little", signed=False)
    valid = (
        len(header) == ANSYS_RST_HEADER_SIZE
        and header[:4] == b"\x64\x00\x00\x00"
        and header[4:8] == b"\x00\x00\x00\x80"
        and header[12:16] == b"\xff\xff\xff\xff"
        and declared_words > 0
        and declared_words <= size // 4
    )
    if not valid:
        log(
            "ANSYS RST preflight rejected an invalid or truncated binary range: "
            "actual=%d bytes declared=%d words" % (size, declared_words)
        )
    return valid


def read_ansys_rst_mesh(result_path: Path) -> tuple[dict[int, tuple[float, float, float]], list[dict[str, object]]]:
    from ansys.mapdl import reader as pymapdl_reader

    result = pymapdl_reader.read_binary(str(result_path))
    labels = [int(value) for value in result.mesh.nnum]
    rows = [tuple(float(value) for value in row[:3]) for row in result.mesh.nodes]
    if len(labels) != len(set(labels)) or len(labels) != len(rows):
        raise ValueError("RST contains duplicate or incomplete node records")
    nodes = dict(zip(labels, rows))
    if any(
        label <= 0 or len(row) != 3 or any(not math.isfinite(value) for value in row)
        for label, row in nodes.items()
    ):
        raise ValueError("RST contains an invalid node-coordinate record")

    type_codes = {int(row[0]): int(row[1]) for row in result.mesh.ekey}
    elements: list[dict[str, object]] = []
    seen_labels: set[int] = set()
    referenced_nodes: set[int] = set()
    for record in result.mesh.elem:
        type_reference = int(record[1])
        label = int(record[8])
        code = type_codes.get(type_reference)
        if label <= 0 or label in seen_labels or code not in (182, 183):
            raise ValueError("RST contains an unsupported or duplicate element record")
        node_count = 4 if code == 182 else 8
        connectivity = [int(value) for value in record[10 : 10 + node_count]]
        if len(connectivity) != node_count or any(value <= 0 for value in connectivity):
            raise ValueError("RST element connectivity is incomplete")
        if code == 182 and len(set(connectivity[:4])) == 3:
            normalized_type = "PLANE182_TRI3"
            connectivity = list(dict.fromkeys(connectivity[:4]))
        elif code == 183 and len(set(connectivity[:4])) == 3:
            normalized_type = "PLANE183_TRI6"
            connectivity = list(dict.fromkeys(connectivity))[:6]
        else:
            normalized_type = "PLANE%d" % code
        seen_labels.add(label)
        referenced_nodes.update(connectivity)
        elements.append(
            {
                "label": label,
                "type": normalized_type,
                "connectivity": connectivity,
            }
        )
    if not elements or not referenced_nodes.issubset(nodes):
        raise ValueError("RST mesh is empty or references missing node coordinates")
    nodes = {label: nodes[label] for label in referenced_nodes}
    times = [float(value) for value in result.time_values]
    if len(times) != int(result.nsets) or not times or any(not math.isfinite(value) for value in times):
        raise ValueError("RST result-set metadata is incomplete")
    if "ENS :" not in str(result.available_results).upper():
        raise ValueError("RST does not advertise native element-nodal stress")
    return nodes, elements


def compare_ansys_meshes(
    db_nodes: dict[int, tuple[float, float, float]],
    db_elements: list[dict[str, object]],
    rst_nodes: dict[int, tuple[float, float, float]],
    rst_elements: list[dict[str, object]],
) -> None:
    if set(db_nodes) != set(rst_nodes):
        raise ValueError("ANSYS DB and RST node labels do not match")
    for label in db_nodes:
        if any(
            not close(db_nodes[label][index], rst_nodes[label][index], rel=0.0, abs_tol=1.0e-7)
            for index in range(3)
        ):
            raise ValueError("ANSYS DB and RST node coordinates do not match")
    db_signature = {
        int(element["label"]): (
            str(element["type"]),
            tuple(int(value) for value in element["connectivity"]),
        )
        for element in db_elements
    }
    rst_signature = {
        int(element["label"]): (
            str(element["type"]),
            tuple(int(value) for value in element["connectivity"]),
        )
        for element in rst_elements
    }
    if db_signature != rst_signature:
        raise ValueError("ANSYS DB and RST element types/connectivity do not match")


def run_ansys_pair(
    root: Path,
    db_path: Path,
    rst_path: Path,
    reported_metrics: dict[str, float],
) -> bool:
    mapdl = None
    run_dir = Path(tempfile.mkdtemp(prefix="__task13_ansys_eval_", dir=str(root)))
    try:
        if not ansys_rst_preflight(rst_path):
            raise ValueError("submitted ANSYS RST failed binary preflight")
        if not ANSYS_PYTHON_SITE.is_dir():
            raise ValueError("the pinned PyMAPDL site-packages directory is unavailable")
        if str(ANSYS_PYTHON_SITE) not in sys.path:
            sys.path.insert(0, str(ANSYS_PYTHON_SITE))
        from ansys.mapdl.core import launch_mapdl

        mapdl = launch_mapdl(
            exec_file=ANSYS_EXEC,
            jobname="task13_eval",
            run_location=str(run_dir),
            nproc=1,
            override=True,
            cleanup_on_exit=True,
        )
        mapdl.resume(str(db_path.with_suffix("")), "db")
        _safe_run(mapdl, "ALLSEL,ALL")
        _safe_run(mapdl, "CDWRITE,DB,__task13_eval_model,cdb")
        cdb_path = run_dir / "__task13_eval_model.cdb"
        if not is_nonempty(cdb_path):
            raise ValueError("MAPDL could not export a model audit CDB")
        parsed = parse_ansys_cdb(cdb_path)
        topology = validate_ansys_model(parsed)
        log(
            "ANSYS model topology passed: mesh=%s outer=%.4g hole=%.4g"
            % (topology["mesh_sha256"], topology["outer_median"], topology["hole_median"])
        )

        rst_nodes, rst_elements = read_ansys_rst_mesh(rst_path)
        compare_ansys_meshes(parsed["nodes"], parsed["elements"], rst_nodes, rst_elements)
        log("ANSYS DB/RST native mesh consistency passed")

        mapdl.post1()
        mapdl.file(str(rst_path.with_suffix("")), rst_path.suffix.lstrip("."))
        mapdl.set("LAST")
        saved = extract_ansys_result(mapdl, parsed)
        log("ANSYS saved result signature: " + json.dumps(saved, sort_keys=True))
        validate_physics(saved, "ANSYS")

        mapdl.finish()
        _safe_run(mapdl, "/FILNAME,__task13_eval_fresh,1")
        _safe_run(mapdl, "/SOLU")
        _safe_run(mapdl, "ANTYPE,STATIC,NEW")
        _safe_run(mapdl, "NLGEOM,OFF")
        _safe_run(mapdl, "OUTRES,ALL,ALL")
        _safe_run(mapdl, "ALLSEL,ALL")
        solve_output = _safe_run(mapdl, "SOLVE")
        if "ERROR" in solve_output.upper() or "TERMINAT" in solve_output.upper():
            raise ValueError("fresh MAPDL solve did not complete cleanly")
        mapdl.finish()
        mapdl.post1()
        mapdl.file(str(run_dir / "__task13_eval_fresh"), "rst")
        mapdl.set("LAST")
        fresh = extract_ansys_result(mapdl, parsed)
        log("ANSYS fresh result signature: " + json.dumps(fresh, sort_keys=True))
        validate_physics(fresh, "fresh ANSYS")
        compare_native_results(saved, fresh, "ANSYS")
        if not metrics_match(reported_metrics, saved):
            return False
        log(
            "ANSYS DB/RST, fresh solve, equilibrium and metrics passed: max_sx=%.9g Kt=%.9g"
            % (saved["max_stress"], saved["stress_concentration_proxy"])
        )
        return True
    except Exception as exc:
        log("ANSYS pair %s / %s failed: %s" % (db_path.name, rst_path.name, exc))
        return False
    finally:
        if mapdl is not None:
            try:
                mapdl.exit()
            except Exception:
                pass
        shutil.rmtree(run_dir, ignore_errors=True)


ABAQUS_CHECKER = r'''# -*- coding: utf-8 -*-
from __future__ import print_function

import builtins
import hashlib
import json
import math
import os
import shutil
import statistics
import tempfile
import traceback
from collections import defaultdict, deque

from abaqus import *
from abaqusConstants import *
from caeModules import *
from odbAccess import openOdb

CAE_PATH = __CAE_PATH__
ODB_PATH = __ODB_PATH__
ROOT = __ROOT__
RESULT_PATH = __RESULT_PATH__
DETAILS = []


class AuditFailure(Exception):
    pass


def log(message):
    DETAILS.append(str(message))


def require(condition, message):
    if not condition:
        raise AuditFailure(message)


def close(actual, expected, rel=0.02, abs_tol=1.0e-8):
    try:
        return math.isclose(float(actual), float(expected), rel_tol=rel, abs_tol=abs_tol)
    except Exception:
        return False


def finite(value):
    try:
        return math.isfinite(float(value))
    except Exception:
        return False


def median(values):
    rows = sorted(float(value) for value in values)
    require(rows, "cannot calculate an empty median")
    middle = len(rows) // 2
    return rows[middle] if len(rows) % 2 else 0.5 * (rows[middle - 1] + rows[middle])


def mesh_rows(nodes, elements):
    rows = []
    node_map = {}
    for node in nodes:
        xyz = list(node.coordinates)
        while len(xyz) < 3:
            xyz.append(0.0)
        xyz = tuple(float(value) for value in xyz[:3])
        node_map[int(node.label)] = xyz
        rows.append("N:%d:%.10g,%.10g,%.10g" % (int(node.label), xyz[0], xyz[1], xyz[2]))
    element_rows = []
    for element in elements:
        try:
            connectivity = [int(node.label) for node in element.getNodes()]
        except Exception:
            connectivity = [int(value) for value in element.connectivity]
        row = {
            "label": int(element.label),
            "type": str(element.type).upper(),
            "connectivity": connectivity,
        }
        element_rows.append(row)
        rows.append("E:%d:%s:%s" % (row["label"], row["type"], ",".join(str(value) for value in connectivity)))
    rows.sort()
    return node_map, element_rows, hashlib.sha256("\n".join(rows).encode("ascii")).hexdigest()


def edge_sequences(element_type, connectivity):
    etype = element_type.upper()
    if etype == "CPS3":
        return [[connectivity[0], connectivity[1]], [connectivity[1], connectivity[2]], [connectivity[2], connectivity[0]]]
    if etype in ("CPS6", "CPS6M"):
        return [[connectivity[0], connectivity[3], connectivity[1]], [connectivity[1], connectivity[4], connectivity[2]], [connectivity[2], connectivity[5], connectivity[0]]]
    if etype.startswith("CPS4"):
        return [[connectivity[0], connectivity[1]], [connectivity[1], connectivity[2]], [connectivity[2], connectivity[3]], [connectivity[3], connectivity[0]]]
    if etype.startswith("CPS8"):
        return [[connectivity[0], connectivity[4], connectivity[1]], [connectivity[1], connectivity[5], connectivity[2]], [connectivity[2], connectivity[6], connectivity[3]], [connectivity[3], connectivity[7], connectivity[0]]]
    raise AuditFailure("unsupported Abaqus plane-stress element type %s" % element_type)


def corners(element_type, connectivity):
    return connectivity[:3] if element_type.upper() in ("CPS3", "CPS6", "CPS6M") else connectivity[:4]


def edge_length(sequence, nodes):
    return builtins.sum(math.hypot(nodes[sequence[index + 1]][0] - nodes[sequence[index]][0], nodes[sequence[index + 1]][1] - nodes[sequence[index]][1]) for index in range(len(sequence) - 1))


def validate_topology(nodes, elements):
    require(len(nodes) >= 100 and len(elements) >= 100, "mesh is too small for 5/1 mm refinement")
    require(all(str(element["type"]).startswith("CPS") for element in elements), "all active elements must be Abaqus CPS plane-stress elements")
    xs = [point[0] for point in nodes.values()]
    ys = [point[1] for point in nodes.values()]
    zs = [point[2] for point in nodes.values()]
    for actual, expected, label in ((builtins.min(xs), 0.0, "xmin"), (builtins.max(xs), 100.0, "xmax"), (builtins.min(ys), 0.0, "ymin"), (builtins.max(ys), 200.0, "ymax")):
        require(close(actual, expected, rel=0.0, abs_tol=0.02), "geometry %s does not match" % label)
    require(builtins.max(abs(value) for value in zs) <= 0.02, "model is not two-dimensional in global XY")
    used = set()
    node_to_elements = defaultdict(list)
    edge_map = defaultdict(list)
    element_by_label = {}
    area = 0.0
    for element in elements:
        label = int(element["label"])
        conn = [int(value) for value in element["connectivity"]]
        etype = str(element["type"])
        element_by_label[label] = element
        used.update(conn)
        for node in conn:
            node_to_elements[node].append(label)
        polygon = [nodes[node] for node in corners(etype, conn)]
        area += abs(builtins.sum(polygon[index][0] * polygon[(index + 1) % len(polygon)][1] - polygon[(index + 1) % len(polygon)][0] * polygon[index][1] for index in range(len(polygon)))) * 0.5
        for face, sequence in enumerate(edge_sequences(etype, conn), start=1):
            key = tuple(sorted((sequence[0], sequence[-1])))
            edge_map[key].append((label, face, sequence))
    require(used == set(nodes), "mesh contains unused dummy nodes")
    require(close(area, 20000.0 - math.pi * 25.0, rel=0.012, abs_tol=2.0), "plate area does not contain the required radius-5 hole")
    remaining = set(element_by_label)
    queue = deque([next(iter(remaining))])
    visited = set()
    while queue:
        current = queue.popleft()
        if current in visited:
            continue
        visited.add(current)
        for node in element_by_label[current]["connectivity"]:
            queue.extend(node_to_elements[int(node)])
    require(visited == remaining, "mesh contains disconnected structural components")
    boundary = {name: [] for name in ("left", "right", "bottom", "top", "hole")}
    for key, occurrences in edge_map.items():
        if len(occurrences) == 2:
            continue
        require(len(occurrences) == 1, "non-manifold mesh edge")
        label, face, sequence = occurrences[0]
        points = [nodes[node] for node in sequence]
        radii = [math.hypot(point[0] - 50.0, point[1] - 100.0) for point in points]
        if all(abs(point[0]) <= 0.02 for point in points): group = "left"
        elif all(abs(point[0] - 100.0) <= 0.02 for point in points): group = "right"
        elif all(abs(point[1]) <= 0.02 for point in points): group = "bottom"
        elif all(abs(point[1] - 200.0) <= 0.02 for point in points): group = "top"
        elif all(abs(radius - 5.0) <= 0.08 for radius in radii): group = "hole"
        else: raise AuditFailure("unexpected free mesh boundary")
        boundary[group].append((key, label, face, sequence, edge_length(sequence, nodes)))
    for group, expected in (("left", 200.0), ("right", 200.0), ("bottom", 100.0), ("top", 100.0)):
        require(close(builtins.sum(row[4] for row in boundary[group]), expected, rel=0.005, abs_tol=0.1), "%s boundary length mismatch" % group)
    require(len(boundary["hole"]) >= 16 and close(builtins.sum(row[4] for row in boundary["hole"]), 2.0 * math.pi * 5.0, rel=0.025, abs_tol=0.15), "hole boundary is not a resolved radius-5 circle")
    require(not any(math.hypot(x - 50.0, y - 100.0) < 4.92 for x, y, z in nodes.values()), "mesh occupies the hole")
    outer = [row[4] for group in ("left", "right", "bottom", "top") for row in boundary[group]]
    hole = [row[4] for row in boundary["hole"]]
    far_field = []
    for occurrences in edge_map.values():
        sequence = occurrences[0][2]
        first = nodes[sequence[0]]; last = nodes[sequence[-1]]
        midpoint_x = 0.5 * (first[0] + last[0]); midpoint_y = 0.5 * (first[1] + last[1])
        if 5.0 <= midpoint_x <= 95.0 and 5.0 <= midpoint_y <= 195.0 and math.hypot(midpoint_x - 50.0, midpoint_y - 100.0) >= 25.0:
            far_field.append(edge_length(sequence, nodes))
    outer_median = median(outer)
    hole_median = median(hole)
    far_field_median = median(far_field)
    require(3.5 <= outer_median <= 6.5, "representative global edge size is not approximately 5 mm")
    require(0.65 <= hole_median <= 1.35, "representative hole edge size is not approximately 1 mm")
    require(3.5 <= far_field_median <= 7.5, "far-field representative edge size is not compatible with global size 5 mm")
    require(builtins.min(outer_median, far_field_median) / hole_median >= 2.5, "mesh lacks distinct global/local refinement")
    return {"boundary": boundary, "edge_map": edge_map, "outer_median": outer_median, "far_field_median": far_field_median, "hole_median": hole_median, "area": area}


def parse_params(line):
    values = [value.strip() for value in line[1:].split(",")]
    name = values[0].upper()
    params = {}
    flags = set()
    for value in values[1:]:
        if "=" in value:
            key, item = value.split("=", 1)
            params[key.strip().upper()] = item.strip()
        elif value:
            flags.add(value.upper())
    return name, params, flags


def input_cards(path):
    cards = []
    current = None
    with open(path, "r") as stream:
        for raw in stream:
            line = raw.strip()
            if not line or line.startswith("**"):
                continue
            if line.startswith("*"):
                name, params, flags = parse_params(line)
                current = {"name": name, "params": params, "flags": flags, "data": []}
                cards.append(current)
            elif current is not None:
                current["data"].append([value.strip() for value in line.split(",")])
    return cards


def integer_set(cards, keyword, parameter):
    raw = defaultdict(list)
    generated = set()
    for card in cards:
        if card["name"] != keyword or parameter not in card["params"]:
            continue
        name = card["params"][parameter].upper()
        if "GENERATE" in card["flags"]:
            generated.add(name)
        for row in card["data"]:
            raw[name].extend(value for value in row if value)
    resolved = {}
    active = set()
    def resolve(name):
        name = name.upper()
        if name in resolved:
            return resolved[name]
        require(name not in active, "cyclic set definition")
        active.add(name)
        values = raw.get(name, [])
        result = set()
        if name in generated:
            require(len(values) % 3 == 0, "invalid generated set")
            for index in range(0, len(values), 3):
                start, stop, step = [int(float(value)) for value in values[index:index + 3]]
                result.update(range(start, stop + (1 if step > 0 else -1), step))
        else:
            for value in values:
                try: result.add(int(float(value)))
                except Exception: result.update(resolve(value))
        active.remove(name)
        resolved[name] = result
        return result
    for name in raw:
        resolve(name)
    return resolved


def rank(rows, tolerance=1.0e-9):
    work = [list(map(float, row)) for row in rows]
    result = 0
    column = 0
    while result < len(work) and column < len(work[0]):
        pivot = builtins.max(range(result, len(work)), key=lambda row: abs(work[row][column]))
        if abs(work[pivot][column]) <= tolerance:
            column += 1
            continue
        work[result], work[pivot] = work[pivot], work[result]
        divisor = work[result][column]
        work[result] = [value / divisor for value in work[result]]
        for row in range(len(work)):
            if row != result:
                factor = work[row][column]
                work[row] = [work[row][index] - factor * work[result][index] for index in range(len(work[row]))]
        result += 1
        column += 1
    return result


def state_is_active(state):
    status = str(getattr(state, "status", "")).upper()
    return not any(token in status for token in ("DEACTIV", "NOT_YET_ACTIVE", "NO_LONGER_ACTIVE"))


def region_name(region):
    try:
        first = region[0]
    except Exception:
        raise AuditFailure("Abaqus region is not the documented tuple form")
    if isinstance(first, str):
        return first
    try:
        return str(first)
    except Exception:
        raise AuditFailure("Abaqus region tuple has no resolvable repository name")


def state_value_is_zero_constraint(value):
    text = str(value).strip().upper()
    if text in ("SET", "FIXED"):
        return True
    try:
        return abs(float(value)) <= 1.0e-10
    except Exception:
        return False


def state_value_is_unconstrained(value):
    return str(value).strip().upper() in ("UNSET", "FREED", "UNCHANGED", "NONE", "")


def state_component_is_zero_constraint(state, attribute):
    value = getattr(state, attribute, None)
    disposition = getattr(state, attribute + "State", None)
    if disposition is not None:
        text = str(disposition).strip().upper()
        if text in ("SET", "FIXED"):
            require(state_value_is_zero_constraint(value), "%s is active but not fixed at zero" % attribute)
            return True
        if text in ("UNSET", "FREED", "UNCHANGED", "NONE", ""):
            return False
        raise AuditFailure("unrecognized %s disposition %s" % (attribute, text))
    if state_value_is_zero_constraint(value):
        return True
    require(state_value_is_unconstrained(value), "%s contains a nonzero/nonstandard in-plane value" % attribute)
    return False


def region_node_labels(region):
    labels = []
    def visit(value):
        if hasattr(value, "label"):
            labels.append(int(value.label))
            return
        try:
            for item in value:
                visit(item)
        except Exception:
            pass
    visit(region.nodes)
    return sorted(set(labels))


def validate_effective_step_states(model, nodes):
    active_steps = [model.steps[name] for name in model.steps.keys() if str(model.steps[name].__class__.__name__).upper() == "STATICSTEP"]
    require(len(active_steps) == 1, "CAE must contain exactly one StaticStep")
    step = active_steps[0]
    assembly = model.rootAssembly

    effective_loads = []
    for name in step.loadStates.keys():
        state = step.loadStates[name]
        if not state_is_active(state):
            continue
        require(name in model.loads.keys(), "active load state has no model load object")
        load = model.loads[name]
        class_name = str(load.__class__.__name__).upper()
        require(class_name in ("PRESSURE", "SURFACETRACTION"), "active load must be Pressure or SurfaceTraction")
        if class_name == "SURFACETRACTION":
            traction = str(getattr(load, "traction", getattr(state, "traction", ""))).upper()
            require("GENERAL" in traction, "SurfaceTraction must use GENERAL traction, not shear-only traction")
        magnitude = getattr(state, "magnitude", None)
        require(finite(magnitude), "active load magnitude must come from the static-step LoadState")
        name_in_repo = region_name(load.region)
        require(name_in_repo in assembly.allSurfaces.keys(), "load region tuple does not resolve through assembly.allSurfaces")
        surface = assembly.allSurfaces[name_in_repo]
        require(len(surface.elements) > 0, "active traction surface is empty")
        log("load state %s class=%s status=%r magnitude=%r region=%r" % (name, class_name, getattr(state, "status", None), magnitude, load.region))
        effective_loads.append((name, class_name, float(magnitude), name_in_repo))
    require(len(effective_loads) == 2, "static step must have exactly two active vertical-edge tractions")

    effective_constraints = []
    for name in step.boundaryConditionStates.keys():
        state = step.boundaryConditionStates[name]
        if not state_is_active(state):
            continue
        require(name in model.boundaryConditions.keys(), "active BC state has no model BC object")
        bc = model.boundaryConditions[name]
        name_in_repo = region_name(bc.region)
        require(name_in_repo in assembly.allSets.keys(), "BC region tuple does not resolve through assembly.allSets")
        region = assembly.allSets[name_in_repo]
        labels = region_node_labels(region)
        require(labels, "active BC set is empty")
        log(
            "BC state %s class=%s status=%r state_u1=%r state_u2=%r u1State=%r u2State=%r bc_u1=%r bc_u2=%r region=%r labels=%r"
            % (
                name,
                str(bc.__class__.__name__),
                getattr(state, "status", None),
                getattr(state, "u1", None),
                getattr(state, "u2", None),
                getattr(state, "u1State", None),
                getattr(state, "u2State", None),
                getattr(bc, "u1", None),
                getattr(bc, "u2", None),
                bc.region,
                labels,
            )
        )
        for dof, attribute in ((1, "u1"), (2, "u2")):
            if state_component_is_zero_constraint(state, attribute):
                for label in labels:
                    effective_constraints.append((label, dof, 0.0))
    unique = set((node, dof) for node, dof, value in effective_constraints)
    require(len(unique) == 3, "static-step BoundaryConditionStates must resolve to exactly three constrained DOFs")
    rigid_rows = []
    for node, dof in unique:
        require(node in nodes, "BC state region contains a node outside the active plate")
        x, y, z = nodes[node]
        rigid_rows.append([1.0, 0.0, -y] if dof == 1 else [0.0, 1.0, x])
    require(rank(rigid_rows) == 3, "effective static-step BC states do not remove exactly three rigid modes")


def validate_input(path, nodes, elements, topology):
    cards = input_cards(path)
    elsets = integer_set(cards, "ELSET", "ELSET")
    nsets = integer_set(cards, "NSET", "NSET")
    materials = {}
    current_material = None
    for card in cards:
        if card["name"] == "MATERIAL":
            current_material = card["params"].get("NAME", "").upper()
            materials.setdefault(current_material, {})
        elif card["name"] == "ELASTIC" and current_material:
            require(len(card["data"]) == 1 and len(card["data"][0]) >= 2, "elastic material must have one isotropic E,nu row")
            materials[current_material]["elastic"] = [float(card["data"][0][0]), float(card["data"][0][1])]
    all_elements = set(int(element["label"]) for element in elements)
    coverage = defaultdict(int)
    sections = [card for card in cards if card["name"] == "SOLID SECTION"]
    require(sections, "no Abaqus solid section assignment")
    for card in sections:
        set_name = card["params"].get("ELSET", "").upper()
        material_name = card["params"].get("MATERIAL", "").upper()
        assigned = elsets.get(set_name, set()) & all_elements
        require(assigned, "solid section does not bind active plate elements")
        elastic = materials.get(material_name, {}).get("elastic")
        require(elastic and close(elastic[0], 210000.0, rel=0.002) and close(elastic[1], 0.3, rel=0.002), "active section material is not E=210000 MPa, nu=0.3")
        require(card["data"] and card["data"][0] and close(float(card["data"][0][0]), 1.0, rel=0.002, abs_tol=0.002), "active plane-stress section thickness is not 1 mm")
        for label in assigned:
            coverage[label] += 1
    require(set(coverage) == all_elements and all(value == 1 for value in coverage.values()), "every active plate element must have exactly one correct material/section")

    static_cards = [card for card in cards if card["name"] == "STATIC"]
    require(len(static_cards) == 1, "expected exactly one static analysis step")
    require(not any(card["name"] in ("DYNAMIC", "FREQUENCY", "BUCKLE") for card in cards), "non-static analysis keyword present")

    constraints = []
    for card in cards:
        if card["name"] != "BOUNDARY":
            continue
        require(not card["params"].get("TYPE"), "typed/kinematic boundary form is not a minimum point support")
        for row in card["data"]:
            require(len(row) >= 2, "invalid boundary row")
            target = row[0].upper()
            try: selected = {int(float(target))}
            except Exception: selected = nsets.get(target, set())
            require(selected, "boundary target cannot be resolved")
            first = int(float(row[1]))
            last = int(float(row[2])) if len(row) > 2 and row[2] else first
            value = float(row[3]) if len(row) > 3 and row[3] else 0.0
            for node in selected:
                for dof in range(first, last + 1):
                    constraints.append((node, dof, value))
    unique = {}
    for node, dof, value in constraints:
        require(dof in (1, 2) and abs(value) <= 1.0e-10, "only zero UX/UY point constraints are permitted")
        require((node, dof) not in unique or close(unique[(node, dof)], value, rel=0.0, abs_tol=1.0e-10), "conflicting constraints")
        unique[(node, dof)] = value
    require(len(unique) == 3 and len(set(node for node, dof in unique)) == 2, "expected exactly three in-plane DOFs at two support nodes")
    rigid_rows = []
    for node, dof in unique:
        require(node in nodes, "constraint target is not an active plate node")
        x, y, z = nodes[node]
        rigid_rows.append([1.0, 0.0, -y] if dof == 1 else [0.0, 1.0, x])
    require(rank(rigid_rows) == 3, "constraints do not remove exactly the three 2D rigid modes")

    surfaces = defaultdict(list)
    for card in cards:
        if card["name"] == "SURFACE":
            name = card["params"].get("NAME", "").upper()
            for row in card["data"]:
                if len(row) >= 2:
                    surfaces[name].append((row[0].upper(), row[1].upper()))
    element_by_label = {int(element["label"]): element for element in elements}
    boundary = topology["boundary"]
    boundary_keys = {name: set(item[0] for item in rows) for name, rows in boundary.items()}
    face_to_key = {(item[1], item[2]): item[0] for rows in boundary.values() for item in rows}
    loaded = defaultdict(set)
    mechanical_cards = [card for card in cards if card["name"] in ("DSLOAD", "DLOAD", "CLOAD")]
    require(mechanical_cards, "no tensile load in static step")
    for card in mechanical_cards:
        require(card["name"] == "DSLOAD", "uniform edge traction must use a distributed surface load")
        for row in card["data"]:
            require(len(row) >= 3, "invalid DSLOAD row")
            surface_name = row[0].upper()
            load_type = row[1].upper()
            require(load_type in ("P", "TRVEC"), "unsupported Abaqus traction type")
            surface_rows = surfaces.get(surface_name, [])
            require(surface_rows, "DSLOAD surface cannot be resolved")
            edge_keys = set()
            for set_name, side_name in surface_rows:
                require(side_name.startswith("S") and side_name[1:].isdigit(), "unsupported surface side")
                face = int(side_name[1:])
                selected = elsets.get(set_name, set())
                require(selected, "surface element set cannot be resolved")
                for label in selected:
                    key = face_to_key.get((label, face))
                    require(key is not None, "traction surface contains an internal/non-boundary face")
                    edge_keys.add(key)
            groups = [name for name, keys in boundary_keys.items() if edge_keys and edge_keys <= keys]
            require(len(groups) == 1 and groups[0] in ("left", "right"), "traction must lie entirely on one vertical outer edge")
            group = groups[0]
            magnitude = float(row[2])
            if load_type == "P":
                require(close(magnitude, -10.0, rel=0.005, abs_tol=0.02), "pressure must be outward 10 MPa")
            else:
                require(len(row) >= 5, "TRVEC direction is missing")
                direction = [float(value) for value in row[3:5]]
                length = math.hypot(direction[0], direction[1])
                require(length > 0.0, "TRVEC direction is zero")
                vector_x = magnitude * direction[0] / length
                vector_y = magnitude * direction[1] / length
                expected_x = -10.0 if group == "left" else 10.0
                require(close(vector_x, expected_x, rel=0.005, abs_tol=0.02) and abs(vector_y) <= 0.02, "TRVEC is not the required +/-X 10 MPa traction")
            loaded[group].update(edge_keys)
    for group in ("left", "right"):
        require(loaded[group] == boundary_keys[group], "traction does not cover the complete %s edge" % group)
        require(close(builtins.sum(row[4] for row in boundary[group]) * 10.0, 2000.0, rel=0.005, abs_tol=1.0), "%s edge resultant is not 2000 N" % group)


def extract_odb(path, expected_digest):
    odb = openOdb(path=path, readOnly=True)
    try:
        status = str(getattr(odb.diagnosticData, "jobStatus", "")).upper()
        require(status and "COMPLETED" in status and "ABORT" not in status and "TERMINAT" not in status, "ODB job is not completed")
        instances = [odb.rootAssembly.instances[name] for name in odb.rootAssembly.instances.keys() if len(odb.rootAssembly.instances[name].elements)]
        require(len(instances) == 1, "ODB must contain exactly one active structural instance")
        nodes, elements, digest = mesh_rows(instances[0].nodes, instances[0].elements)
        require(digest == expected_digest, "CAE and ODB mesh/connectivity signatures do not match")
        active_steps = [odb.steps[name] for name in odb.steps.keys() if len(odb.steps[name].frames) > 1]
        require(len(active_steps) == 1, "ODB does not contain exactly one completed analysis step")
        frame = active_steps[0].frames[-1]
        require("S" in frame.fieldOutputs and "U" in frame.fieldOutputs and "RF" in frame.fieldOutputs, "ODB is missing S/U/RF output")
        stress = frame.fieldOutputs["S"]
        nodal_values = []
        try:
            stored_nodal = stress.getSubset(position=NODAL)
            nodal_values = list(stored_nodal.values)
        except Exception:
            nodal_values = []
        if not nodal_values:
            try:
                extrapolated = stress.getSubset(position=ELEMENT_NODAL, readOnly=ON)
                nodal_values = list(extrapolated.values)
            except Exception:
                nodal_values = []
        require(nodal_values, "ODB has neither stored NODAL stress nor readable ELEMENT_NODAL extrapolation")
        accumulators = defaultdict(lambda: [0.0, 0.0, 0.0, 0])
        for value in nodal_values:
            label = getattr(value, "nodeLabel", None)
            data = list(value.data)
            if label is None or len(data) < 3 or not all(finite(item) for item in data[:3]):
                continue
            row = accumulators[int(label)]
            row[0] += float(data[0]); row[1] += float(data[1]); row[2] += float(data[2]); row[3] += 1
        require(accumulators, "ODB nodal stress recovery contains no labeled finite values")
        averaged = {
            label: (row[0] / row[3], row[1] / row[3], row[2] / row[3])
            for label, row in accumulators.items() if row[3] > 0
        }
        require(set(averaged) <= set(nodes) and len(averaged) >= int(0.95 * len(nodes)), "ODB nodal stress recovery does not cover the CAE mesh")
        s11 = [row[0] for row in averaged.values()]
        s22 = [row[1] for row in averaged.values()]
        s12 = [row[2] for row in averaged.values()]
        far_s11 = [
            averaged[label][0]
            for label in averaged
            if math.hypot(nodes[label][0] - 50.0, nodes[label][1] - 100.0) >= 25.0
            and 10.0 <= nodes[label][0] <= 90.0
        ]
        require(far_s11, "ODB nodal stresses have no far-field sample")
        ux = [float(value.data[0]) for value in frame.fieldOutputs["U"].values if len(value.data) and finite(value.data[0])]
        require(ux, "ODB displacement data is incomplete")
        reactions = [list(value.data) for value in frame.fieldOutputs["RF"].values]
        reaction_x = builtins.sum(float(value[0]) for value in reactions if len(value) >= 1 and finite(value[0]))
        reaction_y = builtins.sum(float(value[1]) for value in reactions if len(value) >= 2 and finite(value[1]))
        return {
            "max_stress": builtins.max(s11),
            "stress_concentration_proxy": builtins.max(s11) / 10.0,
            "ux_min": builtins.min(ux),
            "ux_max": builtins.max(ux),
            "ux_span": builtins.max(ux) - builtins.min(ux),
            "far_sx_median": median(far_s11),
            "sy_median": median(s22),
            "sxy_abs_median": median(abs(value) for value in s12),
            "reaction_x": reaction_x,
            "reaction_y": reaction_y,
            "result_time": float(frame.frameValue),
            "mesh_sha256": digest,
        }
    finally:
        odb.close()


def validate_physics(result, label):
    require(20.0 <= result["max_stress"] <= 42.0, "%s maximum S11 outside physical range" % label)
    require(2.0 <= result["stress_concentration_proxy"] <= 4.2, "%s Kt outside physical range" % label)
    require(0.003 <= result["ux_span"] <= 0.007, "%s relative extension inconsistent with E/load" % label)
    require(7.0 <= result["far_sx_median"] <= 13.0, "%s median S11 is not approximately 10 MPa" % label)
    require(abs(result["sy_median"]) <= 3.0 and result["sxy_abs_median"] <= 3.0, "%s stress field is not predominantly uniaxial" % label)
    require(abs(result["reaction_x"]) <= 5.0 and abs(result["reaction_y"]) <= 5.0, "%s reactions contradict balanced two-sided traction" % label)
    require(result["result_time"] > 0.0, "%s result has no positive-time final frame" % label)


def compare_results(saved, fresh):
    for name, rel, abs_tol in (("max_stress", 0.025, 0.25), ("ux_span", 0.025, 2.0e-5), ("far_sx_median", 0.04, 0.2)):
        require(close(saved[name], fresh[name], rel=rel, abs_tol=abs_tol), "saved ODB is stale/mismatched for %s" % name)


def evaluate_model(model):
    instances = [model.rootAssembly.instances[name] for name in model.rootAssembly.instances.keys() if len(model.rootAssembly.instances[name].elements)]
    require(len(instances) == 1, "CAE must contain exactly one active meshed plate instance")
    nodes, elements, digest = mesh_rows(instances[0].nodes, instances[0].elements)
    topology = validate_topology(nodes, elements)
    validate_effective_step_states(model, nodes)
    run_dir = tempfile.mkdtemp(prefix="__task13_abaqus_eval_", dir=ROOT)
    old_cwd = os.getcwd()
    job_name = "Task13EvalFresh"
    try:
        try:
            if mdb.jobs.has_key(job_name): del mdb.jobs[job_name]
        except Exception: pass
        job = mdb.Job(name=job_name, model=model.name, type=ANALYSIS, numCpus=1, numDomains=1)
        os.chdir(run_dir)
        job.writeInput(consistencyChecking=ON)
        input_path = os.path.join(run_dir, job_name + ".inp")
        require(os.path.isfile(input_path) and os.path.getsize(input_path) > 0, "Abaqus could not write a fresh solver input")
        validate_input(input_path, nodes, elements, topology)
        job.submit(consistencyChecking=ON)
        job.waitForCompletion()
        fresh_odb = os.path.join(run_dir, job_name + ".odb")
        require(os.path.isfile(fresh_odb) and os.path.getsize(fresh_odb) > 0, "fresh Abaqus solve produced no ODB")
        saved = extract_odb(ODB_PATH, digest)
        fresh = extract_odb(fresh_odb, digest)
        validate_physics(saved, "saved ODB")
        validate_physics(fresh, "fresh ODB")
        compare_results(saved, fresh)
        saved["topology"] = {"outer_median": topology["outer_median"], "far_field_median": topology["far_field_median"], "hole_median": topology["hole_median"], "area": topology["area"]}
        return saved
    finally:
        os.chdir(old_cwd)
        shutil.rmtree(run_dir, ignore_errors=True)


def main():
    payload = {"ok": False, "details": DETAILS}
    try:
        openMdb(pathName=CAE_PATH)
        failures = []
        for name in mdb.models.keys():
            model = mdb.models[name]
            try:
                result = evaluate_model(model)
                payload = {"ok": True, "details": DETAILS, "model": str(name), "result": result}
                break
            except Exception as exc:
                failures.append("%s: %s\n%s" % (name, exc, traceback.format_exc()))
        if not payload["ok"]:
            raise AuditFailure("; ".join(failures) if failures else "CAE contains no model")
    except Exception:
        payload = {"ok": False, "details": DETAILS, "error": traceback.format_exc()}
    with open(RESULT_PATH, "w") as stream:
        json.dump(payload, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print("True" if payload["ok"] else "False")


if __name__ == "__main__":
    main()
'''


def formatted_abaqus_checker(cae_path: Path, odb_path: Path, root: Path, result_path: Path) -> str:
    return (
        ABAQUS_CHECKER.replace("__CAE_PATH__", repr(str(cae_path)))
        .replace("__ODB_PATH__", repr(str(odb_path)))
        .replace("__ROOT__", repr(str(root)))
        .replace("__RESULT_PATH__", repr(str(result_path)))
    )


def run_abaqus_pair(
    root: Path,
    cae_path: Path,
    odb_path: Path,
    reported_metrics: dict[str, float],
) -> bool:
    work_dir = Path(tempfile.mkdtemp(prefix="__task13_abaqus_launcher_", dir=str(root)))
    checker_path = work_dir / "checker.py"
    result_path = work_dir / "result.json"
    try:
        checker_path.write_text(
            formatted_abaqus_checker(cae_path, odb_path, root, result_path),
            encoding="utf-8",
        )
        completed = subprocess.run(
            [ABAQUS_COMMAND, "cae", "noGUI=" + str(checker_path)],
            cwd=str(work_dir),
            text=True,
            capture_output=True,
            timeout=1200,
            shell=False,
        )
        if completed.stdout:
            log("Abaqus checker stdout tail: " + completed.stdout[-1200:])
        if completed.stderr:
            log("Abaqus checker stderr tail: " + completed.stderr[-1200:])
        if completed.returncode != 0 or not is_nonempty(result_path):
            log("Abaqus checker failed for %s / %s" % (cae_path.name, odb_path.name))
            return False
        payload = json.loads(result_path.read_text(encoding="utf-8"))
        if payload.get("details"):
            log("Abaqus checker details: " + json.dumps(payload["details"], sort_keys=True))
        if not payload.get("ok"):
            log("Abaqus pair %s / %s failed: %s" % (cae_path.name, odb_path.name, payload.get("error", "unknown error")))
            return False
        result = payload.get("result", {})
        extracted = {
            "max_stress": float(result["max_stress"]),
            "stress_concentration_proxy": float(result["stress_concentration_proxy"]),
        }
        if not metrics_match(reported_metrics, extracted):
            return False
        log(
            "Abaqus CAE/ODB, fresh solve, equilibrium and metrics passed: max_s11=%.9g Kt=%.9g"
            % (extracted["max_stress"], extracted["stress_concentration_proxy"])
        )
        return True
    except Exception as exc:
        log("Abaqus pair %s / %s failed: %s" % (cae_path.name, odb_path.name, exc))
        return False
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


def write_outputs(root: Path, passed: bool) -> None:
    try:
        (root / "eval_detail.txt").write_text("\n".join(DETAILS) + "\n", encoding="utf-8")
        (root / "eval_result.txt").write_text("True\n" if passed else "False\n", encoding="utf-8")
    except Exception:
        pass


def evaluate() -> tuple[bool, Path]:
    root = desktop_dir()
    reported = read_metrics(root)
    if reported is None:
        return False, root
    pair = unique_native_pair(root)
    if pair is None:
        return False, root
    solver, model_path, result_path = pair
    if solver == "abaqus":
        cae_path, odb_path = model_path, result_path
        log("trying Abaqus pair %s / %s" % (cae_path.name, odb_path.name))
        if run_abaqus_pair(root, cae_path, odb_path, reported):
            return True, root
    else:
        db_path, rst_path = model_path, result_path
        log("trying ANSYS pair %s / %s" % (db_path.name, rst_path.name))
        if run_ansys_pair(root, db_path, rst_path, reported):
            return True, root
    log("the unique native solver pair did not pass its internal validation")
    return False, root


def self_test() -> int:
    import copy

    dummy = formatted_abaqus_checker(
        Path("C:/dummy/model.cae"),
        Path("C:/dummy/result.odb"),
        Path("C:/dummy"),
        Path("C:/dummy/result.json"),
    )
    compile(dummy, "<embedded-abaqus-checker>", "exec")
    assert matrix_rank([[1, 0, 0], [0, 1, 0], [0, 1, 100]]) == 3
    assert metrics_match(
        {"max_stress": 30.2, "stress_concentration_proxy": 3.02},
        {"max_stress": 30.2, "stress_concentration_proxy": 3.02},
    )
    local_cdb = Path(__file__).resolve().parent / "task13_native" / "ansys_candidate_attempt4" / "Task13-Plate-With-Hole.cdb"
    if local_cdb.is_file():
        parsed = parse_ansys_cdb(local_cdb)
        topology = validate_ansys_model(parsed)
        def expect_rejected(mutator) -> None:
            candidate = copy.deepcopy(parsed)
            mutator(candidate)
            try:
                validate_ansys_model(candidate)
            except ValueError:
                return
            raise AssertionError("negative CDB mutation was not rejected")

        def bad_keyopt(candidate) -> None:
            type_id = next(iter(candidate["element_types"]))
            number, options = candidate["element_types"][type_id]
            options[2] = 0
            candidate["element_types"][type_id] = (number, options)

        def bad_thickness(candidate) -> None:
            real_id = next(iter(candidate["real_constants"]))
            candidate["real_constants"][real_id][0] = 10.0

        def bad_material(candidate) -> None:
            material_id = next(iter({int(row["material_id"]) for row in candidate["elements"]}))
            candidate["materials"][(material_id, "EX")] = 70000.0

        def overconstrained(candidate) -> None:
            candidate["constraints"].append((3, 1, 0.0))

        def bad_pressure(candidate) -> None:
            for load in candidate["surface_loads"]:
                if int(load["kval"]) in (0, 1):
                    for index, value in enumerate(load["values"]):
                        if abs(float(value)) > 1.0e-10:
                            load["values"][index] = -5.0
                            return

        for mutator in (bad_keyopt, bad_thickness, bad_material, overconstrained, bad_pressure):
            expect_rejected(mutator)
        print(
            "self-test passed: embedded checker compiled; ANSYS CDB topology=%s outer=%.6g hole=%.6g; five threat mutations rejected"
            % (topology["mesh_sha256"], topology["outer_median"], topology["hole_median"])
        )
    else:
        print("self-test passed: embedded checker compiled; no local Task-13 CDB fixture")
    return 0


def main() -> int:
    if len(sys.argv) == 2 and sys.argv[1] == "--self-test":
        return self_test()
    passed, root = evaluate()
    write_outputs(root, passed)
    sys.stdout.write("True\n" if passed else "False\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
