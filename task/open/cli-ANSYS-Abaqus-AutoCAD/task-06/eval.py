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


TASK_ID = "c-open-abaqus-ansys-autocad-task-06-windows"
JOB_NAME = "Job-Thermal"
STEP_NAME = "Step-Thermal"
METRIC_FIELDS = ("midplane_temperature_c", "heat_flux_x_w_per_mm2")
NATIVE_PAYLOAD_SUFFIXES = {
    ".cae", ".odb", ".inp", ".sim", ".fil",
    ".db", ".rst", ".rth", ".cdb",
    ".wbpj", ".wbpz", ".mechdb", ".agdb",
}
ABAQUS_COMMAND = r"C:\SIMULIA\Commands\abaqus.bat"
ANSYS_EXEC = r"C:\Program Files\ANSYS Inc\v261\ansys\bin\winx64\ANSYS261.exe"
POWERSHELL = r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
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
            [path for path in root.iterdir() if path.is_file() and path.suffix.lower() == suffix],
            key=lambda path: path.name.lower(),
        )
    except Exception:
        return []


def finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def close_enough(actual, expected, rel=1.0e-3, abs_tol=1.0e-8):
    try:
        return math.isclose(float(actual), float(expected), rel_tol=rel, abs_tol=abs_tol)
    except Exception:
        return False


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
    if set(data) != set(METRIC_FIELDS) or any(
        not finite_number(data[name]) for name in METRIC_FIELDS
    ):
        log(
            "metrics.json must contain exactly midplane_temperature_c and "
            "heat_flux_x_w_per_mm2 as finite numbers"
        )
        return None
    metrics = {name: float(data[name]) for name in METRIC_FIELDS}
    if not (59.0 < metrics["midplane_temperature_c"] < 61.0):
        log("midplane_temperature_c is outside the Task-06 physical range")
        return None
    if not (0.31 < metrics["heat_flux_x_w_per_mm2"] < 0.33):
        log("heat_flux_x_w_per_mm2 is outside the Task-06 physical range")
        return None
    return metrics


def discover_branch(root):
    caes = files_with_suffix(root, ".cae")
    odbs = files_with_suffix(root, ".odb")
    dbs = files_with_suffix(root, ".db")
    rths = files_with_suffix(root, ".rth")
    try:
        native_payloads = sorted(
            path for path in root.iterdir()
            if path.is_file() and path.suffix.lower() in NATIVE_PAYLOAD_SUFFIXES
        )
    except Exception:
        native_payloads = []
    expected_payloads = set(caes + odbs + dbs + rths)
    if any(path not in expected_payloads for path in native_payloads):
        log("an unsupported or extra native solver payload is present")
        return None
    has_abaqus = bool(caes or odbs)
    has_ansys = bool(dbs or rths)
    if has_abaqus and has_ansys:
        log("deliver exactly one solver branch, not both Abaqus and ANSYS artifacts")
        return None
    if has_abaqus:
        if len(caes) != 1 or len(odbs) != 1 or not is_nonempty(caes[0]) or not is_nonempty(odbs[0]):
            log("Abaqus delivery requires exactly one CAE and one ODB")
            return None
        if caes[0].stem.lower() != odbs[0].stem.lower():
            log("Abaqus model and result stems do not match")
            return None
        return "abaqus", caes[0], odbs[0]
    if has_ansys:
        if len(dbs) != 1 or len(rths) != 1 or not is_nonempty(dbs[0]) or not is_nonempty(rths[0]):
            log("ANSYS delivery requires exactly one DB and one RTH")
            return None
        if dbs[0].stem.lower() != rths[0].stem.lower():
            log("ANSYS model and result stems do not match")
            return None
        return "ansys", dbs[0], rths[0]
    log("no supported native model/result pair found")
    return None


def windows_processes(name_pattern, timeout_seconds=30.0):
    if os.name != "nt":
        return []
    command = (
        "Get-CimInstance Win32_Process | Where-Object { $_.Name -match '%s' } | "
        "Select-Object ProcessId,ParentProcessId,Name,CommandLine,CreationDate | "
        "ConvertTo-Json -Compress" % name_pattern
    )
    completed = subprocess.run(
        [POWERSHELL, "-NoProfile", "-Command", command],
        text=True, capture_output=True, timeout=timeout_seconds, shell=False,
    )
    if completed.returncode != 0:
        raise RuntimeError("process baseline probe failed: " + completed.stderr[-500:])
    if not completed.stdout.strip():
        return []
    payload = json.loads(completed.stdout)
    if isinstance(payload, dict):
        payload = [payload]
    return sorted(
        [
            {
                "pid": int(row["ProcessId"]),
                "parent_pid": int(row.get("ParentProcessId") or 0),
                "name": str(row.get("Name") or ""),
                "command_line": str(row.get("CommandLine") or ""),
                "creation_date": str(row.get("CreationDate") or ""),
            }
            for row in payload
        ],
        key=lambda row: row["pid"],
    )


def terminate_process_tree(pid):
    if os.name == "nt" and pid:
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(pid)],
            text=True, capture_output=True, timeout=10, shell=False,
        )


def restore_process_baseline(before, pattern, markers):
    if os.name != "nt":
        return True
    baseline = {row["pid"]: row for row in before}
    markers = [str(value).lower() for value in markers if value]
    deadline = time.monotonic() + 15.0
    stable_since = None
    last = []
    while time.monotonic() < deadline:
        last = windows_processes(pattern, timeout_seconds=3.0)
        if last == before:
            if stable_since is None:
                stable_since = time.monotonic()
            if time.monotonic() - stable_since >= 2.0:
                return True
            time.sleep(0.2)
            continue
        stable_since = None
        for row in reversed(last):
            if row["pid"] in baseline and baseline[row["pid"]] == row:
                continue
            if any(marker in row["command_line"].lower() for marker in markers):
                terminate_process_tree(row["pid"])
        time.sleep(0.25)
    log("solver process baseline was not restored: %s" % json.dumps(last, sort_keys=True))
    return False


def remove_tree_with_retries(path):
    for _ in range(8):
        try:
            shutil.rmtree(str(path))
        except FileNotFoundError:
            return True
        except Exception:
            time.sleep(0.25)
        if not path.exists():
            return True
    return not path.exists()


