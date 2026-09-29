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


TASK_ID = "c-open-abaqus-ansys-autocad-task-03-windows"
JOB_NAME = "Job-FlangeHole"
STEP_NAME = "Step-HoleTension"
METRIC_FIELDS = ("stress_concentration_proxy", "max_mises", "edge_displacement")
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
        log("metrics.json must contain exactly three finite numeric Task-03 metric fields")
        return None
    metrics = {name: float(data[name]) for name in METRIC_FIELDS}
    if not (0.002 < metrics["edge_displacement"] < 0.02):
        log("edge_displacement is outside the task-specific physical range")
        return None
    if not (12.0 < metrics["max_mises"] < 60.0):
        log("max_mises is outside the task-specific physical range")
        return None
    if not math.isclose(
        metrics["stress_concentration_proxy"],
        metrics["max_mises"] / 8.0,
        rel_tol=1.0e-9,
        abs_tol=1.0e-9,
    ):
        log("stress_concentration_proxy must equal max_mises / 8.0")
        return None
    return metrics


def discover_branch(root):
    caes = files_with_suffix(root, ".cae")
    odbs = files_with_suffix(root, ".odb")
    dbs = files_with_suffix(root, ".db")
    rsts = files_with_suffix(root, ".rst")
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
    temp_root = Path(tempfile.mkdtemp(prefix="eval_cli_task03_abaqus_%s_" % uuid.uuid4().hex))
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
from abaqusConstants import ON
from caeModules import *
from odbAccess import openOdb

CAE_PATH = __CAE_PATH__
ODB_PATH = __ODB_PATH__
RESULT_PATH = __RESULT_PATH__
SUBMITTED = __SUBMITTED__
RECHECK_JOB_NAME = __RECHECK_JOB_NAME__
JOB_NAME = "Job-FlangeHole"
STEP_NAME = "Step-HoleTension"
ALLOWED_TYPES = ("S3", "S3R", "S4", "S4R", "S4I", "S8R", "S8R5", "S9R5")
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


def validate_input_output_request(job, expected_elements):
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
        return fail("CAE-generated input must contain the single Step-HoleTension step")

    elsets = {}
    for card in cards:
        name = card["params"].get("ELSET", "").upper()
        if not name or card["keyword"] not in ("ELEMENT", "ELSET"):
            continue
        values = elsets.setdefault(name, [])
        tokens = [token.strip() for row in card["data"] for token in row.split(",") if token.strip()]
        if card["keyword"] == "ELEMENT":
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
        key = str(name).upper()
        if key not in elsets or key in stack:
            return set()
        result = set()
        for value in elsets[key]:
            if isinstance(value, int):
                result.add(value)
            else:
                result.update(resolve_elset(value, stack | set((key,))))
        return result

    steel_coverage = set()
    other_coverage = set()
    section_definitions = []
    for card in cards:
        if card["keyword"] != "SHELL SECTION":
            continue
        labels = resolve_elset(card["params"].get("ELSET", ""), set())
        if card["params"].get("MATERIAL", "").upper() == "STEEL":
            steel_coverage.update(labels)
        else:
            other_coverage.update(labels)
        numbers = []
        for token in [value.strip() for row in card["data"] for value in row.split(",") if value.strip()]:
            try:
                numbers.append(float(token))
            except Exception:
                pass
        section_definitions.append(numbers)
    if steel_coverage != expected_elements or other_coverage.intersection(expected_elements):
        return fail("CAE-generated input does not assign Steel shell section to every plate element")
    if len(section_definitions) != 1 or len(section_definitions[0]) < 2:
        return fail("CAE-generated input must contain one shell-section definition")
    if not close(section_definitions[0][0], 1.0) or int(round(section_definitions[0][1])) != 5:
        return fail("CAE-generated shell section is not 1 mm with five through-thickness points")

    node_variables = set()
    element_variables = set()
    requested_section_points = set()
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
            for value in values:
                try:
                    requested_section_points.add(int(value))
                except Exception:
                    pass
    if not set(("U", "RF")).issubset(node_variables) or "S" not in element_variables:
        return fail("CAE field output request must explicitly include nodal U/RF and element S")
    if requested_section_points != set((1, 2, 3, 4, 5)):
        return fail("CAE S output must request all five shell section points")
    return True


