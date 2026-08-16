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


TASK_ID = "c-open-abaqus-ansys-autocad-task-05-windows"
JOB_NAME = "Job-BlockTension"
STEP_NAME = "Step-Load"
METRIC_FIELDS = ("end_displacement", "max_stress")
TRACTION_MPA = 800.0 / (12.0 * 8.0)
NATIVE_PAYLOAD_SUFFIXES = {
    ".cae", ".odb", ".inp", ".sim", ".fil",
    ".db", ".rst", ".cdb", ".rth",
    ".wbpj", ".wbpz", ".mechdb", ".agdb",
}
ABAQUS_COMMAND = r"C:\SIMULIA\Commands\abaqus.bat"
ANSYS_EXEC = r"C:\Program Files\ANSYS Inc\v261\ansys\bin\winx64\ANSYS261.exe"
POWERSHELL = r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
ABAQUS_PROCESS_PATTERN = (
    r"^(SMALauncherLE|ABQLauncher|abq2025le|standard|pre|explicit|package|"
    r"mpiexec|hydra_service|hydra_bstrap_proxy|python|pythonw|abq[^.]*)\.exe$"
)
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
        log("metrics.json must contain exactly end_displacement and max_stress as finite numbers")
        return None
    metrics = {name: float(data[name]) for name in METRIC_FIELDS}
    if not (0.010 < metrics["end_displacement"] < 0.020):
        log("end_displacement is outside the task-specific physical range")
        return None
    if not (7.5 < metrics["max_stress"] < 16.0):
        log("max_stress is outside the task-specific physical range")
        return None
    return metrics


def discover_branch(root):
    caes = files_with_suffix(root, ".cae")
    odbs = files_with_suffix(root, ".odb")
    dbs = files_with_suffix(root, ".db")
    rsts = files_with_suffix(root, ".rst")
    try:
        native_payloads = sorted(
            path for path in root.iterdir()
            if path.is_file() and path.suffix.lower() in NATIVE_PAYLOAD_SUFFIXES
        )
    except Exception:
        native_payloads = []
    expected_payloads = set(caes + odbs + dbs + rsts)
    if any(path not in expected_payloads for path in native_payloads):
        log("an unsupported or extra native solver payload is present")
        return None
    has_abaqus = bool(caes or odbs)
    has_ansys = bool(dbs or rsts)
    if has_abaqus and has_ansys:
        log("deliver exactly one solver branch, not both Abaqus and ANSYS artifacts")
        return None
    if has_abaqus:
        expected_cae = [path for path in caes if path.name.lower() == "job-blocktension.cae"]
        expected_odb = [path for path in odbs if path.name.lower() == "job-blocktension.odb"]
        if (
            len(caes) != 1
            or len(odbs) != 1
            or len(expected_cae) != 1
            or len(expected_odb) != 1
            or not is_nonempty(expected_cae[0])
            or not is_nonempty(expected_odb[0])
        ):
            log("Abaqus delivery requires exactly Job-BlockTension.cae and Job-BlockTension.odb")
            return None
        return "abaqus", expected_cae[0], expected_odb[0]
    if has_ansys:
        expected_db = [path for path in dbs if path.name.lower() == "job-blocktension.db"]
        expected_rst = [path for path in rsts if path.name.lower() == "job-blocktension.rst"]
        if (
            len(dbs) != 1
            or len(rsts) != 1
            or len(expected_db) != 1
            or len(expected_rst) != 1
            or not is_nonempty(expected_db[0])
            or not is_nonempty(expected_rst[0])
        ):
            log("ANSYS delivery requires exactly Job-BlockTension.db and Job-BlockTension.rst")
            return None
        return "ansys", expected_db[0], expected_rst[0]
    log("no supported native model/result pair found")
    return None


def close_enough(actual, expected, rel=1.0e-3, abs_tol=1.0e-8):
    try:
        return math.isclose(float(actual), float(expected), rel_tol=rel, abs_tol=abs_tol)
    except Exception:
        return False


def windows_abaqus_processes(timeout_seconds=30.0):
    if os.name != "nt":
        return []
    command = (
        "Get-CimInstance Win32_Process | Where-Object { $_.Name -match '%s' } | "
        "Select-Object ProcessId,ParentProcessId,Name,CommandLine,CreationDate | "
        "ConvertTo-Json -Compress" % ABAQUS_PROCESS_PATTERN
    )
    completed = subprocess.run(
        [POWERSHELL, "-NoProfile", "-Command", command],
        text=True,
        capture_output=True,
        timeout=max(0.1, float(timeout_seconds)),
        shell=False,
    )
    if completed.returncode != 0:
        raise RuntimeError("Abaqus process baseline probe failed: " + completed.stderr[-500:])
    text = completed.stdout.strip()
    if not text:
        return []
    payload = json.loads(text)
    if isinstance(payload, dict):
        payload = [payload]
    return sorted(
        (
            {
                "pid": int(row["ProcessId"]),
                "parent_pid": int(row.get("ParentProcessId") or 0),
                "name": str(row.get("Name") or ""),
                "command_line": str(row.get("CommandLine") or ""),
                "creation_date": str(row.get("CreationDate") or ""),
            }
            for row in payload
        ),
        key=lambda row: row["pid"],
    )


def terminate_windows_process_tree(pid, timeout_seconds=30.0):
    if os.name != "nt" or not pid:
        return
    subprocess.run(
        ["taskkill", "/F", "/T", "/PID", str(pid)],
        text=True,
        capture_output=True,
        timeout=max(0.1, float(timeout_seconds)),
        shell=False,
    )


def restore_abaqus_process_baseline(before, launcher_pid, markers):
    if os.name != "nt":
        return True
    baseline = {row["pid"]: row for row in before}
    marker_values = [str(value).lower() for value in markers if value]
    started = time.monotonic()
    deadline = started + 12.0
    termination_not_before = started + 3.0
    stable_since = None
    termination_attempted = set()
    last_current = []
    while time.monotonic() < deadline:
        remaining = deadline - time.monotonic()
        if remaining <= 0.0:
            break
        current = windows_abaqus_processes(timeout_seconds=min(2.0, remaining))
        last_current = current
        if current == before:
            if stable_since is None:
                stable_since = time.monotonic()
            if time.monotonic() - stable_since >= 3.0:
                return True
            time.sleep(min(0.25, max(0.0, deadline - time.monotonic())))
            continue
        stable_since = None
        new_rows = [
            row
            for row in current
            if row["pid"] not in baseline or row != baseline[row["pid"]]
        ]
        by_parent = {}
        for row in new_rows:
            by_parent.setdefault(row["parent_pid"], []).append(row)
        owned_pids = set(
            row["pid"]
            for row in new_rows
            if any(marker in row["command_line"].lower() for marker in marker_values)
            and (not launcher_pid or row["parent_pid"] == int(launcher_pid))
        )
        owned_pids.update(
            row["pid"]
            for row in new_rows
            if any(marker in row["command_line"].lower() for marker in marker_values)
        )
        changed = True
        while changed:
            changed = False
            for parent, children in by_parent.items():
                if parent in owned_pids:
                    for child in children:
                        if child["pid"] not in owned_pids:
                            owned_pids.add(child["pid"])
                            changed = True
        targeted = [
            row
            for row in new_rows
            if row["pid"] in owned_pids
            or any(marker in row["command_line"].lower() for marker in marker_values)
        ]
        if targeted and time.monotonic() >= termination_not_before:
            for row in sorted(targeted, key=lambda item: item["pid"], reverse=True):
                identity = (row["pid"], row["creation_date"], row["command_line"])
                if identity in termination_attempted:
                    continue
                remaining = deadline - time.monotonic()
                if remaining <= 0.0:
                    break
                terminate_windows_process_tree(
                    row["pid"], timeout_seconds=min(2.0, remaining)
                )
                termination_attempted.add(identity)
        time.sleep(min(0.25, max(0.0, deadline - time.monotonic())))
    remaining = deadline - time.monotonic()
    if remaining <= 0.0:
        final_current = last_current
    else:
        final_current = windows_abaqus_processes(timeout_seconds=min(2.0, remaining))
    current_by_pid = {row["pid"]: row for row in final_current}
    missing = [
        row for row in before
        if row["pid"] not in current_by_pid or current_by_pid[row["pid"]] != row
    ]
    unexpected = [
        row for row in final_current
        if row["pid"] not in baseline or baseline[row["pid"]] != row
    ]
    log(
        "Abaqus process baseline diff missing=%s unexpected=%s last_probe=%s"
        % (
            json.dumps(missing, sort_keys=True),
            json.dumps(unexpected, sort_keys=True),
            json.dumps(last_current, sort_keys=True),
        )
    )
    return False


