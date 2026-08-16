# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
from collections import defaultdict
from pathlib import Path


TASK_ID = "c-open-abaqus-ansys-autocad-task-08-windows"
DESKTOP = Path(os.environ.get("USERPROFILE", r"C:\Users\user")) / "Desktop"
ANSYS_EXEC = Path(r"C:\Program Files\ANSYS Inc\v261\ansys\bin\winx64\ANSYS261.exe")
ABAQUS_COMMAND = Path(r"C:\SIMULIA\Commands\abaqus.bat")
METRIC_KEYS = {
    "max_contact_pressure",
    "vertical_displacement",
    "reaction_force",
}
SOLID_ELEMENT_NUMBERS = {185, 186, 187, 285}
TARGET_ELEMENT_NUMBER = 170
CONTACT_ELEMENT_NUMBERS = {173, 174}
DETAILS = []


class EvaluationError(RuntimeError):
    pass


def log(message):
    DETAILS.append(str(message))


def require(condition, message):
    if not condition:
        raise EvaluationError(message)


def finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def close(actual, expected, *, rel=1.0e-5, abs_tol=1.0e-8):
    return math.isclose(float(actual), float(expected), rel_tol=rel, abs_tol=abs_tol)


def read_metrics(path):
    require(path.is_file() and path.stat().st_size > 0, "metrics.json is missing")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise EvaluationError("metrics.json is invalid JSON: %s" % exc)
    require(isinstance(payload, dict), "metrics.json must be one JSON object")
    require(METRIC_KEYS <= set(payload), "metrics.json is missing a requested metric field")
    require(all(finite_number(payload[name]) for name in METRIC_KEYS), "metrics must be finite JSON numbers")
    result = {name: float(payload[name]) for name in METRIC_KEYS}
    require(result["max_contact_pressure"] > 0.0, "max_contact_pressure must be positive")
    require(result["vertical_displacement"] < 0.0, "vertical_displacement must be downward")
    require(result["reaction_force"] > 0.0, "reaction_force must be positive upward")
    return result


def file_is_nonempty(path, minimum=1):
    try:
        return path.is_file() and path.stat().st_size >= minimum
    except Exception:
        return False


def choose_branch(root):
    ansys = [root / "Job-Contact.db", root / "Job-Contact.rst"]
    abaqus = [root / "Job-Contact.cae", root / "Job-Contact.odb"]
    ansys_present = [path.exists() for path in ansys]
    abaqus_present = [path.exists() for path in abaqus]
    require(not any(abaqus_present), "Abaqus 2025LE cannot solve the specified 1586-node mesh; submit the ANSYS v261 pair")
    require(all(ansys_present), "submit the complete Job-Contact.db/rst ANSYS pair")
    require(file_is_nonempty(ansys[0], 100000), "Job-Contact.db is missing or implausibly small")
    require(file_is_nonempty(ansys[1], 100000), "Job-Contact.rst is missing or implausibly small")
    return "ansys", ansys


def sanitized_solver_environment(work):
    env = dict(os.environ)
    for key in list(env):
        upper = key.upper()
        if upper in {
            "APDL_STARTUP",
            "ANSYS_APDL_STARTUP",
            "ANSYS_MACROLIB",
            "ANSYS_CUSTOMIZATIONS",
            "PYTHONHOME",
            "PYTHONPATH",
        }:
            env.pop(key, None)
    temp = work / "temp"
    temp.mkdir(exist_ok=True)
    env["TEMP"] = str(temp)
    env["TMP"] = str(temp)
    env["ANSYS_LOCK"] = "OFF"
    return env


def run_ansys(work, jobname, script_text, timeout=900):
    require(ANSYS_EXEC.is_file(), "ANSYS v261 executable is unavailable")
    script = work / (jobname + ".inp")
    output = work / (jobname + ".out")
    script.write_text(script_text, encoding="ascii")
    command = [
        str(ANSYS_EXEC),
        "-b",
        "-smp",
        "-np",
        "1",
        "-j",
        jobname,
        "-dir",
        str(work),
        "-i",
        str(script),
        "-o",
        str(output),
    ]
    started = time.time()
    completed = subprocess.run(
        command,
        cwd=str(work),
        env=sanitized_solver_environment(work),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout,
        shell=False,
    )
    text = output.read_text(encoding="utf-8", errors="replace") if output.is_file() else ""
    require(completed.returncode == 0, "%s returned %s" % (jobname, completed.returncode))
    upper_text = text.upper()
    require("RELEASE 2026 R1" in upper_text and "BUILD" in upper_text and "26.1" in upper_text, "%s did not run in ANSYS 2026 R1 v261" % jobname)
    require("RUN COMPLETED" in upper_text, "%s did not complete" % jobname)
    require("NUMBER OF ERROR   MESSAGES ENCOUNTERED=          0" in upper_text, "%s reported MAPDL errors" % jobname)
    log("%s completed in %.3fs" % (jobname, time.time() - started))
    return text


def apdl_path(path):
    return str(path.with_suffix("")).replace("'", "''")


def audit_model_to_cdb(work, db_path):
    script = r"""/BATCH
/CLEAR,NOSTART
/ABBR,DELE,ALL
/PSEARCH,OFF
RESUME,'%s','db'
/PSEARCH,OFF
/PREP7
ALLSEL,ALL
CDWRITE,DB,task08_model,cdb
FINISH
/EXIT,NOSAVE
""" % apdl_path(db_path)
    run_ansys(work, "task08_model_audit", script)
    cdb = work / "task08_model.cdb"
    require(file_is_nonempty(cdb, 10000), "ANSYS DB audit did not create a usable CDB")
    return cdb


