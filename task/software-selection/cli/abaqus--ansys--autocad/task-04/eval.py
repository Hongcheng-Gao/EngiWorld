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
import uuid
from pathlib import Path


TASK_ID = "c-open-abaqus-ansys-autocad-task-04-windows"
JOB_NAME = "Job-Tension"
STEP_NAME = "Step-Load"
METRIC_FIELDS = ("free_end_displacement", "axial_stress")
ABAQUS_COMMAND = r"C:\SIMULIA\Commands\abaqus.bat"
ANSYS_EXEC = r"C:\Program Files\ANSYS Inc\v261\ansys\bin\winx64\ANSYS261.exe"
DESKTOP_CANDIDATES = [
    Path(os.environ.get("USERPROFILE", r"C:\Users\user")) / "Desktop",
    Path(r"C:\Users\user\Desktop"),
    Path(r"C:\Users\User\Desktop"),
]
DETAILS = []


def log(message):
    DETAILS.append(str(message))


def desktop_dir():
    for path in DESKTOP_CANDIDATES:
        if path.exists():
            return path
    return DESKTOP_CANDIDATES[1]


def is_nonempty(path):
    try:
        return path.is_file() and path.stat().st_size > 0
    except Exception:
        return False


def files_with_suffix(root, suffix):
    try:
        return sorted(
            [path for path in root.iterdir() if path.suffix.lower() == suffix and is_nonempty(path)],
            key=lambda path: path.name.lower(),
        )
    except Exception:
        return []


def finite_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def read_metrics(root):
    path = root / "metrics.json"
    if not is_nonempty(path):
        log("metrics.json is missing")
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        log("metrics.json is invalid: %s" % exc)
        return None
    if not isinstance(data, dict):
        log("metrics.json must be an object")
        return None
    if set(data) != set(METRIC_FIELDS) or any(not finite_number(data[name]) for name in METRIC_FIELDS):
        log("metrics.json must contain exactly free_end_displacement and axial_stress as finite numbers")
        return None
    metrics = {name: float(data[name]) for name in METRIC_FIELDS}
    if not (0.0040 < metrics["free_end_displacement"] < 0.0055):
        log("free_end_displacement is outside the task-specific physical range")
        return None
    if not (9.8 < metrics["axial_stress"] < 10.2):
        log("axial_stress is outside the task-specific physical range")
        return None
    return metrics


def discover_branch(root):
    caes = files_with_suffix(root, ".cae")
    odbs = files_with_suffix(root, ".odb")
    dbs = files_with_suffix(root, ".db")
    rsts = files_with_suffix(root, ".rst")
    unsupported = files_with_suffix(root, ".wbpj") + files_with_suffix(root, ".rth")
    if unsupported:
        log("unsupported or extra Workbench/thermal solver artifacts are present")
        return None
    has_abaqus = bool(caes or odbs)
    has_ansys = bool(dbs or rsts)
    if has_abaqus and has_ansys:
        log("deliver exactly one solver branch, not both Abaqus and ANSYS artifacts")
        return None
    if has_abaqus:
        if len(caes) != 1 or len(odbs) != 1:
            log("Abaqus delivery requires exactly one CAE and one ODB")
            return None
        if caes[0].stem.lower() != odbs[0].stem.lower():
            log("Abaqus model and result stems do not match")
            return None
        return "abaqus", caes[0], odbs[0]
    if has_ansys:
        if len(dbs) != 1 or len(rsts) != 1:
            log("ANSYS delivery requires exactly one DB and one RST")
            return None
        if dbs[0].stem.lower() != rsts[0].stem.lower():
            log("ANSYS model and result stems do not match")
            return None
        return "ansys", dbs[0], rsts[0]
    log("no supported native model/result pair found")
    return None


def close_enough(actual, expected, rel=1.0e-3, abs_tol=1.0e-8):
    try:
        return math.isclose(float(actual), float(expected), rel_tol=rel, abs_tol=abs_tol)
    except Exception:
        return False