def run_abaqus_checker(cae_path, odb_path, submitted_metrics):
    token = uuid.uuid4().hex
    temp_root = Path(tempfile.mkdtemp(prefix="eval_cli_task06_abaqus_%s_" % token))
    checker_path = temp_root / "checker.py"
    result_path = temp_root / "result.json"
    staged_cae = temp_root / "submitted.cae"
    staged_odb = temp_root / "submitted.odb"
    recheck_job_name = "eval_task06_abq_" + token[:12]
    process_pattern = (
        r"^(SMALauncherLE|ABQLauncher|abq2025le|standard|pre|explicit|package|"
        r"mpiexec|hydra_service|hydra_bstrap_proxy|python|pythonw|abq[^.]*)\.exe$"
    )
    try:
        baseline = windows_processes(process_pattern)
        shutil.copy2(str(cae_path), str(staged_cae))
        shutil.copy2(str(odb_path), str(staged_odb))
    except Exception as exc:
        log("Abaqus process baseline/staging failed: %s" % exc)
        remove_tree_with_retries(temp_root)
        return False
    checker_source = r'''
# -*- coding: utf-8 -*-
from __future__ import print_function

import builtins
import json
import math
import os
import traceback

from abaqus import openMdb
from abaqusConstants import ON, SIZE
from caeModules import *
from odbAccess import openOdb

CAE_PATH = __CAE_PATH__
ODB_PATH = __ODB_PATH__
RESULT_PATH = __RESULT_PATH__
SUBMITTED = __SUBMITTED__
RECHECK_JOB_NAME = __RECHECK_JOB_NAME__
JOB_NAME = "Job-Thermal"
STEP_NAME = "Step-Thermal"
DETAILS = []


def fail(message):
    DETAILS.append("Abaqus: " + str(message))
    return None


def close(actual, expected, rel=1.0e-6, absolute=1.0e-8):
    try:
        return math.isclose(float(actual), float(expected), rel_tol=rel, abs_tol=absolute)
    except Exception:
        return False


def ci(value):
    try:
        return str(value).strip().upper()
    except Exception:
        return ""


def active_state(obj):
    text = ci(getattr(obj, "suppressed", ""))
    return text not in ("TRUE", "ON", "1")


def analysis_state_active(state):
    return ci(getattr(state, "status", "")) in ("CREATED", "PROPAGATED", "MODIFIED")


def entity_labels(sequence):
    labels = set()
    try:
        iterator = iter(sequence)
    except Exception:
        return labels
    for item in iterator:
        try:
            nodes = item.getNodes()
            node_labels = entity_labels(nodes)
            if node_labels:
                labels.update(node_labels)
                continue
        except Exception:
            pass
        if hasattr(item, "coordinates") and hasattr(item, "label"):
            try:
                labels.add(int(item.label))
                continue
            except Exception:
                pass
        if isinstance(item, (tuple, list)):
            labels.update(entity_labels(item))
    return labels


def entity_indices(sequence):
    try:
        return set(int(item.index) for item in sequence)
    except Exception:
        return set()


def section_region_cells(part, region):
    try:
        return region.cells
    except Exception:
        pass
    names = []
    try:
        names.append(str(region.name).split(".")[-1])
    except Exception:
        pass
    try:
        names.append(str(region[0]).split(".")[-1])
    except Exception:
        pass
    try:
        for key in part.sets.keys():
            if any(ci(key) == ci(name) for name in names if name):
                return part.sets[key].cells
    except Exception:
        pass
    return None


def element_node_labels(mesh_owner, element):
    try:
        return tuple(int(node.label) for node in element.getNodes())
    except Exception:
        try:
            return tuple(int(mesh_owner.nodes[int(index)].label) for index in element.connectivity)
        except Exception:
            return ()


def region_labels(model, region):
    direct = set()
    for attr in ("nodes", "faces", "edges", "elements"):
        try:
            direct.update(entity_labels(getattr(region, attr)))
        except Exception:
            pass
    if direct:
        return direct
    names = []
    try:
        names.append(str(region.name).split(".")[-1])
    except Exception:
        pass
    try:
        names.append(str(region[0]).split(".")[-1])
    except Exception:
        pass
    candidates = []
    if names:
        for repo in (
            getattr(model.rootAssembly, "sets", {}),
            getattr(model.rootAssembly, "surfaces", {}),
        ):
            try:
                for key in repo.keys():
                    if any(ci(key) == ci(name) for name in names if name):
                        resolved = set()
                        for attr in ("nodes", "faces", "edges", "elements"):
                            try:
                                resolved.update(entity_labels(getattr(repo[key], attr)))
                            except Exception:
                                pass
                        if resolved:
                            candidates.append(resolved)
            except Exception:
                pass
        try:
            for key in model.rootAssembly.instances.keys():
                instance = model.rootAssembly.instances[key]
                for repo in (instance.sets, instance.surfaces):
                    for set_key in repo.keys():
                        if any(ci(set_key) == ci(name) for name in names if name):
                            resolved = set()
                            for attr in ("nodes", "faces", "edges", "elements"):
                                try:
                                    resolved.update(entity_labels(getattr(repo[set_key], attr)))
                                except Exception:
                                    pass
                            if resolved:
                                candidates.append(resolved)
        except Exception:
            pass
    unique = []
    for candidate in candidates:
        if candidate not in unique:
            unique.append(candidate)
    return unique[0] if len(unique) == 1 else set()


def hex_jacobian(points, xi, eta, zeta):
    signs = (
        (-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),
        (-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1),
    )
    columns = []
    for axis in range(3):
        column = []
        for coordinate in range(3):
            total = 0.0
            for point, sign in zip(points, signs):
                sx, sy, sz = sign
                if axis == 0:
                    derivative = 0.125 * sx * (1 + sy * eta) * (1 + sz * zeta)
                elif axis == 1:
                    derivative = 0.125 * sy * (1 + sx * xi) * (1 + sz * zeta)
                else:
                    derivative = 0.125 * sz * (1 + sx * xi) * (1 + sy * eta)
                total += point[coordinate] * derivative
            column.append(total)
        columns.append(column)
    a, b, c = columns
    return (
        a[0]*(b[1]*c[2]-b[2]*c[1])
        - a[1]*(b[0]*c[2]-b[2]*c[0])
        + a[2]*(b[0]*c[1]-b[1]*c[0])
    )


def triangle_area(first, second, third):
    left = tuple(second[index] - first[index] for index in range(3))
    right = tuple(third[index] - first[index] for index in range(3))
    cross = (
        left[1]*right[2] - left[2]*right[1],
        left[2]*right[0] - left[0]*right[2],
        left[0]*right[1] - left[1]*right[0],
    )
    return 0.5 * math.sqrt(builtins.sum(value*value for value in cross))


def validate_hex_mesh(coords, elements, scale):
    face_indices = (
        (0,1,2,3), (4,5,6,7), (0,1,5,4),
        (1,2,6,5), (2,3,7,6), (3,0,4,7),
    )
    edge_indices = (
        (0,1), (1,2), (2,3), (3,0),
        (4,5), (5,6), (6,7), (7,4),
        (0,4), (1,5), (2,6), (3,7),
    )
    attached = set()
    total_volume = 0.0
    root = 1.0 / math.sqrt(3.0)
    faces = {}
    adjacency = dict((label, set()) for label in elements)
    connectivity_signatures = set()
    has_global_target_edge = False
    expected_maxs = (100.0*scale, 50.0*scale, 10.0*scale)
    tolerance = 1.0e-8 * scale
    if any(
        point[axis] < -tolerance or point[axis] > expected_maxs[axis] + tolerance
        for point in coords.values() for axis in range(3)
    ):
        return fail("a mesh node lies outside the required solid block")
    for label, connectivity in elements.items():
        signature = tuple(sorted(connectivity))
        if signature in connectivity_signatures:
            return fail("mesh contains duplicate DC3D8 connectivity")
        connectivity_signatures.add(signature)
        points = [coords[node] for node in connectivity]
        attached.update(connectivity)
        determinants = [
            hex_jacobian(points, x, y, z)
            for x in (-root, root) for y in (-root, root) for z in (-root, root)
        ]
        if min(determinants) <= 1.0e-15 * max(1.0, scale**3):
            return fail("mesh contains a non-positive-Jacobian DC3D8 element")
        total_volume += builtins.sum(determinants)
        for first, second in edge_indices:
            length = math.sqrt(builtins.sum(
                (points[first][axis] - points[second][axis])**2
                for axis in range(3)
            ))
            if length <= 1.0e-12*scale or length > 5.5*scale:
                return fail("mesh edge lengths are incompatible with the 5 mm global target")
            if close(length, 5.0*scale, rel=0.1, absolute=1.0e-10):
                has_global_target_edge = True
        local_faces = set()
        for indices in face_indices:
            key = frozenset(connectivity[index] for index in indices)
            if len(key) != 4 or key in local_faces:
                return fail("mesh contains a degenerate or repeated element face")
            local_faces.add(key)
            faces.setdefault(key, []).append((label, indices))
    plane_areas = dict(((axis, side), 0.0) for axis in range(3) for side in (0, 1))
    for key, owners in faces.items():
        if len(owners) not in (1, 2):
            return fail("a DC3D8 face does not have one or two owners")
        if len(owners) == 2:
            if owners[0][0] == owners[1][0]:
                return fail("an element owns the same face more than once")
            adjacency[owners[0][0]].add(owners[1][0])
            adjacency[owners[1][0]].add(owners[0][0])
            continue
        label, indices = owners[0]
        points = [coords[elements[label][index]] for index in indices]
        plane_matches = [
            (axis, side)
            for axis in range(3) for side, bound in enumerate((0.0, expected_maxs[axis]))
            if all(abs(point[axis] - bound) <= tolerance for point in points)
        ]
        if len(plane_matches) != 1:
            return fail("mesh has an exposed face inside the required solid block")
        area = triangle_area(points[0], points[1], points[2])
        area += triangle_area(points[0], points[2], points[3])
        plane_areas[plane_matches[0]] += area
    visited = set()
    stack = [next(iter(elements))]
    while stack:
        label = stack.pop()
        if label in visited:
            continue
        visited.add(label)
        stack.extend(adjacency[label] - visited)
    expected_plane_areas = {
        (0, 0): 500.0*scale*scale, (0, 1): 500.0*scale*scale,
        (1, 0): 1000.0*scale*scale, (1, 1): 1000.0*scale*scale,
        (2, 0): 5000.0*scale*scale, (2, 1): 5000.0*scale*scale,
    }
    if visited != set(elements):
        return fail("DC3D8 mesh is not one face-connected solid")
    if not has_global_target_edge:
        return fail("mesh has no element edge representing the 5 mm global target")
    if attached != set(coords):
        return fail("mesh contains unattached nodes")
    if not close(total_volume, 50000.0*scale**3, rel=1.0e-7, absolute=1.0e-12):
        return fail("DC3D8 elements do not fill the complete block volume")
    if any(
        not close(plane_areas[key], value, rel=1.0e-7, absolute=1.0e-12)
        for key, value in expected_plane_areas.items()
    ):
        return fail("DC3D8 exterior does not have the complete six block faces")
    return True


ABAQUS_ALLOWED_KEYWORDS = {
    "AMPLITUDE", "ASSEMBLY", "BOUNDARY", "CONDUCTIVITY", "DENSITY", "ELEMENT",
    "ELEMENT OUTPUT", "EL FILE", "EL PRINT", "ELSET", "END ASSEMBLY",
    "END INSTANCE", "END PART", "END STEP", "ENERGY FILE", "ENERGY OUTPUT",
    "FILE FORMAT", "HEADING", "HEAT TRANSFER", "INITIAL CONDITIONS", "INSTANCE",
    "MATERIAL", "NODE", "NODE FILE", "NODE OUTPUT", "NODE PRINT", "NSET",
    "OUTPUT", "PART", "PREPRINT", "RESTART", "SOLID SECTION", "SPECIFIC HEAT",
    "STEP",
}
ABAQUS_PROHIBITED_KEYWORDS = {
    "CFLUX", "CFILM", "CONTACT", "CONTACT PAIR", "COUPLING", "CRADIATE",
    "DECURRENT", "DFLUX", "DISTRIBUTING COUPLING", "DSFLUX", "EMBEDDED ELEMENT",
    "EQUATION", "FILM", "GAP CONDUCTANCE", "INCLUDE", "KINEMATIC COUPLING",
    "MASS FLOW RATE", "MODEL CHANGE", "MPC", "RADIATE", "RIGID BODY", "SFILM",
    "SHELL TO SOLID COUPLING", "SRADIATE", "SURFACE INTERACTION", "TEMPERATURE",
    "TIE",
}
ABAQUS_HEADER_OPTIONS = {
    "AMPLITUDE", "CONTACT", "DELTMX", "ECHO", "ELSET", "FIELD", "FILE",
    "FREQUENCY", "GENERATE", "HISTORY", "INPUT", "INSTANCE", "MATERIAL", "MODEL",
    "NAME", "NLGEOM", "NSET", "OP", "PART", "STEADY STATE", "TYPE", "VARIABLE",
    "WRITE",
}


def canonical_abbreviation(value, choices):
    token = ci(value)
    if token in choices:
        return token
    matches = [choice for choice in choices if choice.startswith(token)]
    return matches[0] if token and len(matches) == 1 else None


def inp_blocks(path):
    blocks = []
    current = None
    with open(path, "r") as stream:
        for raw_line in stream:
            line = raw_line.strip()
            if not line or line.startswith("**"):
                continue
            if line.startswith("*"):
                header = line[1:].strip()
                raw_name = ci(header.split(",", 1)[0])
                name = canonical_abbreviation(
                    raw_name, ABAQUS_ALLOWED_KEYWORDS | ABAQUS_PROHIBITED_KEYWORDS
                )
                if name is None:
                    raise ValueError("unsupported or ambiguous Abaqus keyword: " + raw_name)
                current = {"name": name, "header": header, "data": []}
                blocks.append(current)
            elif current is not None:
                current["data"].append(line)
    return blocks


def header_options(header):
    options = {}
    for item in str(header).split(",")[1:]:
        item = item.strip()
        if not item:
            continue
        if "=" in item:
            key, value = item.split("=", 1)
            canonical = canonical_abbreviation(key, ABAQUS_HEADER_OPTIONS)
            options[canonical or ci(key)] = ci(value)
        else:
            canonical = canonical_abbreviation(item, ABAQUS_HEADER_OPTIONS)
            options[canonical or ci(item)] = True
    return options


def header_has_external_reference(header):
    for item in str(header).split(",")[1:]:
        if "=" not in item:
            continue
        raw_key = ci(item.split("=", 1)[0])
        if raw_key and ("INPUT".startswith(raw_key) or "FILE".startswith(raw_key)):
            return True
    return False


def inp_integer_set(block):
    values = set()
    options = header_options(block["header"])
    try:
        if "GENERATE" in options:
            for row in block["data"]:
                fields = [int(value.strip()) for value in row.split(",") if value.strip()]
                if len(fields) not in (2, 3):
                    return None
                first, last = fields[:2]
                increment = fields[2] if len(fields) == 3 else 1
                if increment <= 0 or last < first:
                    return None
                values.update(range(first, last + 1, increment))
        else:
            for row in block["data"]:
                values.update(int(value.strip()) for value in row.split(",") if value.strip())
    except Exception:
        return None
    return values


def inp_set_entries(block):
    options = header_options(block["header"])
    if "GENERATE" in options:
        values = inp_integer_set(block)
        return None if values is None else set(values), set()
    labels = set()
    references = set()
    for row in block["data"]:
        for raw_value in row.split(","):
            value = raw_value.strip()
            if not value:
                continue
            try:
                labels.add(int(value.split(".")[-1]))
            except Exception:
                references.add(ci(value))
    return labels, references


def resolve_inp_set(name, raw_sets, cache, visiting):
    key = ci(name)
    if key in cache:
        return set(cache[key])
    if key in raw_sets:
        candidates = [key]
    else:
        basename = key.split(".")[-1]
        candidates = [
            candidate for candidate in raw_sets
            if candidate.split(".")[-1] == basename
        ]
    unique = []
    for candidate in candidates:
        if candidate in visiting:
            return None
        visiting.add(candidate)
        labels = set(raw_sets[candidate][0])
        for reference in raw_sets[candidate][1]:
            resolved = resolve_inp_set(reference, raw_sets, cache, visiting)
            if resolved is None:
                visiting.remove(candidate)
                return None
            labels.update(resolved)
        visiting.remove(candidate)
        cache[candidate] = set(labels)
        if labels not in unique:
            unique.append(labels)
    return set(unique[0]) if len(unique) == 1 else None


def inp_element_data(blocks):
    element_nodes = {}
    raw_sets = {}
    current_instance = None
    for block in blocks:
        if block["name"] == "INSTANCE":
            current_instance = header_options(block["header"]).get("NAME")
            continue
        if block["name"] == "END INSTANCE":
            current_instance = None
            continue
        if block["name"] not in ("ELEMENT", "ELSET"):
            continue
        options = header_options(block["header"])
        name = options.get("ELSET")
        instance_name = options.get("INSTANCE") or current_instance
        qualified = ci((instance_name + "." if instance_name else "") + name) if name else None
        if block["name"] == "ELEMENT":
            labels = set()
            for row in block["data"]:
                try:
                    fields = [int(value.strip()) for value in row.split(",") if value.strip()]
                except Exception:
                    return None, None
                if len(fields) < 2:
                    return None, None
                label, connectivity = fields[0], tuple(fields[1:])
                if label in element_nodes and element_nodes[label] != connectivity:
                    return None, None
                element_nodes[label] = connectivity
                labels.add(label)
            if qualified:
                raw_sets.setdefault(qualified, (set(), set()))[0].update(labels)
            continue
        if not qualified:
            return None, None
        entries = inp_set_entries(block)
        if entries is None:
            return None, None
        raw_sets.setdefault(qualified, (set(), set()))[0].update(entries[0])
        raw_sets[qualified][1].update(entries[1])
    cache = {}
    resolved_sets = {}
    basename_values = {}
    for name in raw_sets:
        values = resolve_inp_set(name, raw_sets, cache, set())
        if values is None:
            return None, None
        resolved_sets[name] = values
        basename = name.split(".")[-1]
        basename_values.setdefault(basename, []).append(values)
    for basename, candidates in basename_values.items():
        unique = []
        for values in candidates:
            if values not in unique:
                unique.append(values)
        if len(unique) == 1:
            resolved_sets[basename] = unique[0]
    return resolved_sets, element_nodes


def inp_node_sets(blocks):
    element_sets, element_nodes = inp_element_data(blocks)
    if element_sets is None:
        return None
    raw_sets = {}
    current_instance = None
    for block in blocks:
        if block["name"] == "INSTANCE":
            current_instance = header_options(block["header"]).get("NAME")
            continue
        if block["name"] == "END INSTANCE":
            current_instance = None
            continue
        if block["name"] == "NODE":
            options = header_options(block["header"])
            name = options.get("NSET")
            if not name:
                continue
            instance_name = options.get("INSTANCE") or current_instance
            qualified = ci((instance_name + "." if instance_name else "") + name)
            record = raw_sets.setdefault(qualified, (set(), set()))
            try:
                record[0].update(
                    int(row.split(",", 1)[0].strip()) for row in block["data"]
                )
            except Exception:
                return None
            continue
        if block["name"] != "NSET":
            continue
        options = header_options(block["header"])
        name = options.get("NSET")
        if not name:
            return None
        instance_name = options.get("INSTANCE") or current_instance
        qualified = ci((instance_name + "." if instance_name else "") + name)
        record = raw_sets.setdefault(qualified, (set(), set()))
        source_elset = options.get("ELSET")
        if source_elset:
            candidates = [
                ci(source_elset),
                ci((instance_name + "." if instance_name else "") + source_elset),
            ]
            resolved_elements = None
            for candidate in candidates:
                if candidate in element_sets:
                    resolved_elements = element_sets[candidate]
                    break
            if resolved_elements is None:
                return None
            for element in resolved_elements:
                if element not in element_nodes:
                    return None
                record[0].update(element_nodes[element])
            continue
        entries = inp_set_entries(block)
        if entries is None:
            return None
        record[0].update(entries[0])
        record[1].update(entries[1])
    cache = {}
    sets = {}
    basename_values = {}
    for name in raw_sets:
        values = resolve_inp_set(name, raw_sets, cache, set())
        if values is None:
            return None
        sets[name] = values
        basename = name.split(".")[-1]
        basename_values.setdefault(basename, []).append(values)
    for basename, candidates in basename_values.items():
        unique = []
        for values in candidates:
            if values not in unique:
                unique.append(values)
        if len(unique) == 1:
            sets[basename] = unique[0]
    return sets


def inp_element_sets(blocks):
    sets = {}
    all_elements = set()
    current_instance = None
    for block in blocks:
        if block["name"] == "INSTANCE":
            current_instance = header_options(block["header"]).get("NAME")
            continue
        if block["name"] == "END INSTANCE":
            current_instance = None
            continue
        if block["name"] == "ELEMENT":
            options = header_options(block["header"])
            labels = set()
            try:
                labels = set(int(row.split(",", 1)[0].strip()) for row in block["data"])
            except Exception:
                return None, None
            if not labels:
                return None, None
            all_elements.update(labels)
            name = options.get("ELSET")
            if name:
                instance_name = options.get("INSTANCE") or current_instance
                qualified = ci((instance_name + "." if instance_name else "") + name)
                sets.setdefault(qualified, set()).update(labels)
                sets.setdefault(ci(name), set()).update(labels)
            continue
        if block["name"] != "ELSET":
            continue
        options = header_options(block["header"])
        name = options.get("ELSET")
        if not name:
            return None, None
        values = inp_integer_set(block)
        if values is None:
            return None, None
        instance_name = options.get("INSTANCE") or current_instance
        qualified = ci((instance_name + "." if instance_name else "") + name)
        sets.setdefault(qualified, set()).update(values)
        sets.setdefault(ci(name), set()).update(values)
    return sets, all_elements


def resolve_inp_nodes(target, node_sets, instance_names):
    raw_target = ci(target)
    try:
        pieces = raw_target.rsplit(".", 1)
        label = int(pieces[-1])
        if len(pieces) == 2 and pieces[0] not in instance_names:
            return None
        return {label}
    except Exception:
        pass
    key = raw_target
    if key in node_sets:
        return set(node_sets[key])
    basename = key.split(".")[-1]
    if basename in node_sets:
        return set(node_sets[basename])
    suffix_matches = [values for name, values in node_sets.items() if name.endswith("." + key)]
    unique = []
    for values in suffix_matches:
        if values not in unique:
            unique.append(values)
    return set(unique[0]) if len(unique) == 1 else None


def validate_written_input(path, scale, expected_x0, expected_x1, time_period):
    try:
        blocks = inp_blocks(path)
    except Exception as exc:
        return fail("written Abaqus input cannot be parsed: %s" % exc)
    if not blocks:
        return fail("written Abaqus input is empty")
    present_banned = sorted(
        set(block["name"] for block in blocks) & ABAQUS_PROHIBITED_KEYWORDS
        | set(
            block["name"] for block in blocks
            if header_has_external_reference(block["header"])
        )
    )
    if present_banned:
        return fail("written input contains a prohibited thermal keyword: " + ", ".join(present_banned))
    for block in (row for row in blocks if row["name"] == "INITIAL CONDITIONS"):
        options = header_options(block["header"])
        if ci(options.get("TYPE", "")) != "TEMPERATURE" or not block["data"]:
            return fail("written input contains a non-temperature initial condition")
        for row in block["data"]:
            fields = [value.strip() for value in row.split(",")]
            try:
                if len(fields) < 2 or not fields[0]:
                    raise ValueError("missing initial-temperature target")
                values = [float(value) for value in fields[1:] if value]
            except Exception:
                return fail("written input has an unreadable initial temperature")
            if not values or any(not math.isfinite(value) for value in values):
                return fail("written input has a non-finite initial temperature")
    steps = [index for index, block in enumerate(blocks) if block["name"] == "STEP"]
    ends = [index for index, block in enumerate(blocks) if block["name"] == "END STEP"]
    heat = [index for index, block in enumerate(blocks) if block["name"] == "HEAT TRANSFER"]
    if len(steps) != 1 or len(ends) != 1 or len(heat) != 1 or not (steps[0] < heat[0] < ends[0]):
        return fail("written input must contain exactly one complete heat-transfer step")
    step_options = header_options(blocks[steps[0]]["header"])
    if ci(step_options.get("NAME", "")) != ci(STEP_NAME):
        return fail("written input step is not named Step-Thermal")
    heat_options = header_options(blocks[heat[0]]["header"])
    if "STEADY STATE" not in heat_options:
        return fail("written input heat-transfer procedure is not steady state")
    element_blocks = [block for block in blocks if block["name"] == "ELEMENT"]
    if not element_blocks or any(
        ci(header_options(block["header"]).get("TYPE", "")) != "DC3D8"
        for block in element_blocks
    ):
        return fail("written input contains a non-DC3D8 element definition")
    conductivity = [block for block in blocks if block["name"] == "CONDUCTIVITY"]
    expected_k = 0.4 if scale == 1.0 else 400.0
    if len(conductivity) != 1 or len(conductivity[0]["data"]) != 1:
        return fail("written input must contain one constant conductivity record")
    try:
        conductivity_values = [
            float(value.strip())
            for value in conductivity[0]["data"][0].split(",")
            if value.strip()
        ]
    except Exception:
        conductivity_values = []
    if len(conductivity_values) != 1 or not close(
        conductivity_values[0], expected_k, rel=1.0e-6, absolute=1.0e-10
    ):
        return fail("written input conductivity is not the constant allowed unit-system value")
    solid_sections = [block for block in blocks if block["name"] == "SOLID SECTION"]
    if len(solid_sections) != 1:
        return fail("written input must contain exactly one solid section")
    section_options = header_options(solid_sections[0]["header"])
    if ci(section_options.get("MATERIAL", "")) != "COPPER" or not section_options.get("ELSET"):
        return fail("written input solid section is not the Copper section over an element set")
    # The CAE object model already proves that the one Copper assignment covers
    # every cell.  Do not duplicate that semantic check with a partial INP set
    # parser: Abaqus permits NSET/ELSET composition and NSET ELSET=/SURFACE=
    # forms that are not reducible to integer-only rows.
    boundaries = [
        block for index, block in enumerate(blocks)
        if block["name"] == "BOUNDARY" and index < ends[0]
    ]
    if not boundaries or any(not block["data"] for block in boundaries):
        return fail("written input has no populated temperature boundary records")
    node_sets = inp_node_sets(blocks)
    if node_sets is None:
        return fail("written input node sets cannot be resolved unambiguously")
    instance_names = set(
        header_options(block["header"]).get("NAME")
        for block in blocks if block["name"] == "INSTANCE"
    )
    if None in instance_names or len(instance_names) != 1:
        return fail("written input must contain one unambiguous assembly instance")
    covered_boundary_nodes = set()
    for block in boundaries:
        options = header_options(block["header"])
        if ci(options.get("OP", "MOD")) not in ("MOD", "NEW", ""):
            return fail("written input boundary uses an invalid operation mode")
        for row in block["data"]:
            fields = [value.strip() for value in row.split(",")]
            try:
                if not fields[0]:
                    raise ValueError("missing boundary target")
                labels = resolve_inp_nodes(fields[0], node_sets, instance_names)
                first_dof = int(fields[1])
                last_dof = int(fields[2]) if len(fields) > 2 and fields[2] else first_dof
                magnitude = float(fields[3])
            except Exception:
                return fail("written input has an unreadable temperature boundary record")
            if first_dof != 11 or last_dof != 11 or not math.isfinite(magnitude):
                return fail("written input contains a non-temperature or non-finite boundary record")
            if not labels or not labels.issubset(expected_x0 | expected_x1):
                return fail("written input boundary targets nodes outside the two end planes")
            covered_boundary_nodes.update(labels)
    if covered_boundary_nodes != expected_x0 | expected_x1:
        return fail("written input boundaries do not cover both complete end planes")
    # Exact effective end constraints, including propagation, amplitudes, and
    # OP=NEW semantics, are checked from the CAE final state and then proved by
    # both the submitted ODB and an isolated re-solve below.
    field_outputs = [
        block for index, block in enumerate(blocks)
        if block["name"] == "OUTPUT"
        and "FIELD" in header_options(block["header"])
        and steps[0] < index < ends[0]
    ]
    explicit_output = " ".join(
        block["header"] + " " + " ".join(block["data"])
        for block in blocks[steps[0]:ends[0] + 1]
        if block["name"] in ("OUTPUT", "NODE OUTPUT", "ELEMENT OUTPUT")
    ).upper()
    has_preselect = any(
        header_options(block["header"]).get("VARIABLE") == "PRESELECT"
        for block in blocks[steps[0]:ends[0] + 1]
        if block["name"] in ("OUTPUT", "NODE OUTPUT", "ELEMENT OUTPUT")
    )
    has_explicit = all(name in re.split(r"[^A-Z0-9]+", explicit_output) for name in ("NT", "HFL", "RFL"))
    if not field_outputs or not (has_preselect or has_explicit):
        return fail("written input does not request complete NT/HFL/RFL field output")
    return True


def model_info(database):
    if JOB_NAME not in database.jobs.keys():
        return fail("CAE does not contain the required Job-Thermal job")
    job = database.jobs[JOB_NAME]
    model_name = str(job.model)
    if model_name not in database.models.keys():
        return fail("Job-Thermal does not reference a live CAE model")
    model = database.models[model_name]
    if "Initial" not in model.steps.keys() or STEP_NAME not in model.steps.keys():
        return fail("CAE does not contain Initial and Step-Thermal")
    if list(model.steps.keys())[-1] != STEP_NAME:
        return fail("Step-Thermal is not the final CAE analysis step")
    step = model.steps[STEP_NAME]
    if "HEATTRANSFER" not in ci(step.__class__.__name__) or ci(getattr(step, "response", "")) != "STEADY_STATE":
        return fail("Step-Thermal is not a steady HeatTransferStep")
    if len(model.rootAssembly.instances.keys()) != 1:
        return fail("CAE must contain exactly one active assembly instance")
    instance = model.rootAssembly.instances[model.rootAssembly.instances.keys()[0]]
    part_name = str(getattr(instance, "partName", ""))
    if part_name not in model.parts.keys():
        return fail("the active assembly instance is not backed by a live part")
    part = model.parts[part_name]
    global_coords = dict(
        (int(node.label), tuple(float(x) for x in node.coordinates[:3]))
        for node in instance.nodes
    )
    if not global_coords:
        return fail("the single Abaqus instance has no mesh nodes")
    mins = [min(row[i] for row in global_coords.values()) for i in range(3)]
    maxs = [max(row[i] for row in global_coords.values()) for i in range(3)]
    scale = None
    for candidate in (1.0, 0.001):
        target = (100.0*candidate, 50.0*candidate, 10.0*candidate)
        if all(close(mins[i], 0.0, rel=0.0, absolute=1.0e-8) and close(maxs[i], target[i], rel=1.0e-8, absolute=1.0e-10) for i in range(3)):
            scale = candidate
            break
    if scale is None:
        return fail("assembly bounds are not the required global Cartesian block")
    seed = None
    dependent = ci(getattr(instance, "dependent", "")) in ("ON", "TRUE", "1")
    if dependent:
        try:
            seed = float(part.getPartSeeds(SIZE))
        except Exception:
            pass
    else:
        try:
            seed = float(
                model.rootAssembly.getPartSeeds(regions=(instance,), attribute=SIZE)
            )
        except Exception:
            pass
    elements = {}
    for element in instance.elements:
        if ci(element.type) != "DC3D8":
            return fail("every solid element must be DC3D8")
        connectivity = element_node_labels(instance, element)
        if len(connectivity) != 8 or len(set(connectivity)) != 8:
            return fail("DC3D8 connectivity is incomplete or degenerate")
        elements[int(element.label)] = connectivity
    coords = global_coords
    if validate_hex_mesh(coords, elements, scale) is None:
        return None
    if seed is not None and not close(seed, 5.0*scale, rel=2.0e-3, absolute=1.0e-10):
        return fail("global part or assembly seed is not 5 mm or 0.005 m")
    material_keys = list(model.materials.keys())
    copper_keys = [key for key in material_keys if ci(key) == "COPPER"]
    if len(copper_keys) != 1:
        return fail("the thermal model does not contain one unambiguous Copper material")
    copper_key = copper_keys[0]
    material = model.materials[copper_key]
    try:
        table = material.conductivity.table
        conductivity_values = tuple(float(value) for row in table for value in row)
    except Exception:
        return fail("Copper conductivity is missing")
    expected_k = 0.4 if scale == 1.0 else 400.0
    type_value = ci(getattr(material.conductivity, "type", ""))
    temperature_dependency = getattr(material.conductivity, "temperatureDependency", False)
    dependencies = getattr(material.conductivity, "dependencies", 0)
    if (
        len(conductivity_values) != 1
        or not close(conductivity_values[0], expected_k, rel=1.0e-6, absolute=1.0e-10)
        or (type_value and type_value not in ("ISOTROPIC",))
        or ci(temperature_dependency) in ("TRUE", "ON", "1")
        or int(dependencies or 0) != 0
    ):
        return fail("conductivity and geometry do not form an allowed unit-system pair")
    if len(part.sectionAssignments) != 1:
        return fail("the entire block must have one homogeneous solid section assignment")
    assignment = part.sectionAssignments[0]
    section = model.sections[assignment.sectionName]
    if "HOMOGENEOUSSOLID" not in ci(section.__class__.__name__) or ci(section.material) != ci(copper_key):
        return fail("the assigned section is not a homogeneous Copper solid section")
    assigned_sequence = section_region_cells(part, assignment.region)
    if assigned_sequence is None:
        return fail("the Copper section region cannot be resolved")
    assigned_cells = entity_indices(assigned_sequence)
    all_cells = entity_indices(part.cells)
    if not all_cells or assigned_cells != all_cells:
        return fail("the Copper section does not cover every solid cell")
    expected_x0 = set(label for label, xyz in global_coords.items() if close(xyz[0], 0.0, rel=0.0, absolute=1.0e-8*scale))
    expected_x1 = set(label for label, xyz in global_coords.items() if close(xyz[0], 100.0*scale, rel=0.0, absolute=1.0e-8*scale))
    expected_mid = set(label for label, xyz in global_coords.items() if close(xyz[0], 50.0*scale, rel=0.0, absolute=1.0e-8*scale))
    if not expected_x0 or not expected_x1 or not expected_mid:
        return fail("complete X=0, X=100, or X=50 node planes are missing")
    bcs = []
    for key in model.boundaryConditions.keys():
        if not active_state(model.boundaryConditions[key]):
            continue
        if key not in step.boundaryConditionStates.keys():
            continue
        state = step.boundaryConditionStates[key]
        if analysis_state_active(state):
            bcs.append((model.boundaryConditions[key], state))
    if not bcs:
        return fail("model has no active temperature boundary condition")
    covered_boundary_nodes = set()
    for bc, state in bcs:
        bc_type = ci(bc.__class__.__name__)
        if "TEMPERATUREBC" not in bc_type:
            return fail("an active boundary condition is not a TemperatureBC")
        labels = region_labels(model, bc.region)
        if not labels or not labels.issubset(expected_x0 | expected_x1):
            return fail("an active TemperatureBC covers nodes outside the two end planes")
        try:
            magnitude = float(state.magnitude)
        except Exception as exc:
            return fail(
                "a temperature boundary magnitude cannot be read "
                "(status=%s error=%r)" % (getattr(state, "status", ""), exc)
            )
        if not math.isfinite(magnitude):
            return fail("a temperature boundary magnitude is non-finite")
        covered_boundary_nodes.update(labels)
    if covered_boundary_nodes != expected_x0 | expected_x1:
        return fail("active TemperatureBC regions do not cover both complete end planes")
    # The final ODB and isolated re-solve below prove the effective 100/20 C
    # values.  This deliberately permits split BCs, OP=NEW, propagated BCs,
    # and amplitudes whose final multiplier gives the required steady state.
    state_repositories = {
        "loads": "loadStates",
        "predefinedFields": "predefinedFieldStates",
        "interactions": "interactionStates",
        "constraints": "constraintStates",
    }
    for repo_name, state_name in state_repositories.items():
        repo = getattr(model, repo_name)
        states = getattr(step, state_name, None)
        for key in repo.keys():
            if not active_state(repo[key]):
                continue
            if (
                repo_name == "predefinedFields"
                and "TEMPERATURE" in ci(repo[key].__class__.__name__)
                and ci(getattr(repo[key], "createStepName", "INITIAL")) == "INITIAL"
            ):
                continue
            if states is not None and key in states.keys():
                if analysis_state_active(states[key]):
                    return fail(
                        "model contains an active extra thermal load, field, interaction, or constraint: "
                        + repo_name
                    )
                continue
            return fail(
                "model contains an active extra thermal load, field, interaction, or constraint: "
                + repo_name
            )
    return {
        "model": model,
        "model_name": model_name,
        "instance_name": str(model.rootAssembly.instances.keys()[0]),
        "coords": global_coords,
        "elements": elements,
        "scale": scale,
        "x0": expected_x0,
        "x1": expected_x1,
        "mid": expected_mid,
        "time_period": float(getattr(step, "timePeriod", 0.0)),
    }


def scalar_field(field, expected_labels=None):
    result = {}
    try:
        for value in field.values:
            label = int(value.nodeLabel)
            number = float(value.data)
            if label in result or not math.isfinite(number):
                return None
            result[label] = number
    except Exception:
        return None
    if expected_labels is not None and set(result) != set(expected_labels):
        return None
    return result


def validate_odb(info, odb_path, compare_metrics):
    odb = openOdb(path=odb_path, readOnly=True)
    try:
        status = ci(getattr(odb.diagnosticData, "jobStatus", ""))
        if not status.endswith("COMPLETED_SUCCESSFULLY"):
            return fail("ODB does not report successful completion")
        if STEP_NAME not in odb.steps.keys() or list(odb.steps.keys())[-1] != STEP_NAME:
            return fail("Step-Thermal is not the final ODB analysis step")
        step = odb.steps[STEP_NAME]
        if ci(getattr(step, "procedure", "")) != "*HEAT TRANSFER, STEADY STATE":
            return fail("ODB Step-Thermal was not produced by steady-state heat transfer")
        if len(step.frames) < 2:
            return fail("steady heat-transfer ODB has too few frames")
        frame = step.frames[-1]
        if not close(frame.frameValue, info["time_period"], rel=1.0e-8, absolute=1.0e-12):
            return fail("ODB final frame time does not match the CAE steady step period")
        if len(odb.rootAssembly.instances.keys()) != 1:
            return fail("ODB must contain exactly one instance")
        odb_instance_name = str(odb.rootAssembly.instances.keys()[0])
        if ci(odb_instance_name) != ci(info["instance_name"]):
            return fail("CAE and ODB active instance names differ")
        instance = odb.rootAssembly.instances[odb_instance_name]
        odb_coords = dict((int(node.label), tuple(float(x) for x in node.coordinates[:3])) for node in instance.nodes)
        odb_elements = dict((int(element.label), (ci(element.type), tuple(int(x) for x in element.connectivity))) for element in instance.elements)
        expected_elements = dict((label, ("DC3D8", connectivity)) for label, connectivity in info["elements"].items())
        if set(odb_coords) != set(info["coords"]) or any(any(not close(a, b, rel=1.0e-9, absolute=1.0e-10) for a, b in zip(odb_coords[label], info["coords"][label])) for label in odb_coords):
            return fail("CAE and ODB node labels or coordinates do not match")
        if odb_elements != expected_elements:
            return fail("CAE and ODB element types or ordered connectivity do not match")
        for name in ("NT11", "HFL", "RFL11"):
            if name not in frame.fieldOutputs.keys():
                return fail("ODB is missing complete native field " + name)
        temperatures = scalar_field(frame.fieldOutputs["NT11"], info["coords"])
        if temperatures is None:
            return fail("NT11 does not contain one finite value for every node")
        hfl = {}
        element_coverage = set()
        try:
            for value in frame.fieldOutputs["HFL"].values:
                key = (int(value.elementLabel), int(value.integrationPoint))
                row = tuple(float(component) for component in value.data)
                if key in hfl or len(row) != 3 or any(not math.isfinite(x) for x in row):
                    return fail("HFL contains duplicate, incomplete, or non-finite integration-point data")
                hfl[key] = row
                element_coverage.add(key[0])
        except Exception:
            return fail("HFL cannot be read")
        integration_points = dict((label, set()) for label in info["elements"])
        for label, point in hfl:
            if label in integration_points:
                integration_points[label].add(point)
        if (
            element_coverage != set(info["elements"])
            or any(points != set(range(1, 9)) for points in integration_points.values())
        ):
            return fail("HFL does not cover every DC3D8 integration point")
        reactions = scalar_field(frame.fieldOutputs["RFL11"])
        if reactions is None or not (info["x0"] | info["x1"]).issubset(set(reactions)):
            return fail("RFL11 does not cover every prescribed-temperature node")
        if any(
            label not in info["x0"] | info["x1"] and abs(value) > 1.0e-10
            for label, value in reactions.items()
        ):
            return fail("RFL11 reports a nonzero reaction away from the two end planes")
        scale = info["scale"]
        expected_native_flux = 0.32 / (scale * scale)
        for label, xyz in info["coords"].items():
            expected_temperature = 100.0 - 0.8 * (xyz[0] / scale)
            if not close(temperatures[label], expected_temperature, rel=1.0e-5, absolute=2.0e-3):
                return fail("NT11 is not the required one-dimensional linear temperature field")
        for row in hfl.values():
            if not close(row[0], expected_native_flux, rel=2.0e-4, absolute=max(1.0e-7, expected_native_flux*1.0e-6)):
                return fail("HFL1 is not the required axial heat flux density")
            if abs(row[1]) > max(1.0e-7, expected_native_flux*2.0e-5) or abs(row[2]) > max(1.0e-7, expected_native_flux*2.0e-5):
                return fail("HFL has a non-negligible transverse component")
        x0_reaction = builtins.sum(reactions.get(label, 0.0) for label in info["x0"])
        x1_reaction = builtins.sum(reactions.get(label, 0.0) for label in info["x1"])
        if not close(x0_reaction, 160.0, rel=2.0e-4, absolute=0.02) or not close(x1_reaction, -160.0, rel=2.0e-4, absolute=0.02) or abs(x0_reaction + x1_reaction) > 0.02:
            return fail("RFL11 end-face totals are not +160 W and -160 W in balance")
        mid_temperature = builtins.sum(temperatures[label] for label in info["mid"]) / len(info["mid"])
        field_flux = builtins.sum(row[0] for row in hfl.values()) / len(hfl) * scale * scale
        reaction_flux = x0_reaction / 500.0
        if not close(mid_temperature, 60.0, rel=1.0e-6, absolute=2.0e-3):
            return fail("complete X=50 mid-plane mean temperature is not 60 C")
        if not close(field_flux, reaction_flux, rel=2.0e-4, absolute=2.0e-5):
            return fail("HFL1 and end-face RFL/area heat-flux measures disagree")
        metrics = {
            "midplane_temperature_c": mid_temperature,
            "heat_flux_x_w_per_mm2": reaction_flux,
        }
        if compare_metrics:
            if not close(metrics["midplane_temperature_c"], SUBMITTED["midplane_temperature_c"], rel=1.0e-5, absolute=2.0e-4):
                return fail("metrics.json midplane_temperature_c does not match complete native NT11")
            if not close(metrics["heat_flux_x_w_per_mm2"], SUBMITTED["heat_flux_x_w_per_mm2"], rel=2.0e-4, absolute=2.0e-5):
                return fail("metrics.json heat_flux_x_w_per_mm2 does not match native RFL11/area")
        return {
            "coords": odb_coords,
            "elements": odb_elements,
            "temperatures": temperatures,
            "hfl": hfl,
            "reactions": reactions,
            "metrics": metrics,
        }
    finally:
        odb.close()


def signatures_match(left, right):
    if left is None or right is None:
        return False
    if left["coords"] != right["coords"] or left["elements"] != right["elements"]:
        return False
    for key in ("temperatures", "reactions"):
        if set(left[key]) != set(right[key]):
            return False
        if any(not close(left[key][item], right[key][item], rel=2.0e-5, absolute=1.0e-7) for item in left[key]):
            return False
    if set(left["hfl"]) != set(right["hfl"]):
        return False
    for key in left["hfl"]:
        if any(not close(a, b, rel=2.0e-5, absolute=1.0e-7) for a, b in zip(left["hfl"][key], right["hfl"][key])):
            return False
    return True


def main():
    passed = False
    try:
        database = openMdb(pathName=CAE_PATH)
        info = model_info(database)
        if info is None:
            raise RuntimeError("model validation failed")
        submitted = validate_odb(info, ODB_PATH, True)
        if submitted is None:
            raise RuntimeError("submitted ODB validation failed")
        os.chdir(os.path.dirname(RESULT_PATH))
        source_job = database.jobs[JOB_NAME]
        input_path = os.path.join(os.path.dirname(RESULT_PATH), JOB_NAME + ".inp")
        try:
            if os.path.isfile(input_path):
                os.remove(input_path)
            source_job.writeInput(consistencyChecking=ON)
        except Exception:
            DETAILS.append("Abaqus: isolated CAE writeInput failed")
            raise
        if not os.path.isfile(input_path) or os.path.getsize(input_path) <= 0:
            raise RuntimeError("isolated CAE writeInput did not create an INP")
        if validate_written_input(
            input_path, info["scale"], info["x0"], info["x1"], info["time_period"]
        ) is None:
            raise RuntimeError("written input validation failed")
        if RECHECK_JOB_NAME in database.jobs.keys():
            del database.jobs[RECHECK_JOB_NAME]
        recheck_job = database.Job(name=RECHECK_JOB_NAME, model=source_job.model)
        recheck_job.submit(consistencyChecking=ON)
        recheck_job.waitForCompletion()
        recheck_path = os.path.join(os.path.dirname(RESULT_PATH), RECHECK_JOB_NAME + ".odb")
        if not os.path.isfile(recheck_path) or os.path.getsize(recheck_path) <= 0:
            DETAILS.append("Abaqus: isolated re-solve did not produce an ODB")
        else:
            rechecked = validate_odb(info, recheck_path, False)
            if rechecked is not None and signatures_match(submitted, rechecked):
                passed = True
            else:
                DETAILS.append("Abaqus: submitted ODB fields do not match an isolated CAE re-solve")
    except Exception:
        DETAILS.append(traceback.format_exc())
    with open(RESULT_PATH, "w") as stream:
        json.dump({"passed": passed, "details": DETAILS}, stream, sort_keys=True)


if __name__ == "__main__":
    main()
'''
    checker_source = checker_source.replace("__CAE_PATH__", repr(str(staged_cae)))
    checker_source = checker_source.replace("__ODB_PATH__", repr(str(staged_odb)))
    checker_source = checker_source.replace("__RESULT_PATH__", repr(str(result_path)))
    checker_source = checker_source.replace("__SUBMITTED__", repr(submitted_metrics))
    checker_source = checker_source.replace("__RECHECK_JOB_NAME__", repr(recheck_job_name))
    checker_path.write_text(checker_source, encoding="utf-8")
    semantic_passed = False
    process_ok = False
    temp_ok = False
    launcher_pid = None
    try:
        process = subprocess.Popen(
            [ABAQUS_COMMAND, "cae", "noGUI=" + str(checker_path)],
            cwd=str(temp_root), text=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False,
        )
        launcher_pid = process.pid
        stdout, stderr = process.communicate(timeout=1200)
        log("Abaqus checker returncode=%s" % process.returncode)
        if stdout:
            log("Abaqus stdout tail=" + stdout[-1000:])
        if stderr:
            log("Abaqus stderr tail=" + stderr[-1000:])
        if is_nonempty(result_path):
            payload = json.loads(result_path.read_text(encoding="utf-8"))
            for detail in payload.get("details", []):
                log(detail)
            semantic_passed = bool(payload.get("passed"))
    except Exception as exc:
        log("Abaqus checker failed: %s" % exc)
        if launcher_pid:
            terminate_process_tree(launcher_pid)
    finally:
        try:
            process_ok = restore_process_baseline(
                baseline, process_pattern,
                [recheck_job_name, str(temp_root), checker_path.name],
            )
        except Exception as exc:
            log("Abaqus process cleanup failed: %s" % exc)
        temp_ok = remove_tree_with_retries(temp_root)
        if not temp_ok:
            log("Abaqus evaluator temporary directory cleanup was incomplete")
    return semantic_passed and process_ok and temp_ok


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
        value = float(mapdl.get_value(*args))
        return value if math.isfinite(value) else None
    except Exception:
        return None


