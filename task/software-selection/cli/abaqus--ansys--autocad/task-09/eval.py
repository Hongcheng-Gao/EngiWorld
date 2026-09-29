# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib
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
import uuid
from collections import defaultdict
from pathlib import Path


TASK_ID = "c-open-abaqus-ansys-autocad-task-09-windows"
JOB_NAME = "Job-UDL"
STEP_NAME = "Step-Load"
METRIC_FIELDS = ("midspan_deflection", "max_mises")
ABAQUS_LAUNCHER = Path(
    r"C:\SIMULIA\CAE\2025LE\win_b64\code\bin\SMALauncherLE.exe"
)
ANSYS_EXEC = Path(
    r"C:\Program Files\ANSYS Inc\v261\ansys\bin\winx64\ANSYS261.exe"
)
DESKTOP_CANDIDATES = (
    Path(os.environ.get("USERPROFILE", r"C:\Users\user")) / "Desktop",
    Path(r"C:\Users\user\Desktop"),
    Path(r"C:\Users\User\Desktop"),
)
DETAILS = []


class EvaluationError(RuntimeError):
    pass


def log(message):
    DETAILS.append(str(message))


def require(condition, message):
    if not condition:
        raise EvaluationError(message)


def desktop_dir():
    for path in DESKTOP_CANDIDATES:
        if path.is_dir():
            return path
    return DESKTOP_CANDIDATES[1]


def is_nonempty(path, minimum=1):
    try:
        return path.is_file() and path.stat().st_size >= minimum
    except Exception:
        return False


def finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def close(actual, expected, rel=1.0e-5, abs_tol=1.0e-8):
    try:
        return math.isclose(
            float(actual), float(expected), rel_tol=rel, abs_tol=abs_tol
        )
    except Exception:
        return False


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_metrics(root):
    path = root / "metrics.json"
    require(is_nonempty(path), "metrics.json is missing")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise EvaluationError("metrics.json is invalid JSON: %s" % exc)
    require(
        isinstance(payload, dict) and set(payload) == set(METRIC_FIELDS),
        "metrics.json must contain exactly midspan_deflection and max_mises",
    )
    require(
        all(finite_number(payload[name]) for name in METRIC_FIELDS),
        "metrics must be finite JSON numbers, not booleans or strings",
    )
    metrics = dict((name, float(payload[name])) for name in METRIC_FIELDS)
    require(
        -0.20 < metrics["midspan_deflection"] < -0.03,
        "midspan_deflection is outside the downward simply-supported range",
    )
    require(
        1.0 < metrics["max_mises"] < 100.0,
        "max_mises is outside the Task-09 physical range",
    )
    return metrics


def files_with_suffix(root, suffix):
    try:
        return sorted(
            [
                path
                for path in root.iterdir()
                if path.is_file() and path.suffix.lower() == suffix
            ],
            key=lambda path: path.name.lower(),
        )
    except Exception:
        return []


def discover_branch(root):
    caes = files_with_suffix(root, ".cae")
    odbs = files_with_suffix(root, ".odb")
    dbs = files_with_suffix(root, ".db")
    rsts = files_with_suffix(root, ".rst")
    has_abaqus = bool(caes or odbs)
    has_ansys = bool(dbs or rsts)
    require(not (has_abaqus and has_ansys), "deliver exactly one solver branch")
    expected_stem = JOB_NAME.lower()
    if has_abaqus:
        require(
            len(caes) == 1 and len(odbs) == 1,
            "Abaqus delivery requires exactly one CAE and one ODB",
        )
        require(
            odbs[0].stem.lower() == expected_stem,
            "Abaqus result artifact must be Job-UDL.odb",
        )
        require(
            is_nonempty(caes[0], 20000) and is_nonempty(odbs[0], 100000),
            "Abaqus native artifact is empty or implausibly small",
        )
        return "abaqus", caes[0], odbs[0]
    if has_ansys:
        require(
            len(dbs) == 1 and len(rsts) == 1,
            "ANSYS delivery requires exactly one DB and one RST",
        )
        require(
            dbs[0].stem.lower() == expected_stem
            and rsts[0].stem.lower() == expected_stem,
            "ANSYS artifacts must be Job-UDL.db and Job-UDL.rst",
        )
        require(
            is_nonempty(dbs[0], 100000) and is_nonempty(rsts[0], 100000),
            "ANSYS native artifact is empty or implausibly small",
        )
        return "ansys", dbs[0], rsts[0]
    raise EvaluationError("no supported native CAE/ODB or DB/RST pair found")


def remove_tree(path):
    for _ in range(30):
        try:
            if path.exists():
                shutil.rmtree(str(path))
            if not path.exists():
                return True
        except Exception:
            pass
        time.sleep(0.1)
    return not path.exists()


def owned_processes(markers):
    script = (
        "Get-CimInstance Win32_Process | Select-Object ProcessId,Name,"
        "ExecutablePath,CommandLine | ConvertTo-Json -Compress"
    )
    completed = subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command", script],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=30,
        shell=False,
    )
    require(completed.returncode == 0, "Windows process inventory failed")
    text = completed.stdout.strip()
    rows = [] if not text else json.loads(text)
    if isinstance(rows, dict):
        rows = [rows]
    lowered = tuple(str(marker).lower() for marker in markers if marker)
    result = []
    for row in rows:
        command = str(row.get("CommandLine") or "").lower()
        if any(marker in command for marker in lowered):
            result.append(row)
    return result


def clear_owned_processes(markers):
    found = owned_processes(markers)
    for row in found:
        pid = int(row.get("ProcessId") or 0)
        if pid > 0:
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=30,
                shell=False,
            )
    remaining = owned_processes(markers)
    if found:
        log("owned solver processes required cleanup: %s" % found)
    return not remaining