def run_abaqus_checker(cae_path, odb_path, submitted_metrics):
    temp_root = Path(tempfile.mkdtemp(prefix="eval_cli_task04_abaqus_%s_" % uuid.uuid4().hex))
    checker_path = temp_root / "checker.py"
    result_path = temp_root / "result.json"
    checker_source = r'''
# -*- coding: utf-8 -*-
from __future__ import print_function

import json
import math
import traceback
import builtins

from abaqus import openMdb
from abaqusConstants import ON, SIZE
from caeModules import *
from odbAccess import openOdb

CAE_PATH = __CAE_PATH__
ODB_PATH = __ODB_PATH__
RESULT_PATH = __RESULT_PATH__
SUBMITTED = __SUBMITTED__
RECHECK_JOB_NAME = __RECHECK_JOB_NAME__
JOB_NAME = "Job-Tension"
STEP_NAME = "Step-Load"
ALLOWED_TYPES = (
    "C3D4", "C3D4H", "C3D6", "C3D6H", "C3D8", "C3D8H", "C3D8I",
    "C3D8R", "C3D8RH", "C3D10", "C3D10H", "C3D10M", "C3D10MH",
    "C3D15", "C3D15H", "C3D20", "C3D20H", "C3D20R", "C3D20RH",
)
DETAILS = []


def fail(message):
    DETAILS.append(str(message))
    return False


def close(actual, expected, rel=1.0e-6, abs_tol=1.0e-8):
    try:
        return math.isclose(float(actual), float(expected), rel_tol=rel, abs_tol=abs_tol)
    except Exception:
        return False


def label_set(nodes):
    try:
        return set(int(node.label) for node in nodes)
    except Exception:
        return set()


def coords_by_label(nodes):
    result = {}
    for node in nodes:
        coords = tuple(float(value) for value in node.coordinates)
        if len(coords) == 2:
            coords = coords + (0.0,)
        result[int(node.label)] = coords[:3]
    return result


def is_unset(value):
    return value is None or str(value).strip().upper() in ("UNSET", "NONE")


def uses_global_coordinate_system(load, attribute):
    try:
        value = getattr(load, attribute)
    except (AttributeError, KeyError):
        return True
    if value is None:
        return True
    if isinstance(value, bool):
        return not value
    try:
        numeric = float(value)
    except Exception:
        numeric = None
    if numeric is not None and math.isfinite(numeric):
        return abs(numeric) <= 1.0e-12
    text = str(value).strip().upper().replace("-", "_")
    return text in (
        "",
        "NONE",
        "UNSET",
        "DEFAULT",
        "GLOBAL",
        "GLOBAL CSYS",
        "GLOBAL_CSYS",
        "GLOBAL COORDINATE SYSTEM",
        "GLOBAL_COORDINATE_SYSTEM",
        "OFF",
    )


def active_objects(repo):
    return [item for name, item in active_named_objects(repo)]


def active_named_objects(repo):
    values = []
    for name in repo.keys():
        item = repo[name]
        try:
            if item.suppressed:
                continue
        except Exception:
            pass
        values.append((str(name), item))
    return values


def entity_labels(sequence):
    result = set()
    try:
        iterator = iter(sequence)
    except Exception:
        return result
    for item in iterator:
        try:
            result.add(int(item.label))
            continue
        except Exception:
            pass
        result.update(entity_labels(item))
    return result


def region_labels(model, region, entity_name):
    try:
        direct = entity_labels(getattr(region, entity_name))
        if direct:
            return direct
    except Exception:
        pass
    try:
        descriptor = tuple(region)
    except Exception:
        return None
    if len(descriptor) < 4:
        return None
    set_name = str(descriptor[0])
    owners = [str(value) for value in descriptor[1:-3]]
    candidates = []
    for owner in owners:
        try:
            if owner.upper() == "ASSEMBLY" and set_name in model.rootAssembly.sets.keys():
                candidates.append(entity_labels(getattr(model.rootAssembly.sets[set_name], entity_name)))
        except Exception:
            pass
        try:
            if owner in model.parts.keys() and set_name in model.parts[owner].sets.keys():
                candidates.append(entity_labels(getattr(model.parts[owner].sets[set_name], entity_name)))
        except Exception:
            pass
        try:
            instances = model.rootAssembly.instances
            if owner in instances.keys() and set_name in instances[owner].sets.keys():
                candidates.append(entity_labels(getattr(instances[owner].sets[set_name], entity_name)))
        except Exception:
            pass
    if not candidates or not candidates[0]:
        return None
    if any(value != candidates[0] for value in candidates[1:]):
        return None
    return candidates[0]


def state_is_active(state):
    status = str(getattr(state, "status", "")).strip().upper()
    return status in ("CREATED", "PROPAGATED", "MODIFIED")


def state_is_unset(value):
    return value is None or str(value).strip().upper() in ("UNSET", "FREED", "NONE")


def validate_input_output_request(
    job, expected_elements, expected_fixed_nodes, expected_free_nodes, connectivity
):
    try:
        job.writeInput(consistencyChecking=ON)
    except Exception as exc:
        return fail("CAE job cannot write a consistent native input: %s" % exc)
    path = JOB_NAME + ".inp"
    try:
        stream = open(path, "r")
        lines = stream.readlines()
        stream.close()
    except Exception as exc:
        return fail("cannot read CAE-generated input: %s" % exc)
    current_step = None
    current_card = None
    steps = []
    cards = []
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("**"):
            continue
        if line.startswith("*"):
            pieces = [piece.strip() for piece in line[1:].split(",")]
            keyword = pieces[0].upper()
            params = {}
            for piece in pieces[1:]:
                if "=" in piece:
                    key, value = piece.split("=", 1)
                    params[key.strip().upper()] = value.strip()
                elif piece:
                    params[piece.upper()] = True
            current_card = {"keyword": keyword, "params": params, "data": [], "step": current_step}
            if keyword == "STEP":
                current_step = params.get("NAME", "")
                steps.append(current_step)
                current_card["step"] = current_step
            elif keyword == "END STEP":
                current_card["step"] = current_step
                current_step = None
            cards.append(current_card)
            continue
        if current_card is not None:
            current_card["data"].append(line)
    if steps != [STEP_NAME]:
        return fail("CAE-generated input must contain the single Step-Load step")

    elsets = {}
    nsets = {}
    for card in cards:
        set_kind = None
        set_name = ""
        if card["keyword"] in ("ELEMENT", "ELSET"):
            set_kind = "ELSET"
            set_name = card["params"].get("ELSET", "").upper()
        elif card["keyword"] in ("NODE", "NSET"):
            set_kind = "NSET"
            set_name = card["params"].get("NSET", "").upper()
        if not set_kind or not set_name:
            continue
        repository = elsets if set_kind == "ELSET" else nsets
        values = repository.setdefault(set_name, [])
        tokens = [token.strip() for row in card["data"] for token in row.split(",") if token.strip()]
        if card["keyword"] in ("ELEMENT", "NODE"):
            for row in card["data"]:
                fields = [value.strip() for value in row.split(",") if value.strip()]
                try:
                    values.append(int(fields[0]))
                except Exception:
                    pass
        elif "GENERATE" in card["params"]:
            numbers = []
            for token in tokens:
                try:
                    numbers.append(int(token))
                except Exception:
                    pass
            for index in range(0, len(numbers) - 2, 3):
                first, last, increment = numbers[index:index + 3]
                if increment > 0:
                    values.extend(range(first, last + 1, increment))
        else:
            for token in tokens:
                try:
                    values.append(int(token))
                except Exception:
                    values.append(token.upper())

    def resolve_elset(name, stack):
        key = str(name).upper().split(".")[-1]
        if key not in elsets or key in stack:
            return set()
        result = set()
        for value in elsets[key]:
            if isinstance(value, int):
                result.add(value)
            else:
                result.update(resolve_elset(value, stack | set((key,))))
        return result

    def resolve_nset(name, stack):
        key = str(name).upper().split(".")[-1]
        if key not in nsets or key in stack:
            return set()
        result = set()
        for value in nsets[key]:
            if isinstance(value, int):
                result.add(value)
            else:
                result.update(resolve_nset(value, stack | set((key,))))
        return result

    steel_coverage = set()
    other_coverage = set()
    section_cards = []
    for card in cards:
        if card["keyword"] != "SOLID SECTION":
            continue
        labels = resolve_elset(card["params"].get("ELSET", ""), set())
        if card["params"].get("MATERIAL", "").upper() == "STEEL":
            steel_coverage.update(labels)
        else:
            other_coverage.update(labels)
        section_cards.append(card)
    if steel_coverage != expected_elements or other_coverage.intersection(expected_elements):
        return fail("CAE-generated input does not assign a Steel solid section to every bar element")
    if not section_cards:
        return fail("CAE-generated input contains no solid-section assignment")

    static_cards = [card for card in cards if card["step"] == STEP_NAME and card["keyword"] == "STATIC"]
    if len(static_cards) != 1:
        return fail("Step-Load must contain exactly one static procedure")
    boundary_rows = [row for card in cards if card["keyword"] == "BOUNDARY" for row in card["data"]]
    if len(boundary_rows) != 1:
        return fail("CAE-generated input must contain exactly one Encastre boundary row")
    boundary_fields = [value.strip() for value in boundary_rows[0].split(",") if value.strip()]
    if (
        len(boundary_fields) != 2
        or boundary_fields[1].upper() != "ENCASTRE"
        or resolve_nset(boundary_fields[0], set()) != expected_fixed_nodes
    ):
        return fail("CAE-generated input Encastre does not fix exactly the complete X=0 face")

    surfaces = {}
    for card in cards:
        if card["keyword"] != "SURFACE" or str(card["params"].get("TYPE", "")).upper() != "ELEMENT":
            continue
        name = str(card["params"].get("NAME", "")).upper()
        if not name:
            return fail("CAE-generated input contains an unnamed element surface")
        rows = []
        for row in card["data"]:
            fields = [value.strip() for value in row.split(",") if value.strip()]
            if len(fields) != 2 or not re.match(r"^S\d+$", fields[1], re.IGNORECASE):
                return fail("CAE-generated input element surface is unreadable")
            labels = resolve_elset(fields[0], set())
            if not labels:
                return fail("CAE-generated input element surface references an empty ELSET")
            rows.append((labels, fields[1].upper()))
        surfaces[name] = rows

    traction_rows = [row for card in cards if card["step"] == STEP_NAME and card["keyword"] == "DSLOAD" for row in card["data"]]
    if len(traction_rows) != 1:
        return fail("CAE-generated input must contain exactly one surface traction")
    for row in traction_rows:
        fields = [value.strip() for value in row.split(",")]
        if len(fields) < 6 or fields[1].upper() != "TRVEC":
            return fail("Step-Load contains a non-GENERAL surface traction")
        try:
            magnitude = float(fields[2])
            direction = tuple(float(fields[index]) for index in (3, 4, 5))
        except Exception:
            return fail("Step-Load traction data is unreadable")
        length = math.sqrt(builtins.sum(value * value for value in direction))
        direction = tuple(value / length for value in direction) if length > 0.0 else ()
        surface_name = fields[0].upper().split(".")[-1]
        surface_rows = surfaces.get(surface_name, [])
        loaded_elements = set().union(*(labels for labels, side in surface_rows)) if surface_rows else set()
        expected_loaded_elements = set(
            label
            for label, value in connectivity.items()
            if set(value[1]).intersection(expected_free_nodes)
        )
        if (
            not close(magnitude, 10.0)
            or not all(close(a, b) for a, b in zip(direction, (1.0, 0.0, 0.0)))
            or loaded_elements != expected_loaded_elements
            or len(set(side for labels, side in surface_rows)) != 1
        ):
            return fail("Step-Load traction is not 10 MPa in global +X")
    forbidden = set((
        "CLOAD", "DLOAD", "DSFLUX", "DFLUX", "FILM", "RADIATE", "TEMPERATURE",
        "INITIAL CONDITIONS", "EQUATION", "COUPLING", "KINEMATIC COUPLING",
        "DISTRIBUTING COUPLING", "MASS", "ROTARY INERTIA", "CONNECTOR LOAD",
        "MODEL CHANGE", "DYNAMIC", "FREQUENCY", "BUCKLE", "HEAT TRANSFER",
    ))
    for card in cards:
        if card["step"] == STEP_NAME and card["keyword"] in forbidden:
            return fail("CAE-generated input contains an additional load, constraint, or procedure: " + card["keyword"])

    node_variables = set()
    element_variables = set()
    for card in cards:
        if card["step"] != STEP_NAME:
            continue
        values = set(
            token.strip().upper()
            for row in card["data"]
            for token in row.split(",")
            if token.strip()
        )
        if card["keyword"] == "NODE OUTPUT":
            node_variables.update(values)
        elif card["keyword"] == "ELEMENT OUTPUT":
            element_variables.update(values)
    if not set(("U", "RF")).issubset(node_variables) or "S" not in element_variables:
        return fail("CAE field output request must explicitly include nodal U/RF and element S")
    return True


def element_nodes(part, element):
    try:
        return list(element.getNodes())
    except Exception:
        result = []
        for index in element.connectivity:
            result.append(part.nodes[int(index)])
        return result


def tetra_volume(a, b, c, d):
    ab = tuple(b[index] - a[index] for index in range(3))
    ac = tuple(c[index] - a[index] for index in range(3))
    ad = tuple(d[index] - a[index] for index in range(3))
    cross = (
        ac[1] * ad[2] - ac[2] * ad[1],
        ac[2] * ad[0] - ac[0] * ad[2],
        ac[0] * ad[1] - ac[1] * ad[0],
    )
    return abs(builtins.sum(ab[index] * cross[index] for index in range(3))) / 6.0


def validate_solid_mesh(part, coords):
    if len(part.elements) < 80 or len(part.nodes) < 45:
        return fail("solid mesh is too coarse for a 5 mm target size")
    element_types = set(str(element.type).upper() for element in part.elements)
    if not element_types or not element_types.issubset(set(ALLOWED_TYPES)):
        return fail("all elements must use an appropriate 3D mechanical solid formulation")
    total_volume = 0.0
    attached = set()
    adjacency = {}
    node_to_elements = {}
    for element in part.elements:
        nodes = element_nodes(part, element)
        element_type = str(element.type).upper()
        if element_type.startswith("C3D4") or element_type.startswith("C3D10"):
            corner_count = 4
            edges = ((0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3))
            tets = ((0, 1, 2, 3),)
        elif element_type.startswith("C3D6") or element_type.startswith("C3D15"):
            corner_count = 6
            edges = ((0, 1), (1, 2), (2, 0), (3, 4), (4, 5), (5, 3), (0, 3), (1, 4), (2, 5))
            tets = ((0, 1, 2, 3), (1, 2, 4, 3), (2, 4, 5, 3))
        else:
            corner_count = 8
            edges = ((0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6), (6, 7), (7, 4), (0, 4), (1, 5), (2, 6), (3, 7))
            tets = ((0, 1, 3, 4), (1, 2, 3, 6), (1, 3, 4, 6), (1, 4, 5, 6), (3, 4, 6, 7))
        corners = nodes[:corner_count]
        if len(corners) != corner_count:
            return fail("solid element connectivity is incomplete")
        labels = set(int(node.label) for node in nodes)
        attached.update(labels)
        adjacency[int(element.label)] = set()
        for label in labels:
            for other in node_to_elements.setdefault(label, set()):
                adjacency[int(element.label)].add(other)
                adjacency.setdefault(other, set()).add(int(element.label))
            node_to_elements[label].add(int(element.label))
        points = [tuple(float(value) for value in node.coordinates[:3]) for node in corners]
        if any(math.sqrt(builtins.sum((points[a][index] - points[b][index]) ** 2 for index in range(3))) > 8.0 for a, b in edges):
            return fail("solid mesh contains a corner edge inconsistent with the 5 mm target size")
        total_volume += builtins.sum(tetra_volume(points[a], points[b], points[c], points[d]) for a, b, c, d in tets)
    if attached != set(coords):
        return fail("solid mesh contains unattached nodes")
    pending = set(adjacency)
    visited = set()
    if pending:
        stack = [next(iter(pending))]
        while stack:
            label = stack.pop()
            if label in visited:
                continue
            visited.add(label)
            stack.extend(adjacency[label] - visited)
    if visited != set(adjacency):
        return fail("solid mesh is not one connected body")
    if not close(total_volume, 10000.0, rel=0.015, abs_tol=5.0):
        return fail("solid mesh does not cover the complete 100 x 10 x 10 mm bar")
    return element_types


def named_set_labels(model, part, name):
    repositories = [part.sets, model.rootAssembly.sets]
    try:
        for instance_name in model.rootAssembly.instances.keys():
            repositories.append(model.rootAssembly.instances[instance_name].sets)
    except Exception:
        pass
    candidates = []
    for repository in repositories:
        try:
            for key in repository.keys():
                if str(key).upper() == name.upper():
                    labels = entity_labels(repository[key].nodes)
                    if labels:
                        candidates.append(labels)
        except Exception:
            pass
    if not candidates or any(labels != candidates[0] for labels in candidates[1:]):
        return None
    return candidates[0]


def repository_region_labels(repository, name, entity_name):
    try:
        for key in repository.keys():
            if str(key).upper() == str(name).upper():
                return entity_labels(getattr(repository[key], entity_name))
    except Exception:
        pass
    return set()


def region_labels_any(model, region, entity_name):
    direct = region_labels(model, region, entity_name)
    if direct:
        return direct
    try:
        descriptor = tuple(region)
        region_name = str(descriptor[0])
    except Exception:
        return None
    repositories = [model.rootAssembly.sets, model.rootAssembly.surfaces]
    for instance_name in model.rootAssembly.instances.keys():
        instance = model.rootAssembly.instances[instance_name]
        repositories.extend((instance.sets, instance.surfaces))
    for part_name in model.parts.keys():
        part = model.parts[part_name]
        repositories.extend((part.sets, part.surfaces))
    candidates = [repository_region_labels(repo, region_name, entity_name) for repo in repositories]
    candidates = [labels for labels in candidates if labels]
    if not candidates or any(labels != candidates[0] for labels in candidates[1:]):
        return None
    return candidates[0]


def direction_components(value):
    try:
        rows = list(value)
        if len(rows) == 2 and hasattr(rows[0], "__iter__"):
            return tuple(float(rows[1][index]) - float(rows[0][index]) for index in range(3))
        if len(rows) >= 3:
            return tuple(float(rows[index]) for index in range(3))
    except Exception:
        pass
    return None


def validate_model(database):
    if JOB_NAME not in database.jobs.keys():
        return fail("CAE does not contain the required Job-Tension job")
    job = database.jobs[JOB_NAME]
    model_name = str(getattr(job, "model", ""))
    if model_name not in database.models.keys():
        return fail("Job-Tension does not reference a valid model")
    model = database.models[model_name]
    meshed_parts = [model.parts[name] for name in model.parts.keys() if len(model.parts[name].elements)]
    if len(meshed_parts) != 1:
        return fail("job model must contain one meshed solid bar part")
    part = meshed_parts[0]
    if len(model.rootAssembly.instances.keys()) != 1:
        return fail("job model must contain exactly one bar instance")
    instance = model.rootAssembly.instances[model.rootAssembly.instances.keys()[0]]
    if str(getattr(instance, "partName", "")) != str(part.name) or str(getattr(instance, "dependent", "")).upper() not in ("ON", "1"):
        return fail("bar assembly must contain one dependent instance of the meshed part")
    coords = coords_by_label(part.nodes)
    if not coords:
        return fail("part has no nodes")
    if any(len(node.coordinates) != 3 for node in part.nodes):
        return fail("bar part must use three-dimensional nodal coordinates")
    xs = [xyz[0] for xyz in coords.values()]
    ys = [xyz[1] for xyz in coords.values()]
    zs = [xyz[2] for xyz in coords.values()]
    if not (
        close(builtins.min(xs), 0.0)
        and close(builtins.max(xs), 100.0)
        and close(builtins.min(ys), 0.0)
        and close(builtins.max(ys), 10.0)
        and close(builtins.min(zs), 0.0)
        and close(builtins.max(zs), 10.0)
    ):
        return fail("part geometry is not the required 100 x 10 x 10 mm positive-coordinate solid")
    try:
        volume = float(part.getMassProperties().get("volume"))
    except Exception:
        return fail("solid part volume cannot be read")
    if not close(volume, 10000.0, rel=1.0e-8, abs_tol=1.0e-5):
        return fail("solid part volume is not 10000 mm^3")
    try:
        seed_size = float(part.getPartSeeds(attribute=SIZE))
    except Exception:
        return fail("global part seed cannot be read")
    if not close(seed_size, 5.0, rel=0.01, abs_tol=0.05):
        return fail("global part seed is not 5 mm")
    element_types = validate_solid_mesh(part, coords)
    if not element_types:
        return False
    expected_sets = {
        "FIXED": set(label for label, xyz in coords.items() if close(xyz[0], 0.0)),
        "FREE": set(label for label, xyz in coords.items() if close(xyz[0], 100.0)),
        "CENTER": set(label for label, xyz in coords.items() if all(close(xyz[index], (100.0, 5.0, 5.0)[index]) for index in range(3))),
    }
    if not expected_sets["FIXED"] or not expected_sets["FREE"] or len(expected_sets["CENTER"]) != 1:
        return fail("complete end faces or unique free-face center node cannot be identified")

    if "Steel" not in model.materials.keys():
        return fail("material Steel is missing")
    try:
        elastic = model.materials["Steel"].elastic.table[0]
    except Exception:
        return fail("Steel elastic data is missing")
    if len(elastic) < 2 or not close(elastic[0], 210000.0) or not close(elastic[1], 0.3):
        return fail("Steel elastic constants are incorrect")
    valid_sections = set()
    for name in model.sections.keys():
        section = model.sections[name]
        if (
            section.__class__.__name__ == "HomogeneousSolidSection"
            and str(getattr(section, "material", "")) == "Steel"
        ):
            valid_sections.add(str(name))
    if not valid_sections:
        return fail("no homogeneous Steel solid section exists")
    assignments = list(part.sectionAssignments)
    if not assignments or any(str(assignment.sectionName) not in valid_sections for assignment in assignments):
        return fail("every bar section assignment must reference a homogeneous Steel solid section")

    bcs = active_named_objects(model.boundaryConditions)
    if STEP_NAME not in model.steps.keys():
        return fail("Step-Load is missing")
    step = model.steps[STEP_NAME]
    if len(bcs) != 1 or bcs[0][1].__class__.__name__ != "TypeBC":
        return fail("Abaqus model must contain exactly one Encastre boundary condition")
    actual_constraints = {}
    for bc_name, bc in bcs:
        if bc_name not in step.boundaryConditionStates.keys():
            continue
        bc_state = step.boundaryConditionStates[bc_name]
        if not state_is_active(bc_state):
            continue
        labels = region_labels_any(model, bc.region, "nodes")
        if not labels:
            return fail("active displacement BC region cannot be resolved")
        if bc.__class__.__name__ == "TypeBC":
            components = ("U1", "U2", "U3")
        else:
            return fail("only the required Encastre boundary may be active")
        for label in labels:
            actual_constraints.setdefault(label, set()).update(components)
    expected_constraints = dict((label, set(("U1", "U2", "U3"))) for label in expected_sets["FIXED"])
    if actual_constraints != expected_constraints:
        return fail("active constraint signature is not exactly X=0 U1/U2/U3 zero")
    if active_objects(model.constraints):
        return fail("additional model constraints are not allowed")
    if active_objects(model.interactions):
        return fail("additional active model interactions are not allowed")
    if active_objects(model.predefinedFields):
        return fail("additional active predefined fields are not allowed")

    if (
        step.__class__.__name__ != "StaticStep"
        or str(getattr(step, "previous", "")) != "Initial"
        or str(getattr(step, "nlgeom", "")).upper() not in ("OFF", "0", "FALSE")
    ):
        return fail("Step-Load must be one linear static step after Initial")
    if not active_objects(model.fieldOutputRequests):
        return fail("field output request is missing")

    loads = active_named_objects(model.loads)
    if len(loads) != 1:
        return fail("Abaqus model must contain exactly one surface traction load")
    actual_loads = []
    for load_name, load in loads:
        if load_name not in step.loadStates.keys():
            continue
        load_state = step.loadStates[load_name]
        if not state_is_active(load_state):
            continue
        if load.__class__.__name__ != "SurfaceTraction":
            return fail("only native Abaqus SurfaceTraction loads may be active")
        labels = region_labels_any(model, load.region, "nodes")
        magnitude = getattr(load_state, "magnitude", getattr(load, "magnitude", None))
        direction = direction_components(getattr(load, "directionVector", None))
        traction = str(getattr(load, "traction", "")).strip().upper()
        if traction != "GENERAL":
            return fail("surface traction must use GENERAL traction with an explicit global direction")
        for attribute in ("localCsys", "userCsys"):
            if not uses_global_coordinate_system(load, attribute):
                return fail("surface traction direction must use the global coordinate system")
        if str(getattr(load, "distributionType", "")).upper() != "UNIFORM" or str(getattr(load, "follower", "")).upper() not in ("OFF", "0", "FALSE"):
            return fail("surface traction must be uniform and non-follower")
        if not labels or not labels.issubset(expected_sets["FREE"]) or not close(magnitude, 10.0) or direction is None:
            return fail("surface traction region, magnitude, or direction cannot be validated")
        length = math.sqrt(builtins.sum(value * value for value in direction))
        if length <= 0.0:
            return fail("surface traction direction is zero")
        direction = tuple(value / length for value in direction)
        if not all(close(a, b) for a, b in zip(direction, (1.0, 0.0, 0.0))):
            return fail("surface traction direction is not global +X")
        actual_loads.append(labels)
    if not actual_loads or set().union(*actual_loads) != expected_sets["FREE"]:
        return fail("10 MPa surface traction does not cover the complete X=100 face")
    for index, labels in enumerate(actual_loads):
        for other in actual_loads[index + 1:]:
            if labels == other:
                return fail("duplicate overlapping surface traction regions are not allowed")
    element_labels = set(int(element.label) for element in part.elements)
    connectivity = dict(
        (
            int(element.label),
            (
                str(element.type).upper(),
                tuple(int(node.label) for node in element_nodes(part, element)),
            ),
        )
        for element in part.elements
    )
    if not validate_input_output_request(
        job,
        element_labels,
        expected_sets["FIXED"],
        expected_sets["FREE"],
        connectivity,
    ):
        return False
    return {
        "model_name": model_name,
        "part": part,
        "coords": coords,
        "element_types": element_types,
        "sets": expected_sets,
        "elements": element_labels,
        "connectivity": connectivity,
        "step_time": float(getattr(step, "timePeriod", 1.0)),
    }


def abaqus_signatures_match(left, right):
    if left is None or right is None or set(left) != set(right):
        return False
    for field_name in left:
        if set(left[field_name]) != set(right[field_name]):
            return False
        for key in left[field_name]:
            actual = left[field_name][key]
            expected = right[field_name][key]
            if len(actual) != len(expected):
                return False
            for actual_value, expected_value in zip(actual, expected):
                if not close(actual_value, expected_value, rel=2.0e-5, abs_tol=1.0e-8):
                    return False
    return True


def validate_odb(model_info, odb_path, compare_submitted_metrics):
    odb = openOdb(path=odb_path, readOnly=True)
    try:
        status = str(getattr(odb.diagnosticData, "jobStatus", "")).upper()
        if status != "JOB_STATUS_COMPLETED_SUCCESSFULLY":
            return fail("ODB is not a successfully completed analysis")
        if list(odb.steps.keys()) != [STEP_NAME]:
            return fail("ODB must contain the single analysis step Step-Load")
        step = odb.steps[STEP_NAME]
        if len(step.frames) < 2:
            return fail("ODB has no solved final frame")
        frame = step.frames[-1]
        if not math.isfinite(float(frame.frameValue)) or not close(
            frame.frameValue, model_info["step_time"], rel=1.0e-6, abs_tol=1.0e-8
        ):
            return fail("final frame is not the completed static load step")
        if len(odb.rootAssembly.instances.keys()) != 1:
            return fail("ODB must contain one solid bar instance")
        instance = odb.rootAssembly.instances[odb.rootAssembly.instances.keys()[0]]
        odb_coords = coords_by_label(instance.nodes)
        if set(odb_coords) != set(model_info["coords"]):
            return fail("CAE and ODB node labels do not match")
        for label in odb_coords:
            if any(not close(a, b, rel=1.0e-8, abs_tol=1.0e-8) for a, b in zip(odb_coords[label], model_info["coords"][label])):
                return fail("CAE and ODB node coordinates do not match")
        odb_connectivity = dict(
            (
                int(element.label),
                (
                    str(element.type).upper(),
                    tuple(int(label) for label in element.connectivity),
                ),
            )
            for element in instance.elements
        )
        if odb_connectivity != model_info["connectivity"]:
            all_labels = builtins.sorted(set(odb_connectivity).union(set(model_info["connectivity"])))
            first_difference = None
            for label in all_labels:
                if odb_connectivity.get(label) != model_info["connectivity"].get(label):
                    first_difference = (
                        label,
                        model_info["connectivity"].get(label),
                        odb_connectivity.get(label),
                    )
                    break
            return fail(
                "CAE and ODB element labels, types, or connectivity do not match; first difference=%r"
                % (first_difference,)
            )

        for name in ("U", "RF", "S"):
            if name not in frame.fieldOutputs.keys():
                return fail("ODB final frame is missing field " + name)
        all_nodes = set(model_info["coords"])
        for name in ("U", "RF"):
            labels = set(int(value.nodeLabel) for value in frame.fieldOutputs[name].values)
            if labels != all_nodes:
                return fail("%s output does not cover every node" % name)
            for value in frame.fieldOutputs[name].values:
                try:
                    data = tuple(float(item) for item in value.data)
                except Exception:
                    return fail("%s output contains an unreadable value" % name)
                if not data or any(not math.isfinite(item) for item in data):
                    return fail("%s output contains a non-finite value" % name)
        displacement = {}
        for value in frame.fieldOutputs["U"].values:
            displacement[int(value.nodeLabel)] = tuple(float(item) for item in value.data)
        stress_counts = {}
        mises = []
        signature = {"U": {}, "RF": {}, "S": {}}
        for name in ("U", "RF"):
            for value in frame.fieldOutputs[name].values:
                signature[name][int(value.nodeLabel)] = tuple(float(item) for item in value.data)
        for value in frame.fieldOutputs["S"].values:
            if not str(getattr(value, "position", "")).upper().endswith("INTEGRATION_POINT"):
                continue
            label = int(value.elementLabel)
            section_point = getattr(value, "sectionPoint", None)
            section_number = int(getattr(section_point, "number", 0) or 0)
            stress_counts[label] = stress_counts.get(label, 0) + 1
            try:
                invariant = float(value.mises)
                components = tuple(float(item) for item in value.data)
            except Exception:
                return fail("stress value has no finite von Mises invariant")
            if not math.isfinite(invariant) or len(components) != 6 or any(
                not math.isfinite(item) for item in components
            ):
                return fail("stress output is not a finite six-component solid tensor")
            mises.append(invariant)
            integration_point = int(getattr(value, "integrationPoint", 0) or 0)
            key = (label, section_number, integration_point)
            if key in signature["S"]:
                return fail("ODB contains duplicate solid stress records")
            signature["S"][key] = components + (invariant,)
        if set(stress_counts) != model_info["elements"] or any(count < 1 for count in stress_counts.values()):
            return fail("integration-point S output does not cover every solid element")

        fixed_labels = model_info["sets"]["FIXED"]
        center_label = next(iter(model_info["sets"]["CENTER"]))
        if center_label not in displacement or not fixed_labels.issubset(set(signature["RF"])):
            return fail("free-center U or fixed-face RF output is incomplete")
        free_end_displacement = displacement[center_label][0]
        fixed_rf1 = -builtins.sum(signature["RF"][label][0] for label in fixed_labels)
        fixed_rf2 = builtins.sum(signature["RF"][label][1] for label in fixed_labels)
        fixed_rf3 = builtins.sum(signature["RF"][label][2] for label in fixed_labels)
        axial_stress = fixed_rf1 / 100.0
        maximum = builtins.max(mises) if mises else None
        if maximum is None or not math.isfinite(free_end_displacement) or not math.isfinite(axial_stress) or not math.isfinite(maximum):
            return fail("native metrics could not be extracted")
        if not (0.0040 < free_end_displacement < 0.0055 and 9.8 < axial_stress < 10.2 and maximum > 0.0):
            return fail("native Abaqus metrics are outside physical sanity bounds")
        if abs(fixed_rf2) > 0.1 or abs(fixed_rf3) > 0.1:
            return fail("fixed-face transverse reaction is inconsistent with pure axial tension")
        if compare_submitted_metrics:
            if not close(free_end_displacement, SUBMITTED["free_end_displacement"], rel=1.0e-3, abs_tol=1.0e-7):
                return fail("metrics.json free_end_displacement does not match center-node ODB U1")
            if not close(axial_stress, SUBMITTED["axial_stress"], rel=1.0e-3, abs_tol=0.005):
                return fail("metrics.json axial_stress does not match fixed-face ODB RF1 / 100 mm^2")
        return {
            "metrics": {
                "free_end_displacement": free_end_displacement,
                "axial_stress": axial_stress,
            },
            "signature": signature,
        }
    finally:
        odb.close()


def main():
    passed = False
    native_metrics = None
    database = None
    try:
        database = openMdb(pathName=CAE_PATH)
        model_info = validate_model(database)
        if model_info:
            submitted_result = validate_odb(model_info, ODB_PATH, True)
            if submitted_result:
                recheck_job = database.JobFromInputFile(
                    name=RECHECK_JOB_NAME,
                    inputFileName=JOB_NAME + ".inp",
                    numCpus=1,
                    numDomains=1,
                )
                recheck_job.submit(consistencyChecking=ON)
                recheck_job.waitForCompletion()
                rechecked_result = validate_odb(model_info, RECHECK_JOB_NAME + ".odb", False)
                if rechecked_result and abaqus_signatures_match(
                    submitted_result["signature"], rechecked_result["signature"]
                ):
                    native_metrics = submitted_result["metrics"]
                    passed = True
                elif rechecked_result:
                    fail("submitted ODB fields do not match an isolated re-solve of the CAE")
    except Exception:
        DETAILS.append(traceback.format_exc())
        passed = False
    finally:
        if database is not None:
            try:
                database.close()
            except Exception:
                pass
    with open(RESULT_PATH, "w") as stream:
        json.dump(
            {"passed": passed, "details": DETAILS, "native_metrics": native_metrics},
            stream,
            indent=2,
            sort_keys=True,
        )
    print("True" if passed else "False")


if __name__ == "__main__":
    main()
'''
    checker_source = checker_source.replace("__CAE_PATH__", repr(str(cae_path)))
    checker_source = checker_source.replace("__ODB_PATH__", repr(str(odb_path)))
    checker_source = checker_source.replace("__RESULT_PATH__", repr(str(result_path)))
    checker_source = checker_source.replace("__SUBMITTED__", repr(submitted_metrics))
    checker_source = checker_source.replace("__RECHECK_JOB_NAME__", repr("eval_task04_abq_" + uuid.uuid4().hex[:12]))
    checker_path.write_text(checker_source, encoding="utf-8")
    passed = False
    cleanup_ok = False
    try:
        completed = subprocess.run(
            [ABAQUS_COMMAND, "cae", "noGUI=" + str(checker_path)],
            cwd=str(temp_root),
            text=True,
            capture_output=True,
            timeout=900,
            shell=False,
        )
        log("Abaqus checker returncode=%s" % completed.returncode)
        if completed.stdout:
            log("Abaqus checker stdout tail=" + completed.stdout[-1000:])
        if completed.stderr:
            log("Abaqus checker stderr tail=" + completed.stderr[-1000:])
        if completed.returncode == 0 and is_nonempty(result_path):
            payload = json.loads(result_path.read_text(encoding="utf-8"))
            for detail in payload.get("details", []):
                log("Abaqus: " + str(detail))
            passed = payload.get("passed") is True
    except Exception as exc:
        log("Abaqus checker failed: %s" % exc)
    finally:
        cleanup_ok = remove_tree_with_retries(temp_root)
        if not cleanup_ok:
            log("Abaqus evaluator temporary directory cleanup was incomplete")
    return passed and cleanup_ok