def element_nodes(part, element):
    try:
        return list(element.getNodes())
    except Exception:
        result = []
        for index in element.connectivity:
            result.append(part.nodes[int(index)])
        return result


def validate_shell_mesh(part, coords):
    if len(part.elements) < 100 or len(part.nodes) < 100:
        return fail("shell mesh is too coarse for the plate and refined circular hole")
    element_types = set(str(element.type).upper() for element in part.elements)
    if not element_types or not element_types.issubset(set(ALLOWED_TYPES)):
        return fail("all elements must use an appropriate Abaqus shell formulation")
    total_area = 0.0
    attached = set()
    for element in part.elements:
        nodes = element_nodes(part, element)
        corner_count = 3 if str(element.type).upper().startswith("S3") else 4
        corners = nodes[:corner_count]
        if len(corners) != corner_count:
            return fail("shell element connectivity is incomplete")
        attached.update(int(node.label) for node in nodes)
        points = [(float(node.coordinates[0]), float(node.coordinates[1])) for node in corners]
        area = 0.0
        for index, point in enumerate(points):
            other = points[(index + 1) % len(points)]
            area += point[0] * other[1] - other[0] * point[1]
        total_area += abs(area) * 0.5
        span = builtins.max(
            math.hypot(a[0] - b[0], a[1] - b[1])
            for a in points for b in points
        )
        if span > 22.0:
            return fail("shell mesh contains an element inconsistent with the 10 mm global seed")
    if attached != set(coords):
        return fail("shell mesh contains unattached nodes")
    expected_area = 120.0 * 240.0 - math.pi * 6.0 * 6.0
    if not close(total_area, expected_area, rel=0.015, abs_tol=2.0):
        return fail("shell mesh does not cover the rectangular plate minus the central hole")
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


def canonical_shell_type(value):
    name = str(value).upper()
    return "S3" if name == "S3R" else name