ABAQUS_CHECKER = r'''
# -*- coding: utf-8 -*-
from __future__ import print_function

import hashlib
import json
import math
import os
import re
import shutil
import sys
import traceback
from collections import defaultdict

from abaqus import mdb, openMdb
from abaqusConstants import INTEGRATION_POINT, OFF
from caeModules import *
from odbAccess import openOdb


def fail(condition, message):
    if not condition:
        raise RuntimeError(message)


def ci(value):
    try:
        return str(value).strip().upper()
    except Exception:
        return ""


def close(actual, expected, rel=1.0e-5, absolute=1.0e-8):
    try:
        return math.isclose(
            float(actual), float(expected), rel_tol=rel, abs_tol=absolute
        )
    except Exception:
        return False


def finite(value):
    try:
        return math.isfinite(float(value))
    except Exception:
        return False


def repository_value(repository, name):
    for key in repository.keys():
        if ci(key) == ci(name):
            return repository[key]
    raise KeyError(name)


def field_component(value, index):
    data = value.data
    if isinstance(data, (int, float)):
        fail(index == 0, "scalar field component index is invalid")
        return float(data)
    return float(data[index])


def value_data(value):
    data = value.data
    if isinstance(data, (int, float)):
        return (float(data),)
    return tuple(float(item) for item in data)


def field_key(value):
    section = ""
    try:
        section = str(value.sectionPoint)
    except Exception:
        pass
    return (
        ci(getattr(value, "instance", "")),
        int(getattr(value, "nodeLabel", 0) or 0),
        int(getattr(value, "elementLabel", 0) or 0),
        int(getattr(value, "integrationPoint", 0) or 0),
        section,
    )


def field_signature(field):
    result = {}
    for value in field.values:
        key = field_key(value)
        fail(key not in result, "duplicate field signature key")
        result[key] = value_data(value)
    return result


def signatures_match(left, right, rel=5.0e-4, absolute=2.0e-6):
    if set(left) != set(right):
        return False
    for key in left:
        if len(left[key]) != len(right[key]):
            return False
        if any(
            not close(a, b, rel=rel, absolute=absolute)
            for a, b in zip(left[key], right[key])
        ):
            return False
    return True


def bbox(rows):
    fail(rows, "coordinate collection is empty")
    return tuple(
        (min(row[axis] for row in rows), max(row[axis] for row in rows))
        for axis in range(3)
    )


def parse_blocks(text):
    blocks = []
    current = None
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("**"):
            continue
        if line.startswith("*"):
            fields = [item.strip() for item in line[1:].split(",")]
            name = ci(fields[0])
            params = {}
            for item in fields[1:]:
                if not item:
                    continue
                if "=" in item:
                    key, value = item.split("=", 1)
                    params[ci(key)] = value.strip()
                else:
                    params[ci(item)] = None
            current = {"name": name, "params": params, "rows": [], "line": number}
            blocks.append(current)
        else:
            fail(current is not None, "input data exists before a keyword")
            current["rows"].append((number, line))
    return blocks


def blocks_named(blocks, name):
    return [block for block in blocks if block["name"] == ci(name)]


def csv_fields(line):
    return [item.strip() for item in line.split(",") if item.strip()]


def numeric_fields(line):
    return [float(item.replace("D", "E").replace("d", "e")) for item in csv_fields(line)]


def expand_labels(block):
    labels = []
    generated = "GENERATE" in block["params"]
    for _, line in block["rows"]:
        fields = [int(float(item)) for item in csv_fields(line)]
        if generated:
            fail(len(fields) == 3 and fields[2] > 0, "invalid generated label range")
            labels.extend(range(fields[0], fields[1] + 1, fields[2]))
        else:
            labels.extend(fields)
    return labels


def resolved_elsets(blocks):
    raw = defaultdict(list)
    for block in blocks_named(blocks, "ELEMENT"):
        name = ci(block["params"].get("ELSET"))
        if name:
            raw[name].extend(
                int(round(numeric_fields(line)[0])) for _, line in block["rows"]
            )
    for block in blocks_named(blocks, "ELSET"):
        name = ci(block["params"].get("ELSET"))
        fail(name, "Elset has no name")
        if "GENERATE" in block["params"]:
            raw[name].extend(expand_labels(block))
        else:
            for _, line in block["rows"]:
                for token in csv_fields(line):
                    try:
                        raw[name].append(int(float(token)))
                    except Exception:
                        raw[name].append(ci(token))

    cache = {}

    def resolve(name, stack=()):
        name = ci(name).split(".")[-1]
        fail(name in raw, "referenced Elset is missing: %s" % name)
        fail(name not in stack, "recursive Elset definition: %s" % name)
        if name in cache:
            return cache[name]
        labels = set()
        for value in raw[name]:
            if isinstance(value, int):
                labels.add(value)
            else:
                labels.update(resolve(value, stack + (name,)))
        cache[name] = labels
        return labels

    for name in raw:
        resolve(name)
    return cache


def element_surface_facets(blocks, elsets):
    surfaces = {}
    for block in blocks_named(blocks, "SURFACE"):
        name = ci(block["params"].get("NAME"))
        fail(name and ci(block["params"].get("TYPE")) == "ELEMENT", "Task-09 surfaces must be element surfaces")
        facets = []
        for _, line in block["rows"]:
            fields = csv_fields(line)
            fail(len(fields) == 2, "element surface row is malformed")
            region = ci(fields[0]).split(".")[-1]
            face = ci(fields[1])
            fail(re.match(r"^S[1-6]$", face), "solid surface uses an invalid face label")
            if region in elsets:
                labels = elsets[region]
            else:
                try:
                    labels = {int(float(region))}
                except Exception:
                    fail(False, "surface references an unresolved Elset: %s" % region)
            facets.extend((label, int(face[1:])) for label in labels)
        fail(name not in surfaces, "duplicate surface name: %s" % name)
        surfaces[name] = sorted(set(facets))
    return surfaces


def element_shape(element_type):
    name = ci(element_type)
    if name.startswith("C3D4") or name.startswith("C3D10"):
        return "tet"
    if name.startswith("C3D6") or name.startswith("C3D15"):
        return "wedge"
    return "hex"


def element_face_patterns(element_type):
    shape = element_shape(element_type)
    if shape == "tet":
        return (
            (0, 1, 2),
            (0, 3, 1),
            (1, 3, 2),
            (2, 3, 0),
        )
    if shape == "wedge":
        return (
            (0, 1, 2),
            (3, 5, 4),
            (0, 3, 4, 1),
            (1, 4, 5, 2),
            (2, 5, 3, 0),
        )
    return (
        (0, 1, 2, 3),
        (4, 7, 6, 5),
        (0, 4, 5, 1),
        (1, 5, 6, 2),
        (2, 6, 7, 3),
        (3, 7, 4, 0),
    )


def element_edge_patterns(element_type):
    shape = element_shape(element_type)
    if shape == "tet":
        return ((0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3))
    if shape == "wedge":
        return (
            (0, 1), (1, 2), (2, 0),
            (3, 4), (4, 5), (5, 3),
            (0, 3), (1, 4), (2, 5),
        )
    return (
        (0, 1), (1, 2), (2, 3), (3, 0),
        (4, 5), (5, 6), (6, 7), (7, 4),
        (0, 4), (1, 5), (2, 6), (3, 7),
    )


def vector_sub(left, right):
    return tuple(left[index] - right[index] for index in range(3))


def cross(left, right):
    return (
        left[1] * right[2] - left[2] * right[1],
        left[2] * right[0] - left[0] * right[2],
        left[0] * right[1] - left[1] * right[0],
    )


def dot(left, right):
    return (
        left[0] * right[0]
        + left[1] * right[1]
        + left[2] * right[2]
    )


def norm(value):
    return math.sqrt(dot(value, value))


def tetra_volume(a, b, c, d):
    return abs(dot(vector_sub(a, d), cross(vector_sub(b, d), vector_sub(c, d)))) / 6.0


def solid_volume(element, coordinates):
    points = [coordinates[label] for label in element["nodes"]]
    shape = element_shape(element["type"])
    if shape == "tet":
        return tetra_volume(points[0], points[1], points[2], points[3])
    if shape == "wedge":
        pieces = ((0, 1, 2, 3), (1, 2, 4, 3), (2, 4, 5, 3))
    else:
        pieces = (
            (0, 1, 3, 4),
            (1, 2, 3, 6),
            (1, 3, 4, 6),
            (1, 4, 5, 6),
            (3, 4, 6, 7),
        )
    volumes = [tetra_volume(*(points[index] for index in piece)) for piece in pieces]
    fail(all(value > 1.0e-12 for value in volumes), "solid element has a degenerate corner decomposition")
    return sum(volumes)


def polygon_area(labels, coordinates):
    points = [coordinates[label] for label in labels]
    origin = points[0]
    area = 0.0
    for index in range(1, len(points) - 1):
        area += 0.5 * norm(
            cross(
                vector_sub(points[index], origin),
                vector_sub(points[index + 1], origin),
            )
        )
    return area


def audit_deck(path):
    text = open(path, "r").read()
    blocks = parse_blocks(text)
    names = [block["name"] for block in blocks]
    fail(names.count("PART") == 1 and names.count("END PART") == 1, "deck must contain one Part")
    fail(names.count("ASSEMBLY") == 1 and names.count("END ASSEMBLY") == 1, "deck must contain one Assembly")
    fail(names.count("STEP") == 1 and names.count("END STEP") == 1, "deck must contain one analysis step")
    fail(names.count("STATIC") == 1, "Step-Load is not a static general step")

    element_blocks = blocks_named(blocks, "ELEMENT")
    fail(element_blocks, "deck contains no elements")
    allowed = (
        "C3D4", "C3D4H", "C3D10", "C3D10H", "C3D10M", "C3D10MH",
        "C3D6", "C3D6H", "C3D15", "C3D15H", "C3D8", "C3D8R",
        "C3D8I", "C3D8H", "C3D8RH", "C3D20", "C3D20R", "C3D20H",
        "C3D20RH",
    )
    element_types = set()
    element_ids = set()
    for block in element_blocks:
        element_type = ci(block["params"].get("TYPE"))
        fail(element_type in allowed, "unsupported or non-solid Abaqus element type")
        element_types.add(element_type)
        for _, line in block["rows"]:
            values = numeric_fields(line)
            fail(values, "element row is empty")
            label = int(round(values[0]))
            fail(close(values[0], label, rel=0.0, absolute=1.0e-8), "element label is not an integer")
            fail(label not in element_ids, "duplicate element label")
            element_ids.add(label)

    materials = blocks_named(blocks, "MATERIAL")
    elastic = blocks_named(blocks, "ELASTIC")
    sections = blocks_named(blocks, "SOLID SECTION")
    fail(len(materials) == 1 and len(elastic) == 1 and len(sections) == 1, "Steel material/solid section contract is incomplete")
    values = numeric_fields(elastic[0]["rows"][0][1])
    fail(len(values) == 2 and close(values[0], 210000.0, rel=1.0e-8) and close(values[1], 0.3, rel=1.0e-8), "Steel is not E=210000 MPa, nu=0.3")
    fail(ci(sections[0]["params"].get("MATERIAL")) == ci(materials[0]["params"].get("NAME")), "solid section is not assigned to Steel")
    elsets = resolved_elsets(blocks)
    section_elset = ci(sections[0]["params"].get("ELSET")).split(".")[-1]
    fail(section_elset in elsets, "solid section references a missing Elset")
    fail(elsets[section_elset] == element_ids, "Steel solid section does not cover exactly every beam element")
    facet_map = element_surface_facets(blocks, elsets)

    couplings = blocks_named(blocks, "COUPLING")
    fail(len(couplings) == 2, "exactly two end-face couplings are required")
    for coupling in couplings:
        index = blocks.index(coupling)
        fail(index + 1 < len(blocks) and blocks[index + 1]["name"] == "KINEMATIC", "end-face coupling is not kinematic")
        fail(set(coupling["params"]) == {"CONSTRAINT NAME", "REF NODE", "SURFACE"}, "coupling parameters are incomplete or unexpected")
        kin = blocks[index + 1]
        if kin["rows"]:
            kin_values = [csv_fields(row) for _, row in kin["rows"]]
            fail(kin_values == [["1", "6"]], "kinematic coupling must transmit all six rigid-body DOFs")

    boundary_dofs = defaultdict(set)
    for block in blocks_named(blocks, "BOUNDARY"):
        for _, row in block["rows"]:
            fields = csv_fields(row)
            fail(2 <= len(fields) <= 4, "invalid Boundary row")
            region = ci(fields[0])
            if ci(fields[1]) in ("ENCASTRE", "PINNED"):
                fail(False, "named Encastre/Pinned shortcut is not the required RP DOF contract")
            first = int(float(fields[1]))
            last = int(float(fields[2])) if len(fields) >= 3 else first
            value = float(fields[3]) if len(fields) >= 4 else 0.0
            fail(abs(value) <= 1.0e-12, "support prescribed value is nonzero")
            boundary_dofs[region].update(range(first, last + 1))
    coupling_refs = set(ci(block["params"]["REF NODE"]) for block in couplings)
    coupling_surfaces = dict(
        (ci(block["params"]["REF NODE"]), ci(block["params"]["SURFACE"]))
        for block in couplings
    )
    fail(set(boundary_dofs) == coupling_refs, "constraints must exist only on the two coupling RPs")

    nsets = dict(
        (ci(block["params"].get("NSET")), block)
        for block in blocks_named(blocks, "NSET")
        if block["params"].get("NSET")
    )
    rp_rows = []
    assembly_node_blocks = [block for block in blocks_named(blocks, "NODE") if blocks.index(block) > names.index("ASSEMBLY")]
    assembly_nodes = {}
    for block in assembly_node_blocks:
        for _, row in block["rows"]:
            values = numeric_fields(row)
            fail(len(values) >= 4, "assembly reference node row is malformed")
            assembly_nodes[int(values[0])] = tuple(values[1:4])
    for name in coupling_refs:
        fail(name in nsets, "coupling reference-node set is missing")
        labels = expand_labels(nsets[name])
        fail(len(labels) == 1 and labels[0] in assembly_nodes, "coupling reference set is not one assembly RP")
        rp_rows.append((name, labels[0], assembly_nodes[labels[0]], boundary_dofs[name]))
    rp_rows.sort(key=lambda row: row[2][0])
    fail(len(rp_rows) == 2, "two reference points were not resolved")
    fail(all(close(value, expected, rel=0.0, absolute=1.0e-6) for value, expected in zip(rp_rows[0][2], (0.0, 5.0, 5.0))), "left RP is not at (0,5,5)")
    fail(all(close(value, expected, rel=0.0, absolute=1.0e-6) for value, expected in zip(rp_rows[1][2], (200.0, 5.0, 5.0))), "right RP is not at (200,5,5)")
    fail(rp_rows[0][3] == {1, 2, 3, 4}, "left RP must fix U1/U2/U3/UR1 and release UR2/UR3")
    fail(rp_rows[1][3] == {2, 3}, "right RP must fix only U2/U3")

    step = blocks_named(blocks, "STEP")[0]
    fail(ci(step["params"].get("NAME")) == "STEP-LOAD", "static step must be named Step-Load")
    fail(ci(step["params"].get("NLGEOM", "NO")) in ("NO", "OFF", "FALSE", "0"), "small-deflection Task-09 must not enable NLGEOM")
    loads = blocks_named(blocks, "DSLOAD")
    fail(len(loads) == 1 and len(loads[0]["rows"]) == 1, "exactly one distributed surface load is required")
    load_fields = csv_fields(loads[0]["rows"][0][1])
    fail(len(load_fields) == 3 and ci(load_fields[1]) == "P" and close(float(load_fields[2]), 0.05, rel=1.0e-8), "top load is not a uniform 0.05 MPa pressure")
    load_surface = ci(load_fields[0])
    surfaces = dict(
        (ci(block["params"].get("NAME")), block)
        for block in blocks_named(blocks, "SURFACE")
        if block["params"].get("NAME")
    )
    fail(load_surface in facet_map, "pressure surface is missing")
    fail(not blocks_named(blocks, "CLOAD") and not blocks_named(blocks, "DLOAD"), "unexpected concentrated/body load is present")
    left_ref = rp_rows[0][0]
    right_ref = rp_rows[1][0]
    fail(coupling_surfaces[left_ref] in facet_map and coupling_surfaces[right_ref] in facet_map, "coupling surface is missing")
    return {
        "block_count": len(blocks),
        "element_types": sorted(element_types),
        "element_ids": sorted(element_ids),
        "reference_points": [(row[1], row[2], sorted(row[3])) for row in rp_rows],
        "pressure_surface": load_surface,
        "pressure_facets": facet_map[load_surface],
        "left_coupling_facets": facet_map[coupling_surfaces[left_ref]],
        "right_coupling_facets": facet_map[coupling_surfaces[right_ref]],
    }


def primary_model():
    job = repository_value(mdb.jobs, "Job-UDL")
    model = repository_value(mdb.models, job.model)
    return model


def audit_cae(model):
    fail(len(model.parts.keys()) == 1, "CAE must contain exactly one beam part")
    part = model.parts[model.parts.keys()[0]]
    fail(len(part.nodes) >= 100 and len(part.elements) >= 40, "beam mesh is implausibly coarse")
    fail(all(ci(element.type).startswith("C3D") for element in part.elements), "beam mesh is not exclusively three-dimensional solid elements")
    materials = [model.materials[key] for key in model.materials.keys()]
    fail(len(materials) == 1, "CAE must contain one Steel material")
    elastic = tuple(float(value) for value in materials[0].elastic.table[0][:2])
    fail(close(elastic[0], 210000.0, rel=1.0e-8) and close(elastic[1], 0.3, rel=1.0e-8), "CAE Steel material is incorrect")
    fail(len(model.sections.keys()) == 1, "CAE must contain one homogeneous solid section")
    fail(len(part.sectionAssignments) == 1, "CAE must contain one beam-wide section assignment")
    steps = [key for key in model.steps.keys() if ci(key) != "INITIAL"]
    fail(len(steps) == 1 and ci(steps[0]) == "STEP-LOAD", "CAE must contain only Static Step-Load")
    fail("STATICSTEP" in ci(model.steps[steps[0]].__class__.__name__), "Step-Load is not StaticStep")
    return {"part_nodes": len(part.nodes), "part_elements": len(part.elements)}


def validate_odb_mesh(instance, coordinates, deck_audit):
    elements = {}
    for element in instance.elements:
        label = int(element.label)
        fail(label not in elements, "ODB contains a duplicate element label")
        elements[label] = {
            "type": ci(element.type),
            "nodes": tuple(int(value) for value in element.connectivity),
        }
    fail(set(elements) == set(deck_audit["element_ids"]), "ODB and CAE input-deck element labels differ")
    fail(len(elements) >= 40, "beam mesh is implausibly coarse")

    face_counts = defaultdict(int)
    face_order = {}
    edge_keys = set()
    for element in elements.values():
        patterns = element_face_patterns(element["type"])
        corner_needed = max(max(pattern) for pattern in patterns) + 1
        fail(len(element["nodes"]) >= corner_needed, "solid element connectivity is incomplete")
        for pattern in patterns:
            ordered = tuple(element["nodes"][index] for index in pattern)
            key = frozenset(ordered)
            face_counts[key] += 1
            face_order[key] = ordered
        for left, right in element_edge_patterns(element["type"]):
            edge_keys.add(tuple(sorted((element["nodes"][left], element["nodes"][right]))))
    fail(face_counts and max(face_counts.values()) <= 2, "beam mesh contains a nonmanifold face")
    exterior = {face for face, count in face_counts.items() if count == 1}
    expected_bounds = ((0.0, 200.0), (0.0, 10.0), (0.0, 10.0))
    seen_planes = set()
    for face in exterior:
        matched = []
        for axis, limits in enumerate(expected_bounds):
            for side, value in enumerate(limits):
                if all(close(coordinates[label][axis], value, rel=0.0, absolute=1.0e-5) for label in face):
                    matched.append((axis, side))
        fail(len(matched) == 1, "beam has an internal cavity or nonrectangular exterior face")
        seen_planes.add(matched[0])
    fail(seen_planes == {(axis, side) for axis in range(3) for side in range(2)}, "beam does not expose all six rectangular boundary planes")

    volume = 0.0
    for element in elements.values():
        volume += solid_volume(element, coordinates)
    fail(close(volume, 20000.0, rel=1.0e-5, absolute=0.01), "beam solid volume is not 20000 mm^3")
    lengths = sorted(norm(vector_sub(coordinates[left], coordinates[right])) for left, right in edge_keys)
    fail(lengths, "beam mesh has no topological edges")
    middle = len(lengths) // 2
    median = lengths[middle] if len(lengths) % 2 else 0.5 * (lengths[middle - 1] + lengths[middle])
    fail(2.5 <= median <= 7.5 and max(lengths) <= 9.0, "beam mesh is inconsistent with the 5 mm global seed")

    def plane_faces(axis, value):
        return {
            face
            for face in exterior
            if all(close(coordinates[label][axis], value, rel=0.0, absolute=1.0e-5) for label in face)
        }

    def submitted_faces(rows):
        result = set()
        for element_id, face_number in rows:
            fail(element_id in elements, "surface references an unknown element")
            patterns = element_face_patterns(elements[element_id]["type"])
            fail(1 <= int(face_number) <= len(patterns), "surface references an invalid solid face")
            pattern = patterns[int(face_number) - 1]
            result.add(frozenset(elements[element_id]["nodes"][index] for index in pattern))
        return result

    top = plane_faces(1, 10.0)
    left = plane_faces(0, 0.0)
    right = plane_faces(0, 200.0)
    pressure = submitted_faces(deck_audit["pressure_facets"])
    left_coupling = submitted_faces(deck_audit["left_coupling_facets"])
    right_coupling = submitted_faces(deck_audit["right_coupling_facets"])
    fail(pressure == top, "pressure surface does not cover exactly the complete Y=10 top face")
    fail(left_coupling == left, "left kinematic coupling does not cover exactly the complete X=0 end face")
    fail(right_coupling == right, "right kinematic coupling does not cover exactly the complete X=200 end face")
    top_area = sum([polygon_area(face_order[face], coordinates) for face in top])
    left_area = sum([polygon_area(face_order[face], coordinates) for face in left])
    right_area = sum([polygon_area(face_order[face], coordinates) for face in right])
    fail(close(top_area, 2000.0, rel=1.0e-5, absolute=0.01), "top pressure area is not 2000 mm^2")
    fail(close(left_area, 100.0, rel=1.0e-5, absolute=0.01), "left coupling area is not 100 mm^2")
    fail(close(right_area, 100.0, rel=1.0e-5, absolute=0.01), "right coupling area is not 100 mm^2")
    return {
        "volume": volume,
        "top_area": top_area,
        "left_area": left_area,
        "right_area": right_area,
        "median_edge": median,
        "max_edge": max(lengths),
    }


def odb_record(path, deck_audit):
    odb = openOdb(path=path, readOnly=True)
    try:
        observed_status = ci(getattr(odb.diagnosticData, "jobStatus", ""))
        fail(
            observed_status == "JOB_STATUS_COMPLETED_SUCCESSFULLY",
            "ODB job status is not completed successfully: path=%s status=%s"
            % (path, observed_status),
        )
        fail(len(odb.steps.keys()) == 1, "ODB must contain exactly one step")
        step = repository_value(odb.steps, "Step-Load")
        fail(step.frames, "Step-Load has no result frames")
        frame = step.frames[-1]
        fail(close(frame.frameValue, 1.0, rel=1.0e-7), "final frame time is not 1.0")
        fields = frame.fieldOutputs
        u = repository_value(fields, "U")
        rf = repository_value(fields, "RF")
        stress = repository_value(fields, "S")
        instances = [
            odb.rootAssembly.instances[key]
            for key in odb.rootAssembly.instances.keys()
        ]
        solid_instances = [instance for instance in instances if len(instance.elements)]
        fail(
            len(solid_instances) == 1,
            "ODB must contain exactly one instance with solid elements: path=%s instances=%s"
            % (path, [(str(instance.name), len(instance.elements)) for instance in instances]),
        )
        instance = solid_instances[0]
        coords = dict((int(node.label), tuple(float(value) for value in node.coordinates[:3])) for node in instance.nodes)
        bounds = bbox(list(coords.values()))
        expected = ((0.0, 200.0), (0.0, 10.0), (0.0, 10.0))
        fail(all(close(a, e, rel=0.0, absolute=1.0e-5) for pair_a, pair_e in zip(bounds, expected) for a, e in zip(pair_a, pair_e)), "ODB beam bounds are not 200 x 10 x 10 mm")
        mesh_audit = validate_odb_mesh(instance, coords, deck_audit)
        midpoint = [label for label, xyz in coords.items() if all(close(xyz[i], (100.0, 5.0, 5.0)[i], rel=0.0, absolute=1.0e-5) for i in range(3))]
        fail(len(midpoint) == 1, "ODB has no unique node at (100,5,5)")
        u_rows = [value for value in u.values if int(getattr(value, "nodeLabel", 0) or 0) == midpoint[0]]
        fail(len(u_rows) == 1, "midspan U result is not unique")
        midspan = field_component(u_rows[0], 1)
        fail(midspan < 0.0, "midspan displacement is not downward")
        stress_values = stress.getSubset(region=instance, position=INTEGRATION_POINT).values
        mises = [float(value.mises) for value in stress_values if finite(value.mises)]
        fail(mises and len(set(int(value.elementLabel) for value in stress_values)) == len(instance.elements), "integration-point stress coverage is incomplete")
        max_mises = max(mises)
        rp_sets = []
        for name in ("RP-1", "RP-2"):
            region = repository_value(odb.rootAssembly.nodeSets, name)
            values = rf.getSubset(region=region).values
            fail(len(values) == 1, "%s reaction selection is not unique" % name)
            rp_sets.append(field_component(values[0], 1))
        fail(45.0 < rp_sets[0] < 55.0 and 45.0 < rp_sets[1] < 55.0, "support reactions are not symmetric 50 N values")
        fail(close(sum(rp_sets), 100.0, rel=1.0e-5, absolute=1.0e-5), "vertical reaction total is not 100 N")
        return {
            "metrics": {"midspan_deflection": midspan, "max_mises": max_mises},
            "u": field_signature(u),
            "rf": field_signature(rf),
            "s": field_signature(stress),
            "node_count": len(instance.nodes),
            "element_count": len(instance.elements),
            "bounds": bounds,
            "reactions": rp_sets,
            "mesh_audit": mesh_audit,
        }
    finally:
        odb.close()


def main():
    cae_path, odb_path, result_path, metrics_path, audit_root, solve_root, token = sys.argv[-7:]
    result = {"passed": False, "details": [], "token": token}
    db = None
    try:
        with open(metrics_path, "r") as stream:
            metrics = json.load(stream)
        os.chdir(audit_root)
        db = openMdb(pathName=cae_path)
        model = primary_model()
        result["cae"] = audit_cae(model)
        source_job = repository_value(mdb.jobs, "Job-UDL")
        fail(
            ci(source_job.model) == ci(model.name),
            "Job-UDL is not bound to the audited beam model",
        )
        source_job.writeInput(consistencyChecking=OFF)
        generated = os.path.join(audit_root, source_job.name + ".inp")
        fail(os.path.isfile(generated), "CAE did not write its input deck")
        result["deck"] = audit_deck(generated)
        frozen = os.path.join(solve_root, "frozen.inp")
        shutil.copy2(generated, frozen)
        os.chdir(solve_root)
        recheck_name = "t09abq_" + token[:12]
        recheck = mdb.JobFromInputFile(name=recheck_name, inputFileName=frozen, numCpus=1, numDomains=1)
        recheck.submit(consistencyChecking=OFF)
        recheck.waitForCompletion()
        recheck_odb = os.path.join(solve_root, recheck_name + ".odb")
        fail(os.path.isfile(recheck_odb), "isolated Abaqus re-solve did not create an ODB")
        submitted = odb_record(odb_path, result["deck"])
        recomputed = odb_record(recheck_odb, result["deck"])
        fail(submitted["node_count"] == recomputed["node_count"] and submitted["element_count"] == recomputed["element_count"], "submitted and re-solved ODB meshes differ")
        for field in ("u", "rf", "s"):
            fail(signatures_match(submitted[field], recomputed[field]), "submitted and isolated re-solve %s fields differ" % field.upper())
        fail(close(metrics["midspan_deflection"], submitted["metrics"]["midspan_deflection"], rel=2.0e-5, absolute=2.0e-7), "metrics midspan_deflection does not match the submitted ODB")
        fail(close(metrics["max_mises"], submitted["metrics"]["max_mises"], rel=2.0e-5, absolute=2.0e-5), "metrics max_mises does not match the submitted ODB integration-point maximum")
        result["submitted_metrics"] = submitted["metrics"]
        result["recomputed_metrics"] = recomputed["metrics"]
        result["passed"] = True
    except Exception as exc:
        result["details"].append(str(exc))
        result["traceback"] = traceback.format_exc()
    finally:
        try:
            if db is not None:
                db.close()
        except Exception:
            pass
        with open(result_path, "w") as stream:
            json.dump(result, stream, indent=2, sort_keys=True)
    print("True" if result["passed"] else "False")
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    sys.exit(main())
'''


