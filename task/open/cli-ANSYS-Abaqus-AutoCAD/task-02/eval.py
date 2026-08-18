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
from pathlib import Path


TASK_ID = "c-open-abaqus-ansys-autocad-task-02-windows"
JOB_NAME = "Job-Cylinder"
STEP_NAME = "Step-Pressure"
METRIC_FIELDS = ("radial_displacement", "max_mises")
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
    if any(name not in data or not finite_number(data[name]) for name in METRIC_FIELDS):
        log("metrics.json must contain finite numeric radial_displacement and max_mises")
        return None
    metrics = {name: float(data[name]) for name in METRIC_FIELDS}
    if not (0.0044 < metrics["radial_displacement"] < 0.0047):
        log("radial_displacement is outside the task-specific physical range")
        return None
    if not (18.0 < metrics["max_mises"] < 26.0):
        log("max_mises is outside the task-specific physical range")
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
        expected_odb = [path for path in odbs if path.name.lower() == "job-cylinder.odb"]
        if len(caes) != 1 or len(odbs) != 1 or len(expected_odb) != 1:
            log("Abaqus delivery requires one CAE and the single result Job-Cylinder.odb")
            return None
        return "abaqus", caes[0], expected_odb[0]
    if has_ansys:
        expected_db = [path for path in dbs if path.name.lower() == "job-cylinder.db"]
        expected_rst = [path for path in rsts if path.name.lower() == "job-cylinder.rst"]
        if len(dbs) != 1 or len(rsts) != 1 or len(expected_db) != 1 or len(expected_rst) != 1:
            log("ANSYS delivery requires exactly Job-Cylinder.db and Job-Cylinder.rst")
            return None
        return "ansys", expected_db[0], expected_rst[0]
    log("no supported native model/result pair found")
    return None


def close_enough(actual, expected, rel=1.0e-3, abs_tol=1.0e-8):
    try:
        return math.isclose(float(actual), float(expected), rel_tol=rel, abs_tol=abs_tol)
    except Exception:
        return False