def run_abaqus_checker(cae_path, odb_path, submitted_metrics):
    temp_root = Path(tempfile.mkdtemp(prefix="eval_cli_task05_abaqus_%s_" % uuid.uuid4().hex))
    checker_path = temp_root / "checker.py"
    result_path = temp_root / "result.json"
    recheck_job_name = "eval_task05_abq_" + uuid.uuid4().hex[:12]
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
JOB_NAME = "Job-BlockTension"
STEP_NAME = "Step-Load"
TRACTION_MPA = 800.0 / (12.0 * 8.0)
ALLOWED_TYPES = ("C3D8R", "C3D8")
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
    job,
    expected_elements,
    expected_fixed_nodes,
    expected_free_nodes,
    connectivity,
    global_coords,
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
    current_part = None
    current_assembly = None
    current_instance = None
    current_card = None
    steps = []
    cards = []
    instance_parts = {}
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
            current_card = {
                "keyword": keyword,
                "params": params,
                "data": [],
                "step": current_step,
                "part": current_part,
                "assembly": current_assembly,
                "instance": current_instance,
            }
            if keyword == "PART":
                current_part = str(params.get("NAME", "")).upper()
                current_card["part"] = current_part
            elif keyword == "END PART":
                current_card["part"] = current_part
                current_part = None
            elif keyword == "ASSEMBLY":
                current_assembly = str(params.get("NAME", "")).upper()
                current_card["assembly"] = current_assembly
            elif keyword == "END ASSEMBLY":
                current_card["assembly"] = current_assembly
                current_assembly = None
            elif keyword == "INSTANCE":
                current_instance = str(params.get("NAME", "")).upper()
                current_card["instance"] = current_instance
                part_name = str(params.get("PART", "")).upper()
                if not current_instance or not part_name or current_instance in instance_parts:
                    return fail("CAE-generated input contains an unreadable or duplicate instance")
                instance_parts[current_instance] = part_name
            elif keyword == "END INSTANCE":
                current_card["instance"] = current_instance
                current_instance = None
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

    def owner_key(card):
        if card.get("instance"):
            return ("INSTANCE", str(card["instance"]).upper())
        if card.get("part"):
            return ("PART", str(card["part"]).upper())
        if card.get("assembly"):
            return ("ASSEMBLY", str(card["assembly"]).upper())
        return ("MODEL", "")
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
        values = repository.setdefault(owner_key(card) + (set_name,), [])
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

    def qualified_set_key(name, card):
        tokens = str(name).upper().split(".")
        set_name = tokens[-1]
        if len(tokens) == 2:
            owner = tokens[0]
            if owner in instance_parts:
                return ("PART", instance_parts[owner], set_name)
            return ("INSTANCE", owner, set_name)
        return owner_key(card) + (set_name,)

    def resolve_elset(name, card, stack):
        key = qualified_set_key(name, card)
        if key not in elsets or key in stack:
            return set()
        result = set()
        for value in elsets[key]:
            if isinstance(value, int):
                result.add(value)
            else:
                result.update(resolve_elset(value, card, stack | set((key,))))
        return result

    def resolve_nset(name, card, stack):
        key = qualified_set_key(name, card)
        if key not in nsets or key in stack:
            return set()
        result = set()
        for value in nsets[key]:
            if isinstance(value, int):
                result.add(value)
            else:
                result.update(resolve_nset(value, card, stack | set((key,))))
        return result

    aluminum_coverage = set()
    other_coverage = set()
    section_cards = []
    for card in cards:
        if card["keyword"] != "SOLID SECTION":
            continue
        labels = resolve_elset(card["params"].get("ELSET", ""), card, set())
        if card["params"].get("MATERIAL", "").upper() == "ALUMINUM":
            aluminum_coverage.update(labels)
        else:
            other_coverage.update(labels)
        section_cards.append(card)
    if aluminum_coverage != expected_elements or other_coverage.intersection(expected_elements):
        return fail("CAE-generated input does not assign an Aluminum solid section to every block element")
    if not section_cards:
        return fail("CAE-generated input contains no solid-section assignment")

    static_cards = [card for card in cards if card["step"] == STEP_NAME and card["keyword"] == "STATIC"]
    if len(static_cards) != 1:
        return fail("Step-Load must contain exactly one static procedure")
    final_boundaries = {}
    boundary_cards = [card for card in cards if card["keyword"] == "BOUNDARY"]
    if not boundary_cards:
        return fail("CAE-generated input contains no displacement boundary records")
    for card in boundary_cards:
        boundary_type = str(card["params"].get("TYPE", "DISPLACEMENT")).upper()
        if boundary_type not in ("DISPLACEMENT", ""):
            return fail("CAE-generated input contains a non-displacement boundary type")
        operation = str(card["params"].get("OP", "MOD")).upper()
        if operation not in ("MOD", "NEW"):
            return fail("CAE-generated input contains an unsupported boundary operation")
        if operation == "NEW":
            final_boundaries.clear()
        for row in card["data"]:
            fields = [value.strip() for value in row.split(",")]
            if len(fields) < 2 or not fields[0]:
                return fail("CAE-generated input contains an unreadable boundary row")
            try:
                direct_label = int(fields[0])
            except Exception:
                direct_label = None
            labels = (
                set((direct_label,))
                if direct_label is not None
                else resolve_nset(fields[0], card, set())
            )
            if not labels or any(label not in global_coords for label in labels):
                return fail("CAE-generated input boundary target cannot be resolved")
            if fields[1].upper() != "ENCASTRE":
                return fail("CAE-generated boundary is not native Encastre semantics")
            if len([value for value in fields[2:] if value]) != 0:
                return fail("CAE-generated Encastre row contains extra data")
            dofs = (1, 2, 3)
            value = 0.0
            for label in labels:
                for dof in dofs:
                    final_boundaries[(label, dof)] = value
    expected_boundaries = set(
        (label, dof) for label in expected_fixed_nodes for dof in (1, 2, 3)
    )
    if set(final_boundaries) != expected_boundaries or any(
        abs(value) > 1.0e-12 for value in final_boundaries.values()
    ):
        return fail("CAE-generated final boundary signature is not exactly X=0 U1/U2/U3 zero")

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
            labels = resolve_elset(fields[0], card, set())
            if not labels:
                return fail("CAE-generated input element surface references an empty ELSET")
            rows.append((labels, fields[1].upper()))
        surfaces.setdefault(owner_key(card) + (name,), []).extend(rows)

    corner_face_indices = {
        "C3D4": {"S1": (0, 1, 2), "S2": (0, 3, 1), "S3": (1, 3, 2), "S4": (2, 3, 0)},
        "C3D6": {"S1": (0, 1, 2), "S2": (3, 5, 4), "S3": (0, 3, 4, 1), "S4": (1, 4, 5, 2), "S5": (2, 5, 3, 0)},
        "C3D8": {"S1": (0, 1, 2, 3), "S2": (4, 7, 6, 5), "S3": (0, 4, 5, 1), "S4": (1, 5, 6, 2), "S5": (2, 6, 7, 3), "S6": (3, 7, 4, 0)},
    }

    def element_family(element_type):
        if element_type.startswith(("C3D4", "C3D10")):
            return "C3D4"
        if element_type.startswith(("C3D6", "C3D15")):
            return "C3D6"
        if element_type.startswith(("C3D8", "C3D20")):
            return "C3D8"
        return None

    expected_facets = set()
    for label, (element_type, nodes) in connectivity.items():
        family = element_family(element_type)
        for side, indices in corner_face_indices.get(family, {}).items():
            if any(index >= len(nodes) for index in indices):
                return fail("CAE-generated element connectivity is incomplete")
            face_nodes = [nodes[index] for index in indices]
            if all(
                node in global_coords and close(global_coords[node][0], 120.0)
                for node in face_nodes
            ):
                expected_facets.add((label, side))
    if not expected_facets:
        return fail("CAE-generated input has no exterior facets on the global X=120 face")

    def expand_surface_facets(rows):
        result = set()
        for labels, side in rows:
            for label in labels:
                element_type, nodes = connectivity.get(label, ("", ()))
                family = element_family(element_type)
                indices = corner_face_indices.get(family, {}).get(side)
                if not indices or any(index >= len(nodes) for index in indices):
                    return None
                facet = (label, side)
                if facet in result:
                    return None
                result.add(facet)
        return result

    load_records = [
        (card, row)
        for card in cards
        if card["step"] == STEP_NAME and card["keyword"] == "DSLOAD"
        for row in card["data"]
    ]
    if not load_records:
        return fail("CAE-generated input contains no surface load row")

    def normalize_vector(vector):
        length = math.sqrt(builtins.sum(value * value for value in vector))
        if length <= 1.0e-14:
            return None
        return tuple(value / length for value in vector)

    def cross_product(left, right):
        return (
            left[1] * right[2] - left[2] * right[1],
            left[2] * right[0] - left[0] * right[2],
            left[0] * right[1] - left[1] * right[0],
        )

    def subtract_vector(left, right):
        return tuple(left[index] - right[index] for index in range(3))

    def rotate_vector(vector, axis, degrees):
        radians = math.radians(degrees)
        cosine = math.cos(radians)
        sine = math.sin(radians)
        cross = cross_product(axis, vector)
        projection = builtins.sum(axis[index] * vector[index] for index in range(3))
        return tuple(
            vector[index] * cosine
            + cross[index] * sine
            + axis[index] * projection * (1.0 - cosine)
            for index in range(3)
        )

    orientation_cards = {}
    for card in cards:
        if card["keyword"] != "ORIENTATION":
            continue
        name = str(card["params"].get("NAME", "")).upper()
        if name:
            orientation_cards.setdefault(name, []).append(card)

    def orientation_basis(name):
        matches = orientation_cards.get(str(name).upper(), [])
        if len(matches) != 1:
            return None
        card = matches[0]
        system = str(card["params"].get("SYSTEM", "RECTANGULAR")).upper()
        definition = str(card["params"].get("DEFINITION", "COORDINATES")).upper()
        if definition != "COORDINATES" or "DISTRIBUTION" in card["params"]:
            return None
        if system not in ("RECTANGULAR", "Z RECTANGULAR", "CYLINDRICAL"):
            return None
        if not card["data"] or len(card["data"]) > 2:
            return None
        try:
            values = [float(value.strip()) for value in card["data"][0].split(",") if value.strip()]
        except Exception:
            return None
        if len(values) not in (6, 9):
            return None
        first = tuple(values[:3])
        second = tuple(values[3:6])
        origin = tuple(values[6:9]) if len(values) == 9 else (0.0, 0.0, 0.0)
        if system == "CYLINDRICAL":
            axis = normalize_vector(subtract_vector(second, first))
            if axis is None or len(card["data"]) == 2:
                return None
            return (None, None, axis)
        if system == "RECTANGULAR":
            first_axis = normalize_vector(subtract_vector(first, origin))
            in_plane = subtract_vector(second, origin)
            if first_axis is None:
                return None
            third_axis = normalize_vector(cross_product(first_axis, in_plane))
            if third_axis is None:
                return None
            second_axis = normalize_vector(cross_product(third_axis, first_axis))
            basis = (first_axis, second_axis, third_axis)
        else:
            third_axis = normalize_vector(subtract_vector(first, origin))
            in_plane = subtract_vector(second, origin)
            if third_axis is None:
                return None
            second_axis = normalize_vector(cross_product(third_axis, in_plane))
            if second_axis is None:
                return None
            first_axis = normalize_vector(cross_product(second_axis, third_axis))
            basis = (first_axis, second_axis, third_axis)
        if len(card["data"]) == 2:
            try:
                rotation = [float(value.strip()) for value in card["data"][1].split(",") if value.strip()]
            except Exception:
                return None
            if len(rotation) not in (1, 2):
                return None
            rotation_axis = int(rotation[0]) if rotation else 1
            degrees = rotation[1] if len(rotation) == 2 else 0.0
            if rotation_axis not in (1, 2, 3):
                return None
            axis = basis[rotation_axis - 1]
            basis = tuple(
                vector if index == rotation_axis - 1 else rotate_vector(vector, axis, degrees)
                for index, vector in enumerate(basis)
            )
        return basis

    def global_traction_direction(card, direction):
        orientation_name = card["params"].get("ORIENTATION")
        if not orientation_name:
            return normalize_vector(direction)
        basis = orientation_basis(orientation_name)
        if basis is None:
            return None
        if any(vector is None and abs(direction[index]) > 1.0e-12 for index, vector in enumerate(basis)):
            return None
        global_direction = tuple(
            builtins.sum(
                direction[axis] * basis[axis][component]
                for axis in range(3)
                if basis[axis] is not None
            )
            for component in range(3)
        )
        return normalize_vector(global_direction)

    loaded_facets = set()
    load_kind = None
    for load_card, load_row in load_records:
        fields = [value.strip() for value in load_row.split(",")]
        surface_name = fields[0].upper() if fields else ""
        if "." in surface_name:
            instance_name, leaf_name = surface_name.split(".", 1)
            surface_key = ("PART", instance_parts.get(instance_name, ""), leaf_name)
        else:
            surface_key = owner_key(load_card) + (surface_name,)
        surface_rows = surfaces.get(surface_key, [])
        row_facets = expand_surface_facets(surface_rows) if surface_rows else None
        if not row_facets or loaded_facets.intersection(row_facets):
            return fail("CAE-generated surface load contains an unreadable or duplicate element facet")
        loaded_facets.update(row_facets)
        try:
            row_kind = fields[1].upper()
            magnitude = float(fields[2])
        except Exception:
            return fail("Step-Load surface-load data is unreadable")
        if load_kind is None:
            load_kind = row_kind
        elif row_kind != load_kind:
            return fail("Step-Load mixes incompatible surface-load types")
        if row_kind == "TRVEC":
            if len(fields) < 6:
                return fail("GENERAL traction data is incomplete")
            try:
                direction = tuple(float(fields[index]) for index in (3, 4, 5))
            except Exception:
                return fail("GENERAL traction direction is unreadable")
            direction = global_traction_direction(load_card, direction)
            if direction is None or not close(magnitude, TRACTION_MPA, rel=1.0e-6, abs_tol=1.0e-5) or not all(
                close(a, b, rel=1.0e-6, abs_tol=1.0e-8)
                for a, b in zip(direction, (1.0, 0.0, 0.0))
            ):
                return fail("Step-Load GENERAL traction is not the required uniform global +X load")
        elif row_kind == "P":
            if not close(magnitude, -TRACTION_MPA, rel=1.0e-6, abs_tol=1.0e-5):
                return fail("Step-Load pressure is not the required outward-tension value")
        else:
            return fail("Step-Load surface load is neither GENERAL traction nor pressure")
    if loaded_facets != expected_facets:
        return fail("CAE-generated surface load does not cover exactly every global X=120 element facet")

    aluminum_material_cards = [
        (index, card)
        for index, card in enumerate(cards)
        if card["keyword"] == "MATERIAL"
        and str(card["params"].get("NAME", "")).upper() == "ALUMINUM"
    ]
    if len(aluminum_material_cards) != 1:
        return fail("CAE-generated input must define exactly one Aluminum material")
    material_index = aluminum_material_cards[0][0]
    material_properties = []
    material_terminators = set((
        "MATERIAL", "BOUNDARY", "STEP", "PART", "ASSEMBLY", "INSTANCE",
        "SOLID SECTION", "NODE", "ELEMENT", "NSET", "ELSET", "SURFACE",
    ))
    for card in cards[material_index + 1:]:
        if card["keyword"] in material_terminators:
            break
        material_properties.append(card)
    elastic_cards = [card for card in material_properties if card["keyword"] == "ELASTIC"]
    if len(elastic_cards) != 1 or any(
        card["keyword"] not in ("ELASTIC", "DENSITY") for card in material_properties
    ):
        return fail("Aluminum material must contain one isotropic linear-elastic definition and no extra active constitutive behavior")
    elastic_card = elastic_cards[0]
    elastic_type = str(elastic_card["params"].get("TYPE", "ISOTROPIC")).upper()
    if elastic_type not in ("ISOTROPIC", "ISO") or any(
        key in elastic_card["params"] for key in ("DEPENDENCIES", "MODULI", "TYPE")
        if key != "TYPE"
    ):
        return fail("Aluminum elastic definition must be constant isotropic E and nu")
    if len(elastic_card["data"]) != 1:
        return fail("Aluminum elastic definition must contain one constant data row")
    try:
        elastic_values = [float(value.strip()) for value in elastic_card["data"][0].split(",") if value.strip()]
    except Exception:
        elastic_values = []
    if len(elastic_values) != 2 or not close(elastic_values[0], 70000.0) or not close(elastic_values[1], 0.33):
        return fail("Aluminum input-deck elastic constants are not exactly E=70000 and nu=0.33")

    forbidden = set((
        "CLOAD", "DLOAD", "DSFLUX", "DFLUX", "FILM", "RADIATE", "TEMPERATURE",
        "INITIAL CONDITIONS", "EQUATION", "MPC", "COUPLING", "KINEMATIC COUPLING",
        "DISTRIBUTING COUPLING", "RIGID BODY", "TIE", "MASS", "ROTARY INERTIA",
        "CONNECTOR LOAD", "MODEL CHANGE", "DYNAMIC", "FREQUENCY", "BUCKLE",
        "HEAT TRANSFER", "VISCO", "SOILS", "COUPLED TEMPERATURE-DISPLACEMENT",
        "INCLUDE", "INPUT",
    ))
    for card in cards:
        if card["keyword"] in forbidden:
            return fail("CAE-generated input contains an additional load, constraint, or procedure: " + card["keyword"])
        if card["keyword"] == "DSLOAD" and card["step"] != STEP_NAME:
            return fail("CAE-generated input contains a surface load outside Step-Load")

    node_variables = set()
    element_variables = set()
    field_preselect = False
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
        elif (
            card["keyword"] == "OUTPUT"
            and "FIELD" in card["params"]
            and str(card["params"].get("VARIABLE", "")).upper() == "PRESELECT"
        ):
            field_preselect = True
    if not field_preselect and (
        not set(("U", "RF")).issubset(node_variables) or "S" not in element_variables
    ):
        return fail("CAE field output must request nodal U/RF and element S, directly or by PRESELECT")
    return True