def run_abaqus_checker(cae_path, odb_path, metrics):
    require(ABAQUS_LAUNCHER.is_file(), "Abaqus 2025 LE launcher is unavailable")
    token = uuid.uuid4().hex
    control = Path(tempfile.mkdtemp(prefix="eval_cli_task09_abq_control_%s_" % token))
    audit = Path(tempfile.mkdtemp(prefix="eval_cli_task09_abq_audit_%s_" % token))
    solve = Path(tempfile.mkdtemp(prefix="eval_cli_task09_abq_solve_%s_" % token))
    staged_cae = audit / (JOB_NAME + ".cae")
    staged_odb = audit / (JOB_NAME + ".odb")
    staged_metrics = audit / "submitted_metrics.json"
    checker = control / "checker.py"
    result = control / "result.json"
    original_hashes = (sha256(cae_path), sha256(odb_path))
    semantic_ok = False
    process_ok = False
    cleanup_ok = False
    try:
        shutil.copy2(str(cae_path), str(staged_cae))
        shutil.copy2(str(odb_path), str(staged_odb))
        staged_metrics.write_text(
            json.dumps(metrics, sort_keys=True) + "\n", encoding="utf-8"
        )
        checker.write_text(ABAQUS_CHECKER, encoding="utf-8")
        command = [
            str(ABAQUS_LAUNCHER),
            "cae",
            "noGUI=" + str(checker),
            "--",
            str(staged_cae),
            str(staged_odb),
            str(result),
            str(staged_metrics),
            str(audit),
            str(solve),
            token,
        ]
        completed = subprocess.run(
            command,
            cwd=str(control),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=1200,
            shell=False,
        )
        log("Abaqus checker returncode=%s" % completed.returncode)
        if completed.stdout:
            log("Abaqus stdout tail=" + completed.stdout[-1200:])
        if completed.stderr:
            log("Abaqus stderr tail=" + completed.stderr[-1200:])
        require(is_nonempty(result), "Abaqus checker did not create result.json")
        payload = json.loads(result.read_text(encoding="utf-8"))
        for message in payload.get("details", []):
            log("Abaqus: " + str(message))
        if payload.get("traceback"):
            log("Abaqus traceback=" + str(payload.get("traceback"))[-4000:])
        if payload.get("passed") is True:
            log("Abaqus deck audit=%s" % payload.get("deck"))
            log("Abaqus submitted metrics=%s" % payload.get("submitted_metrics"))
            log("Abaqus isolated re-solve metrics=%s" % payload.get("recomputed_metrics"))
        semantic_ok = completed.returncode == 0 and payload.get("passed") is True
        require((sha256(cae_path), sha256(odb_path)) == original_hashes, "submitted Abaqus artifacts changed during evaluation")
    except Exception as exc:
        log("Abaqus evaluator failed: %s" % exc)
        semantic_ok = False
    finally:
        try:
            process_ok = clear_owned_processes((token, str(control), str(audit), str(solve)))
        except Exception as exc:
            log("Abaqus process cleanup failed: %s" % exc)
            process_ok = False
        cleanup_ok = all(remove_tree(path) for path in (control, audit, solve))
        if not cleanup_ok:
            log("Abaqus temporary directory cleanup was incomplete")
    return semantic_ok and process_ok and cleanup_ok