def required_run(mapdl, command):
    try:
        output = mapdl.run(command)
    except Exception as exc:
        raise RuntimeError("MAPDL command failed %s: %s" % (command, exc))
    text = "" if output is None else str(output)
    upper = text.upper()
    if "*** ERROR ***" in upper or "THE COMMAND IS IGNORED" in upper:
        raise RuntimeError("MAPDL command reported an error: %s" % command)
    return text


def try_get(mapdl, *args):
    try:
        return float(mapdl.get_value(*args))
    except Exception:
        return None


def required_get(mapdl, *args):
    value = try_get(mapdl, *args)
    if value is None or not math.isfinite(value):
        raise RuntimeError("MAPDL *GET failed for %r" % (args,))
    return value


def parse_listing_rows(text, labels):
    pattern = re.compile(
        r"^\s*(\d+)\s+(%s)\s+([-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[EeDd][-+]?\d+)?)"
        % "|".join(labels),
        re.MULTILINE | re.IGNORECASE,
    )
    rows = []
    for match in pattern.finditer(text or ""):
        rows.append(
            (
                int(match.group(1)),
                match.group(2).upper(),
                float(match.group(3).replace("D", "E").replace("d", "e")),
            )
        )
    return rows


def selected_component_nodes(mapdl, name):
    try:
        required_run(mapdl, "ALLSEL,ALL")
        output = required_run(mapdl, "CMSEL,S,%s,NODE" % name)
        if "NOT DEFINED" in output.upper():
            return None
        labels = set(int(value) for value in mapdl.mesh.nnum)
    except Exception:
        return None
    finally:
        try:
            required_run(mapdl, "ALLSEL,ALL")
        except Exception:
            pass
    return labels