def element_nodes(part, element):
    try:
        return list(element.getNodes())
    except Exception:
        result = []
        for index in element.connectivity:
            result.append(part.nodes[int(index)])
        return result


def vector_between(left, right):
    return tuple(float(right[index]) - float(left[index]) for index in range(3))


def determinant3(first, second, third):
    cross = (
        second[1] * third[2] - second[2] * third[1],
        second[2] * third[0] - second[0] * third[2],
        second[0] * third[1] - second[1] * third[0],
    )
    return builtins.sum(first[index] * cross[index] for index in range(3))


def element_family_spec(element_type):
    upper = str(element_type).upper()
    tet_faces = (
        ((0, 1, 2), (0, 1, 2)),
        ((0, 3, 1), (0, 3, 1)),
        ((1, 3, 2), (1, 3, 2)),
        ((2, 3, 0), (2, 3, 0)),
    )
    tet_edges = ((0, 1), (1, 2), (2, 0), (0, 3), (1, 3), (2, 3))
    if upper.startswith("C3D10"):
        return {
            "family": "TET", "node_count": 10, "corner_count": 4,
            "edges": tuple((edge[0], edge[1], 4 + index) for index, edge in enumerate(tet_edges)),
            "faces": (
                ((0, 1, 2), (0, 1, 2, 4, 5, 6)),
                ((0, 3, 1), (0, 3, 1, 7, 8, 4)),
                ((1, 3, 2), (1, 3, 2, 8, 9, 5)),
                ((2, 3, 0), (2, 3, 0, 9, 7, 6)),
            ),
        }
    if upper.startswith("C3D4"):
        return {
            "family": "TET", "node_count": 4, "corner_count": 4,
            "edges": tuple((edge[0], edge[1], None) for edge in tet_edges),
            "faces": tet_faces,
        }
    wedge_edges = (
        (0, 1), (1, 2), (2, 0), (3, 4), (4, 5), (5, 3),
        (0, 3), (1, 4), (2, 5),
    )
    if upper.startswith("C3D15"):
        return {
            "family": "WEDGE", "node_count": 15, "corner_count": 6,
            "edges": tuple((edge[0], edge[1], 6 + index) for index, edge in enumerate(wedge_edges)),
            "faces": (
                ((0, 1, 2), (0, 1, 2, 6, 7, 8)),
                ((3, 5, 4), (3, 5, 4, 11, 10, 9)),
                ((0, 3, 4, 1), (0, 3, 4, 1, 12, 9, 13, 6)),
                ((1, 4, 5, 2), (1, 4, 5, 2, 13, 10, 14, 7)),
                ((2, 5, 3, 0), (2, 5, 3, 0, 14, 11, 12, 8)),
            ),
        }
    if upper.startswith("C3D6"):
        return {
            "family": "WEDGE", "node_count": 6, "corner_count": 6,
            "edges": tuple((edge[0], edge[1], None) for edge in wedge_edges),
            "faces": (
                ((0, 1, 2), (0, 1, 2)), ((3, 5, 4), (3, 5, 4)),
                ((0, 3, 4, 1), (0, 3, 4, 1)),
                ((1, 4, 5, 2), (1, 4, 5, 2)),
                ((2, 5, 3, 0), (2, 5, 3, 0)),
            ),
        }
    hex_edges = (
        (0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6),
        (6, 7), (7, 4), (0, 4), (1, 5), (2, 6), (3, 7),
    )
    if upper.startswith("C3D20"):
        return {
            "family": "HEX", "node_count": 20, "corner_count": 8,
            "edges": tuple((edge[0], edge[1], 8 + index) for index, edge in enumerate(hex_edges)),
            "faces": (
                ((0, 1, 2, 3), (0, 1, 2, 3, 8, 9, 10, 11)),
                ((4, 7, 6, 5), (4, 7, 6, 5, 15, 14, 13, 12)),
                ((0, 4, 5, 1), (0, 4, 5, 1, 16, 12, 17, 8)),
                ((1, 5, 6, 2), (1, 5, 6, 2, 17, 13, 18, 9)),
                ((2, 6, 7, 3), (2, 6, 7, 3, 18, 14, 19, 10)),
                ((3, 7, 4, 0), (3, 7, 4, 0, 19, 15, 16, 11)),
            ),
        }
    if upper.startswith("C3D8"):
        return {
            "family": "HEX", "node_count": 8, "corner_count": 8,
            "edges": tuple((edge[0], edge[1], None) for edge in hex_edges),
            "faces": (
                ((0, 1, 2, 3), (0, 1, 2, 3)), ((4, 7, 6, 5), (4, 7, 6, 5)),
                ((0, 4, 5, 1), (0, 4, 5, 1)), ((1, 5, 6, 2), (1, 5, 6, 2)),
                ((2, 6, 7, 3), (2, 6, 7, 3)), ((3, 7, 4, 0), (3, 7, 4, 0)),
            ),
        }
    return None


def linear_element_jacobian(family, corners, first, second, third):
    if family == "HEX":
        signs = (
            (-1.0, -1.0, -1.0), (1.0, -1.0, -1.0),
            (1.0, 1.0, -1.0), (-1.0, 1.0, -1.0),
            (-1.0, -1.0, 1.0), (1.0, -1.0, 1.0),
            (1.0, 1.0, 1.0), (-1.0, 1.0, 1.0),
        )
        derivatives = []
        for axis in range(3):
            derivative = []
            for sx, sy, sz in signs:
                values = (sx, sy, sz)
                factors = (first, second, third)
                value = values[axis] / 8.0
                for other in range(3):
                    if other != axis:
                        value *= 1.0 + values[other] * factors[other]
                derivative.append(value)
            derivatives.append(derivative)
    elif family == "WEDGE":
        r, s, t = first, second, third
        derivatives = (
            (-(1.0 - t) / 2.0, (1.0 - t) / 2.0, 0.0,
             -(1.0 + t) / 2.0, (1.0 + t) / 2.0, 0.0),
            (-(1.0 - t) / 2.0, 0.0, (1.0 - t) / 2.0,
             -(1.0 + t) / 2.0, 0.0, (1.0 + t) / 2.0),
            (-(1.0 - r - s) / 2.0, -r / 2.0, -s / 2.0,
             (1.0 - r - s) / 2.0, r / 2.0, s / 2.0),
        )
    else:
        raise ValueError("unsupported linear Jacobian family")
    columns = []
    for derivative in derivatives:
        columns.append(tuple(
            builtins.sum(float(corners[node][axis]) * derivative[node] for node in range(len(corners)))
            for axis in range(3)
        ))
    return determinant3(columns[0], columns[1], columns[2])


def element_signed_volume_and_legality(spec, points):
    corners = points[:spec["corner_count"]]
    edge_lengths = []
    for first, second, middle in spec["edges"]:
        edge = vector_between(corners[first], corners[second])
        length = math.sqrt(builtins.sum(value * value for value in edge))
        edge_lengths.append(length)
        if length <= 1.0e-9 or length > 6.5:
            return None
        if middle is not None:
            expected = tuple((float(corners[first][axis]) + float(corners[second][axis])) / 2.0 for axis in range(3))
            if any(abs(float(points[middle][axis]) - expected[axis]) > 1.0e-7 for axis in range(3)):
                return None
    threshold = 1.0e-10 * max(edge_lengths) ** 3
    if spec["family"] == "TET":
        determinant = determinant3(
            vector_between(corners[0], corners[1]),
            vector_between(corners[0], corners[2]),
            vector_between(corners[0], corners[3]),
        )
        return determinant / 6.0 if determinant > threshold else None
    root = 1.0 / math.sqrt(3.0)
    if spec["family"] == "HEX":
        samples = (-1.0, -root, 0.0, root, 1.0)
        if any(
            linear_element_jacobian("HEX", corners, xi, eta, zeta) <= threshold
            for xi in samples for eta in samples for zeta in samples
        ):
            return None
        return builtins.sum(
            linear_element_jacobian("HEX", corners, xi, eta, zeta)
            for xi in (-root, root) for eta in (-root, root) for zeta in (-root, root)
        )
    triangle_samples = ((0.0, 0.0), (1.0, 0.0), (0.0, 1.0), (1.0 / 3.0, 1.0 / 3.0))
    if any(
        linear_element_jacobian("WEDGE", corners, r, s, t) <= threshold
        for r, s in triangle_samples for t in (-1.0, 0.0, 1.0)
    ):
        return None
    triangle_rule = ((1.0 / 6.0, 1.0 / 6.0), (2.0 / 3.0, 1.0 / 6.0), (1.0 / 6.0, 2.0 / 3.0))
    return builtins.sum(
        linear_element_jacobian("WEDGE", corners, r, s, t) / 6.0
        for r, s in triangle_rule for t in (-root, root)
    )


def convex_hull_2d(points):
    values = sorted(set((float(point[0]), float(point[1])) for point in points))
    if len(values) < 3:
        return []
    def turn(origin, left, right):
        return (left[0] - origin[0]) * (right[1] - origin[1]) - (left[1] - origin[1]) * (right[0] - origin[0])
    lower = []
    for point in values:
        while len(lower) >= 2 and turn(lower[-2], lower[-1], point) <= 1.0e-12:
            lower.pop()
        lower.append(point)
    upper = []
    for point in reversed(values):
        while len(upper) >= 2 and turn(upper[-2], upper[-1], point) <= 1.0e-12:
            upper.pop()
        upper.append(point)
    return lower[:-1] + upper[:-1]


def polygon_area_2d(points):
    if len(points) < 3:
        return 0.0
    return abs(builtins.sum(
        points[index][0] * points[(index + 1) % len(points)][1]
        - points[(index + 1) % len(points)][0] * points[index][1]
        for index in range(len(points))
    )) * 0.5


def convex_intersection_area(subject, clip_polygon):
    result = list(subject)
    for index in range(len(clip_polygon)):
        clip_a = clip_polygon[index]
        clip_b = clip_polygon[(index + 1) % len(clip_polygon)]
        source = result
        result = []
        if not source:
            break
        def inside(point):
            return ((clip_b[0] - clip_a[0]) * (point[1] - clip_a[1])
                    - (clip_b[1] - clip_a[1]) * (point[0] - clip_a[0])) >= -1.0e-10
        def intersection(left, right):
            dx1, dy1 = right[0] - left[0], right[1] - left[1]
            dx2, dy2 = clip_b[0] - clip_a[0], clip_b[1] - clip_a[1]
            denominator = dx1 * dy2 - dy1 * dx2
            if abs(denominator) <= 1.0e-14:
                return right
            parameter = ((clip_a[0] - left[0]) * dy2 - (clip_a[1] - left[1]) * dx2) / denominator
            return (left[0] + parameter * dx1, left[1] + parameter * dy1)
        previous = source[-1]
        for current in source:
            current_inside = inside(current)
            previous_inside = inside(previous)
            if current_inside:
                if not previous_inside:
                    result.append(intersection(previous, current))
                result.append(current)
            elif previous_inside:
                result.append(intersection(previous, current))
            previous = current
    return polygon_area_2d(result)