SOLID_ELEMENT_NUMBERS = {185, 186, 187, 285}
SURFACE_ELEMENT_NUMBER = 154
TARGET_ELEMENT_NUMBER = 170
CONTACT_ELEMENT_NUMBERS = {173, 174}
COUPLING_ELEMENT_NUMBER = 184


def sanitized_ansys_environment(work):
    env = dict(os.environ)
    for key in list(env):
        if key.upper() in {
            "ANS_USE_UPF",
            "ANS_USER_PATH",
            "ANS_USER_PATH_261",
            "ANSYS_MACROLIB",
            "APDL_STARTUP",
            "ANSYS_APDL_STARTUP",
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
        env=sanitized_ansys_environment(work),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout,
        shell=False,
    )
    text = output.read_text(encoding="utf-8", errors="replace") if output.is_file() else ""
    upper = text.upper()
    require(completed.returncode == 0, "%s returned %s" % (jobname, completed.returncode))
    require(
        "RELEASE 2026 R1" in upper and "BUILD" in upper and "26.1" in upper,
        "%s did not run in ANSYS 2026 R1 v261" % jobname,
    )
    require("RUN COMPLETED" in upper, "%s did not complete" % jobname)
    matches = re.findall(r"NUMBER OF ERROR\s+MESSAGES ENCOUNTERED=\s*(\d+)", upper)
    require(matches and int(matches[-1]) == 0, "%s reported MAPDL errors" % jobname)
    log("%s completed in %.3fs" % (jobname, time.time() - started))
    return text