def required_get(mapdl, *args):
    value = try_get(mapdl, *args)
    if value is None:
        raise RuntimeError("MAPDL *GET failed for %r" % (args,))
    return value


ANSYS_NUMBER = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[EeDd][-+]?\d+)?"


def ansys_number(value):
    return float(str(value).replace("D", "E").replace("d", "e"))


def parse_constraint_listing(text):
    upper = (text or "").upper()
    if (
        "LIST CONSTRAINTS FOR SELECTED NODES" not in upper
        or "NODE  LABEL" not in upper
        or "REAL" not in upper
        or "IMAG" not in upper
    ):
        return None
    pattern = re.compile(
        r"^\s*(\d+)\s+(\S+)\s+(%s)\s+(%s)\s*$" % (ANSYS_NUMBER, ANSYS_NUMBER),
        re.IGNORECASE,
    )
    rows = []
    for line in (text or "").splitlines():
        if not re.match(r"^\s*\d+", line):
            continue
        match = pattern.fullmatch(line)
        if match is None:
            return None
        rows.append(
            (
                int(match.group(1)), match.group(2).upper(),
                ansys_number(match.group(3)), ansys_number(match.group(4)),
            )
        )
    return rows


def listing_has_no_numbered_rows(text, markers):
    upper = (text or "").upper()
    return any(marker in upper for marker in markers) and not any(
        re.match(r"^\s*\d+", line) for line in (text or "").splitlines()
    )