def int_fields(line, width=9):
    values = []
    for index in range(0, len(line), width):
        field = line[index:index + width].strip()
        if field:
            values.append(int(field))
    return values


def integer_tokens(line):
    return [int(value) for value in re.findall(r"[-+]?\d+", line)]


def parse_cdb(path):
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    text = "\n".join(lines)
    element_types = {}
    nodes = {}
    elements = {}
    constraints = []
    pressures = []
    real_constants = {}

    index = 0
    while index < len(lines):
        line = lines[index]
        upper = line.upper()
        if upper.startswith("ETBLOCK,"):
            index += 2
            while index < len(lines) and lines[index].strip() != "-1":
                values = integer_tokens(lines[index])
                if len(values) >= 2:
                    element_types[values[0]] = {
                        "number": values[1],
                        "keyopts": (values[2:] + [0] * 19)[:19],
                    }
                index += 1
        elif upper.startswith("NBLOCK,"):
            index += 2
            while index < len(lines) and not lines[index].upper().startswith("N,UNBL"):
                row = lines[index]
                try:
                    node_id = int(row[0:9])
                    xyz = []
                    for start in (27, 48, 69):
                        value = row[start:start + 21].strip()
                        xyz.append(float(value.replace("D", "E")) if value else 0.0)
                    nodes[node_id] = tuple(xyz)
                except Exception:
                    raise EvaluationError("cannot parse NBLOCK row")
                index += 1
        elif upper.startswith("EBLOCK,"):
            index += 2
            while index < len(lines) and lines[index].strip() != "-1":
                values = integer_tokens(lines[index])
                require(len(values) >= 11, "cannot parse EBLOCK header")
                count = values[8]
                while len(values) < 11 + count:
                    index += 1
                    require(index < len(lines), "truncated EBLOCK connectivity")
                    values.extend(integer_tokens(lines[index]))
                element_id = values[10]
                elements[element_id] = {
                    "material": values[0],
                    "type": values[1],
                    "real": values[2],
                    "nodes": values[11:11 + count],
                }
                index += 1
            continue
        elif upper.startswith("DBLOCK,"):
            index += 2
            while index < len(lines) and lines[index].strip() != "-1":
                fields = lines[index].split()
                if len(fields) >= 3:
                    constraints.append((int(fields[0]), fields[1].upper(), float(fields[2].replace("D", "E"))))
                index += 1
        elif upper.startswith("RLBLOCK,"):
            index += 3
            while index < len(lines):
                fields = lines[index].split()
                if len(fields) < 2 or not re.match(r"^[-+]?\d+$", fields[0]) or not re.match(r"^\d+$", fields[1]):
                    break
                real_id = int(fields[0])
                count = int(fields[1])
                values = [float(value.replace("D", "E").replace("d", "e")) for value in fields[2:]]
                while len(values) < count:
                    index += 1
                    require(index < len(lines), "truncated RLBLOCK record")
                    values.extend(float(value.replace("D", "E").replace("d", "e")) for value in lines[index].split())
                real_constants[real_id] = values[:count]
                index += 1
            continue
        elif upper.startswith("SFEBLOCK,") and ",PRES," in upper:
            index += 2
            while index < len(lines) and not lines[index].upper().startswith("SFE,END"):
                fields = lines[index].split()
                if len(fields) >= 4:
                    pressures.append({
                        "element": int(fields[0]),
                        "face": int(fields[1]),
                        "kind": int(fields[2]),
                        "values": [float(value.replace("D", "E")) for value in fields[3:]],
                    })
                index += 1
        index += 1

    return {
        "lines": lines,
        "text": text,
        "element_types": element_types,
        "nodes": nodes,
        "elements": elements,
        "constraints": constraints,
        "pressures": pressures,
        "real_constants": real_constants,
    }


def bbox(node_ids, nodes):
    xyz = [nodes[node_id] for node_id in node_ids]
    return tuple((min(row[axis] for row in xyz), max(row[axis] for row in xyz)) for axis in range(3))


def bbox_matches(actual, expected, tolerance=1.0e-5):
    return all(close(a, e, rel=0.0, abs_tol=tolerance) for pair_a, pair_e in zip(actual, expected) for a, e in zip(pair_a, pair_e))


def vector_sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def cross(a, b):
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def tetra_volume(a, b, c, d):
    return -dot(vector_sub(a, d), cross(vector_sub(b, d), vector_sub(c, d))) / 6.0


def element_volume(element, element_number, nodes):
    points = [nodes[node_id] for node_id in element["nodes"]]
    if element_number in {187, 285}:
        require(len(points) >= 4, "tetrahedral solid has too few nodes")
        value = tetra_volume(points[0], points[1], points[2], points[3])
        require(value > 1.0e-12, "solid element has a nonpositive oriented Jacobian/volume")
        return value
    require(len(points) >= 8, "hexahedral solid has too few nodes")
    corner = points[:8]
    tetrahedra = (
        (0, 1, 3, 4),
        (1, 2, 3, 6),
        (1, 3, 4, 6),
        (1, 4, 5, 6),
        (3, 4, 6, 7),
    )
    pieces = [tetra_volume(*(corner[index] for index in item)) for item in tetrahedra]
    require(all(value > 1.0e-12 for value in pieces), "solid element has a nonpositive oriented Jacobian/volume")
    return sum(pieces)