def material_matches(mapdl, material_id):
    ex = try_get(mapdl, "EX", material_id, "TEMP", 0)
    nu = try_get(mapdl, "PRXY", material_id, "TEMP", 0)
    if nu is None:
        nu = try_get(mapdl, "NUXY", material_id, "TEMP", 0)
    if ex is not None and nu is not None:
        if close_enough(ex, 210000.0, rel=1.0e-6) and close_enough(nu, 0.3, rel=1.0e-6):
            return True
    tb_ex = try_get(mapdl, "ELASTIC", material_id, "TEMP", 0, "CONST", 1, "ISOT")
    tb_nu = try_get(mapdl, "ELASTIC", material_id, "TEMP", 0, "CONST", 2, "ISOT")
    return (
        tb_ex is not None
        and tb_nu is not None
        and close_enough(tb_ex, 210000.0, rel=1.0e-6)
        and close_enough(tb_nu, 0.3, rel=1.0e-6)
    )


def listing_confirms_none(mapdl, command, marker):
    text = required_run(mapdl, command).upper()
    return bool(text.strip()) and marker in text


def inertia_loads_are_zero(export_text):
    active_commands = set()
    pattern = re.compile(
        r"^\s*(ACEL|OMEGA|DOMEGA|CGOMGA|DCGOMG|CMACEL|CMOMEGA|CMDOMEGA)\s*,(.*)$",
        re.MULTILINE | re.IGNORECASE,
    )
    for match in pattern.finditer(export_text or ""):
        command = match.group(1).upper()
        active_commands.add(command)
        fields = [field.strip() for field in match.group(2).split(",")]
        if command.startswith("CM"):
            fields = fields[1:]
        for field in fields:
            if not field:
                continue
            try:
                value = float(field.replace("D", "E").replace("d", "e"))
            except Exception:
                return False
            if not math.isfinite(value) or abs(value) > 1.0e-12:
                return False
    return True