def read_ansys_rth(result_path):
    from ansys.mapdl import reader as pymapdl_reader

    result = pymapdl_reader.read_binary(str(result_path))
    result_header = result.read_record(103)
    if len(result_header) < 72:
        raise RuntimeError("RTH result header does not contain the v261 analysis-type fields")
    kan = int(result_header[7])
    analysis_type = int(result_header[71])
    if kan != 0 or analysis_type != 0:
        raise RuntimeError("RTH was not produced by a static/steady analysis")
    labels = [int(value) for value in result.mesh.nnum]
    rows = [tuple(float(value) for value in row[:3]) for row in result.mesh.nodes]
    if len(labels) != len(set(labels)) or len(labels) != len(rows):
        raise RuntimeError("RTH contains duplicate or incomplete node labels")
    coords = dict(zip(labels, rows))
    type_codes = dict((int(row[0]), int(row[1])) for row in result.mesh.ekey)
    raw_keyopts = getattr(result, "_element_table", {}).get("keyopts", {})
    type_keyopts = {}
    for type_reference in type_codes:
        values = raw_keyopts.get(type_reference)
        if values is None:
            values = raw_keyopts.get(str(type_reference))
        if values is None or len(values) < 8:
            raise RuntimeError("RTH element KEYOPT metadata is incomplete")
        type_keyopts[type_reference] = tuple(int(value) for value in values)
        if type_keyopts[type_reference][6] != 0 or type_keyopts[type_reference][7] != 0:
            raise RuntimeError("RTH SOLID70 uses a prohibited KEYOPT(7) or KEYOPT(8)")
    elements = {}
    for record in result.mesh.elem:
        type_reference = int(record[1])
        label = int(record[8])
        code = type_codes.get(type_reference)
        if code != 70 or label <= 0:
            raise RuntimeError("RTH contains an unsupported thermal solid element")
        node_count = 8
        connectivity = tuple(int(value) for value in record[10:10 + node_count])
        if len(connectivity) != node_count or any(value <= 0 for value in connectivity):
            raise RuntimeError("RTH thermal connectivity is incomplete")
        if label in elements:
            raise RuntimeError("RTH contains duplicate element labels")
        elements[label] = (code, connectivity)
    time_values = [float(value) for value in result.time_values]
    if (
        int(result.nsets) < 1
        or len(time_values) != int(result.nsets)
        or any(not math.isfinite(value) for value in time_values)
    ):
        raise RuntimeError("RTH has no complete finite result-set index")
    try:
        temperature_labels, temperature_values = result.nodal_temperature(int(result.nsets) - 1)
        if (
            len(temperature_labels) != len(temperature_values)
            or len(temperature_labels) != len(coords)
            or len(set(int(label) for label in temperature_labels)) != len(temperature_labels)
        ):
            raise RuntimeError("RTH native TEMP contains duplicate or incomplete node labels")
        temperature_signature = dict(
            (int(label), float(value))
            for label, value in zip(temperature_labels, temperature_values)
        )
    except Exception as exc:
        raise RuntimeError("RTH native nodal temperature cannot be read: %s" % exc)
    if set(temperature_signature) != set(coords) or any(
        not math.isfinite(value) for value in temperature_signature.values()
    ):
        raise RuntimeError("RTH native TEMP does not cover every node")
    return (
        coords, elements, type_keyopts, int(result.nsets), time_values,
        temperature_signature,
    )