def solid_corner_ids(element, element_number):
    count = 4 if element_number in {187, 285} else 8
    require(len(element["nodes"]) >= count, "solid element has incomplete corner connectivity")
    return element["nodes"][:count]


def solid_corner_faces(element, element_number):
    corners = solid_corner_ids(element, element_number)
    patterns = (
        ((0, 1, 2), (0, 1, 3), (1, 2, 3), (2, 0, 3))
        if element_number in {187, 285}
        else (
            (0, 1, 2, 3),
            (0, 1, 5, 4),
            (1, 2, 6, 5),
            (2, 3, 7, 6),
            (3, 0, 4, 7),
            (4, 5, 6, 7),
        )
    )
    return [tuple(corners[index] for index in pattern) for pattern in patterns]


def solid_face_for_load(element, element_number, face_number):
    faces = solid_corner_faces(element, element_number)
    if element_number in {187, 285}:
        mapping = {1: 0, 2: 1, 3: 2, 4: 3}
    else:
        mapping = {1: 0, 2: 1, 3: 2, 4: 3, 5: 4, 6: 5}
    require(face_number in mapping, "pressure references an invalid solid face")
    return faces[mapping[face_number]]


def component_edge_lengths(component, types, nodes):
    edges = set()
    for element in component.values():
        element_number = types[element["type"]]["number"]
        corners = solid_corner_ids(element, element_number)
        patterns = (
            ((0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3))
            if element_number in {187, 285}
            else (
                (0, 1), (1, 2), (2, 3), (3, 0),
                (4, 5), (5, 6), (6, 7), (7, 4),
                (0, 4), (1, 5), (2, 6), (3, 7),
            )
        )
        for left, right in patterns:
            edges.add(tuple(sorted((corners[left], corners[right]))))
    lengths = []
    for left, right in edges:
        delta = vector_sub(nodes[left], nodes[right])
        lengths.append(math.sqrt(dot(delta, delta)))
    return sorted(lengths)


def median(values):
    require(values, "mesh has no topological edges")
    middle = len(values) // 2
    if len(values) % 2:
        return values[middle]
    return 0.5 * (values[middle - 1] + values[middle])


def connected_solid_components(solid_elements):
    parent = {}

    def find(value):
        parent.setdefault(value, value)
        while parent[value] != value:
            parent[value] = parent[parent[value]]
            value = parent[value]
        return value

    def union(left, right):
        left = find(left)
        right = find(right)
        if left != right:
            parent[right] = left

    for element in solid_elements.values():
        labels = element["nodes"]
        for node_id in labels[1:]:
            union(labels[0], node_id)
    groups = defaultdict(dict)
    for element_id, element in solid_elements.items():
        groups[find(element["nodes"][0])][element_id] = element
    return list(groups.values())


def validate_rectangular_component_boundary(name, component, types, nodes, expected_bbox):
    face_counts = defaultdict(int)
    for element in component.values():
        element_number = types[element["type"]]["number"]
        for face in solid_corner_faces(element, element_number):
            face_counts[frozenset(face)] += 1
    require(face_counts and max(face_counts.values()) <= 2, "%s mesh has a nonmanifold face" % name)
    exterior = [tuple(face) for face, count in face_counts.items() if count == 1]
    require(exterior, "%s mesh has no exterior boundary" % name)
    seen_planes = set()
    for face in exterior:
        matched = []
        for axis, limits in enumerate(expected_bbox):
            for side, coordinate in enumerate(limits):
                if all(close(nodes[node_id][axis], coordinate, rel=0.0, abs_tol=1.0e-5) for node_id in face):
                    matched.append((axis, side))
        require(matched, "%s has an internal cavity, overlap, or non-rectangular exterior face" % name)
        seen_planes.update(matched)
    require(seen_planes == {(axis, side) for axis in range(3) for side in range(2)}, "%s does not expose all six rectangular boundary planes" % name)


def component_node_ids(component):
    return set(node_id for element in component.values() for node_id in element["nodes"])