def run_abaqus_checker(cae_path, odb_path, submitted_metrics):
    temp_root = Path(tempfile.mkdtemp(prefix="eval_cli_task02_abaqus_"))
    checker_path = temp_root / "checker.py"
    result_path = temp_root / "result.json"
    checker_source = r'''
# -*- coding: utf-8 -*-
from __future__ import print_function

import json
import math
import traceback

from abaqus import openMdb
from abaqusConstants import ON
from caeModules import *
from odbAccess import openOdb

CAE_PATH = __CAE_PATH__
ODB_PATH = __ODB_PATH__
RESULT_PATH = __RESULT_PATH__
SUBMITTED = __SUBMITTED__
JOB_NAME = "Job-Cylinder"
STEP_NAME = "Step-Pressure"
REQUIRED_SETS = ("ALLNODES", "INNER", "OUTER", "ZMIN", "ZMAX")
ALLOWED_TYPES = ("CAX4", "CAX4R", "CAX8", "CAX8R")
EXPECTED_IP = {"CAX4": 4, "CAX4R": 1, "CAX8": 9, "CAX8R": 4}
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
        return fail("CAE-generated input must contain the single Step-Pressure step")

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
    for card in cards:
        if card["keyword"] != "SOLID SECTION":
            continue
        labels = resolve_elset(card["params"].get("ELSET", ""), set())
        if card["params"].get("MATERIAL", "").upper() == "STEEL":
            steel_coverage.update(labels)
        else:
            other_coverage.update(labels)
    if steel_coverage != expected_elements or other_coverage.intersection(expected_elements):
        return fail("CAE-generated input does not assign Steel to every cylinder element")

    node_variables = set()
    element_variables = set()
    uses_preselect = False
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
        elif card["keyword"] == "OUTPUT" and card["params"].get("VARIABLE", "").upper() == "PRESELECT":
            uses_preselect = True
    if not uses_preselect and (
        not set(("U", "RF")).issubset(node_variables) or "S" not in element_variables
    ):
        return fail("CAE field output request must include nodal U/RF and element S")
    return True


def element_nodes(part, element):
    try:
        return list(element.getNodes())
    except Exception:
        result = []
        for index in element.connectivity:
            result.append(part.nodes[int(index)])
        return result


def validate_structured_mesh(part):
    if len(part.elements) != 20:
        return fail("mesh must contain 20 mapped 5 mm elements")
    element_types = set(str(element.type).upper() for element in part.elements)
    if len(element_types) != 1 or not element_types.issubset(set(ALLOWED_TYPES)):
        return fail("all elements must use one supported CAX4/CAX8 axisymmetric quadrilateral type")
    element_type = next(iter(element_types))
    expected_nodes = 33 if element_type.startswith("CAX4") else 85
    if len(part.nodes) != expected_nodes:
        return fail("node count does not match a structured 5 mm %s mesh" % element_type)
    boxes = set()
    for element in part.elements:
        nodes = element_nodes(part, element)
        xs = [float(node.coordinates[0]) for node in nodes]
        ys = [float(node.coordinates[1]) for node in nodes]
        box = (round(min(xs), 6), round(max(xs), 6), round(min(ys), 6), round(max(ys), 6))
        if not close(box[1] - box[0], 5.0) or not close(box[3] - box[2], 5.0):
            return fail("an element does not span one 5 mm by 5 mm mapped cell")
        boxes.add(box)
    expected_boxes = set(
        (float(50 + 5 * i), float(55 + 5 * i), float(5 * j), float(5 + 5 * j))
        for j in range(2)
        for i in range(10)
    )
    if boxes != expected_boxes:
        return fail("element cells do not exactly cover the required structured grid")
    return element_type


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


def validate_sets(model, part, coords):
    all_labels = set(coords)
    expected = {
        "ALLNODES": all_labels,
        "INNER": set(label for label, xyz in coords.items() if close(xyz[0], 50.0)),
        "OUTER": set(label for label, xyz in coords.items() if close(xyz[0], 100.0)),
        "ZMIN": set(label for label, xyz in coords.items() if close(xyz[1], 0.0)),
        "ZMAX": set(label for label, xyz in coords.items() if close(xyz[1], 10.0)),
    }
    for name in REQUIRED_SETS:
        actual = named_set_labels(model, part, name)
        if actual != expected[name]:
            return fail("node set %s is missing, conflicting, or has incorrect membership" % name)
    return expected


def validate_model(database):
    if JOB_NAME not in database.jobs.keys():
        return fail("CAE does not contain the required Job-Cylinder job")
    job = database.jobs[JOB_NAME]
    model_name = str(getattr(job, "model", ""))
    if model_name not in database.models.keys():
        return fail("Job-Cylinder does not reference a valid model")
    model = database.models[model_name]
    meshed_parts = [model.parts[name] for name in model.parts.keys() if len(model.parts[name].elements)]
    if len(meshed_parts) != 1:
        return fail("job model must contain one meshed cylinder part")
    part = meshed_parts[0]
    coords = coords_by_label(part.nodes)
    if not coords:
        return fail("part has no nodes")
    if any(len(node.coordinates) not in (2, 3) for node in part.nodes):
        return fail("cylinder part has unsupported nodal coordinates")
    xs = [xyz[0] for xyz in coords.values()]
    ys = [xyz[1] for xyz in coords.values()]
    zs = [xyz[2] for xyz in coords.values()]
    if not (
        close(min(xs), 50.0)
        and close(max(xs), 100.0)
        and close(min(ys), 0.0)
        and close(max(ys), 10.0)
        and close(min(zs), 0.0)
        and close(max(zs), 0.0)
    ):
        return fail("part geometry is not r=50..100, z=0..10")
    element_type = validate_structured_mesh(part)
    if not element_type:
        return False
    expected_sets = validate_sets(model, part, coords)
    if not expected_sets:
        return False

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
        if section.__class__.__name__ == "HomogeneousSolidSection" and str(getattr(section, "material", "")) == "Steel":
            valid_sections.add(str(name))
    if not valid_sections:
        return fail("no homogeneous solid section references Steel")
    assignments = list(part.sectionAssignments)
    if not assignments or any(str(assignment.sectionName) not in valid_sections for assignment in assignments):
        return fail("every cylinder section assignment must reference homogeneous Steel")

    bcs = active_named_objects(model.boundaryConditions)
    if STEP_NAME not in model.steps.keys():
        return fail("Step-Pressure is missing")
    step = model.steps[STEP_NAME]
    constrained_u2 = set()
    for bc_name, bc in bcs:
        if bc_name not in step.boundaryConditionStates.keys():
            continue
        bc_state = step.boundaryConditionStates[bc_name]
        if not state_is_active(bc_state):
            continue
        if bc.__class__.__name__ != "DisplacementBC":
            return fail("only displacement BCs may be active")
        labels = region_labels(model, bc.region, "nodes")
        if not labels:
            return fail("active displacement BC region cannot be resolved")
        if not state_is_unset(getattr(bc_state, "u1State", None)):
            return fail("radial U1 must remain unconstrained")
        if not state_is_unset(getattr(bc_state, "u2State", None)):
            if not close(getattr(bc_state, "u2", None), 0.0):
                return fail("axial U2 constraint must be zero")
            constrained_u2.update(labels)
        for component in ("u3", "ur1", "ur2", "ur3"):
            if not state_is_unset(getattr(bc_state, component + "State", None)):
                return fail("active displacement BC contains an extra constrained component")
    if constrained_u2 != expected_sets["ALLNODES"]:
        return fail("active U2=0 displacement BC coverage must equal ALLNODES")
    if active_objects(model.constraints):
        return fail("additional model constraints are not allowed")

    if step.__class__.__name__ != "StaticStep":
        return fail("Step-Pressure must be a static step")
    if not active_objects(model.fieldOutputRequests):
        return fail("field output request is missing")

    inner_rows = sorted(
        [(label, coords[label][1]) for label in expected_sets["INNER"]],
        key=lambda row: row[1],
    )
    expected_loads = {}
    for index, (label, axial) in enumerate(inner_rows):
        if index == 0:
            delta_z = 0.5 * (inner_rows[1][1] - axial)
        elif index == len(inner_rows) - 1:
            delta_z = 0.5 * (axial - inner_rows[index - 1][1])
        else:
            delta_z = 0.5 * (inner_rows[index + 1][1] - inner_rows[index - 1][1])
        expected_loads[label] = 10.0 * 2.0 * math.pi * 50.0 * delta_z
    loads = active_named_objects(model.loads)
    actual_loads = {}
    for load_name, load in loads:
        if load_name not in step.loadStates.keys():
            continue
        load_state = step.loadStates[load_name]
        if not state_is_active(load_state):
            continue
        if load.__class__.__name__ != "ConcentratedForce":
            return fail("only concentrated nodal forces may be active")
        labels = region_labels(model, load.region, "nodes")
        if not labels or not labels.issubset(set(expected_loads)):
            return fail("concentrated force targets a non-INNER node")
        cf1 = getattr(load_state, "cf1", None)
        cf2 = getattr(load_state, "cf2", None)
        if state_is_unset(getattr(load_state, "cf1State", None)):
            return fail("INNER radial nodal force is unset")
        if not state_is_unset(getattr(load_state, "cf2State", None)) and not close(cf2, 0.0):
            return fail("INNER load contains an axial component")
        for label in labels:
            actual_loads[label] = actual_loads.get(label, 0.0) + float(cf1)
    if set(actual_loads) != set(expected_loads) or any(
        not close(actual_loads[label], expected_loads[label], rel=1.0e-6, abs_tol=1.0e-3)
        for label in expected_loads
    ):
        return fail("aggregated INNER nodal force distribution is incorrect")
    element_labels = set(int(element.label) for element in part.elements)
    if not validate_input_output_request(job, element_labels):
        return False
    connectivity = dict(
        (
            int(element.label),
            (str(element.type).upper(), tuple(int(node.label) for node in element_nodes(part, element))),
        )
        for element in part.elements
    )
    return {
        "model_name": model_name,
        "part": part,
        "coords": coords,
        "element_type": element_type,
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
            return fail("ODB must contain the single analysis step Step-Pressure")
        step = odb.steps[STEP_NAME]
        if len(step.frames) < 2:
            return fail("ODB has no solved final frame")
        frame = step.frames[-1]
        if not math.isfinite(float(frame.frameValue)) or not close(
            frame.frameValue, model_info["step_time"], rel=1.0e-6, abs_tol=1.0e-8
        ):
            return fail("final frame is not the completed static load step")
        if len(odb.rootAssembly.instances.keys()) != 1:
            return fail("ODB must contain one cylinder instance")
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
                (str(element.type).upper(), tuple(int(label) for label in element.connectivity)),
            )
            for element in instance.elements
        )
        if odb_connectivity != model_info["connectivity"]:
            return fail("CAE and ODB element labels, types, or connectivity do not match")

        def odb_named_set(name):
            candidates = []
            for repository in (instance.nodeSets, odb.rootAssembly.nodeSets):
                for key in repository.keys():
                    if str(key).upper() == name.upper():
                        labels = entity_labels(repository[key].nodes)
                        if labels:
                            candidates.append(labels)
            if not candidates or any(labels != candidates[0] for labels in candidates[1:]):
                return None
            return candidates[0]

        for name in REQUIRED_SETS:
            if odb_named_set(name) != model_info["sets"][name]:
                return fail("ODB node set %s does not match the CAE" % name)

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
        for value in frame.fieldOutputs["U"].values:
            if abs(float(value.data[1])) > 1.0e-10:
                return fail("final U2 is nonzero despite the ALLNODES plane-strain BC")

        stress_counts = {}
        mises = []
        inner_s22 = []
        signature = {"U": {}, "RF": {}, "S": {}}
        for name in ("U", "RF"):
            for value in frame.fieldOutputs[name].values:
                signature[name][int(value.nodeLabel)] = tuple(float(item) for item in value.data)
        inner_elements = set()
        inner_labels = model_info["sets"]["INNER"]
        for element in instance.elements:
            if inner_labels.intersection(set(int(label) for label in element.connectivity)):
                inner_elements.add(int(element.label))
        for value in frame.fieldOutputs["S"].values:
            if not str(getattr(value, "position", "")).upper().endswith("INTEGRATION_POINT"):
                continue
            label = int(value.elementLabel)
            stress_counts[label] = stress_counts.get(label, 0) + 1
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
            signature["S"][(label, integration_point)] = components + (invariant,)
            if label in inner_elements:
                inner_s22.append(components[1])
        expected_ip = EXPECTED_IP[model_info["element_type"]]
        if set(stress_counts) != model_info["elements"] or any(count != expected_ip for count in stress_counts.values()):
            return fail("integration-point S output is incomplete or region-restricted")
        if not inner_s22 or not any(1.0 < value < 3.5 for value in inner_s22):
            return fail("inner stress lacks the plane-strain axial stress signature")

        midpoint = [
            label
            for label in inner_labels
            if close(model_info["coords"][label][1], 5.0, rel=1.0e-8, abs_tol=1.0e-8)
        ]
        if len(midpoint) != 1:
            return fail("INNER midpoint node is not unique")
        radial = None
        for value in frame.fieldOutputs["U"].values:
            if int(value.nodeLabel) == midpoint[0]:
                radial = float(value.data[0])
                break
        maximum = max(mises) if mises else None
        if radial is None or maximum is None or not math.isfinite(radial) or not math.isfinite(maximum):
            return fail("native metrics could not be extracted")
        if not (0.0044 < radial < 0.0047 and 18.0 < maximum < 26.0):
            return fail("native Abaqus metrics are outside physical sanity bounds")
        if compare_submitted_metrics:
            if not close(radial, SUBMITTED["radial_displacement"], rel=1.0e-3, abs_tol=5.0e-6):
                return fail("metrics.json radial_displacement does not match ODB")
            if not close(maximum, SUBMITTED["max_mises"], rel=1.0e-3, abs_tol=0.05):
                return fail("metrics.json max_mises does not match ODB integration-point S")
        return {
            "metrics": {"radial_displacement": radial, "max_mises": maximum},
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
                job = database.jobs[JOB_NAME]
                job.submit(consistencyChecking=ON)
                job.waitForCompletion()
                rechecked_result = validate_odb(model_info, JOB_NAME + ".odb", False)
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
        displacements = [try_get(mapdl, "NODE", label, "U", component) for component in ("X", "Y")]
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
    temp_root = Path(tempfile.mkdtemp(prefix="eval_cli_task02_ansys_"))
    mapdl = None
    mapdl_jobname = "eval_cli_task02"
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
        if len(coords) not in (33, 85):
            log("ANSYS node count is not a structured PLANE182/183 5 mm mesh")
            return False
        xs = [row[0] for row in node_rows]
        ys = [row[1] for row in node_rows]
        zs = [row[2] for row in node_rows]
        if not (
            close_enough(min(xs), 50.0, rel=1.0e-8)
            and close_enough(max(xs), 100.0, rel=1.0e-8)
            and close_enough(min(ys), 0.0, rel=1.0e-8)
            and close_enough(max(ys), 10.0, rel=1.0e-8)
            and close_enough(min(zs), 0.0, rel=1.0e-8)
            and close_enough(max(zs), 0.0, rel=1.0e-8)
        ):
            log("ANSYS geometry bounds are incorrect")
            return False
        element_numbers = [int(value) for value in mapdl.mesh.enum]
        if len(element_numbers) != 20:
            log("ANSYS mesh must contain 20 elements")
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
        for element in element_numbers:
            type_id = required_get(mapdl, "ELEM", element, "ATTR", "TYPE")
            material_id = required_get(mapdl, "ELEM", element, "ATTR", "MAT")
            type_ids.add(int(round(type_id)))
            material_ids.add(int(round(material_id)))
        if len(type_ids) != 1 or len(material_ids) != 1:
            log("all cylinder elements must use one element type and one material")
            return False
        type_id = next(iter(type_ids))
        element_code = int(round(required_get(mapdl, "ETYP", type_id, "ATTR", "ENAM")))
        if element_code not in (182, 183):
            log("actual elements are not PLANE182/PLANE183")
            return False
        element_name = "PLANE%d" % element_code
        expected_nodes = 33 if element_code == 182 else 85
        if len(coords) != expected_nodes:
            log("node count does not match the actual ANSYS element order")
            return False
        axisymmetric_keyopt = try_get(mapdl, "ETYP", type_id, "ATTR", "KOP3")
        if axisymmetric_keyopt is None or int(round(axisymmetric_keyopt)) != 1:
            log("actual ANSYS element type is not configured as axisymmetric")
            return False

        nodes_per_element = 4 if element_code == 182 else 8
        boxes = set()
        attached_nodes = set()
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
            rows = [coords[label] for label in connectivity]
            exs = [row[0] for row in rows]
            eys = [row[1] for row in rows]
            box = (round(min(exs), 6), round(max(exs), 6), round(min(eys), 6), round(max(eys), 6))
            if not close_enough(box[1] - box[0], 5.0) or not close_enough(box[3] - box[2], 5.0):
                log("ANSYS element does not span one 5 mm by 5 mm structured cell")
                return False
            boxes.add(box)
        expected_boxes = set(
            (float(50 + 5 * i), float(55 + 5 * i), float(5 * j), float(5 + 5 * j))
            for j in range(2)
            for i in range(10)
        )
        if boxes != expected_boxes or attached_nodes != set(coords):
            log("ANSYS connectivity does not exactly cover the required structured grid")
            return False

        material_id = next(iter(material_ids))
        if not material_matches(mapdl, material_id):
            log("actual ANSYS material is not E=210000, nu=0.3")
            return False

        expected_sets = {
            "ALLNODES": set(coords),
            "INNER": set(label for label, xyz in coords.items() if close_enough(xyz[0], 50.0, rel=1.0e-8)),
            "OUTER": set(label for label, xyz in coords.items() if close_enough(xyz[0], 100.0, rel=1.0e-8)),
            "ZMIN": set(label for label, xyz in coords.items() if close_enough(xyz[1], 0.0, rel=1.0e-8)),
            "ZMAX": set(label for label, xyz in coords.items() if close_enough(xyz[1], 10.0, rel=1.0e-8)),
        }
        for name, expected in expected_sets.items():
            if selected_component_nodes(mapdl, name) != expected:
                log("ANSYS component %s is missing or has incorrect membership" % name)
                return False

        required_run(mapdl, "ALLSEL,ALL")
        constraints = parse_listing_rows(required_run(mapdl, "DLIST,ALL"), ("UX", "UY", "UZ"))
        actual_uy = set(node for node, label, value in constraints if label == "UY" and abs(value) <= 1.0e-12)
        if actual_uy != expected_sets["ALLNODES"]:
            log("ANSYS must constrain UY=0 on ALLNODES")
            return False
        if any(label == "UX" for node, label, value in constraints):
            log("ANSYS contains a forbidden radial UX constraint")
            return False
        if any(label not in ("UY",) or abs(value) > 1.0e-12 for node, label, value in constraints):
            log("ANSYS contains an extra or nonzero displacement constraint")
            return False

        force_rows = parse_listing_rows(required_run(mapdl, "FLIST,ALL"), ("FX", "FY", "FZ"))
        if any(label != "FX" for node, label, value in force_rows):
            log("ANSYS contains a nonradial nodal load")
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
        export_stem = "task02_model_audit"
        required_run(mapdl, "CDWRITE,DB,%s,cdb" % export_stem)
        export_path = temp_root / (export_stem + ".cdb")
        if not is_nonempty(export_path) or not inertia_loads_are_zero(
            export_path.read_text(encoding="utf-8", errors="ignore")
        ):
            log("ANSYS model contains a nonzero translational or rotational inertia load")
            return False
        inner_rows = sorted([(label, coords[label][1]) for label in expected_sets["INNER"]], key=lambda row: row[1])
        expected_forces = {}
        for index, (label, axial) in enumerate(inner_rows):
            if index == 0:
                delta_z = 0.5 * (inner_rows[1][1] - axial)
            elif index == len(inner_rows) - 1:
                delta_z = 0.5 * (axial - inner_rows[index - 1][1])
            else:
                delta_z = 0.5 * (inner_rows[index + 1][1] - inner_rows[index - 1][1])
            expected_forces[label] = 10.0 * 2.0 * math.pi * 50.0 * delta_z
        actual_forces = {}
        for node, label, value in force_rows:
            if node in actual_forces or node not in expected_forces:
                log("ANSYS radial load targets a duplicate or non-INNER node")
                return False
            actual_forces[node] = value
        if set(actual_forces) != set(expected_forces) or any(
            not close_enough(actual_forces[node], expected_forces[node], rel=1.0e-6, abs_tol=1.0e-3)
            for node in expected_forces
        ):
            log("ANSYS INNER nodal force distribution is incorrect")
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
        midpoint = [label for label in expected_sets["INNER"] if close_enough(coords[label][1], 5.0, rel=1.0e-8)]
        if len(midpoint) != 1:
            log("ANSYS INNER midpoint node is not unique")
            return False
        radial = try_get(mapdl, "NODE", midpoint[0], "U", "X")
        axial_values = [try_get(mapdl, "NODE", label, "U", "Y") for label in expected_sets["ALLNODES"]]
        if (
            radial is None
            or not math.isfinite(radial)
            or any(value is None or not math.isfinite(value) or abs(value) > 1.0e-10 for value in axial_values)
        ):
            log("ANSYS displacement solution is missing or violates UY=0")
            return False
        submitted_signature = ansys_nodal_result_signature(mapdl, expected_sets["ALLNODES"])
        if submitted_signature is None:
            log("ANSYS submitted RST contains missing or non-finite nodal U/S data")
            return False
        required_run(mapdl, "ALLSEL,ALL")
        required_run(mapdl, "NSORT,S,EQV,0,1,ALL")
        maximum = try_get(mapdl, "SORT", 0, "MAX")
        axial_stress = try_get(mapdl, "NODE", midpoint[0], "S", "Y")
        if maximum is None or axial_stress is None or not (1.0 < axial_stress < 3.5):
            log("ANSYS stress result lacks the plane-strain signature")
            return False
        if not (0.0044 < radial < 0.0047 and 18.0 < maximum < 26.0):
            log("native ANSYS metrics are outside physical sanity bounds")
            return False
        if not close_enough(radial, submitted_metrics["radial_displacement"], rel=1.0e-3, abs_tol=5.0e-6):
            log("metrics.json radial_displacement does not match RST")
            return False
        if not close_enough(maximum, submitted_metrics["max_mises"], rel=1.0e-3, abs_tol=0.05):
            log("metrics.json max_mises does not match RST")
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
        rechecked_signature = ansys_nodal_result_signature(mapdl, expected_sets["ALLNODES"])
        if not ansys_signatures_match(submitted_signature, rechecked_signature):
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
    root = desktop_dir()
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