def ansys_hex_jacobian(corners, xi, eta, zeta):
    signs = (
        (-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),
        (-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1),
    )
    columns = []
    for axis in range(3):
        column = []
        for coordinate in range(3):
            total = 0.0
            for point, sign in zip(corners, signs):
                sx, sy, sz = sign
                if axis == 0:
                    derivative = 0.125 * sx * (1 + sy*eta) * (1 + sz*zeta)
                elif axis == 1:
                    derivative = 0.125 * sy * (1 + sx*xi) * (1 + sz*zeta)
                else:
                    derivative = 0.125 * sz * (1 + sx*xi) * (1 + sy*eta)
                total += point[coordinate] * derivative
            column.append(total)
        columns.append(column)
    a, b, c = columns
    return (
        a[0]*(b[1]*c[2]-b[2]*c[1])
        - a[1]*(b[0]*c[2]-b[2]*c[0])
        + a[2]*(b[0]*c[1]-b[1]*c[0])
    )


def ansys_triangle_area(first, second, third):
    left = tuple(second[index] - first[index] for index in range(3))
    right = tuple(third[index] - first[index] for index in range(3))
    cross = (
        left[1]*right[2] - left[2]*right[1],
        left[2]*right[0] - left[0]*right[2],
        left[0]*right[1] - left[1]*right[0],
    )
    return 0.5 * math.sqrt(sum(value*value for value in cross))