def validate_solid_mesh(part, part_coords, global_coords):
    if len(part.elements) < 150 or len(part.nodes) < 100:
        return fail("solid mesh is too coarse for a 4 mm target size")
    element_types = set(str(element.type).upper() for element in part.elements)
    if not element_types or not element_types.issubset(set(ALLOWED_TYPES)):
        return fail("all elements must use an appropriate 3D mechanical solid formulation")
    total_volume = 0.0
    attached = set()
    adjacency = {}
    face_incidence = {}
    connectivity_keys = set()
    edge_incidence = {}
    for element in part.elements:
        nodes = element_nodes(part, element)
        element_type = str(element.type).upper()
        spec = element_family_spec(element_type)
        if spec is None or len(nodes) != spec["node_count"]:
            return fail("solid element connectivity is incomplete")
        ordered_labels = tuple(int(node.label) for node in nodes)
        if len(set(ordered_labels)) != len(ordered_labels) or any(label not in part_coords for label in ordered_labels):
            return fail("solid mesh contains a degenerate or unreadable element connectivity")
        corner_key = frozenset(ordered_labels[:spec["corner_count"]])
        if corner_key in connectivity_keys:
            return fail("solid mesh contains duplicate solid elements")
        connectivity_keys.add(corner_key)
        attached.update(ordered_labels)
        adjacency[int(element.label)] = set()
        points = [part_coords[label] for label in ordered_labels]
        volume = element_signed_volume_and_legality(spec, points)
        if volume is None:
            return fail("solid mesh contains an oversized, curved, collapsed, or non-positive-Jacobian element")
        total_volume += volume
        for first, second, middle in spec["edges"]:
            edge_key = frozenset((ordered_labels[first], ordered_labels[second]))
            edge_incidence.setdefault(edge_key, set()).add(int(element.label))
        for side, (corner_indices, full_indices) in enumerate(spec["faces"], 1):
            face_corner_key = frozenset(ordered_labels[index] for index in corner_indices)
            full_key = frozenset(ordered_labels[index] for index in full_indices)
            face_incidence.setdefault(face_corner_key, []).append(
                (int(element.label), side, tuple(ordered_labels[index] for index in corner_indices), full_key)
            )
    if attached != set(part_coords):
        return fail("solid mesh contains unattached nodes")
    exterior = []
    for owners in face_incidence.values():
        if len(owners) not in (1, 2) or len(set(owner[0] for owner in owners)) != len(owners):
            return fail("solid mesh contains duplicate or non-manifold solid faces")
        if len(owners) == 2:
            if owners[0][3] != owners[1][3]:
                return fail("quadratic solid mesh has a nonconforming internal face")
            adjacency[owners[0][0]].add(owners[1][0])
            adjacency[owners[1][0]].add(owners[0][0])
        else:
            exterior.append(owners[0])
    for edge_key, incident_elements in edge_incidence.items():
        link = dict((label, set()) for label in incident_elements)
        boundary_face_count = 0
        for face_key, owners in face_incidence.items():
            if not edge_key.issubset(face_key):
                continue
            owner_labels = [owner[0] for owner in owners if owner[0] in incident_elements]
            if len(owners) == 1:
                boundary_face_count += 1
            elif len(owner_labels) == 2:
                link[owner_labels[0]].add(owner_labels[1])
                link[owner_labels[1]].add(owner_labels[0])
        linked = set()
        stack = [next(iter(incident_elements))]
        while stack:
            label = stack.pop()
            if label in linked:
                continue
            linked.add(label)
            stack.extend(link[label] - linked)
        degrees = sorted(len(link[label]) for label in incident_elements)
        interior_ok = boundary_face_count == 0 and linked == incident_elements and all(degree == 2 for degree in degrees)
        boundary_ok = (
            boundary_face_count == 2
            and linked == incident_elements
            and (
                (len(degrees) == 1 and degrees == [0])
                or (degrees.count(1) == 2 and all(degree in (1, 2) for degree in degrees))
            )
        )
        if not interior_ok and not boundary_ok:
            return fail("solid mesh contains a non-manifold or disconnected element fan around an edge")
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
    boundary_areas = dict((name, 0.0) for name in ("X0", "X120", "Y0", "Y12", "Z0", "Z8"))
    boundary_polygons = dict((name, []) for name in boundary_areas)
    plane_specs = (
        ("X0", 0, 0.0), ("X120", 0, 120.0),
        ("Y0", 1, 0.0), ("Y12", 1, 12.0),
        ("Z0", 2, 0.0), ("Z8", 2, 8.0),
    )
    for element_label, side, ordered_corners, full_key in exterior:
        planes = []
        for name, axis, value in plane_specs:
            if all(abs(float(global_coords[label][axis]) - value) <= 1.0e-7 for label in full_key):
                planes.append((name, axis))
        if len(planes) != 1:
            return fail("solid mesh has an exterior face away from the six required block planes")
        name, dropped_axis = planes[0]
        axes = [axis for axis in range(3) if axis != dropped_axis]
        polygon = convex_hull_2d([
            (global_coords[label][axes[0]], global_coords[label][axes[1]])
            for label in ordered_corners
        ])
        if len(polygon) != len(ordered_corners):
            return fail("solid mesh exterior contains a degenerate or non-convex facet")
        area = polygon_area_2d(polygon)
        if area <= 1.0e-10:
            return fail("solid mesh exterior contains a zero-area facet")
        for other in boundary_polygons[name]:
            if convex_intersection_area(polygon, other) > 1.0e-8:
                return fail("solid mesh exterior facets overlap on a block boundary")
        boundary_polygons[name].append(polygon)
        boundary_areas[name] += area
    expected_areas = {"X0": 96.0, "X120": 96.0, "Y0": 960.0, "Y12": 960.0, "Z0": 1440.0, "Z8": 1440.0}
    if any(not boundary_polygons[name] for name in boundary_polygons) or any(
        not close(boundary_areas[name], expected, rel=1.0e-8, abs_tol=1.0e-5)
        for name, expected in expected_areas.items()
    ):
        return fail("solid mesh exterior does not cover each required block boundary exactly once")
    if not close(total_volume, 11520.0, rel=1.0e-8, abs_tol=1.0e-5):
        return fail("solid mesh does not cover the complete 120 x 12 x 8 mm block")
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
        return fail("CAE does not contain the required Job-BlockTension job")
    job = database.jobs[JOB_NAME]
    model_name = str(getattr(job, "model", ""))
    if model_name not in database.models.keys():
        return fail("Job-BlockTension does not reference a valid model")
    model = database.models[model_name]
    if len(model.parts.keys()) != 1:
        return fail("job model must contain exactly one solid block part")
    part = model.parts[model.parts.keys()[0]]
    if len(part.cells) < 1 or not len(part.elements):
        return fail("job part must contain one or more partitioned cells of the meshed extruded solid")
    if len(model.rootAssembly.instances.keys()) != 1:
        return fail("job model must contain exactly one block instance")
    instance = model.rootAssembly.instances[model.rootAssembly.instances.keys()[0]]
    if str(getattr(instance, "partName", "")) != str(part.name) or str(getattr(instance, "dependent", "")).upper() not in ("ON", "1"):
        return fail("block assembly must contain one dependent instance of the meshed part")
    part_coords = coords_by_label(part.nodes)
    global_coords = coords_by_label(instance.nodes)
    if not part_coords or set(part_coords) != set(global_coords):
        return fail("part and dependent instance node labels do not match")
    if any(len(node.coordinates) != 3 for node in part.nodes) or any(
        len(node.coordinates) != 3 for node in instance.nodes
    ):
        return fail("block must use three-dimensional nodal coordinates")
    xs = [xyz[0] for xyz in global_coords.values()]
    ys = [xyz[1] for xyz in global_coords.values()]
    zs = [xyz[2] for xyz in global_coords.values()]
    if not (
        close(builtins.min(xs), 0.0)
        and close(builtins.max(xs), 120.0)
        and close(builtins.min(ys), 0.0)
        and close(builtins.max(ys), 12.0)
        and close(builtins.min(zs), 0.0)
        and close(builtins.max(zs), 8.0)
    ):
        return fail("assembly geometry is not the required global 120 x 12 x 8 mm positive-coordinate solid")
    try:
        volume = float(part.getMassProperties().get("volume"))
    except Exception:
        return fail("extruded solid geometry volume cannot be read")
    if not close(volume, 11520.0, rel=1.0e-8, abs_tol=1.0e-5):
        return fail("extruded solid geometry volume is not 11520 mm^3")
    try:
        seed_size = float(part.getPartSeeds(attribute=SIZE))
    except Exception:
        return fail("global part seed cannot be read")
    if not close(seed_size, 4.0, rel=0.01, abs_tol=0.05):
        return fail("global part seed is not 4 mm")
    element_types = validate_solid_mesh(part, part_coords, global_coords)
    if not element_types:
        return False
    expected_sets = {
        "ALL": set(global_coords),
        "FIXED": set(label for label, xyz in global_coords.items() if close(xyz[0], 0.0)),
        "FREE": set(label for label, xyz in global_coords.items() if close(xyz[0], 120.0)),
    }
    if not expected_sets["FIXED"] or not expected_sets["FREE"]:
        return fail("complete global X=0 and X=120 end faces cannot be identified")

    if "Aluminum" not in model.materials.keys():
        return fail("material Aluminum is missing")
    try:
        elastic = model.materials["Aluminum"].elastic.table[0]
    except Exception:
        return fail("Aluminum elastic data is missing")
    if len(elastic) < 2 or not close(elastic[0], 70000.0) or not close(elastic[1], 0.33):
        return fail("Aluminum elastic constants are incorrect")
    valid_sections = set()
    for name in model.sections.keys():
        section = model.sections[name]
        if (
            section.__class__.__name__ == "HomogeneousSolidSection"
            and str(getattr(section, "material", "")) == "Aluminum"
        ):
            valid_sections.add(str(name))
    if not valid_sections:
        return fail("no homogeneous Aluminum solid section exists")
    assignments = list(part.sectionAssignments)
    if not assignments or any(str(assignment.sectionName) not in valid_sections for assignment in assignments):
        return fail("every block section assignment must reference a homogeneous Aluminum solid section")

    if set(str(name) for name in model.steps.keys()) != set(("Initial", STEP_NAME)):
        return fail("model must contain exactly Initial followed by Step-Load")
    step = model.steps[STEP_NAME]
    bcs = []
    for bc_name, bc in active_named_objects(model.boundaryConditions):
        state = step.boundaryConditionStates[bc_name] if bc_name in step.boundaryConditionStates.keys() else None
        if state is not None and state_is_active(state):
            bcs.append((bc_name, bc, state))
    if len(bcs) != 1 or bcs[0][1].__class__.__name__ != "TypeBC":
        return fail("Abaqus model must contain exactly one active Encastre boundary condition")
    actual_constraints = {}
    for bc_name, bc, state in bcs:
        labels = region_labels_any(model, bc.region, "nodes")
        if not labels:
            return fail("active Encastre region cannot be resolved")
        for label in labels:
            actual_constraints.setdefault(label, set()).update(("U1", "U2", "U3"))
    expected_constraints = dict(
        (label, set(("U1", "U2", "U3"))) for label in expected_sets["FIXED"]
    )
    if actual_constraints != expected_constraints:
        return fail("active Encastre signature is not exactly X=0 U1/U2/U3 zero")
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

    loads = []
    for load_name, load in active_named_objects(model.loads):
        state = step.loadStates[load_name] if load_name in step.loadStates.keys() else None
        if state is not None and state_is_active(state):
            loads.append((load_name, load, state))
    if not loads:
        return fail("Abaqus model must contain at least one active uniform surface load")
    actual_loads = []
    for load_name, load, load_state in loads:
        labels = region_labels_any(model, load.region, "nodes")
        magnitude = getattr(load_state, "magnitude", getattr(load, "magnitude", None))
        if not labels or not labels.issubset(expected_sets["FREE"]):
            return fail("surface load region contains nodes outside the global X=120 face")
        if str(getattr(load, "distributionType", "")).upper() != "UNIFORM":
            return fail("surface load must be uniform")
        if load.__class__.__name__ == "SurfaceTraction":
            direction = direction_components(getattr(load, "directionVector", None))
            traction = str(getattr(load, "traction", "")).strip().upper()
            if traction != "GENERAL":
                return fail("surface traction must use GENERAL traction with an explicit global direction")
            if not close(magnitude, TRACTION_MPA, rel=1.0e-10, abs_tol=1.0e-9) or direction is None:
                return fail("surface traction magnitude or direction cannot be validated")
            length = math.sqrt(builtins.sum(value * value for value in direction))
            direction = tuple(value / length for value in direction) if length > 0.0 else ()
            has_direction_transform = any(
                not uses_global_coordinate_system(load, attribute)
                for attribute in ("localCsys", "userCsys")
            )
            try:
                has_direction_transform = has_direction_transform or abs(
                    float(getattr(load, "angle", 0.0))
                ) > 1.0e-12
            except Exception:
                has_direction_transform = True
            if not direction or (
                not has_direction_transform
                and not all(close(a, b) for a, b in zip(direction, (1.0, 0.0, 0.0)))
            ):
                return fail("surface traction direction is not global +X")
        elif load.__class__.__name__ == "Pressure":
            if not close(magnitude, -TRACTION_MPA, rel=1.0e-10, abs_tol=1.0e-9):
                return fail("Abaqus pressure must use the outward-tension sign and exact 800 N resultant")
        else:
            return fail("active load is neither native Pressure nor GENERAL SurfaceTraction")
        actual_loads.append(labels)
    if not actual_loads or set().union(*actual_loads) != expected_sets["FREE"]:
        return fail("surface load does not cover the complete global X=120 face")
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
        global_coords,
    ):
        return False
    return {
        "model_name": model_name,
        "part": part,
        "coords": global_coords,
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
            return fail("ODB must contain one solid block instance")
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
            values = list(frame.fieldOutputs[name].values)
            labels = [int(value.nodeLabel) for value in values]
            if len(labels) != len(all_nodes) or set(labels) != all_nodes or len(set(labels)) != len(labels):
                return fail("%s output must contain exactly one value for every node" % name)
            for value in values:
                if not str(getattr(value, "position", "")).upper().endswith("NODAL"):
                    return fail("%s output is not stored at nodal position" % name)
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
        free_labels = model_info["sets"]["FREE"]
        if not free_labels.issubset(set(displacement)) or not fixed_labels.issubset(set(signature["RF"])):
            return fail("complete free-face U or fixed-face RF output is missing")
        end_displacement = builtins.sum(displacement[label][0] for label in free_labels) / len(free_labels)
        reaction_resultant = -builtins.sum(signature["RF"][label][0] for label in fixed_labels)
        fixed_rf2 = builtins.sum(signature["RF"][label][1] for label in fixed_labels)
        fixed_rf3 = builtins.sum(signature["RF"][label][2] for label in fixed_labels)
        max_stress = builtins.max(mises) if mises else None
        if max_stress is None or not math.isfinite(end_displacement) or not math.isfinite(reaction_resultant) or not math.isfinite(max_stress):
            return fail("native metrics could not be extracted")
        if not (0.010 < end_displacement < 0.020 and 7.5 < max_stress < 16.0):
            return fail("native Abaqus metrics are outside physical sanity bounds")
        if not close(reaction_resultant, 800.0, rel=1.0e-3, abs_tol=0.5):
            return fail("fixed-face reaction does not balance the required 800 N tensile load")
        if abs(fixed_rf2) > 0.1 or abs(fixed_rf3) > 0.1:
            return fail("fixed-face transverse reaction is inconsistent with pure axial tension")
        if compare_submitted_metrics:
            if not close(end_displacement, SUBMITTED["end_displacement"], rel=1.0e-3, abs_tol=1.0e-7):
                return fail("metrics.json end_displacement does not match mean global U1 over the complete X=120 face")
            if not close(max_stress, SUBMITTED["max_stress"], rel=1.0e-3, abs_tol=0.01):
                return fail("metrics.json max_stress does not match the maximum integration-point ODB Mises stress")
        return {
            "metrics": {
                "end_displacement": end_displacement,
                "max_stress": max_stress,
            },
            "reaction_resultant": reaction_resultant,
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
    checker_source = checker_source.replace("__RECHECK_JOB_NAME__", repr(recheck_job_name))
    checker_path.write_text(checker_source, encoding="utf-8")
    passed = False
    cleanup_ok = False
    process_cleanup_ok = False
    process = None
    process_baseline = []
    try:
        process_baseline = windows_abaqus_processes()
        process = subprocess.Popen(
            [ABAQUS_COMMAND, "cae", "noGUI=" + str(checker_path)],
            cwd=str(temp_root),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
        )
        try:
            stdout, stderr = process.communicate(timeout=900)
        except subprocess.TimeoutExpired:
            terminate_windows_process_tree(process.pid)
            stdout, stderr = process.communicate(timeout=60)
            raise RuntimeError("Abaqus checker timed out after 900 seconds")
        completed = subprocess.CompletedProcess(
            process.args, process.returncode, stdout=stdout, stderr=stderr
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
        if process is not None and process.poll() is None:
            terminate_windows_process_tree(process.pid)
        log("Abaqus checker failed: %s" % exc)
    finally:
        try:
            process_cleanup_ok = restore_abaqus_process_baseline(
                process_baseline,
                process.pid if process is not None else None,
                (temp_root, checker_path, recheck_job_name),
            )
        except Exception as exc:
            process_cleanup_ok = False
            log("Abaqus evaluator process cleanup failed: %s" % exc)
        if not process_cleanup_ok:
            log("Abaqus evaluator process baseline was not restored")
        cleanup_ok = remove_tree_with_retries(temp_root)
        if not cleanup_ok:
            log("Abaqus evaluator temporary directory cleanup was incomplete")
    return passed and cleanup_ok and process_cleanup_ok


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
        rows.append((int(match.group(1)), match.group(2).upper(), ansys_number(match.group(3)), ansys_number(match.group(4))))
    return rows


def nodal_forces_are_absent(text):
    upper = (text or "").upper()
    if "NO NODAL FORCES TO LIST." not in upper:
        return False
    return not any(re.match(r"^\s*\d+", line) for line in (text or "").splitlines())


def parse_area_surface_listing(text):
    upper = (text or "").upper()
    no_load_markers = (
        "NO SURFACE LOADS ON AREAS TO LIST",
        "NO SURFACE LOADS TO LIST",
        "NO SURFACE LOADS ON SELECTED AREAS",
    )
    if any(marker in upper for marker in no_load_markers):
        if any(re.match(r"^\s*\d+", line) for line in (text or "").splitlines()):
            return None
        return []
    if "LIST SURFACE LOADS ON ALL SELECTED AREAS" not in upper or "AREA" not in upper or "LOAD LABEL" not in upper:
        return None
    pattern = re.compile(
        r"^\s*(\d+)\s+(\d+)\s+(\S+)\s+(%s)\s+(%s)\s*$" % (ANSYS_NUMBER, ANSYS_NUMBER),
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
            {
                "area": int(match.group(1)),
                "lkey": int(match.group(2)),
                "label": match.group(3).upper(),
                "real": ansys_number(match.group(4)),
                "imag": ansys_number(match.group(5)),
            }
        )
    return rows if rows else None


def parse_element_surface_listing(text, title):
    upper = (text or "").upper()
    if title not in upper or "ELEMENT  LKEY" not in upper or "FACE NODES" not in upper or "IMAGINARY" not in upper:
        return None
    first_pattern = re.compile(
        r"^\s*(\d+)\s+(\d+)\s+(\d+)\s+(%s)\s+(%s)\s*$" % (ANSYS_NUMBER, ANSYS_NUMBER),
        re.IGNORECASE,
    )
    continuation_pattern = re.compile(
        r"^\s*(\d+)\s+(%s)\s+(%s)\s*$" % (ANSYS_NUMBER, ANSYS_NUMBER),
        re.IGNORECASE,
    )
    blocks = []
    current = None
    for line in (text or "").splitlines():
        if not re.match(r"^\s*\d+", line):
            continue
        first = first_pattern.fullmatch(line)
        if first is not None:
            current = {
                "element": int(first.group(1)),
                "lkey": int(first.group(2)),
                "nodes": [int(first.group(3))],
                "real": [ansys_number(first.group(4))],
                "imag": [ansys_number(first.group(5))],
            }
            blocks.append(current)
            continue
        continuation = continuation_pattern.fullmatch(line)
        if continuation is None or current is None:
            return None
        current["nodes"].append(int(continuation.group(1)))
        current["real"].append(ansys_number(continuation.group(2)))
        current["imag"].append(ansys_number(continuation.group(3)))
    return blocks if blocks else None


def parse_result_set_listing(text):
    upper = (text or "").upper()
    if "INDEX OF DATA SETS ON RESULTS FILE" not in upper or "LOAD STEP" not in upper or "SUBSTEP" not in upper:
        return None
    pattern = re.compile(
        r"^\s*(\d+)\s+(%s)\s+(\d+)\s+(\d+)\s+(\d+)\s*$" % ANSYS_NUMBER,
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
            {
                "set": int(match.group(1)),
                "time": ansys_number(match.group(2)),
                "load_step": int(match.group(3)),
                "substep": int(match.group(4)),
                "cumulative": int(match.group(5)),
            }
        )
    return rows if rows else None


def validate_pressure_blocks(blocks, element_codes):
    if not blocks:
        return None
    signature = set()
    element_lkeys = set()
    for block in blocks:
        element_code = element_codes.get(block["element"])
        expected_node_count = {185: 4, 186: 4, 187: 3}.get(element_code)
        key = (block["element"], block["lkey"])
        facet = (block["element"], block["lkey"], frozenset(block["nodes"]))
        if (
            expected_node_count is None
            or key in element_lkeys
            or facet in signature
            or len(block["nodes"]) != expected_node_count
            or len(set(block["nodes"])) != len(block["nodes"])
            or any(abs(value) > 1.0e-12 for value in block["imag"])
            or any(
                not close_enough(value, -TRACTION_MPA, rel=1.0e-5, abs_tol=1.0e-4)
                for value in block["real"]
            )
        ):
            return None
        element_lkeys.add(key)
        signature.add(facet)
    return signature


def solution_status_is_linear_static(text):
    upper = (text or "").upper()
    if "S O L U T I O N   O P T I O N S" not in upper or "STATIC (STEADY-STATE)" not in upper:
        return False
    match = re.search(r"NONLINEAR GEOMETRIC EFFECTS\s*\.+\s*(\S+)", upper)
    return match is None or match.group(1) == "OFF"


def export_solution_state_is_linear(export_text):
    values = []
    for match in re.finditer(r"^\s*NLGEOM\s*,\s*([^,\s!]+)", export_text or "", re.MULTILINE | re.IGNORECASE):
        token = match.group(1).strip().upper()
        if token in ("OFF", "NO", "FALSE"):
            values.append(0.0)
        elif token in ("ON", "YES", "TRUE"):
            values.append(1.0)
        else:
            try:
                values.append(ansys_number(token))
            except Exception:
                return False
    return not values or all(abs(value) <= 1.0e-12 for value in values)


def export_surface_loads_are_only_pressure(export_text):
    labels = [
        match.group(1).upper()
        for match in re.finditer(r"^\s*SFEBLOCK\s*,[^,]*,\s*([^,\s!]+)", export_text or "", re.MULTILINE | re.IGNORECASE)
    ]
    labels.extend(
        match.group(1).upper()
        for match in re.finditer(
            r"^\s*SFE\s*,\s*\d+\s*,[^,]*,\s*([^,\s!]+)",
            export_text or "",
            re.MULTILINE | re.IGNORECASE,
        )
    )
    return bool(labels) and all(label == "PRES" for label in labels)


def export_material_is_constant_elastic(export_text, material_id):
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
            if start < 1 or count < 1 or len(values) != count or any(not math.isfinite(value) for value in values):
                return False
            slots = [start + offset for offset in range(count)]
            for slot, value in zip(slots, values):
                if slot in temperatures and not close_enough(
                    temperatures[slot], value, rel=1.0e-12, abs_tol=1.0e-12
                ):
                    return False
            temperatures.update((slot, value) for slot, value in zip(slots, values))
            continue
        if command == "MPDATA":
            try:
                if fields[1].upper() != "UNBL":
                    return False
                count = int(float(fields[2]))
                label = fields[3].upper()
                row_material = int(float(fields[4]))
                start = int(float(fields[5]))
                values = [ansys_number(token) for token in fields[6:] if token]
            except Exception:
                return False
            if row_material != int(material_id):
                continue
            if label not in ("EX", "NUXY", "PRXY", "DENS"):
                return False
            if start < 1 or count < 1 or len(values) != count or any(not math.isfinite(value) for value in values):
                return False
            samples = properties.setdefault(label, [])
            for offset, value in enumerate(values):
                slot = start + offset
                if slot not in temperatures:
                    return False
                if any(existing_slot == slot for existing_slot, temperature, existing_value in samples):
                    return False
                sample = (temperatures[slot], value)
                samples.append((slot, sample[0], sample[1]))
            continue
        if command == "TB":
            try:
                row_material = int(float(fields[2]))
            except Exception:
                return False
            if row_material == int(material_id):
                return False
        if command in ("TREF", "TUNIF"):
            values = []
            for token in fields[1:]:
                if not token:
                    continue
                try:
                    values.append(ansys_number(token))
                except Exception:
                    return False
            if any(abs(value) > 1.0e-12 for value in values):
                return False
        if command == "BFUNIF" and len(fields) > 1 and fields[1].upper() == "TEMP":
            values = []
            for token in fields[2:]:
                if not token or token.upper() == "_TINY":
                    continue
                try:
                    values.append(ansys_number(token))
                except Exception:
                    return False
            if any(abs(value) > 1.0e-12 for value in values):
                return False
    elastic_keys = set(properties) - set(("DENS",))
    if elastic_keys not in (set(("EX", "NUXY")), set(("EX", "PRXY")), set(("EX", "NUXY", "PRXY"))):
        return False
    if any(not samples for samples in properties.values()):
        return False
    for label in elastic_keys:
        expected = 70000.0 if label == "EX" else 0.33
        if any(not close_enough(value, expected, rel=1.0e-6) for slot, temperature, value in properties[label]):
            return False
    if "DENS" in properties:
        density_values = [value for slot, temperature, value in properties["DENS"]]
        if any(value <= 0.0 for value in density_values) or any(
            not close_enough(value, density_values[0], rel=1.0e-12, abs_tol=1.0e-20)
            for value in density_values[1:]
        ):
            return False
    return True


def export_has_no_persistent_initial_state(export_text):
    forbidden = set((
        "INISTATE", "LDREAD", "LDWRITE", "UPGEOM", "INRES", "LREAD",
        "IC", "DDELE", "FDELE", "BF", "BFE",
    ))
    for raw in (export_text or "").splitlines():
        line = raw.split("!", 1)[0].strip()
        if not line:
            continue
        command = line.split(",", 1)[0].strip().upper()
        if command in forbidden:
            return False
    return True


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
        if close_enough(ex, 70000.0, rel=1.0e-6) and close_enough(nu, 0.33, rel=1.0e-6):
            return True
    tb_ex = try_get(mapdl, "ELASTIC", material_id, "TEMP", 0, "CONST", 1, "ISOT")
    tb_nu = try_get(mapdl, "ELASTIC", material_id, "TEMP", 0, "CONST", 2, "ISOT")
    return (
        tb_ex is not None
        and tb_nu is not None
        and close_enough(tb_ex, 70000.0, rel=1.0e-6)
        and close_enough(tb_nu, 0.33, rel=1.0e-6)
    )


def listing_confirms_none(mapdl, command, marker):
    lines = [" ".join(line.strip().upper().split()) for line in required_run(mapdl, command).splitlines() if line.strip()]
    if len(lines) != 2 or lines[1].rstrip(".") != marker.rstrip("."):
        return False
    return re.fullmatch(
        r"\*\*\* NOTE \*\*\* ELAPSED TIME = %s TIME= \d{2}:\d{2}:\d{2}" % ANSYS_NUMBER,
        lines[0],
        re.IGNORECASE,
    ) is not None


def inertia_loads_are_zero(export_text):
    irlf_state = None
    airl_state = None
    pattern = re.compile(
        r"^\s*(ACEL|OMEGA|DOMEGA|CGOMEGA|CGOMGA|DCGOMG|CMACEL|CMOMEGA|CMDOMEGA)\s*,(.*)$",
        re.MULTILINE | re.IGNORECASE,
    )
    for match in pattern.finditer(export_text or ""):
        command = match.group(1).upper()
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
    for raw in (export_text or "").splitlines():
        line = raw.split("!", 1)[0].strip()
        if not line:
            continue
        fields = [field.strip() for field in line.split(",")]
        command = fields[0].upper()
        if command == "IRLF":
            try:
                value = ansys_number(fields[1])
            except Exception:
                return False
            if not math.isfinite(value) or value not in (0.0, -1.0, 1.0):
                return False
            irlf_state = value
        elif command == "AIRL":
            if len(fields) < 2 or not fields[1]:
                return False
            token = fields[1].upper()
            try:
                value = ansys_number(token)
            except Exception:
                value = None
            if token == "AUTO":
                airl_state = True
            elif value is not None and math.isfinite(value):
                airl_state = abs(value) > 1.0e-12
            else:
                return False
    return irlf_state != 1.0 and airl_state is not True


def read_ansys_rst_mesh(result_path):
    from ansys.mapdl import reader as pymapdl_reader

    result = pymapdl_reader.read_binary(str(result_path))
    labels = [int(value) for value in result.mesh.nnum]
    rows = [[float(value) for value in row[:3]] for row in result.mesh.nodes]
    if len(labels) != len(set(labels)):
        raise RuntimeError("RST contains duplicate node labels")
    coords = dict(zip(labels, rows))
    type_codes = dict((int(row[0]), int(row[1])) for row in result.mesh.ekey)
    elements = {}
    element_labels = []
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
        element_labels.append(label)
        elements[label] = (code, connectivity)
    if len(element_labels) != len(set(element_labels)):
        raise RuntimeError("RST contains duplicate element labels")
    time_values = [float(value) for value in result.time_values]
    if len(time_values) != int(result.nsets) or any(not math.isfinite(value) for value in time_values):
        raise RuntimeError("RST result-set time metadata is incomplete")
    if "ENS :" not in str(result.available_results).upper():
        raise RuntimeError("RST does not advertise native element-nodal stress results")
    try:
        stress_labels, stress_rows, stress_nodes = result.element_stress(int(result.nsets) - 1)
    except Exception as exc:
        raise RuntimeError("RST native element stress records cannot be read: %s" % exc)
    labels = [int(value) for value in stress_labels]
    if set(labels) != set(elements) or len(labels) != len(set(labels)) or len(stress_rows) != len(labels) or len(stress_nodes) != len(labels):
        raise RuntimeError("RST native element stress labels do not cover every solid element")
    ens_signature = {}
    for index, label in enumerate(labels):
        code, connectivity = elements[label]
        expected_count = {185: 8, 186: 8, 187: 4}[code]
        row_nodes = tuple(int(value) for value in stress_nodes[index])
        rows = list(stress_rows[index])
        if (
            len(row_nodes) != expected_count
            or set(row_nodes) != set(connectivity[:expected_count])
            or len(rows) != expected_count
        ):
            raise RuntimeError("RST native element stress node coverage is incomplete")
        flattened = []
        for row in rows:
            values = [float(value) for value in row]
            if len(values) != 6 or any(not math.isfinite(value) for value in values):
                raise RuntimeError("RST native element stress contains missing or non-finite components")
            flattened.extend(values)
        ens_signature[label] = (code, row_nodes, tuple(flattened))
    return coords, elements, int(result.nsets), time_values, ens_signature


def ansys_ens_signatures_match(left, right):
    if left is None or right is None or set(left) != set(right):
        return False
    for label in left:
        left_code, left_nodes, left_values = left[label]
        right_code, right_nodes, right_values = right[label]
        if left_code != right_code or left_nodes != right_nodes or len(left_values) != len(right_values):
            return False
        if any(
            not close_enough(actual, expected, rel=2.0e-5, abs_tol=1.0e-8)
            for actual, expected in zip(left_values, right_values)
        ):
            return False
    return True


def planar_face_polygon(points, dropped_axis):
    axes = [axis for axis in range(3) if axis != dropped_axis]
    values = sorted(set((float(point[axes[0]]), float(point[axes[1]])) for point in points))
    if len(values) < 3:
        return []

    def cross(origin, left, right):
        return (left[0] - origin[0]) * (right[1] - origin[1]) - (left[1] - origin[1]) * (right[0] - origin[0])

    lower = []
    for point in values:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], point) <= 0.0:
            lower.pop()
        lower.append(point)
    upper = []
    for point in reversed(values):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], point) <= 0.0:
            upper.pop()
        upper.append(point)
    return lower[:-1] + upper[:-1]