def apdl_path(path):
    return str(path.with_suffix("")).replace("'", "''")


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
                    constraints.append(
                        (
                            int(fields[0]),
                            fields[1].upper(),
                            float(fields[2].replace("D", "E")),
                        )
                    )
                index += 1
        elif upper.startswith("RLBLOCK,"):
            index += 3
            while index < len(lines):
                fields = lines[index].split()
                if (
                    len(fields) < 2
                    or not re.match(r"^[-+]?\d+$", fields[0])
                    or not re.match(r"^\d+$", fields[1])
                ):
                    break
                real_id = int(fields[0])
                count = int(fields[1])
                values = [
                    float(value.replace("D", "E").replace("d", "e"))
                    for value in fields[2:]
                ]
                while len(values) < count:
                    index += 1
                    require(index < len(lines), "truncated RLBLOCK record")
                    values.extend(
                        float(value.replace("D", "E").replace("d", "e"))
                        for value in lines[index].split()
                    )
                real_constants[real_id] = values[:count]
                index += 1
            continue
        elif upper.startswith("SFEBLOCK,") and ",PRES," in upper:
            index += 2
            while index < len(lines) and not lines[index].upper().startswith("SFE,END"):
                fields = lines[index].split()
                if len(fields) >= 4:
                    pressures.append(
                        {
                            "element": int(fields[0]),
                            "face": int(fields[1]),
                            "kind": int(fields[2]),
                            "values": [
                                float(value.replace("D", "E"))
                                for value in fields[3:]
                            ],
                        }
                    )
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


def vector_sub(left, right):
    return tuple(left[index] - right[index] for index in range(3))


def cross(left, right):
    return (
        left[1] * right[2] - left[2] * right[1],
        left[2] * right[0] - left[0] * right[2],
        left[0] * right[1] - left[1] * right[0],
    )


def dot(left, right):
    return sum(left[index] * right[index] for index in range(3))


def norm(value):
    return math.sqrt(dot(value, value))


def tetra_volume(a, b, c, d):
    return -dot(vector_sub(a, d), cross(vector_sub(b, d), vector_sub(c, d))) / 6.0


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
    mapping = (
        {1: 0, 2: 1, 3: 2, 4: 3}
        if element_number in {187, 285}
        else {1: 0, 2: 1, 3: 2, 4: 3, 5: 4, 6: 5}
    )
    require(face_number in mapping, "pressure references an invalid solid face")
    return faces[mapping[face_number]]


def element_volume(element, element_number, nodes):
    points = [nodes[node_id] for node_id in element["nodes"]]
    if element_number in {187, 285}:
        value = tetra_volume(points[0], points[1], points[2], points[3])
        require(value > 1.0e-12, "solid tetrahedron has nonpositive volume")
        return value
    corner = points[:8]
    tetrahedra = (
        (0, 1, 3, 4),
        (1, 2, 3, 6),
        (1, 3, 4, 6),
        (1, 4, 5, 6),
        (3, 4, 6, 7),
    )
    pieces = [
        tetra_volume(*(corner[index] for index in item)) for item in tetrahedra
    ]
    require(all(value > 1.0e-12 for value in pieces), "solid hexahedron has a nonpositive subvolume")
    return sum(pieces)