def validate_ansys_mesh(coords, elements, scale):
    attached = set()
    total_volume = 0.0
    root = 1.0 / math.sqrt(3.0)
    adjacency = dict((label, set()) for label in elements)
    faces = {}
    connectivity_signatures = set()
    has_global_target_edge = False
    expected_maxs = (100.0*scale, 50.0*scale, 10.0*scale)
    tolerance = 1.0e-8 * scale
    if not coords or not elements or any(
        point[axis] < -tolerance or point[axis] > expected_maxs[axis] + tolerance
        for point in coords.values() for axis in range(3)
    ):
        return False
    face_indices = (
        (0,1,2,3),(4,5,6,7),(0,1,5,4),
        (1,2,6,5),(2,3,7,6),(3,0,4,7),
    )
    edge_indices = (
        (0,1), (1,2), (2,3), (3,0),
        (4,5), (5,6), (6,7), (7,4),
        (0,4), (1,5), (2,6), (3,7),
    )
    for label, (code, connectivity) in elements.items():
        corners = [coords[node] for node in connectivity[:8]]
        if len(set(connectivity)) != len(connectivity):
            return False
        signature = tuple(sorted(connectivity))
        if signature in connectivity_signatures:
            return False
        connectivity_signatures.add(signature)
        attached.update(connectivity)
        determinants = [
            ansys_hex_jacobian(corners, x, y, z)
            for x in (-root, root) for y in (-root, root) for z in (-root, root)
        ]
        if min(determinants) <= 1.0e-15 * max(1.0, scale**3):
            return False
        total_volume += sum(determinants)
        for first, second in edge_indices:
            length = math.sqrt(sum(
                (corners[first][axis] - corners[second][axis])**2
                for axis in range(3)
            ))
            if length <= 1.0e-12*scale or length > 5.5*scale:
                return False
            if close_enough(length, 5.0*scale, rel=0.1, abs_tol=1.0e-10):
                has_global_target_edge = True
        for indices in face_indices:
            key = frozenset(connectivity[index] for index in indices)
            if len(key) != 4:
                return False
            faces.setdefault(key, []).append(label)
    plane_areas = dict(((axis, side), 0.0) for axis in range(3) for side in (0, 1))
    for key, owners in faces.items():
        if len(owners) not in (1, 2):
            return False
        if len(owners) == 2:
            adjacency[owners[0]].add(owners[1])
            adjacency[owners[1]].add(owners[0])
            continue
        label = owners[0]
        connectivity = elements[label][1]
        indices = next(
            values for values in face_indices
            if frozenset(connectivity[index] for index in values) == key
        )
        points = [coords[connectivity[index]] for index in indices]
        plane_matches = [
            (axis, side)
            for axis in range(3) for side, bound in enumerate((0.0, expected_maxs[axis]))
            if all(abs(point[axis] - bound) <= tolerance for point in points)
        ]
        if len(plane_matches) != 1:
            return False
        area = ansys_triangle_area(points[0], points[1], points[2])
        area += ansys_triangle_area(points[0], points[2], points[3])
        plane_areas[plane_matches[0]] += area
    visited = set()
    stack = [next(iter(elements))]
    while stack:
        label = stack.pop()
        if label in visited:
            continue
        visited.add(label)
        stack.extend(adjacency[label] - visited)
    expected_plane_areas = {
        (0, 0): 500.0*scale*scale, (0, 1): 500.0*scale*scale,
        (1, 0): 1000.0*scale*scale, (1, 1): 1000.0*scale*scale,
        (2, 0): 5000.0*scale*scale, (2, 1): 5000.0*scale*scale,
    }
    has_midplane_node = any(
        close_enough(point[0], 50.0*scale, rel=0.0, abs_tol=tolerance)
        for point in coords.values()
    )
    return (
        attached == set(coords)
        and visited == set(elements)
        and has_global_target_edge
        and has_midplane_node
        and close_enough(total_volume, 50000.0*scale**3, rel=1.0e-7, abs_tol=1.0e-12)
        and all(
            close_enough(plane_areas[key], value, rel=1.0e-7, abs_tol=1.0e-12)
            for key, value in expected_plane_areas.items()
        )
    )