def polygon_area(points):
    if len(points) < 3:
        return 0.0
    return abs(sum(
        points[index][0] * points[(index + 1) % len(points)][1]
        - points[(index + 1) % len(points)][0] * points[index][1]
        for index in range(len(points))
    )) * 0.5


def planar_face_area(points, dropped_axis):
    return polygon_area(planar_face_polygon(points, dropped_axis))


def convex_polygon_intersection_area(subject, clip_polygon):
    result = list(subject)
    for index in range(len(clip_polygon)):
        clip_a = clip_polygon[index]
        clip_b = clip_polygon[(index + 1) % len(clip_polygon)]
        source = result
        result = []
        if not source:
            break
        def inside(point):
            return ((clip_b[0] - clip_a[0]) * (point[1] - clip_a[1])
                    - (clip_b[1] - clip_a[1]) * (point[0] - clip_a[0])) >= -1.0e-10
        def intersection(left, right):
            dx1, dy1 = right[0] - left[0], right[1] - left[1]
            dx2, dy2 = clip_b[0] - clip_a[0], clip_b[1] - clip_a[1]
            denominator = dx1 * dy2 - dy1 * dx2
            if abs(denominator) <= 1.0e-14:
                return right
            factor = ((clip_a[0] - left[0]) * dy2 - (clip_a[1] - left[1]) * dx2) / denominator
            return (left[0] + factor * dx1, left[1] + factor * dy1)
        previous = source[-1]
        for current in source:
            current_inside = inside(current)
            previous_inside = inside(previous)
            if current_inside:
                if not previous_inside:
                    result.append(intersection(previous, current))
                result.append(current)
            elif previous_inside:
                result.append(intersection(previous, current))
            previous = current
    return polygon_area(result)