def validate_model(database):
    if JOB_NAME not in database.jobs.keys():
        return fail("CAE does not contain the required Job-FlangeHole job")
    job = database.jobs[JOB_NAME]
    model_name = str(getattr(job, "model", ""))
    if model_name not in database.models.keys():
        return fail("Job-FlangeHole does not reference a valid model")
    model = database.models[model_name]
    meshed_parts = [model.parts[name] for name in model.parts.keys() if len(model.parts[name].elements)]
    if len(meshed_parts) != 1:
        return fail("job model must contain one meshed shell plate part")
    part = meshed_parts[0]
    if len(model.rootAssembly.instances.keys()) != 1:
        return fail("job model must contain exactly one plate instance")
    instance = model.rootAssembly.instances[model.rootAssembly.instances.keys()[0]]
    if str(getattr(instance, "partName", "")) != str(part.name) or str(getattr(instance, "dependent", "")).upper() not in ("ON", "1"):
        return fail("plate assembly must contain one dependent instance of the meshed part")
    coords = coords_by_label(part.nodes)
    if not coords:
        return fail("part has no nodes")
    if any(len(node.coordinates) not in (2, 3) for node in part.nodes):
        return fail("plate part has unsupported nodal coordinates")
    xs = [xyz[0] for xyz in coords.values()]
    ys = [xyz[1] for xyz in coords.values()]
    zs = [xyz[2] for xyz in coords.values()]
    if not (
        close(builtins.min(xs), 0.0)
        and close(builtins.max(xs), 120.0)
        and close(builtins.min(ys), 0.0)
        and close(builtins.max(ys), 240.0)
        and close(builtins.min(zs), 0.0)
        and close(builtins.max(zs), 0.0)
    ):
        return fail("part geometry is not a 120 x 240 mm XY shell midsurface")
    if any(math.hypot(xyz[0] - 60.0, xyz[1] - 120.0) < 5.99 for xyz in coords.values()):
        return fail("mesh contains nodes inside the required circular hole")
    hole_labels = set(
        label for label, xyz in coords.items()
        if close(math.hypot(xyz[0] - 60.0, xyz[1] - 120.0), 6.0, rel=1.0e-4, abs_tol=1.0e-3)
    )
    if len(hole_labels) < 12:
        return fail("central radius-6 hole is missing or lacks the required 2.4 mm refinement")
    hole_angles = builtins.sorted(
        math.atan2(coords[label][1] - 120.0, coords[label][0] - 60.0)
        for label in hole_labels
    )
    gaps = [hole_angles[index + 1] - hole_angles[index] for index in range(len(hole_angles) - 1)]
    gaps.append(hole_angles[0] + 2.0 * math.pi - hole_angles[-1])
    if builtins.max(gaps) * 6.0 > 3.7:
        return fail("circular-hole edge mesh is not refined to approximately 2.4 mm")
    element_types = validate_shell_mesh(part, coords)
    if not element_types:
        return False
    expected_sets = {
        "LEFT": set(label for label, xyz in coords.items() if close(xyz[0], 0.0)),
        "RIGHT": set(label for label, xyz in coords.items() if close(xyz[0], 120.0)),
        "BOTTOM_LEFT": set(label for label, xyz in coords.items() if close(xyz[0], 0.0) and close(xyz[1], 0.0)),
        "BOTTOM_RIGHT": set(label for label, xyz in coords.items() if close(xyz[0], 120.0) and close(xyz[1], 0.0)),
        "TOP_LEFT": set(label for label, xyz in coords.items() if close(xyz[0], 0.0) and close(xyz[1], 240.0)),
        "HOLE": hole_labels,
    }
    if any(not labels for labels in expected_sets.values()):
        return fail("required plate edge or corner nodes cannot be identified")

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
            section.__class__.__name__ == "HomogeneousShellSection"
            and str(getattr(section, "material", "")) == "Steel"
            and close(getattr(section, "thickness", None), 1.0)
            and int(getattr(section, "numIntPts", 0)) == 5
        ):
            valid_sections.add(str(name))
    if not valid_sections:
        return fail("no 1 mm homogeneous Steel shell section with five integration points exists")
    assignments = list(part.sectionAssignments)
    if not assignments or any(str(assignment.sectionName) not in valid_sections for assignment in assignments):
        return fail("every plate section assignment must reference the valid homogeneous Steel shell section")

    bcs = active_named_objects(model.boundaryConditions)
    if STEP_NAME not in model.steps.keys():
        return fail("Step-HoleTension is missing")
    step = model.steps[STEP_NAME]
    actual_constraints = {}
    for bc_name, bc in bcs:
        if bc_name not in step.boundaryConditionStates.keys():
            continue
        bc_state = step.boundaryConditionStates[bc_name]
        if not state_is_active(bc_state):
            continue
        if bc.__class__.__name__ != "DisplacementBC":
            return fail("only displacement BCs may be active")
        labels = region_labels_any(model, bc.region, "nodes")
        if not labels:
            return fail("active displacement BC region cannot be resolved")
        for component in ("u1", "u2", "u3", "ur1", "ur2", "ur3"):
            if state_is_unset(getattr(bc_state, component + "State", None)):
                continue
            if not close(getattr(bc_state, component, None), 0.0):
                return fail("active displacement constraint must be zero")
            for label in labels:
                actual_constraints.setdefault(label, set()).add(component.upper())
    expected_constraints = {
        next(iter(expected_sets["BOTTOM_LEFT"])): set(("U1", "U2", "U3")),
        next(iter(expected_sets["BOTTOM_RIGHT"])): set(("U2", "U3")),
        next(iter(expected_sets["TOP_LEFT"])): set(("U3",)),
    }
    if actual_constraints != expected_constraints:
        return fail("active corner constraint signature is not BL U1/U2/U3, BR U2/U3, TL U3")
    if active_objects(model.constraints):
        return fail("additional model constraints are not allowed")

    if step.__class__.__name__ != "StaticStep":
        return fail("Step-HoleTension must be a static step")
    if not active_objects(model.fieldOutputRequests):
        return fail("field output request is missing")

    loads = active_named_objects(model.loads)
    actual_loads = []
    for load_name, load in loads:
        if load_name not in step.loadStates.keys():
            continue
        load_state = step.loadStates[load_name]
        if not state_is_active(load_state):
            continue
        if load.__class__.__name__ != "ShellEdgeLoad":
            return fail("only native shell edge loads may be active")
        labels = region_labels_any(model, load.region, "nodes")
        magnitude = getattr(load_state, "magnitude", getattr(load, "magnitude", None))
        direction = direction_components(getattr(load, "directionVector", None))
        traction = str(getattr(load, "traction", "")).strip().upper()
        if traction != "GENERAL":
            return fail("shell edge loads must use GENERAL traction with an explicit global direction")
        for attribute in ("localCsys", "userCsys"):
            if not uses_global_coordinate_system(load, attribute):
                return fail("shell edge load directions must use the global coordinate system")
        if not labels or not close(magnitude, 8.0) or direction is None:
            return fail("shell edge load region, magnitude, or direction cannot be validated")
        length = math.sqrt(builtins.sum(value * value for value in direction))
        if length <= 0.0:
            return fail("shell edge load direction is zero")
        direction = tuple(value / length for value in direction)
        actual_loads.append((labels, direction))
    expected_loads = [
        (expected_sets["LEFT"], (-1.0, 0.0, 0.0)),
        (expected_sets["RIGHT"], (1.0, 0.0, 0.0)),
    ]
    unmatched = list(actual_loads)
    for expected_labels, expected_direction in expected_loads:
        found = None
        for item in unmatched:
            if item[0] == expected_labels and all(close(a, b) for a, b in zip(item[1], expected_direction)):
                found = item
                break
        if found is None:
            return fail("opposing 8 N/mm shell edge loads are not applied to the complete vertical edges")
        unmatched.remove(found)
    if unmatched:
        return fail("model contains an extra active load")
    element_labels = set(int(element.label) for element in part.elements)
    if not validate_input_output_request(job, element_labels):
        return False
    connectivity = dict(
        (
            int(element.label),
            (
                canonical_shell_type(element.type),
                tuple(builtins.sorted(int(node.label) for node in element_nodes(part, element))),
            ),
        )
        for element in part.elements
    )
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
            return fail("ODB must contain the single analysis step Step-HoleTension")
        step = odb.steps[STEP_NAME]
        if len(step.frames) < 2:
            return fail("ODB has no solved final frame")
        frame = step.frames[-1]
        if not math.isfinite(float(frame.frameValue)) or not close(
            frame.frameValue, model_info["step_time"], rel=1.0e-6, abs_tol=1.0e-8
        ):
            return fail("final frame is not the completed static load step")
        if len(odb.rootAssembly.instances.keys()) != 1:
            return fail("ODB must contain one shell plate instance")
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
                    canonical_shell_type(element.type),
                    tuple(builtins.sorted(int(label) for label in element.connectivity)),
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
        stress_sections = {}
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
            stress_sections.setdefault(label, set()).add(section_number)
            try:
                invariant = float(value.mises)
                components = tuple(float(item) for item in value.data)
            except Exception:
                return fail("stress value has no finite von Mises invariant")
            if not math.isfinite(invariant) or not components or any(
                not math.isfinite(item) for item in components
            ):
                return fail("stress output contains a non-finite value")
            mises.append(invariant)
            integration_point = int(getattr(value, "integrationPoint", 0) or 0)
            key = (label, section_number, integration_point)
            if key in signature["S"]:
                return fail("ODB contains duplicate shell stress records")
            signature["S"][key] = components + (invariant,)
        if set(stress_sections) != model_info["elements"] or any(
            points != set((1, 2, 3, 4, 5)) for points in stress_sections.values()
        ):
            return fail("integration-point S output does not cover every shell element and all five section points")

        left_labels = model_info["sets"]["LEFT"]
        right_labels = model_info["sets"]["RIGHT"]
        if not left_labels or not right_labels or not left_labels.issubset(set(displacement)) or not right_labels.issubset(set(displacement)):
            return fail("loaded vertical-edge displacement output is incomplete")
        left_mean = builtins.sum(displacement[label][0] for label in left_labels) / float(len(left_labels))
        right_mean = builtins.sum(displacement[label][0] for label in right_labels) / float(len(right_labels))
        edge_displacement = right_mean - left_mean
        maximum = builtins.max(mises) if mises else None
        if maximum is None or not math.isfinite(edge_displacement) or not math.isfinite(maximum):
            return fail("native metrics could not be extracted")
        proxy = maximum / 8.0
        if not (0.002 < edge_displacement < 0.02 and 12.0 < maximum < 60.0 and 1.5 < proxy < 7.5):
            return fail("native Abaqus metrics are outside physical sanity bounds")
        if compare_submitted_metrics:
            if not close(edge_displacement, SUBMITTED["edge_displacement"], rel=1.0e-3, abs_tol=5.0e-6):
                return fail("metrics.json edge_displacement does not match the ODB edge means")
            if not close(maximum, SUBMITTED["max_mises"], rel=1.0e-3, abs_tol=0.05):
                return fail("metrics.json max_mises does not match all-element, all-section-point ODB S")
            if not close(proxy, SUBMITTED["stress_concentration_proxy"], rel=1.0e-6, abs_tol=1.0e-8):
                return fail("metrics.json stress_concentration_proxy does not equal ODB max_mises / 8.0")
        return {
            "metrics": {
                "stress_concentration_proxy": proxy,
                "max_mises": maximum,
                "edge_displacement": edge_displacement,
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
    checker_source = checker_source.replace("__RECHECK_JOB_NAME__", repr("eval_task03_abq_" + uuid.uuid4().hex[:12]))
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
    return set(("ACEL", "OMEGA", "DOMEGA", "DCGOMG")).issubset(active_commands)


def cdb_has_rotated_nodes(export_text):
    return bool(re.search(r"^\s*(?:NROTAT|NANG|NMODIF)\s*,", export_text or "", re.MULTILINE | re.IGNORECASE))


def shell_section_matches(listing_text, section_id, material_id):
    text = (listing_text or "").upper()
    if not re.search(r"SECTION ID NUMBER:\s*%d\b" % int(section_id), text):
        return False
    if "SHELL SECTION TYPE" not in text:
        return False
    layers = re.search(r"NUMBER OF LAYERS\s*=\s*(\d+)", text)
    total = re.search(r"TOTAL THICKNESS\s*=\s*([-+0-9.EED]+)", text)
    layer = re.search(
        r"^\s*1\s+([-+0-9.EED]+)\s+(\d+)\s+([-+0-9.EED]+)\s+(\d+)\s*$",
        text,
        re.MULTILINE,
    )
    if layers is None or total is None or layer is None:
        return False
    try:
        return (
            int(layers.group(1)) == 1
            and close_enough(float(total.group(1).replace("D", "E")), 1.0, rel=1.0e-8)
            and close_enough(float(layer.group(1).replace("D", "E")), 1.0, rel=1.0e-8)
            and int(layer.group(2)) == int(material_id)
            and int(layer.group(4)) == 5
        )
    except Exception:
        return False


def read_ansys_rst_mesh(result_path):
    from ansys.mapdl import reader as pymapdl_reader

    result = pymapdl_reader.read_binary(str(result_path))
    labels = [int(value) for value in result.mesh.nnum]
    rows = [[float(value) for value in row[:3]] for row in result.mesh.nodes]
    coords = dict(zip(labels, rows))
    elements = [int(value) for value in result.mesh.enum]
    return coords, elements, int(result.nsets)


def ansys_nodal_result_signature(mapdl, node_labels):
    signature = {}
    stress_fields = (
        ("S", "X"),
        ("S", "Y"),
        ("S", "Z"),
        ("S", "XY"),
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


def ansys_shell_stress_signature(mapdl, element_labels, surfaces):
    signature = {}
    for surface in surfaces:
        required_run(mapdl, "ALLSEL,ALL")
        required_run(mapdl, "ETABLE,ERAS")
        required_run(mapdl, "SHELL,%s" % surface)
        required_run(mapdl, "ETABLE,SEQV_TASK03,S,EQV")
        values = {}
        for label in sorted(element_labels):
            value = try_get(mapdl, "ELEM", label, "ETAB", "SEQV_TASK03")
            if value is None or not math.isfinite(value):
                return None
            values[label] = value
        signature[surface] = values
    required_run(mapdl, "ALLSEL,ALL")
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


def ansys_shell_signatures_match(left, right):
    if left is None or right is None or set(left) != set(right):
        return False
    for surface in left:
        if set(left[surface]) != set(right[surface]):
            return False
        for label in left[surface]:
            if not close_enough(left[surface][label], right[surface][label], rel=2.0e-4, abs_tol=1.0e-6):
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
    temp_root = Path(tempfile.mkdtemp(prefix="eval_cli_task03_ansys_%s_" % run_token))
    mapdl = None
    mapdl_jobname = "eval_task03_" + run_token[:16]
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
        if len(coords) < 100:
            log("ANSYS shell mesh is too coarse for the plate and refined hole")
            return False
        xs = [row[0] for row in node_rows]
        ys = [row[1] for row in node_rows]
        zs = [row[2] for row in node_rows]
        if not (
            close_enough(min(xs), 0.0, rel=1.0e-8)
            and close_enough(max(xs), 120.0, rel=1.0e-8)
            and close_enough(min(ys), 0.0, rel=1.0e-8)
            and close_enough(max(ys), 240.0, rel=1.0e-8)
            and close_enough(min(zs), 0.0, rel=1.0e-8)
            and close_enough(max(zs), 0.0, rel=1.0e-8)
        ):
            log("ANSYS geometry bounds are incorrect")
            return False
        element_numbers = [int(value) for value in mapdl.mesh.enum]
        if len(element_numbers) < 100:
            log("ANSYS shell mesh is too coarse")
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
        section_ids = set()
        for element in element_numbers:
            type_id = required_get(mapdl, "ELEM", element, "ATTR", "TYPE")
            material_id = required_get(mapdl, "ELEM", element, "ATTR", "MAT")
            section_id = required_get(mapdl, "ELEM", element, "ATTR", "SEC")
            type_ids.add(int(round(type_id)))
            material_ids.add(int(round(material_id)))
            section_ids.add(int(round(section_id)))
        if len(type_ids) != 1 or len(material_ids) != 1 or len(section_ids) != 1:
            log("all plate elements must use one shell type, material, and section")
            return False
        type_id = next(iter(type_ids))
        element_code = int(round(required_get(mapdl, "ETYP", type_id, "ATTR", "ENAM")))
        if element_code not in (181, 281):
            log("actual elements are not SHELL181/SHELL281")
            return False
        storage_keyopt = try_get(mapdl, "ETYP", type_id, "ATTR", "KOP8")
        if storage_keyopt is None or int(round(storage_keyopt)) not in (0, 1, 2):
            log("ANSYS shell section-result storage option is unsupported")
            return False
        storage_keyopt = int(round(storage_keyopt))
        stored_surfaces = ("TOP", "MID", "BOT") if storage_keyopt == 2 else ("TOP", "BOT")

        nodes_per_element = 4 if element_code == 181 else 8
        attached_nodes = set()
        total_area = 0.0
        for element in element_numbers:
            connectivity = []
            for position in range(1, nodes_per_element + 1):
                label = int(round(required_get(mapdl, "ELEM", element, "NODE", position)))
                if label <= 0 or label not in coords:
                    log("ANSYS element connectivity references a missing node")
                    return False
                connectivity.append(label)
            if len(set(connectivity)) != nodes_per_element:
                log("ANSYS mesh contains a degenerate quadrilateral element")
                return False
            attached_nodes.update(connectivity)
            rows = [coords[label] for label in connectivity[:4]]
            area = 0.0
            for index, row in enumerate(rows):
                other = rows[(index + 1) % len(rows)]
                area += row[0] * other[1] - other[0] * row[1]
            total_area += abs(area) * 0.5
            span = max(math.hypot(a[0] - b[0], a[1] - b[1]) for a in rows for b in rows)
            if span > 22.0:
                log("ANSYS shell mesh contains an element inconsistent with the 10 mm global seed")
                return False
        expected_area = 120.0 * 240.0 - math.pi * 6.0 * 6.0
        if attached_nodes != set(coords) or not close_enough(total_area, expected_area, rel=0.015, abs_tol=2.0):
            log("ANSYS shell mesh does not cover the rectangular plate minus the central hole")
            return False

        hole_nodes = set(
            label for label, xyz in coords.items()
            if close_enough(math.hypot(xyz[0] - 60.0, xyz[1] - 120.0), 6.0, rel=1.0e-4, abs_tol=1.0e-3)
        )
        if len(hole_nodes) < 12 or any(
            math.hypot(xyz[0] - 60.0, xyz[1] - 120.0) < 5.99 for xyz in coords.values()
        ):
            log("ANSYS central radius-6 hole is missing or lacks the required refinement")
            return False
        hole_angles = sorted(math.atan2(coords[label][1] - 120.0, coords[label][0] - 60.0) for label in hole_nodes)
        gaps = [hole_angles[index + 1] - hole_angles[index] for index in range(len(hole_angles) - 1)]
        gaps.append(hole_angles[0] + 2.0 * math.pi - hole_angles[-1])
        if max(gaps) * 6.0 > 3.7:
            log("ANSYS circular-hole edge mesh is not refined to approximately 2.4 mm")
            return False

        material_id = next(iter(material_ids))
        if not material_matches(mapdl, material_id):
            log("actual ANSYS material is not E=210000, nu=0.3")
            return False

        expected_sets = {
            "ALL": set(coords),
            "LEFT": set(label for label, xyz in coords.items() if close_enough(xyz[0], 0.0, rel=1.0e-8, abs_tol=1.0e-7)),
            "RIGHT": set(label for label, xyz in coords.items() if close_enough(xyz[0], 120.0, rel=1.0e-8, abs_tol=1.0e-7)),
            "BOTTOM_LEFT": set(label for label, xyz in coords.items() if close_enough(xyz[0], 0.0, rel=1.0e-8, abs_tol=1.0e-7) and close_enough(xyz[1], 0.0, rel=1.0e-8, abs_tol=1.0e-7)),
            "BOTTOM_RIGHT": set(label for label, xyz in coords.items() if close_enough(xyz[0], 120.0, rel=1.0e-8, abs_tol=1.0e-7) and close_enough(xyz[1], 0.0, rel=1.0e-8, abs_tol=1.0e-7)),
            "TOP_LEFT": set(label for label, xyz in coords.items() if close_enough(xyz[0], 0.0, rel=1.0e-8, abs_tol=1.0e-7) and close_enough(xyz[1], 240.0, rel=1.0e-8, abs_tol=1.0e-7)),
        }
        if any(not value for value in expected_sets.values()):
            log("ANSYS required vertical edges or corner nodes cannot be identified")
            return False

        required_run(mapdl, "ALLSEL,ALL")
        constraints = parse_listing_rows(required_run(mapdl, "DLIST,ALL"), ("UX", "UY", "UZ"))
        actual_constraints = {}
        for node, label, value in constraints:
            if abs(value) > 1.0e-12:
                log("ANSYS contains a nonzero displacement constraint")
                return False
            actual_constraints.setdefault(node, set()).add(label)
        expected_constraints = {
            next(iter(expected_sets["BOTTOM_LEFT"])): set(("UX", "UY", "UZ")),
            next(iter(expected_sets["BOTTOM_RIGHT"])): set(("UY", "UZ")),
            next(iter(expected_sets["TOP_LEFT"])): set(("UZ",)),
        }
        if actual_constraints != expected_constraints:
            log("ANSYS constraint signature is not BL UX/UY/UZ, BR UY/UZ, TL UZ")
            return False
        if any(label not in ("UX", "UY", "UZ") for node, label, value in constraints):
            log("ANSYS contains an extra or nonzero displacement constraint")
            return False

        force_rows = parse_listing_rows(required_run(mapdl, "FLIST,ALL"), ("FX", "FY", "FZ"))
        if any(label != "FX" for node, label, value in force_rows):
            log("ANSYS contains a non-X nodal load")
            return False
        if not listing_confirms_none(mapdl, "SFLIST,ALL", "NO SURFACE LOADS TO LIST"):
            log("ANSYS uses a surface load instead of the required nodal forces")
            return False
        if not listing_confirms_none(mapdl, "SFELIST,ALL", "NO SURFACE LOADS TO LIST"):
            log("ANSYS uses an element surface load instead of nodal forces")
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
        export_stem = "task03_model_audit_" + run_token[:8]
        required_run(mapdl, "CDWRITE,DB,%s,cdb" % export_stem)
        export_path = temp_root / (export_stem + ".cdb")
        export_text = export_path.read_text(encoding="utf-8", errors="ignore") if is_nonempty(export_path) else ""
        if not export_text or not inertia_loads_are_zero(export_text):
            log("ANSYS model contains a nonzero translational or rotational inertia load")
            return False
        if cdb_has_rotated_nodes(export_text):
            log("ANSYS nodal edge-load directions must use the global nodal coordinate system")
            return False
        for label in coords:
            for item in ("ANG", "THXY", "THYZ", "THZX"):
                angle = try_get(mapdl, "NODE", label, item)
                if angle is not None and abs(angle) > 1.0e-10:
                    log("ANSYS contains a node with a rotated nodal coordinate system")
                    return False
        section_id = next(iter(section_ids))
        section_listing = required_run(mapdl, "SLIST,%d" % section_id)
        if not shell_section_matches(section_listing, section_id, material_id):
            log("ANSYS shell section is not exactly 1 mm, material 1, with five integration points")
            return False
        expected_forces = {}
        for set_name, sign in (("LEFT", -1.0), ("RIGHT", 1.0)):
            edge_rows = sorted([(label, coords[label][1]) for label in expected_sets[set_name]], key=lambda row: row[1])
            if len(edge_rows) < 2:
                log("ANSYS loaded edge has too few nodes")
                return False
            for index, (label, axial) in enumerate(edge_rows):
                if index == 0:
                    tributary = 0.5 * (edge_rows[1][1] - axial)
                elif index == len(edge_rows) - 1:
                    tributary = 0.5 * (axial - edge_rows[index - 1][1])
                else:
                    tributary = 0.5 * (edge_rows[index + 1][1] - edge_rows[index - 1][1])
                expected_forces[label] = sign * 8.0 * tributary
        actual_forces = {}
        for node, label, value in force_rows:
            if node in actual_forces or node not in expected_forces:
                log("ANSYS nodal edge load targets a duplicate or non-vertical-edge node")
                return False
            actual_forces[node] = value
        if set(actual_forces) != set(expected_forces) or any(
            not close_enough(actual_forces[node], expected_forces[node], rel=1.0e-6, abs_tol=1.0e-3)
            for node in expected_forces
        ):
            log("ANSYS consistent nodal force distribution is not equivalent to opposing 8 N/mm edge loads")
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
        left_u1 = [try_get(mapdl, "NODE", label, "U", "X") for label in expected_sets["LEFT"]]
        right_u1 = [try_get(mapdl, "NODE", label, "U", "X") for label in expected_sets["RIGHT"]]
        if any(value is None or not math.isfinite(value) for value in left_u1 + right_u1):
            log("ANSYS loaded-edge displacement result is missing")
            return False
        edge_displacement = sum(right_u1) / len(right_u1) - sum(left_u1) / len(left_u1)
        submitted_signature = ansys_nodal_result_signature(mapdl, expected_sets["ALL"])
        submitted_shell_signature = ansys_shell_stress_signature(mapdl, element_numbers, stored_surfaces)
        if submitted_signature is None or submitted_shell_signature is None:
            log("ANSYS submitted RST contains missing or non-finite nodal U/S data")
            return False
        maximum = max(
            value
            for values in submitted_shell_signature.values()
            for value in values.values()
        )
        proxy = maximum / 8.0
        if not (0.002 < edge_displacement < 0.02 and 12.0 < maximum < 60.0 and 1.5 < proxy < 7.5):
            log("native ANSYS metrics are outside physical sanity bounds")
            return False
        if not close_enough(edge_displacement, submitted_metrics["edge_displacement"], rel=1.0e-3, abs_tol=5.0e-6):
            log("metrics.json edge_displacement does not match RST edge means")
            return False
        if not close_enough(maximum, submitted_metrics["max_mises"], rel=1.0e-3, abs_tol=0.05):
            log("metrics.json max_mises does not match RST shell section results")
            return False
        if not close_enough(proxy, submitted_metrics["stress_concentration_proxy"], rel=1.0e-6, abs_tol=1.0e-8):
            log("metrics.json stress_concentration_proxy does not equal RST max_mises / 8.0")
            return False
        reaction_text = required_run(mapdl, "PRRSOL,F").upper()
        if "REACTION SOLUTION LISTING" not in reaction_text or "TOTAL VALUES" not in reaction_text:
            log("ANSYS result does not expose reaction-force output")
            return False

        required_run(mapdl, "FINISH")
        mapdl.resume(str(model_path.with_suffix("")), "db")
        required_run(mapdl, "/SOLU")
        required_run(mapdl, "ALLSEL,ALL")
        required_run(mapdl, "SOLVE")
        required_run(mapdl, "FINISH")
        required_run(mapdl, "/POST1")
        mapdl.file(str((temp_root / mapdl_jobname).with_suffix("")), "rst")
        mapdl.set("LAST")
        required_run(mapdl, "RSYS,0")
        rechecked_signature = ansys_nodal_result_signature(mapdl, expected_sets["ALL"])
        rechecked_shell_signature = ansys_shell_stress_signature(mapdl, element_numbers, stored_surfaces)
        if not ansys_signatures_match(submitted_signature, rechecked_signature) or not ansys_shell_signatures_match(
            submitted_shell_signature, rechecked_shell_signature
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