def ansys_export_material_is_constant_thermal(export_text, material_id, expected_k):
    temperatures = {}
    properties = {}
    for raw in (export_text or "").splitlines():
        line = raw.split("!", 1)[0].strip()
        if not line:
            continue
        fields = [field.strip() for field in line.split(",")]
        command = fields[0].upper()
        if command == "MPTEMP":
            try:
                start = int(float(fields[2]))
                count = int(float(fields[3]))
                values = [ansys_number(token) for token in fields[4:] if token]
            except Exception:
                return False
            if start < 1 or count < 1 or len(values) != count or any(
                not math.isfinite(value) for value in values
            ):
                return False
            temperatures = dict((start + offset, value) for offset, value in enumerate(values))
            continue
        if command == "MPDATA":
            try:
                row_material = int(float(fields[2]))
                label = fields[3].upper()
                start = int(float(fields[4]))
                count = int(float(fields[5]))
                values = [ansys_number(token) for token in fields[6:] if token]
            except Exception:
                return False
            if row_material != int(material_id):
                continue
            if label.startswith("K") and label not in ("KXX", "KYY", "KZZ"):
                return False
            if label not in ("KXX", "KYY", "KZZ"):
                continue
            if start < 1 or count < 1 or len(values) != count or any(
                not math.isfinite(value) for value in values
            ):
                return False
            samples = properties.setdefault(label, [])
            for offset, value in enumerate(values):
                slot = start + offset
                if slot not in temperatures:
                    return False
                samples.append((temperatures[slot], value))
            continue
        if command == "MP":
            try:
                label = fields[1].upper()
                row_material = int(float(fields[2]))
                value = ansys_number(fields[3])
            except Exception:
                return False
            if row_material != int(material_id):
                continue
            if label.startswith("K") and label not in ("KXX", "KYY", "KZZ"):
                return False
            if label in ("KXX", "KYY", "KZZ"):
                properties.setdefault(label, []).append((0.0, value))
    if set(properties) != {"KXX", "KYY", "KZZ"}:
        return False
    for samples in properties.values():
        if not samples or any(
            not close_enough(value, expected_k, rel=1.0e-6, abs_tol=1.0e-10)
            for temperature, value in samples
        ):
            return False
    return True


def ansys_field_signature(mapdl, coords, elements, scale, expected_sets):
    temperatures = {}
    for label in sorted(coords):
        value = try_get(mapdl, "NODE", label, "TEMP")
        if value is None:
            return None
        temperatures[label] = value
    required_run(mapdl, "ALLSEL,ALL")
    required_run(mapdl, "RSYS,0")
    required_run(mapdl, "ETABLE,ERAS")
    for name, component in (("TFLX", "X"), ("TFLY", "Y"), ("TFLZ", "Z")):
        required_run(mapdl, "ETABLE,%s,TF,%s" % (name, component))
    fluxes = {}
    for label in sorted(elements):
        row = tuple(try_get(mapdl, "ELEM", label, "ETAB", name) for name in ("TFLX", "TFLY", "TFLZ"))
        if any(value is None for value in row):
            return None
        fluxes[label] = row
    reactions = {}
    for label in sorted(expected_sets["X0"] | expected_sets["X1"]):
        value = try_get(mapdl, "NODE", label, "RF", "HEAT")
        if value is None:
            return None
        reactions[label] = value
    expected_native_flux = 0.32 / (scale*scale)
    for label, xyz in coords.items():
        target = 100.0 - 0.8*(xyz[0]/scale)
        if not close_enough(temperatures[label], target, rel=1.0e-5, abs_tol=2.0e-3):
            return None
    for row in fluxes.values():
        if not close_enough(row[0], expected_native_flux, rel=2.0e-4, abs_tol=max(1.0e-7, expected_native_flux*1.0e-6)):
            return None
        if abs(row[1]) > max(1.0e-7, expected_native_flux*2.0e-5) or abs(row[2]) > max(1.0e-7, expected_native_flux*2.0e-5):
            return None
    x0_reaction = sum(reactions[label] for label in expected_sets["X0"])
    x1_reaction = sum(reactions[label] for label in expected_sets["X1"])
    if (
        not close_enough(x0_reaction, 160.0, rel=2.0e-4, abs_tol=0.02)
        or not close_enough(x1_reaction, -160.0, rel=2.0e-4, abs_tol=0.02)
        or abs(x0_reaction+x1_reaction) > 0.02
    ):
        return None
    mid_temperature = sum(temperatures[label] for label in expected_sets["MID"]) / len(expected_sets["MID"])
    field_flux = sum(row[0] for row in fluxes.values()) / len(fluxes) * scale*scale
    reaction_flux = x0_reaction / 500.0
    if not close_enough(field_flux, reaction_flux, rel=2.0e-4, abs_tol=2.0e-5):
        return None
    return {
        "temperatures": temperatures,
        "fluxes": fluxes,
        "reactions": reactions,
        "metrics": {
            "midplane_temperature_c": mid_temperature,
            "heat_flux_x_w_per_mm2": reaction_flux,
        },
    }


def ansys_signatures_match(left, right):
    if left is None or right is None:
        return False
    for key in ("temperatures", "fluxes", "reactions"):
        if set(left[key]) != set(right[key]):
            return False
        for label in left[key]:
            left_values = left[key][label]
            right_values = right[key][label]
            if not isinstance(left_values, tuple):
                left_values, right_values = (left_values,), (right_values,)
            if any(not close_enough(a, b, rel=2.0e-5, abs_tol=1.0e-7) for a, b in zip(left_values, right_values)):
                return False
    return True


def ansys_solver_processes():
    pattern = r"^(ANSYS|ANSYS261|mpiexec|hydra_service|hydra_bstrap_proxy|hydra_pmi_proxy)\.exe$"
    try:
        return windows_processes(pattern)
    except Exception:
        return None


def cleanup_ansys_job_processes(jobname, baseline):
    if baseline is None:
        return False
    pattern = r"^(ANSYS|ANSYS261|mpiexec|hydra_service|hydra_bstrap_proxy|hydra_pmi_proxy)\.exe$"
    marker = str(jobname).lower()
    baseline_by_identity = {
        (row["pid"], row["creation_date"], row["name"], row["command_line"]): row
        for row in baseline
    }
    current = windows_processes(pattern)
    targeted = [
        row for row in current
        if (
            row["pid"], row["creation_date"], row["name"], row["command_line"]
        ) not in baseline_by_identity
        and marker in row["command_line"].lower()
    ]
    for row in reversed(targeted):
        terminate_process_tree(row["pid"])
    deadline = time.monotonic() + 20.0
    stable_since = None
    while time.monotonic() < deadline:
        current = windows_processes(pattern)
        if current == baseline:
            if stable_since is None:
                stable_since = time.monotonic()
            if time.monotonic() - stable_since >= 2.0:
                return True
        else:
            stable_since = None
            for row in reversed(current):
                identity = (
                    row["pid"], row["creation_date"], row["name"], row["command_line"]
                )
                if identity not in baseline_by_identity and marker in row["command_line"].lower():
                    terminate_process_tree(row["pid"])
        time.sleep(0.25)
    log("ANSYS solver process baseline was not restored")
    return False