def bbox(node_ids, nodes):
    rows = [nodes[node_id] for node_id in node_ids]
    return tuple(
        (min(row[axis] for row in rows), max(row[axis] for row in rows))
        for axis in range(3)
    )


def connected_components(elements):
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

    for element in elements.values():
        labels = element["nodes"]
        for node_id in labels[1:]:
            union(labels[0], node_id)
    groups = defaultdict(dict)
    for element_id, element in elements.items():
        groups[find(element["nodes"][0])][element_id] = element
    return list(groups.values())


def mesh_edge_lengths(elements, types, nodes):
    edges = set()
    for element in elements.values():
        number = types[element["type"]]["number"]
        corners = solid_corner_ids(element, number)
        patterns = (
            ((0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3))
            if number in {187, 285}
            else (
                (0, 1), (1, 2), (2, 3), (3, 0),
                (4, 5), (5, 6), (6, 7), (7, 4),
                (0, 4), (1, 5), (2, 6), (3, 7),
            )
        )
        for left, right in patterns:
            edges.add(tuple(sorted((corners[left], corners[right]))))
    return sorted(norm(vector_sub(nodes[left], nodes[right])) for left, right in edges)


def median(values):
    require(values, "mesh has no topological edges")
    middle = len(values) // 2
    return values[middle] if len(values) % 2 else 0.5 * (values[middle - 1] + values[middle])


def polygon_area(node_ids, nodes):
    unique = []
    seen = set()
    for node_id in node_ids:
        if node_id not in seen:
            seen.add(node_id)
            unique.append(nodes[node_id])
    require(len(unique) >= 3, "surface element has too few unique nodes")
    origin = unique[0]
    return sum(
        0.5 * norm(cross(vector_sub(unique[index], origin), vector_sub(unique[index + 1], origin)))
        for index in range(1, len(unique) - 1)
    )


def parse_materials(text):
    properties = defaultdict(dict)
    pattern = re.compile(
        r"^MPDATA,[^,]*,[^,]*,\s*(EX|PRXY)\s*,\s*(\d+)\s*,\s*\d+\s*,\s*([-+0-9.EeDd]+)",
        re.MULTILINE | re.IGNORECASE,
    )
    for name, material, value in pattern.findall(text):
        properties[int(material)][name.upper()] = float(
            value.replace("D", "E").replace("d", "e")
        )
    return properties


def validate_rectangular_boundary(solid_elements, types, nodes):
    counts = defaultdict(int)
    for element in solid_elements.values():
        number = types[element["type"]]["number"]
        for face in solid_corner_faces(element, number):
            counts[frozenset(face)] += 1
    require(counts and max(counts.values()) <= 2, "beam mesh has a nonmanifold face")
    exterior = [tuple(face) for face, count in counts.items() if count == 1]
    expected = ((0.0, 200.0), (0.0, 10.0), (0.0, 10.0))
    seen = set()
    for face in exterior:
        matched = []
        for axis, limits in enumerate(expected):
            for side, coordinate in enumerate(limits):
                if all(close(nodes[node_id][axis], coordinate, rel=0.0, abs_tol=1.0e-5) for node_id in face):
                    matched.append((axis, side))
        require(matched, "beam has an internal cavity or nonrectangular exterior face")
        seen.update(matched)
    require(seen == {(axis, side) for axis in range(3) for side in range(2)}, "beam does not expose all six rectangular boundary planes")
    return exterior