ANSYS_FULL_FACE_INDICES = {
    185: (
        (0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1),
        (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0),
    ),
    186: (
        (0, 1, 2, 3, 8, 9, 10, 11),
        (4, 7, 6, 5, 15, 14, 13, 12),
        (0, 4, 5, 1, 16, 12, 17, 8),
        (1, 5, 6, 2, 17, 13, 18, 9),
        (2, 6, 7, 3, 18, 14, 19, 10),
        (3, 7, 4, 0, 19, 15, 16, 11),
    ),
    187: (
        (0, 1, 2, 4, 5, 6), (0, 3, 1, 7, 8, 4),
        (1, 3, 2, 8, 9, 5), (2, 3, 0, 9, 7, 6),
    ),
}
ANSYS_CORNER_FACE_INDICES = {
    code: tuple(face[:(4 if code in (185, 186) else 3)] for face in faces)
    for code, faces in ANSYS_FULL_FACE_INDICES.items()
}
ANSYS_EDGE_INDICES = {
    185: (
        (0,1,None),(1,2,None),(2,3,None),(3,0,None),
        (4,5,None),(5,6,None),(6,7,None),(7,4,None),
        (0,4,None),(1,5,None),(2,6,None),(3,7,None),
    ),
    186: (
        (0,1,8),(1,2,9),(2,3,10),(3,0,11),
        (4,5,12),(5,6,13),(6,7,14),(7,4,15),
        (0,4,16),(1,5,17),(2,6,18),(3,7,19),
    ),
    187: ((0,1,4),(1,2,5),(2,0,6),(0,3,7),(1,3,8),(2,3,9)),
}


def ansys_edge_fans_are_manifold(edge_incidence, face_incidence):
    for edge_key, incident_elements in edge_incidence.items():
        if not incident_elements:
            return False
        link = dict((label, set()) for label in incident_elements)
        boundary_face_count = 0
        for face_key, owners in face_incidence.items():
            if not edge_key.issubset(face_key):
                continue
            owner_labels = [owner[0] for owner in owners if owner[0] in incident_elements]
            if len(owners) == 1:
                boundary_face_count += 1
            elif len(owner_labels) == 2:
                link[owner_labels[0]].add(owner_labels[1])
                link[owner_labels[1]].add(owner_labels[0])
        linked = set()
        stack = [next(iter(incident_elements))]
        while stack:
            label = stack.pop()
            if label in linked:
                continue
            linked.add(label)
            stack.extend(link[label] - linked)
        degrees = sorted(len(link[label]) for label in incident_elements)
        interior_ok = (
            boundary_face_count == 0
            and linked == incident_elements
            and all(degree == 2 for degree in degrees)
        )
        boundary_ok = (
            boundary_face_count == 2
            and linked == incident_elements
            and (
                (len(degrees) == 1 and degrees == [0])
                or (degrees.count(1) == 2 and all(degree in (1, 2) for degree in degrees))
            )
        )
        if not interior_ok and not boundary_ok:
            return False
    return True