def read_ansys_rst_mesh(result_path):
    from ansys.mapdl import reader as pymapdl_reader

    result = pymapdl_reader.read_binary(str(result_path))
    labels = [int(value) for value in result.mesh.nnum]
    rows = [[float(value) for value in row[:3]] for row in result.mesh.nodes]
    coords = dict(zip(labels, rows))
    type_codes = dict((int(row[0]), int(row[1])) for row in result.mesh.ekey)
    elements = {}
    for record in result.mesh.elem:
        type_reference = int(record[1])
        label = int(record[8])
        code = type_codes.get(type_reference)
        if label <= 0 or code not in (185, 186, 187):
            raise RuntimeError("RST contains an unsupported or unreadable solid element")
        node_count = {185: 8, 186: 20, 187: 10}[code]
        connectivity = tuple(int(value) for value in record[10:10 + node_count])
        if any(value <= 0 for value in connectivity):
            raise RuntimeError("RST solid connectivity is incomplete")
        elements[label] = (code, connectivity)
    return coords, elements, int(result.nsets)


def ansys_nodal_result_signature(mapdl, node_labels):
    signature = {}
    stress_fields = (
        ("S", "X"),
        ("S", "Y"),
        ("S", "Z"),
        ("S", "XY"),
        ("S", "YZ"),
        ("S", "XZ"),
        ("S", "EQV"),
    )
    for label in sorted(node_labels):
        displacements = [try_get(mapdl, "NODE", label, "U", component) for component in ("X", "Y", "Z")]
        if any(value is None or not math.isfinite(value) for value in displacements):
            return None
        stresses = []
        for item, component in stress_fields:
            value = try_get(mapdl, "NODE", label, item, component)
            stresses.append(value)
        if any(value is None or not math.isfinite(value) for value in stresses):
            stresses = None
        else:
            stresses = tuple(stresses)
        signature[label] = (tuple(displacements), stresses)
    return signature