def validate_ansys_model(model):
    text = model["text"]
    nodes = model["nodes"]
    types = model["element_types"]
    elements = model["elements"]
    require(nodes and types and elements, "CDB is missing FE records")
    solid_type_ids = {
        type_id
        for type_id, row in types.items()
        if row["number"] in SOLID_ELEMENT_NUMBERS
    }
    surface_type_ids = {
        type_id
        for type_id, row in types.items()
        if row["number"] == SURFACE_ELEMENT_NUMBER
    }
    target_type_ids = {
        type_id
        for type_id, row in types.items()
        if row["number"] == TARGET_ELEMENT_NUMBER
    }
    contact_type_ids = {
        type_id
        for type_id, row in types.items()
        if row["number"] in CONTACT_ELEMENT_NUMBERS
    }
    coupling_type_ids = {
        type_id
        for type_id, row in types.items()
        if row["number"] == COUPLING_ELEMENT_NUMBER
    }
    require(solid_type_ids, "no supported three-dimensional structural solid element")
    solid_elements = {
        eid: row for eid, row in elements.items() if row["type"] in solid_type_ids
    }
    surface_elements = {
        eid: row for eid, row in elements.items() if row["type"] in surface_type_ids
    }
    target_elements = {
        eid: row for eid, row in elements.items() if row["type"] in target_type_ids
    }
    contact_elements = {
        eid: row for eid, row in elements.items() if row["type"] in contact_type_ids
    }
    coupling_elements = {
        eid: row for eid, row in elements.items() if row["type"] in coupling_type_ids
    }
    classified = set(solid_elements) | set(surface_elements) | set(target_elements) | set(contact_elements) | set(coupling_elements)
    require(classified == set(elements), "model contains an unsupported or extra active element")
    require(len(solid_elements) >= 40, "solid mesh is implausibly coarse")
    require(len(connected_components(solid_elements)) == 1, "beam solid mesh is not one connected body")
    solid_nodes = set(
        node_id for element in solid_elements.values() for node_id in element["nodes"]
    )
    expected_bounds = ((0.0, 200.0), (0.0, 10.0), (0.0, 10.0))
    observed_bounds = bbox(solid_nodes, nodes)
    require(all(close(a, e, rel=0.0, abs_tol=1.0e-5) for pair_a, pair_e in zip(observed_bounds, expected_bounds) for a, e in zip(pair_a, pair_e)), "beam bounds are not exactly 200 x 10 x 10 mm")
    exterior = validate_rectangular_boundary(solid_elements, types, nodes)
    volume = sum(
        element_volume(row, types[row["type"]]["number"], nodes)
        for row in solid_elements.values()
    )
    require(close(volume, 20000.0, rel=1.0e-5, abs_tol=0.01), "beam solid volume is not 20000 mm^3")
    edges = mesh_edge_lengths(solid_elements, types, nodes)
    require(2.5 <= median(edges) <= 7.5 and max(edges) <= 9.0, "beam mesh is inconsistent with the 5 mm global seed")

    materials = parse_materials(text)
    solid_materials = {row["material"] for row in solid_elements.values()}
    require(len(solid_materials) == 1, "beam solids do not use one Steel material")
    material = materials.get(next(iter(solid_materials)), {})
    require(close(material.get("EX", float("nan")), 210000.0, rel=1.0e-6, abs_tol=0.1), "Steel Young's modulus is not 210000 MPa")
    require(close(material.get("PRXY", float("nan")), 0.3, rel=1.0e-6, abs_tol=1.0e-7), "Steel Poisson ratio is not 0.3")

    fixed = defaultdict(dict)
    for node_id, label, value in model["constraints"]:
        fixed[node_id][label] = value
    require(set(fixed).isdisjoint(solid_nodes), "support constraints are applied directly to beam solid nodes instead of RPs")
    require(len(fixed) == 2, "exactly two constrained support RPs are required")
    ordered_pilots = sorted(fixed, key=lambda node_id: nodes[node_id][0])
    left, right = ordered_pilots
    require(all(close(value, expected, rel=0.0, abs_tol=1.0e-5) for value, expected in zip(nodes[left], (0.0, 5.0, 5.0))), "left pilot is not at (0,5,5)")
    require(all(close(value, expected, rel=0.0, abs_tol=1.0e-5) for value, expected in zip(nodes[right], (200.0, 5.0, 5.0))), "right pilot is not at (200,5,5)")
    require(set(fixed[left]) == {"UX", "UY", "UZ", "ROTX"}, "left support must fix UX/UY/UZ/ROTX and release ROTY/ROTZ")
    require(set(fixed[right]) == {"UY", "UZ"}, "right support must fix only UY/UZ")
    require(all(abs(value) <= 1.0e-12 for dofs in fixed.values() for value in dofs.values()), "support prescribed value is nonzero")

    end_nodes = {
        left: {node_id for node_id in solid_nodes if close(nodes[node_id][0], 0.0, rel=0.0, abs_tol=1.0e-5)},
        right: {node_id for node_id in solid_nodes if close(nodes[node_id][0], 200.0, rel=0.0, abs_tol=1.0e-5)},
    }
    mpc_mode = bool(contact_elements or target_elements)
    if mpc_mode:
        require(contact_elements and target_elements, "rigid surface constraint has an incomplete CONTA/TARGE pair")
        target_by_real = defaultdict(list)
        contact_by_real = defaultdict(list)
        for row in target_elements.values():
            target_by_real[row["real"]].append(row)
        for row in contact_elements.values():
            contact_by_real[row["real"]].append(row)
        require(set(target_by_real) == set(contact_by_real) and len(target_by_real) == 2, "two independent rigid end-surface pairs are required")
        resolved = {}
        for real_id in target_by_real:
            pilot_labels = set(
                node_id for row in target_by_real[real_id] for node_id in row["nodes"]
            )
            require(len(pilot_labels) == 1, "TARGE170 PILO pair does not resolve one pilot")
            pilot = next(iter(pilot_labels))
            require(pilot in (left, right), "TARGE170 PILO is not a support RP")
            face_nodes = set(
                node_id for row in contact_by_real[real_id] for node_id in row["nodes"]
            )
            require(face_nodes == end_nodes[pilot], "CONTA end surface does not cover the complete beam end face")
            resolved[pilot] = real_id
        require(set(resolved) == {left, right}, "both support RPs are not coupled")
        for type_id in contact_type_ids:
            keyopts = types[type_id]["keyopts"]
            require(keyopts[1] == 2 and keyopts[3] == 2 and keyopts[11] == 5, "CONTA173/174 is not MPC rigid-surface constraint mode")
        for type_id in target_type_ids:
            keyopts = types[type_id]["keyopts"]
            require(keyopts[1] == 1 and keyopts[3] == 111111, "TARGE170 is not an unconstrained six-DOF PILO target")
    else:
        ce_text = "\n".join(
            line for line in model["lines"] if re.match(r"^\s*(?:CEBLOCK\b|CE\s*,|CERIG\b|RBE3\b)", line, re.IGNORECASE)
        )
        require(coupling_elements and not ce_text, "non-MPC184 equation coupling is not semantically auditable")
        resolved = defaultdict(set)
        for row in coupling_elements.values():
            labels = set(row["nodes"])
            pilots = labels & {left, right}
            require(len(pilots) == 1 and len(labels) == 2, "MPC184 coupling element must join one support RP to one end-face node")
            pilot = next(iter(pilots))
            dependent = next(iter(labels - {pilot}))
            require(dependent in end_nodes[pilot], "MPC184 coupling crosses an end face or references a non-face node")
            resolved[pilot].add(dependent)
        require(set(resolved) == {left, right}, "both support RPs are not coupled by MPC184")
        for pilot in (left, right):
            require(resolved[pilot] == end_nodes[pilot], "MPC184 coupling does not cover every end-face node exactly")

    pressure_rows = [row for row in model["pressures"] if row["kind"] == 1]
    require(pressure_rows, "no pressure load is stored in the DB")
    require(all(row["values"] and all(close(value, 0.05, rel=1.0e-6, abs_tol=1.0e-8) for value in row["values"]) for row in pressure_rows), "top pressure is not uniformly 0.05 MPa")
    require(all(row["kind"] == 1 or all(abs(value) <= 1.0e-12 for value in row["values"]) for row in model["pressures"]), "pressure has a nonzero secondary component")
    top_faces = {
        frozenset(face)
        for face in exterior
        if all(close(nodes[node_id][1], 10.0, rel=0.0, abs_tol=1.0e-5) for node_id in face)
    }
    if surface_elements:
        require({row["element"] for row in pressure_rows} == set(surface_elements), "pressure does not cover exactly the SURF154 load mesh")
        actual_faces = []
        for element in surface_elements.values():
            labels = [node_id for node_id in element["nodes"] if node_id in solid_nodes]
            require(labels and all(close(nodes[node_id][1], 10.0, rel=0.0, abs_tol=1.0e-5) for node_id in labels), "SURF154 pressure element is not on Y=10")
            actual_faces.append(frozenset(labels))
        require(len(actual_faces) == len(set(actual_faces)) and set(actual_faces) == top_faces, "SURF154 mesh does not cover exactly the complete beam top")
        pressure_area = sum(polygon_area(element["nodes"], nodes) for element in surface_elements.values())
    else:
        require(all(row["element"] in solid_elements for row in pressure_rows), "pressure references a non-solid element")
        actual_faces = []
        for row in pressure_rows:
            element = solid_elements[row["element"]]
            face = solid_face_for_load(element, types[element["type"]]["number"], row["face"])
            require(all(close(nodes[node_id][1], 10.0, rel=0.0, abs_tol=1.0e-5) for node_id in face), "pressure references a non-top solid face")
            actual_faces.append(frozenset(face))
        require(set(actual_faces) == top_faces, "solid-face pressure does not cover exactly the complete beam top")
        pressure_area = sum(polygon_area(face, nodes) for face in actual_faces)
    require(close(pressure_area, 2000.0, rel=1.0e-5, abs_tol=0.01), "pressure area is not 2000 mm^2")
    require(not re.search(r"^\s*(?:F|FBLOCK|BF|BFBLOCK|BFEBLOCK),", text, re.MULTILINE | re.IGNORECASE), "unexpected nodal or body load is present")
    for command in ("ACEL", "OMEGA", "DOMEGA", "CGOMEGA", "DCGOMG"):
        for line in re.findall(r"^%s,.*$" % command, text, re.MULTILINE | re.IGNORECASE):
            values = [float(value.replace("D", "E").replace("d", "e")) for value in re.findall(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[EeDd][-+]?\d+)?", line)]
            require(all(abs(value) <= 1.0e-12 for value in values), "unexpected nonzero %s load is present" % command)
    midpoint = [node_id for node_id in solid_nodes if all(close(nodes[node_id][axis], (100.0, 5.0, 5.0)[axis], rel=0.0, abs_tol=1.0e-5) for axis in range(3))]
    require(len(midpoint) == 1, "mesh has no unique node at (100,5,5)")
    return {
        "solid_type_ids": sorted(solid_type_ids),
        "solid_nodes": solid_nodes,
        "solid_elements": set(solid_elements),
        "midpoint": midpoint[0],
        "left_pilot": left,
        "right_pilot": right,
        "volume": volume,
        "pressure_area": pressure_area,
        "coupling_mode": "mpc_contact_target" if mpc_mode else "constraint_equation_or_mpc184",
    }


def audit_model_to_cdb(work, db_path):
    script = r"""/BATCH
/CLEAR,NOSTART
/ABBR,DELE,ALL
/PSEARCH,OFF
RESUME,'%s','db'
/PSEARCH,OFF
/PREP7
ALLSEL,ALL
CDWRITE,DB,task09_model,cdb
FINISH
/EXIT,NOSAVE
""" % apdl_path(db_path)
    run_ansys(work, "t09_model_audit", script)
    cdb = work / "task09_model.cdb"
    require(is_nonempty(cdb, 10000), "ANSYS DB audit did not create a usable CDB")
    return cdb


def extract_ansys_result(work, jobname, db_path, rst_path, model_info):
    signature = work / (jobname + "_signature.txt")
    selection = []
    for index, type_id in enumerate(model_info["solid_type_ids"]):
        selection.append(
            "ESEL,%s,TYPE,,%d" % ("S" if index == 0 else "A", type_id)
        )
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
*GET,NCOUNT,NODE,0,COUNT
NID=0
*CFOPEN,%s,txt
*DO,II,1,NCOUNT
NID=NDNEXT(NID)
*GET,UX,NODE,NID,U,X
*GET,UY,NODE,NID,U,Y
*GET,UZ,NODE,NID,U,Z
*GET,RFX,NODE,NID,RF,FX
*GET,RFY,NODE,NID,RF,FY
*GET,RFZ,NODE,NID,RF,FZ
*VWRITE,NID,UX,UY,UZ,RFX,RFY,RFZ
('N,',7(E24.16,','))
*ENDDO
ALLSEL,ALL
%s
NSLE,S
*GET,SCOUNT,NODE,0,COUNT
SID=0
*DIM,SXNAR,ARRAY,1
*DIM,SYNAR,ARRAY,1
*DIM,SZNAR,ARRAY,1
*DIM,SXYNAR,ARRAY,1
*DIM,SYZNAR,ARRAY,1
*DIM,SXZNAR,ARRAY,1
*DIM,SEQVNAR,ARRAY,1
*DO,II,1,SCOUNT
SID=NDNEXT(SID)
*VGET,SXNAR(1),NODE,SID,S,X,NAR
*VGET,SYNAR(1),NODE,SID,S,Y,NAR
*VGET,SZNAR(1),NODE,SID,S,Z,NAR
*VGET,SXYNAR(1),NODE,SID,S,XY,NAR
*VGET,SYZNAR(1),NODE,SID,S,YZ,NAR
*VGET,SXZNAR(1),NODE,SID,S,XZ,NAR
*VGET,SEQVNAR(1),NODE,SID,S,EQV,NAR
SX=SXNAR(1)
SY=SYNAR(1)
SZ=SZNAR(1)
SXY=SXYNAR(1)
SYZ=SYZNAR(1)
SXZ=SXZNAR(1)
SEQV=SEQVNAR(1)
*VWRITE,SID,SX,SY,SZ,SXY,SYZ,SXZ,SEQV
('S,',8(E24.16,','))
*ENDDO
*CFCLOS
FINISH
/EXIT,NOSAVE
""" % (
        apdl_path(db_path),
        apdl_path(rst_path),
        str(signature.with_suffix("")).replace("'", "''"),
        "\n".join(selection),
    )
    run_ansys(work, jobname, script)
    require(is_nonempty(signature, 1000), "%s did not emit a result signature" % jobname)
    nodal = {}
    stress = {}
    for line in signature.read_text(encoding="utf-8", errors="replace").splitlines():
        fields = [field.strip() for field in line.split(",") if field.strip()]
        if not fields or fields[0] not in ("N", "S"):
            continue
        values = [float(value.replace("D", "E")) for value in fields[1:]]
        expected = 7 if fields[0] == "N" else 8
        require(len(values) == expected, "malformed ANSYS result signature row")
        node_id = int(round(values[0]))
        require(close(values[0], node_id, rel=0.0, abs_tol=1.0e-7), "noninteger result node label")
        target = nodal if fields[0] == "N" else stress
        require(node_id not in target, "duplicate ANSYS result signature row")
        target[node_id] = tuple(values[1:])
    require(
        nodal and stress and set(stress) <= set(nodal),
        "ANSYS U/RF/NAR stress signature is incomplete",
    )
    return {"nodal": nodal, "stress": stress}


def write_resolve_script(db_path, solid_type_ids):
    selection = []
    for index, type_id in enumerate(solid_type_ids):
        selection.append(
            "ESEL,%s,TYPE,,%d" % ("S" if index == 0 else "A", type_id)
        )
    selection.append("CM,EVAL_SOLID,ELEM")
    selection.append("ALLSEL,ALL")
    return r"""/BATCH
/CLEAR,NOSTART
/ABBR,DELE,ALL
/PSEARCH,OFF
RESUME,'%s','db'
/PSEARCH,OFF
/SOLU
ANTYPE,STATIC
NLGEOM,OFF
TIME,1
NSUBST,1,1,1
OUTRES,ALL,ALL
%s
OUTRES,NAR,ALL,EVAL_SOLID
ALLSEL,ALL
SOLVE
SAVE
FINISH
/EXIT,NOSAVE
""" % (apdl_path(db_path), "\n".join(selection))


def result_metrics(signature, model_info):
    nodal = signature["nodal"]
    stress = signature["stress"]
    require(model_info["midpoint"] in nodal, "midspan node is absent from RST")
    midspan = nodal[model_info["midpoint"]][1]
    require(midspan < 0.0, "midspan displacement is not downward")
    solid_stress = [stress[node_id][6] for node_id in model_info["solid_nodes"]]
    require(solid_stress and all(math.isfinite(value) for value in solid_stress), "nodal stress is incomplete or nonfinite")
    max_mises = max(solid_stress)
    left = nodal[model_info["left_pilot"]]
    right = nodal[model_info["right_pilot"]]
    require(45.0 < left[4] < 55.0 and 45.0 < right[4] < 55.0, "support reactions are not symmetric 50 N values")
    require(close(left[4] + right[4], 100.0, rel=1.0e-5, abs_tol=1.0e-5), "support RFY total is not 100 N")
    return {
        "midspan_deflection": midspan,
        "max_mises": max_mises,
        "left_reaction_y": left[4],
        "right_reaction_y": right[4],
    }


def ansys_signatures_match(left, right):
    for name in ("nodal", "stress"):
        if set(left[name]) != set(right[name]):
            return False
        for node_id in left[name]:
            actual = left[name][node_id]
            expected = right[name][node_id]
            if len(actual) != len(expected):
                return False
            if any(not close(a, b, rel=5.0e-4, abs_tol=2.0e-6) for a, b in zip(actual, expected)):
                return False
    return True


def run_ansys_checker(db_path, rst_path, metrics):
    token = uuid.uuid4().hex
    audit = Path(tempfile.mkdtemp(prefix="eval_cli_task09_ansys_audit_%s_" % token))
    solve = Path(tempfile.mkdtemp(prefix="eval_cli_task09_ansys_solve_%s_" % token))
    staged_db = audit / "submitted.db"
    staged_rst = audit / "submitted.rst"
    resolve_db = solve / "model.db"
    original_hashes = (sha256(db_path), sha256(rst_path))
    semantic_ok = False
    process_ok = False
    cleanup_ok = False
    try:
        shutil.copy2(str(db_path), str(staged_db))
        shutil.copy2(str(rst_path), str(staged_rst))
        shutil.copy2(str(db_path), str(resolve_db))
        cdb = audit_model_to_cdb(audit, staged_db)
        model = parse_cdb(cdb)
        model_info = validate_ansys_model(model)
        submitted = extract_ansys_result(
            audit,
            "t09_submitted_" + token[:8],
            staged_db,
            staged_rst,
            model_info,
        )
        submitted_metrics = result_metrics(submitted, model_info)
        resolve_job = "t09_resolve_" + token[:8]
        run_ansys(
            solve,
            resolve_job,
            write_resolve_script(resolve_db, model_info["solid_type_ids"]),
        )
        resolved_rst = solve / (resolve_job + ".rst")
        require(is_nonempty(resolved_rst, 100000), "isolated ANSYS re-solve did not create a usable RST")
        recomputed = extract_ansys_result(
            solve,
            "t09_recheck_" + token[:8],
            resolve_db,
            resolved_rst,
            model_info,
        )
        recomputed_metrics = result_metrics(recomputed, model_info)
        require(ansys_signatures_match(submitted, recomputed), "submitted RST and isolated ANSYS re-solve U/RF/S fields differ")
        require(close(metrics["midspan_deflection"], submitted_metrics["midspan_deflection"], rel=2.0e-5, abs_tol=2.0e-7), "metrics midspan_deflection does not match the submitted RST")
        require(close(metrics["max_mises"], submitted_metrics["max_mises"], rel=2.0e-5, abs_tol=2.0e-5), "metrics max_mises does not match the submitted RST nodal-averaged SEQV maximum")
        require(close(submitted_metrics["midspan_deflection"], recomputed_metrics["midspan_deflection"], rel=5.0e-4, abs_tol=2.0e-6), "isolated ANSYS re-solve changed midspan displacement")
        require(close(submitted_metrics["max_mises"], recomputed_metrics["max_mises"], rel=5.0e-4, abs_tol=5.0e-4), "isolated ANSYS re-solve changed maximum Mises stress")
        require((sha256(db_path), sha256(rst_path)) == original_hashes, "submitted ANSYS artifacts changed during evaluation")
        log("ANSYS model volume=%s pressure_area=%s coupling=%s" % (model_info["volume"], model_info["pressure_area"], model_info["coupling_mode"]))
        log("ANSYS submitted metrics=%s" % submitted_metrics)
        log("ANSYS isolated re-solve metrics=%s" % recomputed_metrics)
        semantic_ok = True
    except Exception as exc:
        log("ANSYS evaluator failed: %s" % exc)
        semantic_ok = False
    finally:
        try:
            process_ok = clear_owned_processes((token, str(audit), str(solve)))
        except Exception as exc:
            log("ANSYS process cleanup failed: %s" % exc)
            process_ok = False
        cleanup_ok = all(remove_tree(path) for path in (audit, solve))
        if not cleanup_ok:
            log("ANSYS temporary directory cleanup was incomplete")
    return semantic_ok and process_ok and cleanup_ok


def write_details(root, passed):
    try:
        (root / "eval_detail.txt").write_text(
            "\n".join(DETAILS) + "\n", encoding="utf-8"
        )
        (root / "eval_result.txt").write_text(
            "True\n" if passed else "False\n", encoding="utf-8"
        )
    except Exception:
        pass


def evaluate():
    desktop = desktop_dir()
    root = desktop / 'result'
    if not root.is_dir():
        log('result directory missing')
        return False, desktop
    metrics = read_metrics(root)
    branch = discover_branch(root)
    log("selected native branch: %s" % branch[0])
    if branch[0] == "abaqus":
        return run_abaqus_checker(branch[1], branch[2], metrics), root
    return run_ansys_checker(branch[1], branch[2], metrics), root


def main():
    passed = False
    root = desktop_dir()
    try:
        passed, root = evaluate()
    except Exception as exc:
        log("evaluation failed: %s" % exc)
        log(traceback.format_exc())
        passed = False
    write_details(root, passed)
    print("True" if passed else "False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