def determinant3_ansys(first, second, third):
    return (
        first[0] * (second[1] * third[2] - second[2] * third[1])
        - first[1] * (second[0] * third[2] - second[2] * third[0])
        + first[2] * (second[0] * third[1] - second[1] * third[0])
    )


def ansys_hex_jacobian(corners, xi, eta, zeta):
    signs = (
        (-1.0,-1.0,-1.0),(1.0,-1.0,-1.0),(1.0,1.0,-1.0),(-1.0,1.0,-1.0),
        (-1.0,-1.0,1.0),(1.0,-1.0,1.0),(1.0,1.0,1.0),(-1.0,1.0,1.0),
    )
    columns = []
    parameters = (xi, eta, zeta)
    for axis in range(3):
        column = []
        for coordinate in range(3):
            value = 0.0
            for node, node_signs in enumerate(signs):
                derivative = node_signs[axis] / 8.0
                for other in range(3):
                    if other != axis:
                        derivative *= 1.0 + node_signs[other] * parameters[other]
                value += corners[node][coordinate] * derivative
            column.append(value)
        columns.append(tuple(column))
    return determinant3_ansys(columns[0], columns[1], columns[2])


def ansys_element_volume_and_legality(element_code, connectivity, coords):
    corner_count = 8 if element_code in (185, 186) else 4
    corners = [coords[label] for label in connectivity[:corner_count]]
    edge_lengths = []
    for first, second, middle in ANSYS_EDGE_INDICES[element_code]:
        edge = tuple(corners[second][axis] - corners[first][axis] for axis in range(3))
        length = math.sqrt(sum(value * value for value in edge))
        if length <= 1.0e-9 or length > 6.5:
            return None
        edge_lengths.append(length)
        if middle is not None:
            point = coords[connectivity[middle]]
            expected = tuple((corners[first][axis] + corners[second][axis]) / 2.0 for axis in range(3))
            if any(abs(point[axis] - expected[axis]) > 1.0e-7 for axis in range(3)):
                return None
    threshold = 1.0e-10 * max(edge_lengths) ** 3
    if element_code == 187:
        columns = [
            tuple(corners[index][axis] - corners[0][axis] for axis in range(3))
            for index in (1, 2, 3)
        ]
        determinant = determinant3_ansys(columns[0], columns[1], columns[2])
        return determinant / 6.0 if determinant > threshold else None
    root = 1.0 / math.sqrt(3.0)
    samples = (-1.0, -root, 0.0, root, 1.0)
    if any(ansys_hex_jacobian(corners, xi, eta, zeta) <= threshold for xi in samples for eta in samples for zeta in samples):
        return None
    return sum(
        ansys_hex_jacobian(corners, xi, eta, zeta)
        for xi in (-root, root) for eta in (-root, root) for zeta in (-root, root)
    )


def ansys_nodal_result_signature(mapdl, node_labels, required_stress_nodes):
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
            if label in required_stress_nodes:
                return None
            stress_signature = None
        else:
            stress_signature = tuple(stresses)
        signature[label] = (tuple(displacements), stress_signature)
    return signature