def ansys_solid_stress_signature(mapdl, element_labels):
    columns = (
        ("SX04", "X"), ("SY04", "Y"), ("SZ04", "Z"),
        ("SXY04", "XY"), ("SYZ04", "YZ"), ("SXZ04", "XZ"),
        ("SEQV04", "EQV"),
    )
    required_run(mapdl, "ALLSEL,ALL")
    required_run(mapdl, "ETABLE,ERAS")
    for name, component in columns:
        required_run(mapdl, "ETABLE,%s,S,%s" % (name, component))
    signature = {}
    for label in sorted(element_labels):
        values = tuple(try_get(mapdl, "ELEM", label, "ETAB", name) for name, component in columns)
        if any(value is None or not math.isfinite(value) for value in values):
            return None
        signature[label] = values
    required_run(mapdl, "ALLSEL,ALL")
    return signature


def ansys_reaction_signature(mapdl, expected_nodes):
    text = required_run(mapdl, "PRRSOL,F")
    upper = text.upper()
    if "REACTION SOLUTION LISTING" not in upper or "TOTAL VALUES" not in upper:
        return None
    number = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[EeDd][-+]?\d+)?"
    pattern = re.compile(
        r"^\s*(\d+)\s+(%s)\s*(%s)\s*(%s)\s*$" % (number, number, number),
        re.MULTILINE,
    )
    signature = {}
    for match in pattern.finditer(text):
        label = int(match.group(1))
        values = tuple(
            float(match.group(index).replace("D", "E").replace("d", "e"))
            for index in (2, 3, 4)
        )
        if label in signature or any(not math.isfinite(value) for value in values):
            return None
        signature[label] = values
    if set(signature) != set(expected_nodes):
        return None
    return signature


def ansys_signatures_match(left, right):
    if left is None or right is None or set(left) != set(right):
        return False
    for label in left:
        left_u, left_s = left[label]
        right_u, right_s = right[label]
        if len(left_u) != len(right_u):
            return False
        for actual, expected in zip(left_u, right_u):
            if not close_enough(actual, expected, rel=2.0e-4, abs_tol=1.0e-7):
                return False
        if (left_s is None) != (right_s is None):
            return False
        if left_s is not None:
            for actual, expected in zip(left_s, right_s):
                if not close_enough(actual, expected, rel=2.0e-4, abs_tol=1.0e-7):
                    return False
    return True


def ansys_reaction_signatures_match(left, right):
    if left is None or right is None or set(left) != set(right):
        return False
    for label in left:
        if len(left[label]) != len(right[label]):
            return False
        for actual, expected in zip(left[label], right[label]):
            if not close_enough(actual, expected, rel=2.0e-4, abs_tol=1.0e-6):
                return False
    return True


def ansys_solid_signatures_match(left, right):
    if left is None or right is None or set(left) != set(right):
        return False
    for label in left:
        if len(left[label]) != len(right[label]):
            return False
        for actual, expected in zip(left[label], right[label]):
            if not close_enough(actual, expected, rel=2.0e-4, abs_tol=1.0e-6):
                return False
    return True


def ansys_job_process_ids(jobname):
    command = (
        "Get-CimInstance Win32_Process | Where-Object { "
        "$_.Name -match '^(ANSYS(261)?|mpiexec|hydra_service)\\.exe$' -and $_.CommandLine -like '*%s*' "
        "} | ForEach-Object { $_.ProcessId }" % jobname
    )
    try:
        completed = subprocess.run(
            [
                r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
                "-NoProfile",
                "-Command",
                command,
            ],
            text=True,
            capture_output=True,
            timeout=30,
            shell=False,
        )
        return set(int(value) for value in completed.stdout.split() if value.isdigit())
    except Exception:
        return None


def cleanup_ansys_job_processes(jobname, baseline):
    if baseline is None:
        return False
    for _ in range(20):
        current = ansys_job_process_ids(jobname)
        if current is None:
            return False
        remaining = current - baseline
        if not remaining:
            return True
        time.sleep(0.1)
    for pid in sorted(remaining):
        try:
            subprocess.run(
                ["cmd", "/c", "taskkill", "/F", "/T", "/PID", str(pid)],
                text=True,
                capture_output=True,
                timeout=30,
                shell=False,
            )
        except Exception:
            pass
    current = ansys_job_process_ids(jobname)
    return current is not None and not bool(current - baseline)


def remove_tree_with_retries(path):
    for _ in range(30):
        shutil.rmtree(str(path), ignore_errors=True)
        if not path.exists():
            return True
        time.sleep(0.1)
    return False