def polygon_area_xy(node_ids, nodes):
    points = sorted(set((nodes[node_id][0], nodes[node_id][1]) for node_id in node_ids))
    if len(points) < 3:
        return 0.0

    def orient(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower = []
    for point in points:
        while len(lower) >= 2 and orient(lower[-2], lower[-1], point) <= 0.0:
            lower.pop()
        lower.append(point)
    upper = []
    for point in reversed(points):
        while len(upper) >= 2 and orient(upper[-2], upper[-1], point) <= 0.0:
            upper.pop()
        upper.append(point)
    hull = lower[:-1] + upper[:-1]
    return abs(sum(hull[i][0] * hull[(i + 1) % len(hull)][1] - hull[(i + 1) % len(hull)][0] * hull[i][1] for i in range(len(hull)))) / 2.0


def surface_normal_z(element, nodes):
    points = [nodes[node_id] for node_id in element["nodes"]]
    require(len(points) >= 3, "surface element has too few nodes")
    return cross(vector_sub(points[1], points[0]), vector_sub(points[2], points[0]))[2]


def parse_materials(text):
    properties = defaultdict(dict)
    pattern = re.compile(
        r"^MPDATA,[^,]*,[^,]*,\s*(EX|PRXY|MU)\s*,\s*(\d+)\s*,\s*\d+\s*,\s*([-+0-9.EeDd]+)",
        re.MULTILINE | re.IGNORECASE,
    )
    for name, material, value in pattern.findall(text):
        properties[int(material)][name.upper()] = float(value.replace("D", "E").replace("d", "e"))
    return properties


def validate_ansys_model(model):
    text = model["text"]
    nodes = model["nodes"]
    types = model["element_types"]
    elements = model["elements"]
    require(nodes and elements and types, "CDB is missing FE model records")
    require(re.search(r"^ANTYPE,\s*0\s*$", text, re.MULTILINE), "analysis is not static")
    require(re.search(r"^NLGEOM,\s*1\s*$", text, re.MULTILINE), "NLGEOM is not enabled")

    declared_solid_type_ids = {type_id for type_id, data in types.items() if data["number"] in SOLID_ELEMENT_NUMBERS}
    declared_target_type_ids = {type_id for type_id, data in types.items() if data["number"] == TARGET_ELEMENT_NUMBER}
    declared_contact_type_ids = {type_id for type_id, data in types.items() if data["number"] in CONTACT_ELEMENT_NUMBERS}
    require(declared_solid_type_ids, "no supported 3D structural solid element type")

    solid_elements = {eid: row for eid, row in elements.items() if row["type"] in declared_solid_type_ids}
    solid_type_ids = {row["type"] for row in solid_elements.values()}
    target_elements = {eid: row for eid, row in elements.items() if row["type"] in declared_target_type_ids}
    contact_elements = {eid: row for eid, row in elements.items() if row["type"] in declared_contact_type_ids}
    target_type_ids = {row["type"] for row in target_elements.values()}
    contact_type_ids = {row["type"] for row in contact_elements.values()}
    require(len(solid_elements) >= 20, "solid mesh is implausibly small")
    require(target_elements and contact_elements, "contact/target surface meshes are empty")
    classified_element_ids = set(solid_elements) | set(target_elements) | set(contact_elements)
    require(classified_element_ids == set(elements), "the model contains an unsupported or extra active element")
    require(not re.search(r"^\s*(?:CEBLOCK\b|CPBLOCK\b|CE\s*,|CP\s*,|CERIG\b|RBE3\b)", text, re.MULTILINE | re.IGNORECASE), "unexpected constraint equation or coupled-DOF definition is present")
    surface_blocks = re.findall(r"^SFEBLOCK,.*$", text, re.MULTILINE | re.IGNORECASE)
    require(surface_blocks and all(",PRES," in line.upper() for line in surface_blocks), "unexpected non-pressure surface load is present")

    components = connected_solid_components(solid_elements)
    require(len(components) == 2, "the solid mesh must contain exactly two disconnected bodies")
    expected_plate = ((0.0, 100.0), (0.0, 100.0), (0.0, 5.0))
    expected_block = ((40.0, 60.0), (40.0, 60.0), (5.0, 35.0))
    plate = next((part for part in components if bbox_matches(bbox(component_node_ids(part), nodes), expected_plate)), None)
    block = next((part for part in components if bbox_matches(bbox(component_node_ids(part), nodes), expected_block)), None)
    require(plate is not None, "plate bounds are not exactly 0..100 x 0..100 x 0..5 mm")
    require(block is not None, "assembled block bounds are not exactly 40..60 x 40..60 x 5..35 mm")
    plate_nodes = component_node_ids(plate)
    block_nodes = component_node_ids(block)
    require(plate_nodes.isdisjoint(block_nodes), "plate and block share node labels at the interface")
    validate_rectangular_component_boundary("plate", plate, types, nodes, expected_plate)
    validate_rectangular_component_boundary("block", block, types, nodes, expected_block)

    volumes = {}
    for name, component, expected in (("plate", plate, 50000.0), ("block", block, 12000.0)):
        volume = sum(element_volume(row, types[row["type"]]["number"], nodes) for row in component.values())
        require(close(volume, expected, rel=1.0e-5, abs_tol=1.0e-3), "%s solid volume is incorrect: %s" % (name, volume))
        volumes[name] = volume

    plate_edges = component_edge_lengths(plate, types, nodes)
    block_edges = component_edge_lengths(block, types, nodes)
    require(3.5 <= median(plate_edges) <= 6.5 and max(plate_edges) <= 9.0, "plate mesh is inconsistent with the 5 mm target")
    require(2.0 <= median(block_edges) <= 4.2 and max(block_edges) <= 5.5, "block mesh is inconsistent with the 3 mm target")

    target_nodes = set(node_id for row in target_elements.values() for node_id in row["nodes"])
    contact_nodes = set(node_id for row in contact_elements.values() for node_id in row["nodes"])
    require(target_nodes <= plate_nodes, "target elements are not on the plate")
    require(contact_nodes <= block_nodes, "contact elements are not on the block")
    require(all(close(nodes[node_id][2], 5.0, rel=0.0, abs_tol=1.0e-5) for node_id in target_nodes | contact_nodes), "contact interface has a gap or penetration")
    solid_corner_node_set = set()
    for row in solid_elements.values():
        solid_corner_node_set.update(solid_corner_ids(row, types[row["type"]]["number"]))
    expected_target_faces = {
        frozenset(face)
        for row in plate.values()
        for face in solid_corner_faces(row, types[row["type"]]["number"])
        if all(close(nodes[node_id][2], 5.0, rel=0.0, abs_tol=1.0e-5) for node_id in face)
    }
    expected_contact_faces = {
        frozenset(face)
        for row in block.values()
        for face in solid_corner_faces(row, types[row["type"]]["number"])
        if all(close(nodes[node_id][2], 5.0, rel=0.0, abs_tol=1.0e-5) for node_id in face)
    }
    actual_target_faces = [frozenset(node_id for node_id in row["nodes"] if node_id in solid_corner_node_set) for row in target_elements.values()]
    actual_contact_faces = [frozenset(node_id for node_id in row["nodes"] if node_id in solid_corner_node_set) for row in contact_elements.values()]
    require(len(actual_target_faces) == len(set(actual_target_faces)) and set(actual_target_faces) == expected_target_faces, "target surface has missing, duplicate, or non-plate-top faces")
    require(len(actual_contact_faces) == len(set(actual_contact_faces)) and set(actual_contact_faces) == expected_contact_faces, "contact surface has missing, duplicate, or non-block-bottom faces")
    target_area = sum(polygon_area_xy(row["nodes"], nodes) for row in target_elements.values())
    contact_area = sum(polygon_area_xy(row["nodes"], nodes) for row in contact_elements.values())
    require(close(target_area, 10000.0, rel=0.01, abs_tol=1.0), "target surface does not cover the complete plate top")
    require(close(contact_area, 400.0, rel=0.01, abs_tol=0.1), "contact surface does not cover the complete block bottom")
    require(all(surface_normal_z(row, nodes) > 0.0 for row in target_elements.values()), "plate target normals must point toward +Z")
    require(all(surface_normal_z(row, nodes) < 0.0 for row in contact_elements.values()), "block contact normals must point toward -Z")
    target_pairs = {row["real"] for row in target_elements.values()}
    contact_pairs = {row["real"] for row in contact_elements.values()}
    require(target_pairs == contact_pairs and 0 not in target_pairs, "contact and target elements are not paired by real constant set")

    for type_id in contact_type_ids:
        keyopts = types[type_id]["keyopts"]
        require(keyopts[1] in {0, 1, 3, 4}, "contact formulation is not a hard-contact Lagrange or penalty method")
        require(keyopts[3] in {0, 1, 2, 3, 4, 5}, "contact detection algorithm is not a supported CONTA173/174 surface-to-surface option")
        require(keyopts[4] == 0, "automatic contact adjustment is not allowed")
        require(keyopts[8] == 0, "contact offset/gap ramping is not allowed")
        require(keyopts[11] == 0, "bonded/no-separation/rough contact is not allowed")
    used_real_constants = model["real_constants"]
    for real_id in contact_pairs:
        values = used_real_constants.get(real_id, [])
        # CONTA173/174 real constants list CNOF ninth, at zero-based index 8.
        require(len(values) < 9 or abs(values[8]) <= 1.0e-12, "nonzero contact offset CNOF is not allowed")
    materials = parse_materials(text)
    solid_materials = {row["material"] for row in solid_elements.values()}
    require(len(solid_materials) == 1, "all solids must use one Steel material")
    material = materials.get(next(iter(solid_materials)), {})
    require(close(material.get("EX", float("nan")), 210000.0, rel=1.0e-6, abs_tol=0.1), "Steel Young's modulus is not 210000 MPa")
    require(close(material.get("PRXY", float("nan")), 0.3, rel=1.0e-6, abs_tol=1.0e-7), "Steel Poisson ratio is not 0.3")
    require(not any(abs(row.get("MU", 0.0)) > 1.0e-12 for row in materials.values()), "contact is not frictionless")
    require(not re.search(r"^TB,\s*(?:FRIC|CZM|INTER)\b", text, re.MULTILINE | re.IGNORECASE), "frictional/cohesive/interface material data is not allowed")

    fixed = defaultdict(dict)
    for node_id, label, value in model["constraints"]:
        fixed[node_id][label] = value
    expected_fixed = {node_id for node_id in plate_nodes if close(nodes[node_id][2], 0.0, rel=0.0, abs_tol=1.0e-5)}
    require(set(fixed) == expected_fixed, "constraints must exist only on every plate-bottom node")
    for node_id, dofs in fixed.items():
        require(set(dofs) == {"UX", "UY", "UZ"}, "plate bottom is not a complete Encastre constraint")
        require(all(abs(value) <= 1.0e-12 for value in dofs.values()), "Encastre values must be zero")

    pressure_rows = [row for row in model["pressures"] if row["kind"] == 1]
    require(pressure_rows, "no pressure load is stored in the DB")
    require(all(row["element"] in block for row in pressure_rows), "pressure is applied outside the block")
    top_elements = {
        eid for eid, row in block.items()
        if sum(close(nodes[node_id][2], 35.0, rel=0.0, abs_tol=1.0e-5) for node_id in row["nodes"]) >= 3
    }
    require({row["element"] for row in pressure_rows} == top_elements, "pressure does not cover exactly the complete block top")
    for row in pressure_rows:
        element = block[row["element"]]
        face = solid_face_for_load(element, types[element["type"]]["number"], row["face"])
        require(all(close(nodes[node_id][2], 35.0, rel=0.0, abs_tol=1.0e-5) for node_id in face), "pressure is stored on a non-top solid face")
    require(all(row["values"] and all(close(value, 10.0, rel=1.0e-6, abs_tol=1.0e-6) for value in row["values"]) for row in pressure_rows), "block-top pressure is not uniformly 10 MPa")
    require(all(row["kind"] == 1 or all(abs(value) <= 1.0e-12 for value in row["values"]) for row in model["pressures"]), "pressure contains a nonzero imaginary/secondary component")
    require(not re.search(r"^(?:F|FBLOCK|BF|BFBLOCK|BFEBLOCK),", text, re.MULTILINE | re.IGNORECASE), "unexpected nodal/body force load is present")
    for command in ("ACEL", "OMEGA", "DOMEGA", "CGOMEGA", "DCGOMG"):
        for line in re.findall(r"^%s,.*$" % command, text, re.MULTILINE | re.IGNORECASE):
            values = [float(value.replace("D", "E").replace("d", "e")) for value in re.findall(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[EeDd][-+]?\d+)?", line)]
            require(all(abs(value) <= 1.0e-12 for value in values), "unexpected nonzero %s load is present" % command)

    return {
        "solid_type_ids": sorted(solid_type_ids),
        "contact_type_ids": sorted(contact_type_ids),
        "target_type_ids": sorted(target_type_ids),
        "plate_element_ids": sorted(plate),
        "block_element_ids": sorted(block),
        "volumes": volumes,
        "surface_areas": {"target": target_area, "contact": contact_area},
    }


def selection_commands(type_ids):
    commands = []
    for index, type_id in enumerate(type_ids):
        commands.append("ESEL,%s,TYPE,,%d" % ("S" if index == 0 else "A", type_id))
    return "\n".join(commands)


def extract_result(work, jobname, db_path, rst_path, model_info):
    output_name = jobname + "_metrics"
    signature_name = jobname + "_sig"
    script = r"""/BATCH
/CLEAR,NOSTART
/ABBR,DELE,ALL
/PSEARCH,OFF
RESUME,'%s','db'
/PSEARCH,OFF
/POST1
FILE,'%s','rst'
SET,LAST
RSYS,0
ALLSEL,ALL
%s
ETABLE,CPRESS,CONT,PRES
*GET,ECNT,ELEM,0,COUNT
*GET,EID,ELEM,0,NUM,MIN
CPMAX=0
CP1=0
CP2=0
CPW=0
*CFOPEN,%s,txt
*DO,II,1,ECNT
  *GET,CPVAL,ELEM,EID,ETAB,CPRESS
  *VWRITE,EID,CPVAL
('C ',F20.0,1X,E24.16)
  CP1=CP1+CPVAL
  CP2=CP2+CPVAL*CPVAL
  CPW=CPW+EID*CPVAL
  *IF,CPVAL,GT,CPMAX,THEN
    CPMAX=CPVAL
  *ENDIF
  *GET,EID,ELEM,EID,NXTH
*ENDDO
ALLSEL,ALL
NSEL,S,LOC,Z,35
NSORT,U,Z,0,0,ALL
*GET,UZMIN,SORT,0,MIN
ALLSEL,ALL
NSEL,S,LOC,Z,0
*GET,NCNT,NODE,0,COUNT
*GET,NID,NODE,0,NUM,MIN
RFSUM=0
RF2=0
RFW=0
*DO,II,1,NCNT
  *GET,RFVAL,NODE,NID,RF,FZ
  *VWRITE,NID,RFVAL
('R ',F20.0,1X,E24.16)
  RFSUM=RFSUM+RFVAL
  RF2=RF2+RFVAL*RFVAL
  RFW=RFW+NID*RFVAL
  *GET,NID,NODE,NID,NXTH
*ENDDO
ALLSEL,ALL
%s
NSLE,S
*GET,SNCNT,NODE,0,COUNT
*GET,NID,NODE,0,NUM,MIN
UMAX=0
SMAX=0
U1=0
U2=0
UW=0
S1=0
S2=0
SW=0
/NOPR
*DO,II,1,SNCNT
  *GET,UXV,NODE,NID,U,X
  *GET,UYV,NODE,NID,U,Y
  *GET,UZV,NODE,NID,U,Z
  *GET,SV,NODE,NID,S,EQV
  *VWRITE,NID,UXV,UYV,UZV,SV
('N ',F20.0,4(1X,E24.16))
  UV=SQRT(UXV*UXV+UYV*UYV+UZV*UZV)
  U1=U1+UXV+UYV+UZV
  U2=U2+UXV*UXV+UYV*UYV+UZV*UZV
  UW=UW+NID*(UXV+2*UYV+3*UZV)
  S1=S1+SV
  S2=S2+SV*SV
  SW=SW+NID*SV
  *IF,UV,GT,UMAX,THEN
    UMAX=UV
  *ENDIF
  *IF,SV,GT,SMAX,THEN
    SMAX=SV
  *ENDIF
  *GET,NID,NODE,NID,NXTH
*ENDDO
/GOPR
*CFCLOS
*GET,RTIME,ACTIVE,0,SET,TIME
*CFOPEN,%s,txt
*VWRITE,CPMAX
('CPMAX=',E24.16)
*VWRITE,UZMIN
('UZMIN=',E24.16)
*VWRITE,RFSUM
('RFSUM=',E24.16)
*VWRITE,UMAX
('UMAX=',E24.16)
*VWRITE,SMAX
('SMAX=',E24.16)
*VWRITE,ECNT
('CONTACT_COUNT=',E24.16)
*VWRITE,NCNT
('FIXED_COUNT=',E24.16)
*VWRITE,SNCNT
('SOLID_NODE_COUNT=',E24.16)
*VWRITE,RTIME
('RESULT_TIME=',E24.16)
*VWRITE,CP1
('CP_SUM=',E24.16)
*VWRITE,CP2
('CP_SUMSQ=',E24.16)
*VWRITE,CPW
('CP_WEIGHTED=',E24.16)
*VWRITE,RF2
('RF_SUMSQ=',E24.16)
*VWRITE,RFW
('RF_WEIGHTED=',E24.16)
*VWRITE,U1
('U_SUM=',E24.16)
*VWRITE,U2
('U_SUMSQ=',E24.16)
*VWRITE,UW
('U_WEIGHTED=',E24.16)
*VWRITE,S1
('S_SUM=',E24.16)
*VWRITE,S2
('S_SUMSQ=',E24.16)
*VWRITE,SW
('S_WEIGHTED=',E24.16)
*CFCLOS
ALLSEL,ALL
FINISH
/EXIT,NOSAVE
""" % (
        apdl_path(db_path),
        apdl_path(rst_path),
        selection_commands(model_info["contact_type_ids"]),
        signature_name,
        selection_commands(model_info["solid_type_ids"]),
        output_name,
    )
    run_ansys(work, jobname, script)
    result_path = work / (output_name + ".txt")
    require(file_is_nonempty(result_path), "%s did not emit result metrics" % jobname)
    result_text = result_path.read_text(encoding="utf-8", errors="replace")
    pairs = dict(re.findall(r"([A-Z_]+)=\s*([-+0-9.EeDd]+)", result_text))
    required = {
        "CPMAX", "UZMIN", "RFSUM", "UMAX", "SMAX", "CONTACT_COUNT",
        "FIXED_COUNT", "SOLID_NODE_COUNT", "RESULT_TIME", "CP_SUM",
        "CP_SUMSQ", "CP_WEIGHTED", "RF_SUMSQ", "RF_WEIGHTED", "U_SUM",
        "U_SUMSQ", "U_WEIGHTED", "S_SUM", "S_SUMSQ", "S_WEIGHTED",
    }
    require(required <= set(pairs), "%s emitted incomplete result metrics" % jobname)
    values = {key: float(pairs[key].replace("D", "E").replace("d", "e")) for key in required}
    require(all(math.isfinite(value) for value in values.values()), "%s emitted nonfinite result metrics" % jobname)
    signature_path = work / (signature_name + ".txt")
    require(file_is_nonempty(signature_path), "%s did not emit a native field signature" % jobname)
    signature = {"contact": {}, "reaction": {}, "solid": {}}
    expected_lengths = {"C": 3, "R": 3, "N": 6}
    destinations = {"C": "contact", "R": "reaction", "N": "solid"}
    for line in signature_path.read_text(encoding="utf-8", errors="replace").splitlines():
        fields = line.split()
        if not fields:
            continue
        require(fields[0] in expected_lengths and len(fields) == expected_lengths[fields[0]], "%s emitted a malformed field-signature row" % jobname)
        label = int(round(float(fields[1])))
        destination = signature[destinations[fields[0]]]
        require(label not in destination, "%s emitted a duplicate field-signature label" % jobname)
        row = tuple(float(value.replace("D", "E").replace("d", "e")) for value in fields[2:])
        require(all(math.isfinite(value) for value in row), "%s emitted nonfinite native field data" % jobname)
        destination[label] = row
    require(len(signature["contact"]) == int(round(values["CONTACT_COUNT"])), "contact field signature is incomplete")
    require(len(signature["reaction"]) == int(round(values["FIXED_COUNT"])), "reaction field signature is incomplete")
    require(len(signature["solid"]) == int(round(values["SOLID_NODE_COUNT"])), "U/S field signature is incomplete")
    values["__signature"] = signature
    return values


def independent_resolve(work, db_path):
    staged_db = work / "Job-Contact.db"
    shutil.copy2(str(db_path), str(staged_db))
    before = time.time()
    script = r"""/BATCH
/CLEAR,NOSTART
/ABBR,DELE,ALL
/PSEARCH,OFF
RESUME,'%s','db'
/PSEARCH,OFF
/SOLU
ANTYPE,STATIC,NEW
NLGEOM,ON
NROPT,FULL
AUTOTS,ON
NSUBST,20,100,5
NEQIT,50
CNVTOL,DEFA
NCNV,1
OUTRES,ALL,ALL
TIME,1.0
SOLVE
FINISH
/EXIT,NOSAVE
""" % apdl_path(staged_db)
    output = run_ansys(work, "task08_resolve", script, timeout=1200)
    require("SOLUTION CONVERGED AFTER EQUILIBRIUM ITERATION" in output, "independent nonlinear re-solve did not converge")
    for marker in (
        "DID NOT CONVERGE",
        "ANALYSIS TERMINATED",
        "SOLUTION NOT CONVERGED",
        "ERROR TERMINATION",
    ):
        require(marker not in output.upper(), "independent re-solve contains failure marker: %s" % marker)
    penetration = re.search(r"MAX\.\s+INITIAL PENETRATION\s+([-+0-9.EEDd]+)", output, re.IGNORECASE)
    require(penetration is not None, "independent re-solve did not report initial penetration")
    require(abs(float(penetration.group(1).replace("D", "E").replace("d", "e"))) <= 1.0e-8, "initial penetration is nonzero")
    fresh_rst = work / "task08_resolve.rst"
    require(file_is_nonempty(fresh_rst, 100000), "independent re-solve did not create a native RST")
    require(fresh_rst.stat().st_mtime >= before - 2.0, "independent RST is not fresh")
    return staged_db, fresh_rst


def compare_metrics_json(metrics, result):
    mapping = {
        "max_contact_pressure": "CPMAX",
        "vertical_displacement": "UZMIN",
        "reaction_force": "RFSUM",
    }
    tolerances = {
        "max_contact_pressure": (0.005, 0.02),
        "vertical_displacement": (0.01, 2.0e-5),
        "reaction_force": (0.002, 2.0),
    }
    for metric, native in mapping.items():
        relative, absolute = tolerances[metric]
        require(close(metrics[metric], result[native], rel=relative, abs_tol=absolute), "%s does not match the submitted native RST" % metric)


def validate_result_physics(result, model_info):
    require(9.0 <= result["CPMAX"] <= 100.0, "contact pressure is not physically plausible")
    require(-0.01 <= result["UZMIN"] <= -0.0001, "block-top vertical displacement is not downward and plausible")
    require(3980.0 <= result["RFSUM"] <= 4020.0, "fixed-bottom reaction does not balance the 4000 N pressure resultant within 0.5 percent")
    require(result["UMAX"] > 0.0 and result["SMAX"] > 0.0, "native U/S fields are missing or zero")
    require(int(round(result["CONTACT_COUNT"])) >= 1, "no contact result elements were extracted")
    require(int(round(result["FIXED_COUNT"])) >= 4, "no fixed-bottom reactions were extracted")
    require(int(round(result["SOLID_NODE_COUNT"])) >= 8, "native U/S fields do not cover the solid mesh")
    require(result["RESULT_TIME"] > 0.0, "final native result pseudo-time is not positive")


def compare_native_results(submitted, recomputed):
    for key, relative, absolute in (
        ("CPMAX", 0.02, 1.0e-4),
        ("UZMIN", 0.02, 1.0e-7),
        ("RFSUM", 0.01, 0.1),
        ("UMAX", 0.02, 1.0e-7),
        ("SMAX", 0.03, 1.0e-3),
    ):
        require(close(submitted[key], recomputed[key], rel=relative, abs_tol=absolute), "submitted RST does not agree with the isolated re-solve for %s" % key)
    for key in (
        "CONTACT_COUNT", "FIXED_COUNT", "SOLID_NODE_COUNT",
        "CP_SUM", "CP_SUMSQ", "CP_WEIGHTED", "RF_SUMSQ", "RF_WEIGHTED",
        "U_SUM", "U_SUMSQ", "U_WEIGHTED", "S_SUM", "S_SUMSQ", "S_WEIGHTED",
    ):
        require(close(submitted[key], recomputed[key], rel=0.005, abs_tol=1.0e-8), "submitted RST field signature does not agree with the isolated re-solve for %s" % key)
    submitted_signature = submitted["__signature"]
    recomputed_signature = recomputed["__signature"]
    for field in ("contact", "reaction", "solid"):
        require(set(submitted_signature[field]) == set(recomputed_signature[field]), "submitted RST label coverage differs for %s" % field)
        for label in submitted_signature[field]:
            left = submitted_signature[field][label]
            right = recomputed_signature[field][label]
            require(len(left) == len(right), "submitted RST component count differs for %s label %s" % (field, label))
            require(all(close(a, b, rel=0.005, abs_tol=1.0e-10) for a, b in zip(left, right)), "submitted RST field differs for %s label %s" % (field, label))


def check_ansys(root, artifacts, metrics):
    db_path, rst_path = artifacts
    temp_root = Path(tempfile.mkdtemp(prefix="eval_cli_task08_"))
    try:
        submitted_root = temp_root / "submitted"
        solve_root = temp_root / "resolve"
        post_root = temp_root / "post"
        submitted_root.mkdir()
        solve_root.mkdir()
        post_root.mkdir()
        submitted_db = submitted_root / db_path.name
        submitted_rst = submitted_root / rst_path.name
        shutil.copy2(str(db_path), str(submitted_db))
        shutil.copy2(str(rst_path), str(submitted_rst))

        cdb = audit_model_to_cdb(submitted_root, submitted_db)
        model = parse_cdb(cdb)
        model_info = validate_ansys_model(model)
        submitted = extract_result(
            submitted_root,
            "task08_submitted_post",
            submitted_db,
            submitted_rst,
            model_info,
        )
        compare_metrics_json(metrics, submitted)
        validate_result_physics(submitted, model_info)

        solve_db, fresh_rst = independent_resolve(solve_root, db_path)
        post_rst = post_root / "task08_resolve.rst"
        shutil.copy2(str(fresh_rst), str(post_rst))
        recomputed = extract_result(
            post_root,
            "task08_resolved_post",
            solve_db,
            post_rst,
            model_info,
        )
        validate_result_physics(recomputed, model_info)
        compare_native_results(submitted, recomputed)
        log("ANSYS model audit volumes=%r areas=%r" % (model_info["volumes"], model_info["surface_areas"]))
        log("submitted native metrics=%r" % {key: value for key, value in submitted.items() if key != "__signature"})
        log("isolated re-solve metrics=%r" % {key: value for key, value in recomputed.items() if key != "__signature"})
        log("native field rows contact=%d reaction=%d solid=%d" % tuple(len(submitted["__signature"][name]) for name in ("contact", "reaction", "solid")))
        return True
    finally:
        shutil.rmtree(str(temp_root), ignore_errors=True)


def write_details(root, passed):
    try:
        (root / "eval_detail.txt").write_text("\n".join(DETAILS) + "\n", encoding="utf-8")
        (root / "eval_result.txt").write_text("True\n" if passed else "False\n", encoding="ascii")
    except Exception:
        pass


def evaluate():
    metrics = read_metrics(DESKTOP / "metrics.json")
    branch, artifacts = choose_branch(DESKTOP)
    log("selected native branch=%s" % branch)
    return check_ansys(DESKTOP, artifacts, metrics)


def main():
    passed = False
    try:
        passed = bool(evaluate())
    except Exception as exc:
        log("evaluation failed: %s" % exc)
        log(traceback.format_exc())
        passed = False
    write_details(DESKTOP, passed)
    sys.stdout.write("True\n" if passed else "False\n")


if __name__ == "__main__":
    main()