def ansys_solid_stress_signature(mapdl, elements):
    common_columns = (
        ("SX04", "X"), ("SY04", "Y"), ("SZ04", "Z"),
        ("SXY04", "XY"), ("SYZ04", "YZ"), ("SXZ04", "XZ"),
        ("SEQV04", "EQV"),
    )
    columns_by_code = dict((code, common_columns) for code in (185, 186, 187))
    if not elements or any(code not in columns_by_code for code, connectivity in elements.values()):
        return None
    required_run(mapdl, "ALLSEL,ALL")
    required_run(mapdl, "ETABLE,ERAS")
    for name, component in common_columns:
        required_run(mapdl, "ETABLE,%s,S,%s" % (name, component))
    signature = {}
    for label in sorted(elements):
        code = elements[label][0]
        columns = columns_by_code[code]
        values = tuple(try_get(mapdl, "ELEM", label, "ETAB", name) for name, component in columns)
        if any(value is None or not math.isfinite(value) for value in values):
            return None
        signature[label] = (code, values)
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
        left_code, left_values = left[label]
        right_code, right_values = right[label]
        if left_code != right_code or len(left_values) != len(right_values):
            return False
        for actual, expected in zip(left_values, right_values):
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
    temp_root = Path(tempfile.mkdtemp(prefix="eval_cli_task05_ansys_%s_" % run_token))
    mapdl = None
    mapdl_jobname = "eval_task05_" + run_token[:16]
    process_baseline = ansys_job_process_ids(mapdl_jobname)
    semantic_passed = False
    cleanup_ok = False
    try:
        from ansys.mapdl.core import launch_mapdl

        if process_baseline is None:
            log("ANSYS evaluator could not establish a process baseline")
            return False
        try:
            rst_coords, rst_elements, rst_set_count, rst_time_values, submitted_ens = read_ansys_rst_mesh(result_path)
        except Exception as exc:
            log("ANSYS submitted RST mesh cannot be read: %s" % exc)
            return False
        if (
            rst_set_count < 1
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
        required_run(mapdl, "FINISH")
        required_run(mapdl, "/SOLU")
        solution_status = required_run(mapdl, "/STATUS,SOLU")
        if not solution_status_is_linear_static(solution_status):
            log("ANSYS saved solution state is not linear static with NLGEOM off")
            return False
        required_run(mapdl, "FINISH")
        required_run(mapdl, "/PREP7")
        required_run(mapdl, "ALLSEL,ALL")
        required_run(mapdl, "CSYS,0")
        required_run(mapdl, "DSYS,0")
        if int(round(required_get(mapdl, "CP", 0, "NUM"))) != 0 or int(
            round(required_get(mapdl, "CE", 0, "NUM"))
        ) != 0:
            log("ANSYS model contains additional coupled DOFs or constraint equations")
            return False
        node_numbers = [int(value) for value in mapdl.mesh.nnum]
        node_rows = [[float(value) for value in row[:3]] for row in mapdl.mesh.nodes]
        coords = dict(zip(node_numbers, node_rows))
        if len(coords) < 100:
            log("ANSYS solid mesh is too coarse for a 4 mm target size")
            return False
        xs = [row[0] for row in node_rows]
        ys = [row[1] for row in node_rows]
        zs = [row[2] for row in node_rows]
        if not (
            close_enough(min(xs), 0.0, rel=1.0e-8)
            and close_enough(max(xs), 120.0, rel=1.0e-8)
            and close_enough(min(ys), 0.0, rel=1.0e-8)
            and close_enough(max(ys), 12.0, rel=1.0e-8)
            and close_enough(min(zs), 0.0, rel=1.0e-8)
            and close_enough(max(zs), 8.0, rel=1.0e-8)
        ):
            log("ANSYS geometry bounds are incorrect")
            return False
        element_numbers = [int(value) for value in mapdl.mesh.enum]
        if len(element_numbers) < 150:
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
        type_codes = {}
        element_attributes = {}
        material_ids = set()
        db_connectivity = {}
        for element in element_numbers:
            live = required_get(mapdl, "ELEM", element, "ATTR", "LIVE")
            if live != 1.0:
                log("ANSYS mesh contains a killed, inactive, or unselected solid element")
                return False
            type_value = required_get(mapdl, "ELEM", element, "ATTR", "TYPE")
            material_value = required_get(mapdl, "ELEM", element, "ATTR", "MAT")
            type_id = int(round(type_value))
            material_id = int(round(material_value))
            if (
                type_id <= 0
                or material_id <= 0
                or not close_enough(type_value, type_id, rel=0.0, abs_tol=1.0e-9)
                or not close_enough(material_value, material_id, rel=0.0, abs_tol=1.0e-9)
            ):
                log("ANSYS element TYPE or MAT attribute is invalid")
                return False
            if type_id not in type_codes:
                code_value = required_get(mapdl, "ETYP", type_id, "ATTR", "ENAM")
                code = int(round(code_value))
                if (
                    code not in (185, 186, 187)
                    or not close_enough(code_value, code, rel=0.0, abs_tol=1.0e-9)
                ):
                    log("actual elements are not SOLID185/SOLID186/SOLID187")
                    return False
                type_codes[type_id] = code
            element_attributes[element] = (type_id, type_codes[type_id], material_id)
            material_ids.add(material_id)
        attached_nodes = set()
        total_volume = 0.0
        adjacency = {}
        face_incidence = {}
        edge_incidence = {}
        edge_middle_nodes = {}
        connectivity_keys = set()
        for element in element_numbers:
            type_id, element_code, material_id = element_attributes[element]
            nodes_per_element = {185: 8, 186: 20, 187: 10}[element_code]
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
            corner_count = 8 if element_code in (185, 186) else 4
            connectivity_key = frozenset(connectivity[:corner_count])
            if connectivity_key in connectivity_keys:
                log("ANSYS mesh contains duplicate solid elements")
                return False
            connectivity_keys.add(connectivity_key)
            db_connectivity[element] = (element_code, tuple(connectivity))
            attached_nodes.update(connectivity)
            adjacency[element] = set()
            volume = ansys_element_volume_and_legality(element_code, connectivity, coords)
            if volume is None:
                log("ANSYS mesh contains an oversized, curved, collapsed, or non-positive-Jacobian element")
                return False
            total_volume += volume
            for first, second, middle in ANSYS_EDGE_INDICES[element_code]:
                edge_key = frozenset((connectivity[first], connectivity[second]))
                edge_incidence.setdefault(edge_key, set()).add(element)
                middle_label = None if middle is None else connectivity[middle]
                if edge_key in edge_middle_nodes and edge_middle_nodes[edge_key] != middle_label:
                    log("ANSYS mesh contains a nonconforming linear/quadratic or quadratic edge")
                    return False
                edge_middle_nodes[edge_key] = middle_label
            for corner_indices, full_indices in zip(
                ANSYS_CORNER_FACE_INDICES[element_code], ANSYS_FULL_FACE_INDICES[element_code]
            ):
                corner_key = frozenset(connectivity[index] for index in corner_indices)
                full_key = frozenset(connectivity[index] for index in full_indices)
                face_incidence.setdefault(corner_key, []).append((element, full_key, tuple(connectivity[index] for index in corner_indices)))
        if attached_nodes != set(coords):
            log("ANSYS solid mesh contains unattached nodes")
            return False
        exterior_faces = []
        for owners in face_incidence.values():
            if len(owners) not in (1, 2) or len(set(owner[0] for owner in owners)) != len(owners):
                log("ANSYS mesh contains duplicate, overlapping, or non-manifold solid faces")
                return False
            if len(owners) == 2:
                if owners[0][1] != owners[1][1]:
                    log("ANSYS high-order mesh contains a nonconforming internal face")
                    return False
                adjacency[owners[0][0]].add(owners[1][0])
                adjacency[owners[1][0]].add(owners[0][0])
            else:
                exterior_faces.append(owners[0])
        if not ansys_edge_fans_are_manifold(edge_incidence, face_incidence):
            log("ANSYS mesh contains a non-manifold or disconnected element fan around an edge")
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
        boundary_counts = dict((name, 0) for name in ("X0", "X120", "Y0", "Y12", "Z0", "Z8"))
        boundary_areas = dict((name, 0.0) for name in boundary_counts)
        boundary_polygons = dict((name, []) for name in boundary_counts)
        for element, full_face, ordered_corners in exterior_faces:
            points = [coords[label] for label in full_face]
            planes = []
            for name, axis, value in (
                ("X0",0,0.0),("X120",0,120.0),("Y0",1,0.0),("Y12",1,12.0),("Z0",2,0.0),("Z8",2,8.0),
            ):
                if all(close_enough(point[axis], value, rel=1.0e-8, abs_tol=1.0e-7) for point in points):
                    planes.append(name)
            if len(planes) != 1:
                log("ANSYS exterior solid facet is not on exactly one required block boundary plane")
                return False
            boundary_counts[planes[0]] += 1
            corner_points = [coords[label] for label in ordered_corners]
            dropped_axis = {"X": 0, "Y": 1, "Z": 2}[planes[0][0]]
            polygon = planar_face_polygon(corner_points, dropped_axis)
            if len(polygon) != len(ordered_corners) or polygon_area(polygon) <= 1.0e-10:
                log("ANSYS exterior solid facet is degenerate or non-convex")
                return False
            if any(convex_polygon_intersection_area(polygon, other) > 1.0e-8 for other in boundary_polygons[planes[0]]):
                log("ANSYS exterior solid facets overlap on a block boundary")
                return False
            boundary_polygons[planes[0]].append(polygon)
            boundary_areas[planes[0]] += polygon_area(polygon)
        if any(count <= 0 for count in boundary_counts.values()):
            log("ANSYS solid mesh does not expose all six exterior block faces")
            return False
        expected_boundary_areas = {
            "X0": 96.0,
            "X120": 96.0,
            "Y0": 960.0,
            "Y12": 960.0,
            "Z0": 1440.0,
            "Z8": 1440.0,
        }
        if any(
            not close_enough(boundary_areas[name], expected, rel=1.0e-8, abs_tol=1.0e-5)
            for name, expected in expected_boundary_areas.items()
        ):
            log("ANSYS exterior solid facets do not cover the exact six block boundary areas")
            return False
        if not close_enough(total_volume, 11520.0, rel=1.0e-8, abs_tol=1.0e-5):
            log("ANSYS solid elements do not cover the complete 120 x 12 x 8 mm block")
            return False
        if db_connectivity != rst_elements:
            log("ANSYS DB and submitted RST element types or ordered connectivity do not match")
            return False

        if any(not material_matches(mapdl, material_id) for material_id in material_ids):
            log("an actual ANSYS material is not Aluminum E=70000, nu=0.33")
            return False

        expected_sets = {
            "ALL": set(coords),
            "FIXED": set(label for label, xyz in coords.items() if close_enough(xyz[0], 0.0, rel=1.0e-8, abs_tol=1.0e-7)),
            "FREE": set(label for label, xyz in coords.items() if close_enough(xyz[0], 120.0, rel=1.0e-8, abs_tol=1.0e-7)),
        }
        if not expected_sets["FIXED"] or not expected_sets["FREE"]:
            log("ANSYS complete global X=0 and X=120 end faces cannot be identified")
            return False
        required_stress_nodes = set(
            label
            for code, connectivity in db_connectivity.values()
            for label in connectivity[:(8 if code in (185, 186) else 4)]
        )

        required_run(mapdl, "ALLSEL,ALL")
        constraints = parse_constraint_listing(required_run(mapdl, "DLIST,ALL"))
        if constraints is None:
            log("ANSYS DLIST output is unreadable or contains an unrecognized data row")
            return False
        actual_constraints = {}
        seen_constraints = set()
        for node, label, real, imag in constraints:
            key = (node, label)
            if key in seen_constraints or label not in ("UX", "UY", "UZ") or abs(real) > 1.0e-12 or abs(imag) > 1.0e-12:
                log("ANSYS contains a duplicate, unsupported, complex, or nonzero displacement constraint")
                return False
            seen_constraints.add(key)
            actual_constraints.setdefault(node, set()).add(label)
        expected_constraints = dict((node, set(("UX", "UY", "UZ"))) for node in expected_sets["FIXED"])
        if actual_constraints != expected_constraints:
            log("ANSYS constraint signature is not exactly all X=0 nodes UX/UY/UZ zero")
            return False
        if not nodal_forces_are_absent(required_run(mapdl, "FLIST,ALL")):
            log("ANSYS contains user nodal force loads instead of only the required face traction")
            return False
        sfa_rows = parse_area_surface_listing(required_run(mapdl, "SFALIST,ALL"))
        if sfa_rows is None:
            log("ANSYS SFALIST output is unreadable or contains an unrecognized data row")
            return False
        loaded_area_nodes = set()
        for row in sfa_rows:
            if row["label"] != "PRES" or row["lkey"] != 1 or abs(row["imag"]) > 1.0e-12 or not close_enough(row["real"], -TRACTION_MPA, rel=1.0e-5, abs_tol=1.0e-4):
                log("ANSYS area surface load is not only the required real outward pressure")
                return False
            required_run(mapdl, "ASEL,S,AREA,,%d" % row["area"])
            required_run(mapdl, "NSLA,S,1")
            loaded_area_nodes.update(int(value) for value in mapdl.mesh.nnum)
        required_run(mapdl, "ALLSEL,ALL")
        if sfa_rows and loaded_area_nodes != expected_sets["FREE"]:
            log("ANSYS area pressures do not cover exactly the complete X=120 face")
            return False

        sflist_blocks = parse_element_surface_listing(
            required_run(mapdl, "SFLIST,ALL"),
            "LIST NODAL SURFACE LOAD PRES FOR ALL SELECTED NODES",
        )
        sfe_blocks = parse_element_surface_listing(
            required_run(mapdl, "SFELIST,ALL"),
            "LIST ELEMENT SURFACE LOAD PRES FOR ALL SELECTED ELEMENTS",
        )
        if sflist_blocks is None or sfe_blocks is None:
            log("ANSYS SFLIST/SFELIST output is unreadable or contains an unrecognized data row")
            return False
        expected_facets = set()
        element_codes = dict((element, code) for element, (code, connectivity) in db_connectivity.items())
        for element, (element_code, connectivity) in db_connectivity.items():
            for corner_indices, full_indices in zip(
                ANSYS_CORNER_FACE_INDICES[element_code], ANSYS_FULL_FACE_INDICES[element_code]
            ):
                full_face_nodes = frozenset(connectivity[index] for index in full_indices)
                if all(label in expected_sets["FREE"] for label in full_face_nodes):
                    expected_facets.add((element, frozenset(connectivity[index] for index in corner_indices)))
        sflist_signature = validate_pressure_blocks(sflist_blocks, element_codes)
        sfelist_signature = validate_pressure_blocks(sfe_blocks, element_codes)
        if sflist_signature is None or sfelist_signature is None:
            log("ANSYS surface-pressure listings contain duplicate facets or invalid real/imaginary values")
            return False
        sflist_facets = set((element, nodes) for element, lkey, nodes in sflist_signature)
        sfelist_facets = set((element, nodes) for element, lkey, nodes in sfelist_signature)
        if sflist_signature != sfelist_signature or sfelist_facets != expected_facets:
            log("ANSYS transferred pressure records do not cover exactly the X=120 element faces")
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
        export_stem = "task05_model_audit_" + run_token[:8]
        required_run(mapdl, "CDWRITE,DB,%s,cdb" % export_stem)
        export_path = temp_root / (export_stem + ".cdb")
        export_text = export_path.read_text(encoding="utf-8", errors="ignore") if is_nonempty(export_path) else ""
        if (
            not export_text
            or not inertia_loads_are_zero(export_text)
            or not export_solution_state_is_linear(export_text)
            or not export_surface_loads_are_only_pressure(export_text)
            or any(
                not export_material_is_constant_elastic(export_text, material_id)
                for material_id in material_ids
            )
            or not export_has_no_persistent_initial_state(export_text)
        ):
            log("ANSYS CDB contains an extra load, nonlinear state, or non-constant Aluminum material law")
            return False
        required_run(mapdl, "FINISH")
        required_run(mapdl, "/POST1")
        mapdl.file(str(result_path.with_suffix("")), "rst")
        result_sets = parse_result_set_listing(required_run(mapdl, "SET,LIST"))
        if (
            result_sets is None
            or len(result_sets) != rst_set_count
            or any(row["load_step"] != 1 for row in result_sets)
            or any(not close_enough(row["time"], rst_time_values[index], rel=1.0e-8, abs_tol=1.0e-10) for index, row in enumerate(result_sets))
        ):
            log("ANSYS submitted RST result-set index is unreadable or contains another load step")
            return False
        mapdl.set("LAST")
        required_run(mapdl, "RSYS,0")
        if int(round(required_get(mapdl, "ACTIVE", 0, "ANTY"))) != 0:
            log("ANSYS result analysis type is not static")
            return False
        result_load_step = int(round(required_get(mapdl, "ACTIVE", 0, "SET", "LSTP")))
        result_set_number = int(round(required_get(mapdl, "ACTIVE", 0, "SET", "NSET")))
        if result_load_step != 1 or result_set_number != result_sets[-1]["set"]:
            log("ANSYS result does not contain the completed static result set")
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
        submitted_signature = ansys_nodal_result_signature(mapdl, expected_sets["ALL"], required_stress_nodes)
        submitted_solid_signature = ansys_solid_stress_signature(mapdl, db_connectivity)
        if submitted_signature is None or submitted_solid_signature is None:
            log("ANSYS submitted RST contains missing or non-finite nodal U/S data")
            return False
        end_displacement = sum(
            submitted_signature[label][0][0] for label in expected_sets["FREE"]
        ) / len(expected_sets["FREE"])
        max_stress = max(values[1][-1] for values in submitted_signature.values() if values[1] is not None)
        reaction_resultant = -fixed_reaction[0]
        if not (0.010 < end_displacement < 0.020 and 7.5 < max_stress < 16.0):
            log("native ANSYS metrics are outside physical sanity bounds")
            return False
        if not close_enough(reaction_resultant, 800.0, rel=1.0e-3, abs_tol=0.5):
            log("ANSYS fixed-face reaction does not balance the required 800 N tensile load")
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
        if not close_enough(end_displacement, submitted_metrics["end_displacement"], rel=1.0e-3, abs_tol=1.0e-7):
            log("metrics.json end_displacement does not match mean RST global U1 over the complete X=120 face")
            return False
        if not close_enough(max_stress, submitted_metrics["max_stress"], rel=1.0e-3, abs_tol=0.01):
            log("metrics.json max_stress does not match the complete native nodal-extrapolated RST equivalent-stress field")
            return False
        required_run(mapdl, "FINISH")
        mapdl.resume(str(model_path.with_suffix("")), "db")
        required_run(mapdl, "/FILNAME,%s,1" % mapdl_jobname)
        required_run(mapdl, "/SOLU")
        required_run(mapdl, "ALLSEL,ALL")
        required_run(mapdl, "SOLVE")
        required_run(mapdl, "FINISH")
        rechecked_rst_path = temp_root / (mapdl_jobname + ".rst")
        if not is_nonempty(rechecked_rst_path):
            log("ANSYS independent re-solve did not create a nonempty RST")
            return False
        try:
            rechecked_coords, rechecked_elements, rechecked_nsets, rechecked_times, rechecked_ens = read_ansys_rst_mesh(rechecked_rst_path)
        except Exception as exc:
            log("ANSYS independent re-solve RST cannot be read: %s" % exc)
            return False
        rechecked_coordinate_match = set(rechecked_coords) == set(rst_coords) and all(
            all(
                close_enough(actual, expected, rel=1.0e-8, abs_tol=1.0e-8)
                for actual, expected in zip(rechecked_coords[label], rst_coords[label])
            )
            for label in rst_coords
        )
        if not rechecked_coordinate_match or rechecked_elements != rst_elements or rechecked_nsets < 1:
            log("ANSYS independent re-solve RST mesh does not match the submitted DB/RST")
            return False
        required_run(mapdl, "/POST1")
        mapdl.file(str(rechecked_rst_path.with_suffix("")), "rst")
        rechecked_sets = parse_result_set_listing(required_run(mapdl, "SET,LIST"))
        if (
            rechecked_sets is None
            or len(rechecked_sets) != rechecked_nsets
            or any(row["load_step"] != 1 for row in rechecked_sets)
            or any(
                not close_enough(row["time"], rechecked_times[index], rel=1.0e-8, abs_tol=1.0e-10)
                for index, row in enumerate(rechecked_sets)
            )
        ):
            log("ANSYS independent re-solve RST result-set index is invalid")
            return False
        mapdl.set("LAST")
        required_run(mapdl, "RSYS,0")
        if (
            int(round(required_get(mapdl, "ACTIVE", 0, "ANTY"))) != 0
            or int(round(required_get(mapdl, "ACTIVE", 0, "SET", "LSTP"))) != 1
            or int(round(required_get(mapdl, "ACTIVE", 0, "SET", "NSET"))) != rechecked_sets[-1]["set"]
        ):
            log("ANSYS independent re-solve did not select the final static load-step-1 result")
            return False
        required_run(mapdl, "NSEL,NONE")
        for label in sorted(expected_sets["FIXED"]):
            required_run(mapdl, "NSEL,A,NODE,,%d" % label)
        rechecked_reactions = ansys_reaction_signature(mapdl, expected_sets["FIXED"])
        required_run(mapdl, "ALLSEL,ALL")
        rechecked_signature = ansys_nodal_result_signature(mapdl, expected_sets["ALL"], required_stress_nodes)
        rechecked_solid_signature = ansys_solid_stress_signature(mapdl, db_connectivity)
        if (
            not ansys_signatures_match(submitted_signature, rechecked_signature)
            or not ansys_solid_signatures_match(submitted_solid_signature, rechecked_solid_signature)
            or not ansys_reaction_signatures_match(submitted_reactions, rechecked_reactions)
            or not ansys_ens_signatures_match(submitted_ens, rechecked_ens)
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