def run_ansys_checker(model_path, result_path, submitted_metrics):
    run_token = uuid.uuid4().hex
    temp_root = Path(tempfile.mkdtemp(prefix="eval_cli_task04_ansys_%s_" % run_token))
    mapdl = None
    mapdl_jobname = "eval_task04_" + run_token[:16]
    process_baseline = ansys_job_process_ids(mapdl_jobname)
    semantic_passed = False
    cleanup_ok = False
    try:
        from ansys.mapdl.core import launch_mapdl

        if process_baseline is None:
            log("ANSYS evaluator could not establish a process baseline")
            return False
        try:
            rst_coords, rst_elements, rst_set_count = read_ansys_rst_mesh(result_path)
        except Exception as exc:
            log("ANSYS submitted RST mesh cannot be read: %s" % exc)
            return False
        if (
            rst_set_count < 1
            or len(rst_coords) != len(set(rst_coords))
            or len(rst_elements) != len(set(rst_elements))
        ):
            log("ANSYS submitted RST has invalid mesh labels or no result set")
            return False

        mapdl = launch_mapdl(
            exec_file=ANSYS_EXEC,
            jobname=mapdl_jobname,
            run_location=str(temp_root),
            nproc=1,
            override=True,
            cleanup_on_exit=True,
            start_timeout=180,
        )
        mapdl.resume(str(model_path.with_suffix("")), "db")
        required_run(mapdl, "FINISH")
        required_run(mapdl, "/PREP7")
        required_run(mapdl, "ALLSEL,ALL")
        required_run(mapdl, "CSYS,0")
        required_run(mapdl, "DSYS,0")
        if int(round(required_get(mapdl, "ACTIVE", 0, "ANTY"))) != 0:
            log("ANSYS database analysis type is not static")
            return False
        if int(round(required_get(mapdl, "CP", 0, "NUM"))) != 0 or int(
            round(required_get(mapdl, "CE", 0, "NUM"))
        ) != 0:
            log("ANSYS model contains additional coupled DOFs or constraint equations")
            return False
        node_numbers = [int(value) for value in mapdl.mesh.nnum]
        node_rows = [[float(value) for value in row[:3]] for row in mapdl.mesh.nodes]
        coords = dict(zip(node_numbers, node_rows))
        if len(coords) < 45:
            log("ANSYS solid mesh is too coarse for a 5 mm target size")
            return False
        xs = [row[0] for row in node_rows]
        ys = [row[1] for row in node_rows]
        zs = [row[2] for row in node_rows]
        if not (
            close_enough(min(xs), 0.0, rel=1.0e-8)
            and close_enough(max(xs), 100.0, rel=1.0e-8)
            and close_enough(min(ys), 0.0, rel=1.0e-8)
            and close_enough(max(ys), 10.0, rel=1.0e-8)
            and close_enough(min(zs), 0.0, rel=1.0e-8)
            and close_enough(max(zs), 10.0, rel=1.0e-8)
        ):
            log("ANSYS geometry bounds are incorrect")
            return False
        element_numbers = [int(value) for value in mapdl.mesh.enum]
        if len(element_numbers) < 80:
            log("ANSYS solid mesh is too coarse")
            return False
        if set(rst_coords) != set(coords) or set(rst_elements) != set(element_numbers):
            log("ANSYS submitted RST mesh labels do not match the DB")
            return False
        for label in coords:
            if any(
                not close_enough(actual, expected, rel=1.0e-8, abs_tol=1.0e-8)
                for actual, expected in zip(rst_coords[label], coords[label])
            ):
                log("ANSYS submitted RST node coordinates do not match the DB")
                return False
        type_ids = set()
        material_ids = set()
        db_connectivity = {}
        for element in element_numbers:
            type_id = required_get(mapdl, "ELEM", element, "ATTR", "TYPE")
            material_id = required_get(mapdl, "ELEM", element, "ATTR", "MAT")
            type_ids.add(int(round(type_id)))
            material_ids.add(int(round(material_id)))
        if len(type_ids) != 1 or len(material_ids) != 1:
            log("all bar elements must use one supported solid type and actual Steel material")
            return False
        type_id = next(iter(type_ids))
        element_code = int(round(required_get(mapdl, "ETYP", type_id, "ATTR", "ENAM")))
        if element_code not in (185, 186, 187):
            log("actual elements are not SOLID185/SOLID186/SOLID187")
            return False
        nodes_per_element = {185: 8, 186: 20, 187: 10}[element_code]
        attached_nodes = set()
        total_volume = 0.0
        adjacency = {}
        node_to_elements = {}
        for element in element_numbers:
            connectivity = []
            for position in range(1, nodes_per_element + 1):
                label = int(round(required_get(mapdl, "ELEM", element, "NODE", position)))
                if label <= 0 or label not in coords:
                    log("ANSYS element connectivity references a missing node")
                    return False
                connectivity.append(label)
            if len(set(connectivity)) != nodes_per_element:
                log("ANSYS mesh contains a degenerate solid element")
                return False
            db_connectivity[element] = (element_code, tuple(connectivity))
            attached_nodes.update(connectivity)
            adjacency[element] = set()
            for node in connectivity:
                for other in node_to_elements.setdefault(node, set()):
                    adjacency[element].add(other)
                    adjacency.setdefault(other, set()).add(element)
                node_to_elements[node].add(element)
            corners = [coords[label] for label in connectivity[:(8 if element_code in (185, 186) else 4)]]
            if element_code in (185, 186):
                edges = ((0,1),(1,2),(2,3),(3,0),(4,5),(5,6),(6,7),(7,4),(0,4),(1,5),(2,6),(3,7))
            else:
                edges = ((0,1),(0,2),(0,3),(1,2),(1,3),(2,3))
            if any(math.sqrt(sum((corners[a][index] - corners[b][index]) ** 2 for index in range(3))) > 8.0 for a,b in edges):
                log("ANSYS solid mesh contains a corner edge inconsistent with the 5 mm target size")
                return False
            if element_code in (185, 186):
                tets = ((0,1,3,4),(1,2,3,6),(1,3,4,6),(1,4,5,6),(3,4,6,7))
            else:
                tets = ((0,1,2,3),)
            for a,b,c,d in tets:
                pa,pb,pc,pd = corners[a],corners[b],corners[c],corners[d]
                ab = [pb[index]-pa[index] for index in range(3)]
                ac = [pc[index]-pa[index] for index in range(3)]
                ad = [pd[index]-pa[index] for index in range(3)]
                cross = [ac[1]*ad[2]-ac[2]*ad[1],ac[2]*ad[0]-ac[0]*ad[2],ac[0]*ad[1]-ac[1]*ad[0]]
                total_volume += abs(sum(ab[index]*cross[index] for index in range(3))) / 6.0
        if attached_nodes != set(coords):
            log("ANSYS solid mesh contains unattached nodes")
            return False
        visited = set()
        stack = [element_numbers[0]]
        while stack:
            item = stack.pop()
            if item in visited:
                continue
            visited.add(item)
            stack.extend(adjacency[item] - visited)
        if visited != set(element_numbers):
            log("ANSYS solid mesh is not one connected body")
            return False
        if not close_enough(total_volume, 10000.0, rel=0.015, abs_tol=5.0):
            log("ANSYS solid elements do not cover the complete 100 x 10 x 10 mm bar")
            return False
        if db_connectivity != rst_elements:
            log("ANSYS DB and submitted RST element types or ordered connectivity do not match")
            return False

        material_id = next(iter(material_ids))
        if not material_matches(mapdl, material_id):
            log("actual ANSYS material is not E=210000, nu=0.3")
            return False

        expected_sets = {
            "ALL": set(coords),
            "FIXED": set(label for label, xyz in coords.items() if close_enough(xyz[0], 0.0, rel=1.0e-8, abs_tol=1.0e-7)),
            "FREE": set(label for label, xyz in coords.items() if close_enough(xyz[0], 100.0, rel=1.0e-8, abs_tol=1.0e-7)),
            "CENTER": set(label for label, xyz in coords.items() if all(close_enough(xyz[index], (100.0,5.0,5.0)[index], rel=1.0e-8, abs_tol=1.0e-7) for index in range(3))),
        }
        if not expected_sets["FIXED"] or not expected_sets["FREE"] or len(expected_sets["CENTER"]) != 1:
            log("ANSYS complete end faces or unique free-face center node cannot be identified")
            return False

        required_run(mapdl, "ALLSEL,ALL")
        constraints = parse_listing_rows(required_run(mapdl, "DLIST,ALL"), ("UX", "UY", "UZ"))
        actual_constraints = {}
        for node, label, value in constraints:
            if abs(value) > 1.0e-12:
                log("ANSYS contains a nonzero displacement constraint")
                return False
            actual_constraints.setdefault(node, set()).add(label)
        expected_constraints = dict((node, set(("UX", "UY", "UZ"))) for node in expected_sets["FIXED"])
        if actual_constraints != expected_constraints:
            log("ANSYS constraint signature is not exactly all X=0 nodes UX/UY/UZ zero")
            return False
        if any(label not in ("UX", "UY", "UZ") for node, label, value in constraints):
            log("ANSYS contains an extra or nonzero displacement constraint")
            return False

        force_rows = parse_listing_rows(required_run(mapdl, "FLIST,ALL"), ("FX", "FY", "FZ"))
        if force_rows:
            log("ANSYS contains user nodal force loads instead of only the required face traction")
            return False
        sfa_text = required_run(mapdl, "SFALIST,ALL")
        sfa_rows = re.findall(r"^\s*(\d+)\s+(\d+)\s+PRES\s+([-+0-9.EeDd]+)\s+([-+0-9.EeDd]+)", sfa_text, re.MULTILINE | re.IGNORECASE)
        if len(sfa_rows) != 1 or not close_enough(float(sfa_rows[0][2].replace("D","E").replace("d","e")), -10.0, rel=1.0e-8, abs_tol=1.0e-8):
            log("ANSYS must contain exactly one geometric area pressure PRES=-10 MPa")
            return False
        loaded_area = int(sfa_rows[0][0])
        required_run(mapdl, "ASEL,S,AREA,,%d" % loaded_area)
        required_run(mapdl, "NSLA,S,1")
        loaded_area_nodes = set(int(value) for value in mapdl.mesh.nnum)
        required_run(mapdl, "ALLSEL,ALL")
        if loaded_area_nodes != expected_sets["FREE"]:
            log("ANSYS PRES=-10 is not applied to the complete X=100 face")
            return False
        sfe_text = required_run(mapdl, "SFELIST,ALL")
        sfe_blocks = []
        current_block = None
        for raw_line in sfe_text.splitlines():
            fields = raw_line.split()
            if len(fields) >= 5:
                try:
                    current_block = {
                        "element": int(fields[0]), "lkey": int(fields[1]),
                        "nodes": [int(fields[2])],
                        "values": [float(fields[3].replace("D", "E").replace("d", "e"))],
                    }
                    float(fields[4].replace("D", "E").replace("d", "e"))
                    sfe_blocks.append(current_block)
                    continue
                except Exception:
                    current_block = None
            if current_block is not None and len(fields) >= 3:
                try:
                    current_block["nodes"].append(int(fields[0]))
                    current_block["values"].append(float(fields[1].replace("D", "E").replace("d", "e")))
                    float(fields[2].replace("D", "E").replace("d", "e"))
                except Exception:
                    current_block = None
        transferred_nodes = set()
        if not sfe_blocks:
            log("ANSYS area pressure has no transferred solid-element surface records")
            return False
        expected_loaded_elements = set()
        expected_transferred_nodes = set()
        face_corner_count = 4 if element_code in (185, 186) else 3
        corner_count = 8 if element_code in (185, 186) else 4
        for element, (_, connectivity) in db_connectivity.items():
            face_corners = set(
                label
                for label in connectivity[:corner_count]
                if label in expected_sets["FREE"]
            )
            if len(face_corners) == face_corner_count:
                expected_loaded_elements.add(element)
                expected_transferred_nodes.update(face_corners)
        transferred_elements = set()
        for block in sfe_blocks:
            if block["element"] not in set(element_numbers) or any(not close_enough(value, -10.0, rel=1.0e-8, abs_tol=1.0e-8) for value in block["values"]):
                log("ANSYS transferred element-face pressure is not uniformly -10 MPa")
                return False
            transferred_elements.add(block["element"])
            transferred_nodes.update(block["nodes"])
        if (
            transferred_elements != expected_loaded_elements
            or transferred_nodes != expected_transferred_nodes
        ):
            log("ANSYS transferred pressure records do not cover exactly the X=100 element faces")
            return False
        for command, marker in (
            ("BFLIST,ALL", "NO NODAL BODY FORCES TO LIST"),
            ("BFELIST,ALL", "NO ELEMENT BODY FORCES TO LIST"),
            ("ICLIST,ALL", "NO INITIAL CONDITIONS TO LIST"),
            ("CPLIST,ALL", "NO COUPLED SETS TO LIST"),
            ("CELIST,ALL", "NO CONSTRAINT EQUATIONS TO LIST"),
        ):
            if not listing_confirms_none(mapdl, command, marker):
                log("ANSYS model contains an additional load or constraint category: %s" % command)
                return False
        export_stem = "task04_model_audit_" + run_token[:8]
        required_run(mapdl, "CDWRITE,DB,%s,cdb" % export_stem)
        export_path = temp_root / (export_stem + ".cdb")
        export_text = export_path.read_text(encoding="utf-8", errors="ignore") if is_nonempty(export_path) else ""
        if not export_text or not inertia_loads_are_zero(export_text):
            log("ANSYS model contains a nonzero translational or rotational inertia load")
            return False
        required_run(mapdl, "FINISH")
        required_run(mapdl, "/POST1")
        mapdl.file(str(result_path.with_suffix("")), "rst")
        mapdl.set("LAST")
        required_run(mapdl, "RSYS,0")
        if int(round(required_get(mapdl, "ACTIVE", 0, "ANTY"))) != 0:
            log("ANSYS result analysis type is not static")
            return False
        result_load_step = int(round(required_get(mapdl, "ACTIVE", 0, "SET", "LSTP")))
        result_set_count = int(round(required_get(mapdl, "ACTIVE", 0, "SET", "NSET")))
        if result_load_step != 1 or result_set_count < 1:
            log("ANSYS result does not contain the completed static result set")
            return False
        center_node = next(iter(expected_sets["CENTER"]))
        free_end_displacement = try_get(mapdl, "NODE", center_node, "U", "X")
        if free_end_displacement is None or not math.isfinite(free_end_displacement):
            log("ANSYS free-face center U1 result is missing")
            return False
        required_run(mapdl, "NSEL,NONE")
        for label in sorted(expected_sets["FIXED"]):
            required_run(mapdl, "NSEL,A,NODE,,%d" % label)
        required_run(mapdl, "FSUM")
        fixed_fsum = tuple(
            required_get(mapdl, "FSUM", 0, "ITEM", component)
            for component in ("FX", "FY", "FZ")
        )
        submitted_reactions = ansys_reaction_signature(mapdl, expected_sets["FIXED"])
        if submitted_reactions is None:
            log("ANSYS result does not expose complete fixed-face global reactions")
            return False
        required_run(mapdl, "ALLSEL,ALL")
        fixed_reaction = tuple(
            sum(values[index] for values in submitted_reactions.values())
            for index in range(3)
        )
        axial_stress = -fixed_reaction[0] / 100.0
        submitted_signature = ansys_nodal_result_signature(mapdl, expected_sets["ALL"])
        submitted_solid_signature = ansys_solid_stress_signature(mapdl, element_numbers)
        if submitted_signature is None or submitted_solid_signature is None:
            log("ANSYS submitted RST contains missing or non-finite nodal U/S data")
            return False
        maximum = max(values[-1] for values in submitted_solid_signature.values())
        if not (0.0040 < free_end_displacement < 0.0055 and 9.8 < axial_stress < 10.2 and maximum > 0.0):
            log("native ANSYS metrics are outside physical sanity bounds")
            return False
        if abs(fixed_reaction[1]) > 0.1 or abs(fixed_reaction[2]) > 0.1:
            log("ANSYS transverse fixed-face reaction is inconsistent with pure axial tension")
            return False
        if any(
            not close_enough(
                fixed_fsum[index],
                -fixed_reaction[index],
                rel=1.0e-4,
                abs_tol=0.01,
            )
            for index in range(3)
        ):
            log("ANSYS fixed-face element force and global reaction are not in equilibrium")
            return False
        if not close_enough(free_end_displacement, submitted_metrics["free_end_displacement"], rel=1.0e-3, abs_tol=1.0e-7):
            log("metrics.json free_end_displacement does not match center-node RST U1")
            return False
        if not close_enough(axial_stress, submitted_metrics["axial_stress"], rel=1.0e-3, abs_tol=0.005):
            log("metrics.json axial_stress does not match fixed-face RST reaction / 100 mm^2")
            return False
        required_run(mapdl, "FINISH")
        mapdl.resume(str(model_path.with_suffix("")), "db")
        required_run(mapdl, "/FILNAME,%s,1" % mapdl_jobname)
        required_run(mapdl, "/SOLU")
        required_run(mapdl, "ALLSEL,ALL")
        required_run(mapdl, "SOLVE")
        required_run(mapdl, "FINISH")
        required_run(mapdl, "/POST1")
        mapdl.file(str((temp_root / mapdl_jobname).with_suffix("")), "rst")
        mapdl.set("LAST")
        required_run(mapdl, "RSYS,0")
        required_run(mapdl, "NSEL,NONE")
        for label in sorted(expected_sets["FIXED"]):
            required_run(mapdl, "NSEL,A,NODE,,%d" % label)
        rechecked_reactions = ansys_reaction_signature(mapdl, expected_sets["FIXED"])
        required_run(mapdl, "ALLSEL,ALL")
        rechecked_signature = ansys_nodal_result_signature(mapdl, expected_sets["ALL"])
        rechecked_solid_signature = ansys_solid_stress_signature(mapdl, element_numbers)
        if (
            not ansys_signatures_match(submitted_signature, rechecked_signature)
            or not ansys_solid_signatures_match(submitted_solid_signature, rechecked_solid_signature)
            or not ansys_reaction_signatures_match(submitted_reactions, rechecked_reactions)
        ):
            log("ANSYS submitted RST fields do not match an isolated re-solve of the DB")
            return False
        semantic_passed = True
    except Exception as exc:
        log("ANSYS checker failed: %s" % exc)
        return False
    finally:
        if mapdl is not None:
            try:
                mapdl.exit()
            except Exception:
                pass
        process_cleanup_ok = cleanup_ansys_job_processes(mapdl_jobname, process_baseline)
        if not process_cleanup_ok:
            log("ANSYS evaluator process cleanup was incomplete")
        temp_cleanup_ok = remove_tree_with_retries(temp_root)
        if not temp_cleanup_ok:
            log("ANSYS evaluator temporary directory cleanup was incomplete")
        cleanup_ok = process_cleanup_ok and temp_cleanup_ok
    return semantic_passed and cleanup_ok


def evaluate():
    desktop = desktop_dir()
    root = desktop / 'result'
    if not root.is_dir():
        log('result directory missing')
        return False, desktop
    metrics = read_metrics(root)
    if metrics is None:
        return False, root
    branch = discover_branch(root)
    if branch is None:
        return False, root
    if branch[0] == "abaqus":
        log("evaluating Abaqus 2025 native branch")
        return run_abaqus_checker(branch[1], branch[2], metrics), root
    log("evaluating ANSYS MAPDL 2026 R1 native branch")
    return run_ansys_checker(branch[1], branch[2], metrics), root


def main():
    passed = False
    root = desktop_dir()
    try:
        passed, root = evaluate()
    except Exception as exc:
        log("unhandled evaluator error: %s" % exc)
        passed = False
    try:
        (root / "eval_detail.txt").write_text("\n".join(DETAILS) + "\n", encoding="utf-8")
        (root / "eval_result.txt").write_text("True\n" if passed else "False\n", encoding="utf-8")
    except Exception:
        pass
    sys.stdout.write("True\n" if passed else "False\n")


if __name__ == "__main__":
    main()