def run_ansys_checker(model_path, result_path, submitted_metrics):
    token = uuid.uuid4().hex
    temp_root = Path(tempfile.mkdtemp(prefix="eval_cli_task06_ansys_%s_" % token))
    jobname = "eval_task06_" + token[:16]
    baseline = ansys_solver_processes()
    staged_model = temp_root / "submitted.db"
    staged_result = temp_root / "submitted.rth"
    mapdl = None
    semantic_passed = False
    process_ok = False
    temp_ok = False
    try:
        from ansys.mapdl.core import launch_mapdl

        if baseline is None:
            log("ANSYS evaluator could not establish a process baseline")
            return False
        shutil.copy2(str(model_path), str(staged_model))
        shutil.copy2(str(result_path), str(staged_result))
        (
            rth_coords, rth_elements, rth_keyopts, rth_set_count, rth_times,
            rth_temperatures,
        ) = read_ansys_rth(staged_result)
        mapdl = launch_mapdl(
            exec_file=ANSYS_EXEC, jobname=jobname, run_location=str(temp_root),
            nproc=1, override=True, cleanup_on_exit=True, start_timeout=180,
        )
        mapdl.resume(str(staged_model.with_suffix("")), "db")
        required_run(mapdl, "FINISH")
        required_run(mapdl, "/PREP7")
        required_run(mapdl, "ALLSEL,ALL")
        required_run(mapdl, "CSYS,0")
        required_run(mapdl, "DSYS,0")
        coords = dict(
            (int(label), tuple(float(value) for value in row[:3]))
            for label, row in zip(mapdl.mesh.nnum, mapdl.mesh.nodes)
        )
        scale = None
        mins = [min(row[i] for row in coords.values()) for i in range(3)]
        maxs = [max(row[i] for row in coords.values()) for i in range(3)]
        for candidate in (1.0, 0.001):
            target = (100.0*candidate, 50.0*candidate, 10.0*candidate)
            if all(close_enough(mins[i], 0.0, rel=0.0, abs_tol=1.0e-9) and close_enough(maxs[i], target[i], rel=1.0e-8, abs_tol=1.0e-10) for i in range(3)):
                scale = candidate
                break
        if scale is None:
            log("ANSYS DB bounds are not the required block")
            return False
        element_numbers = [int(value) for value in mapdl.mesh.enum]
        elements = {}
        material_ids = set()
        type_ids = set()
        for element in element_numbers:
            if required_get(mapdl, "ELEM", element, "ATTR", "LIVE") != 1.0:
                log("ANSYS mesh contains a killed or inactive element")
                return False
            type_id = int(round(required_get(mapdl, "ELEM", element, "ATTR", "TYPE")))
            material_id = int(round(required_get(mapdl, "ELEM", element, "ATTR", "MAT")))
            code = int(round(required_get(mapdl, "ETYP", type_id, "ATTR", "ENAM")))
            if code != 70:
                log("ANSYS actual element is not first-order SOLID70")
                return False
            node_count = 8
            connectivity = tuple(int(round(required_get(mapdl, "ELEM", element, "NODE", position))) for position in range(1, node_count+1))
            if any(label not in coords for label in connectivity):
                log("ANSYS element references a missing node")
                return False
            elements[element] = (code, connectivity)
            material_ids.add(material_id)
            type_ids.add(type_id)
        db_keyopts = {}
        for type_id in type_ids:
            keyopt7 = required_get(mapdl, "ETYP", type_id, "ATTR", "KOP7")
            keyopt8 = required_get(mapdl, "ETYP", type_id, "ATTR", "KOP8")
            db_keyopts[type_id] = (int(round(keyopt7)), int(round(keyopt8)))
            if int(round(keyopt7)) != 0 or int(round(keyopt8)) != 0:
                log("ANSYS SOLID70 uses a prohibited fluid-flow or mass-transport KEYOPT")
                return False
        if not validate_ansys_mesh(coords, elements, scale):
            log("ANSYS mesh is not one complete legal 5 mm thermal-solid mesh")
            return False
        if set(coords) != set(rth_coords) or elements != rth_elements:
            log("ANSYS DB and submitted RTH mesh labels/types/connectivity differ")
            return False
        if set(db_keyopts) != set(rth_keyopts) or any(
            db_keyopts[type_id] != tuple(rth_keyopts[type_id][6:8])
            for type_id in db_keyopts
        ):
            log("ANSYS DB and submitted RTH KEYOPT(7/8) metadata differ")
            return False
        if any(any(not close_enough(a, b, rel=1.0e-9, abs_tol=1.0e-10) for a, b in zip(coords[label], rth_coords[label])) for label in coords):
            log("ANSYS DB and RTH node coordinates differ")
            return False
        expected_k = 0.4 if scale == 1.0 else 400.0
        for material_id in material_ids:
            values = [
                try_get(mapdl, label, material_id, "TEMP", temperature)
                for label in ("KXX", "KYY", "KZZ")
                for temperature in (20.0, 40.0, 60.0, 80.0, 100.0)
            ]
            if any(value is None or not close_enough(value, expected_k, rel=1.0e-6, abs_tol=1.0e-10) for value in values):
                log("ANSYS material conductivity and geometry unit branch do not match")
                return False
        export_stem = "task06_model_audit_" + token[:8]
        required_run(mapdl, "CDWRITE,DB,%s,cdb" % export_stem)
        export_path = temp_root / (export_stem + ".cdb")
        export_text = (
            export_path.read_text(encoding="utf-8", errors="ignore")
            if is_nonempty(export_path) else ""
        )
        if not export_text or any(
            not ansys_export_material_is_constant_thermal(
                export_text, material_id, expected_k
            )
            for material_id in material_ids
        ):
            log("ANSYS CDB does not contain only constant isotropic conductivity")
            return False
        expected_sets = {
            "X0": set(label for label, xyz in coords.items() if close_enough(xyz[0], 0.0, rel=0.0, abs_tol=1.0e-8*scale)),
            "X1": set(label for label, xyz in coords.items() if close_enough(xyz[0], 100.0*scale, rel=0.0, abs_tol=1.0e-8*scale)),
            "MID": set(label for label, xyz in coords.items() if close_enough(xyz[0], 50.0*scale, rel=0.0, abs_tol=1.0e-8*scale)),
        }
        constraints = parse_constraint_listing(required_run(mapdl, "DLIST,ALL"))
        if constraints is None:
            log("ANSYS DLIST output cannot be parsed")
            return False
        actual = {}
        for node, label, real, imag in constraints:
            if label != "TEMP" or abs(imag) > 1.0e-12 or node in actual:
                log("ANSYS has a duplicate, complex, or non-temperature constraint")
                return False
            actual[node] = real
        expected = dict((label, 100.0) for label in expected_sets["X0"])
        expected.update((label, 20.0) for label in expected_sets["X1"])
        if set(actual) != set(expected) or any(not close_enough(actual[label], expected[label], rel=1.0e-8, abs_tol=1.0e-8) for label in expected):
            log("ANSYS temperature constraints are not exactly full X=0 at 100 C and full X=100 at 20 C")
            return False
        no_load_commands = (
            ("FLIST,ALL", ("NO NODAL FORCES TO LIST",)),
            ("BFLIST,ALL", ("NO NODAL BODY FORCES TO LIST",)),
            ("BFELIST,ALL", ("NO ELEMENT BODY FORCES TO LIST",)),
            ("SFLIST,ALL", ("NO SURFACE LOADS TO LIST", "NO NODAL SURFACE LOADS TO LIST")),
            ("SFELIST,ALL", ("NO SURFACE LOADS TO LIST", "NO ELEMENT SURFACE LOADS TO LIST")),
            ("SFALIST,ALL", ("NO SURFACE LOADS ON AREAS TO LIST", "NO SURFACE LOADS TO LIST")),
        )
        for command, markers in no_load_commands:
            if not listing_has_no_numbered_rows(required_run(mapdl, command), markers):
                log("ANSYS model contains an extra load or initial-condition category: " + command)
                return False
        cp_listing = required_run(mapdl, "CPLIST,ALL").upper()
        ce_listing = required_run(mapdl, "CELIST,ALL").upper()
        if (
            "NO COUPLED SETS TO LIST" not in cp_listing
            or "NO CONSTRAINT EQUATIONS TO LIST" not in ce_listing
        ):
            log("ANSYS model contains coupled DOFs or constraint equations")
            return False
        required_run(mapdl, "FINISH")
        required_run(mapdl, "/SOLU")
        status = required_run(mapdl, "/STATUS,SOLU").upper()
        if "STATIC" not in status or "TRANSIENT" in status:
            log("ANSYS saved solution state is not steady/static thermal")
            return False
        required_run(mapdl, "FINISH")
        # Drop the resumed solved DB before reading the submitted result.  This
        # makes TEMP, TF, and RF,HEAT provenance fail closed on the RTH itself.
        required_run(mapdl, "/CLEAR,NOSTART")
        required_run(mapdl, "/POST1")
        mapdl.file(str(staged_result.with_suffix("")), "rth")
        mapdl.set("LAST")
        submitted = ansys_field_signature(mapdl, coords, elements, scale, expected_sets)
        if submitted is None:
            log("ANSYS submitted RTH lacks the required complete TEMP/TF/RF-HEAT fields")
            return False
        if any(not close_enough(submitted["temperatures"][label], rth_temperatures[label], rel=1.0e-8, abs_tol=1.0e-8) for label in coords):
            log("PyMAPDL and binary RTH temperature fields disagree")
            return False
        for name in METRIC_FIELDS:
            if not close_enough(submitted["metrics"][name], submitted_metrics[name], rel=2.0e-4, abs_tol=2.0e-5):
                log("metrics.json %s does not match the native RTH" % name)
                return False
        required_run(mapdl, "FINISH")
        mapdl.resume(str(staged_model.with_suffix("")), "db")
        required_run(mapdl, "/FILNAME,%s,1" % jobname)
        required_run(mapdl, "/SOLU")
        required_run(mapdl, "ALLSEL,ALL")
        required_run(mapdl, "SOLVE")
        required_run(mapdl, "FINISH")
        rechecked_path = temp_root / (jobname + ".rth")
        if not is_nonempty(rechecked_path):
            log("ANSYS isolated DB re-solve did not create an RTH")
            return False
        (
            re_coords, re_elements, re_keyopts, re_count, re_times,
            re_temperatures,
        ) = read_ansys_rth(rechecked_path)
        if (
            re_coords != rth_coords
            or re_elements != rth_elements
            or re_keyopts != rth_keyopts
        ):
            log("ANSYS isolated re-solve mesh differs from submitted RTH")
            return False
        required_run(mapdl, "/CLEAR,NOSTART")
        required_run(mapdl, "/POST1")
        mapdl.file(str(rechecked_path.with_suffix("")), "rth")
        mapdl.set("LAST")
        rechecked = ansys_field_signature(mapdl, coords, elements, scale, expected_sets)
        if not ansys_signatures_match(submitted, rechecked):
            log("ANSYS submitted RTH fields do not match an isolated DB re-solve")
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
        try:
            process_ok = cleanup_ansys_job_processes(jobname, baseline)
        except Exception as exc:
            log("ANSYS evaluator process cleanup failed: %s" % exc)
        temp_ok = remove_tree_with_retries(temp_root)
        if not temp_ok:
            log("ANSYS evaluator temporary directory cleanup was incomplete")
    return semantic_passed and process_ok and temp_ok


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
        log("evaluating Abaqus 2025 native thermal branch")
        return run_abaqus_checker(branch[1], branch[2], metrics), root
    log("evaluating ANSYS MAPDL 2026 R1 native thermal branch")
    return run_ansys_checker(branch[1], branch[2], metrics), root


def main():
    passed = False
    root = desktop_dir()
    try:
        passed, root = evaluate()
    except Exception as exc:
        log("unhandled evaluator failure: %s" % exc)
        passed = False
    try:
        (root / "eval_detail.txt").write_text("\n".join(DETAILS) + "\n", encoding="utf-8")
        (root / "eval_result.txt").write_text("True\n" if passed else "False\n", encoding="utf-8")
    except Exception:
        pass
    sys.stdout.write("True\n" if passed else "False\n")


if __name__ == "__main__":
    main()
