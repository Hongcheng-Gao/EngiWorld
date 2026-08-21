# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import math
import os
import re
import shutil
import site
import subprocess
import sys
import tempfile
import time
from pathlib import Path


TASK_ID = "c-open-abaqus-ansys-autocad-task-16-windows"
JOB_NAME = "task16_eval_resolve"
STEP_NAME = "Static-Pressure"
METRIC_FIELDS = ("radial_displacement", "max_stress")
ABAQUS_COMMAND = r"C:\SIMULIA\CAE\2025LE\win_b64\code\bin\SMALauncherLE.exe"
ANSYS_EXEC = r"C:\Program Files\ANSYS Inc\v261\ansys\bin\winx64\ANSYS261.exe"
DESKTOP_CANDIDATES = [
    Path(os.environ.get("USERPROFILE", r"C:\Users\user")) / "Desktop",
    Path(r"C:\Users\user\Desktop"),
    Path(r"C:\Users\User\Desktop"),
]
DETAILS = []
_ANSYS_RUNTIME = None
OWNED_TEMP_DIRS = []


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
        def pairs(values):
            output = {}
            for key, value in values:
                if key in output:
                    raise ValueError("duplicate JSON key: %s" % key)
                output[key] = value
            return output

        def invalid_constant(value):
            raise ValueError("non-finite JSON value: %s" % value)

        data = json.loads(
            path.read_text(encoding="utf-8-sig"),
            object_pairs_hook=pairs,
            parse_constant=invalid_constant,
        )
    except Exception as exc:
        log("metrics.json is invalid: %s" % exc)
        return None
    if not isinstance(data, dict):
        log("metrics.json must be an object")
        return None
    if set(data) != set(METRIC_FIELDS) or any(not finite_number(data[name]) for name in METRIC_FIELDS):
        log("metrics.json must contain exactly two finite numeric task metrics")
        return None
    metrics = {name: float(data[name]) for name in METRIC_FIELDS}
    if not (1.0e-4 < metrics["radial_displacement"] < 0.02):
        log("radial_displacement is outside the task-specific physical range")
        return None
    if not (10.0 < metrics["max_stress"] < 60.0):
        log("max_stress is outside the task-specific physical range")
        return None
    return metrics


def discover_branch(root):
    caes = files_with_suffix(root, ".cae")
    odbs = files_with_suffix(root, ".odb")
    dbs = files_with_suffix(root, ".db")
    rsts = files_with_suffix(root, ".rst")
    unsupported = sum((files_with_suffix(root, suffix) for suffix in (".rth", ".wbpj", ".dwg", ".dxf")), [])
    if unsupported:
        log("unsupported or decoy native artifacts are present")
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
        return "abaqus", caes[0], odbs[0]
    if has_ansys:
        if len(dbs) != 1 or len(rsts) != 1:
            log("ANSYS delivery requires exactly one DB and one RST")
            return None
        return "ansys", dbs[0], rsts[0]
    log("no supported native model/result pair found")
    return None


def close_enough(actual, expected, rel=1.0e-3, abs_tol=1.0e-8):
    try:
        return math.isclose(float(actual), float(expected), rel_tol=rel, abs_tol=abs_tol)
    except Exception:
        return False


def ansys_runtime():
    global _ANSYS_RUNTIME
    if _ANSYS_RUNTIME is not None:
        return _ANSYS_RUNTIME
    package_candidates = []
    appdata = os.environ.get("APPDATA")
    if appdata:
        package_candidates.append(
            str(Path(appdata) / "Python" / "Python311" / "site-packages")
        )
    try:
        package_candidates.append(site.getusersitepackages())
    except Exception:
        pass
    for candidate in package_candidates:
        if isinstance(candidate, str) and Path(candidate).is_dir() and candidate not in sys.path:
            sys.path.insert(0, candidate)
    saved_userprofile = os.environ.get("USERPROFILE")
    try:
        if appdata:
            os.environ["USERPROFILE"] = str(Path(appdata).parent.parent)
        from ansys.mapdl import reader as pymapdl_reader
        from ansys.mapdl.core import launch_mapdl
    finally:
        if saved_userprofile is None:
            os.environ.pop("USERPROFILE", None)
        else:
            os.environ["USERPROFILE"] = saved_userprofile
    _ANSYS_RUNTIME = (launch_mapdl, pymapdl_reader)
    return _ANSYS_RUNTIME


def cleanup_owned_processes(work):
    if os.name != "nt":
        return True
    query = (
        "Get-CimInstance Win32_Process | "
        "Select-Object ProcessId,Name,ExecutablePath,CommandLine | "
        "ConvertTo-Json -Compress"
    )
    try:
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", query],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            return False
        rows = [] if not result.stdout.strip() else json.loads(result.stdout)
        if isinstance(rows, dict):
            rows = [rows]
        marker = str(work).lower()
        allowed = {
            "python.exe", "ansys.exe", "ansys261.exe", "ansyscl.exe",
            "smalauncherle.exe", "abqlauncher.exe", "abq2025le.exe",
            "pre.exe", "standard.exe", "package.exe", "mpiexec.exe",
            "hydra_service.exe", "hydra_bstrap_proxy.exe", "hydra_pmi_proxy.exe",
        }
        owned = []
        for row in rows:
            command = str(row.get("CommandLine") or "")
            if marker not in command.lower():
                continue
            executable = Path(str(row.get("ExecutablePath") or ""))
            name = (executable.name or str(row.get("Name") or "")).lower()
            if name not in allowed:
                return False
            pid = int(row.get("ProcessId") or 0)
            if pid > 0 and pid != os.getpid():
                owned.append(pid)
        for pid in sorted(set(owned), reverse=True):
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                capture_output=True,
                text=True,
                timeout=60,
            )
        time.sleep(0.5)
        probe = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", query],
            capture_output=True,
            text=True,
            timeout=60,
        )
        return probe.returncode == 0 and marker not in probe.stdout.lower()
    except Exception:
        return False


def run_abaqus_checker(cae_path, odb_path, submitted_metrics):
    temp_root = Path(tempfile.mkdtemp(prefix="engiworld_task16_eval_abaqus_", dir=str(desktop_dir())))
    OWNED_TEMP_DIRS.append(temp_root)
    candidate_cae = temp_root / "candidate.cae"
    candidate_odb = temp_root / "candidate.odb"
    shutil.copy2(cae_path, candidate_cae)
    shutil.copy2(odb_path, candidate_odb)
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
JOB_NAME = "task16_eval_resolve"
STEP_NAME = "Static-Pressure"
ALLOWED_TYPES = (
    "CAX4", "CAX4H", "CAX4R", "CAX4RH",
    "CAX8", "CAX8H", "CAX8R", "CAX8RH",
)
EXPECTED_IP = {
    "CAX4": 4, "CAX4H": 4, "CAX4R": 1, "CAX4RH": 1,
    "CAX8": 9, "CAX8H": 9, "CAX8R": 4, "CAX8RH": 4,
}
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


def validate_input_output_request(job, expected_elements, material_name, mesh_coords, connectivity, step_name):
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
    current_card = None
    steps = []
    cards = []
    parse_error = None
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
                    key = key.strip().upper()
                    if key in params:
                        parse_error = "duplicate parameter on *%s: %s" % (keyword, key)
                    params[key] = value.strip()
                elif piece:
                    key = piece.upper()
                    if key in params:
                        parse_error = "duplicate parameter on *%s: %s" % (keyword, key)
                    params[key] = True
            current_card = {
                "keyword": keyword,
                "params": params,
                "data": [],
                "step": current_step,
                "part": current_part,
                "assembly": current_assembly,
            }
            if keyword == "STEP":
                current_step = params.get("NAME", "")
                steps.append(current_step)
                current_card["step"] = current_step
            elif keyword == "END STEP":
                current_card["step"] = current_step
                current_step = None
            elif keyword == "PART":
                current_part = params.get("NAME", "")
            elif keyword == "END PART":
                current_part = None
            elif keyword == "ASSEMBLY":
                current_assembly = params.get("NAME", "")
            elif keyword == "END ASSEMBLY":
                current_assembly = None
            cards.append(current_card)
            continue
        if current_card is not None:
            current_card["data"].append(line)
    if parse_error:
        return fail("CAE-generated input is ambiguous: " + parse_error)
    if len(steps) != 1 or steps[0].upper() != step_name.upper():
        return fail("CAE-generated input must contain the model's single static step")

    allowed_keywords = set((
        "HEADING", "PREPRINT", "PART", "END PART", "NODE", "ELEMENT",
        "NSET", "ELSET", "SOLID SECTION", "ASSEMBLY", "END ASSEMBLY",
        "INSTANCE", "END INSTANCE", "SURFACE", "MATERIAL", "ELASTIC",
        "DENSITY", "EXPANSION", "STEP", "STATIC", "BOUNDARY", "DSLOAD",
        "RESTART", "OUTPUT", "NODE OUTPUT", "ELEMENT OUTPUT", "END STEP",
    ))
    for card in cards:
        keyword = card["keyword"]
        if keyword not in allowed_keywords:
            return fail("unsupported or dangerous injected Abaqus keyword: *" + keyword)
        if any(name in card["params"] for name in ("INPUT", "FILE", "LIBRARY")):
            return fail("external Abaqus keyword data sources are not allowed")
        if keyword == "RESTART":
            if "READ" in card["params"] or "WRITE" not in card["params"]:
                return fail("only native restart-output requests are allowed")

    static_cards = [
        card for card in cards
        if card["keyword"] == "STATIC" and str(card["step"]).upper() == step_name.upper()
    ]
    if len(static_cards) != 1 or static_cards[0]["params"]:
        return fail("generated input must contain exactly one unmodified *STATIC procedure")

    def integer_token(value):
        try:
            text = str(value).strip()
            if not re.match(r"^[+-]?\d+$", text):
                return None
            return int(text)
        except Exception:
            return None

    def real_token(value):
        try:
            return float(str(value).strip().replace("D", "E").replace("d", "e"))
        except Exception:
            return None

    step_cards = [card for card in cards if card["keyword"] == "STEP"]
    if len(step_cards) != 1:
        return fail("generated input must contain exactly one *STEP card")
    step_params = step_cards[0]["params"]
    if set(step_params).difference(set(("NAME", "NLGEOM", "INC"))):
        return fail("generated *STEP contains unsupported analysis parameters")
    if str(step_params.get("NAME", "")).upper() != step_name.upper():
        return fail("generated *STEP name does not match the native model")
    if str(step_params.get("NLGEOM", "NO")).upper() not in ("NO", "OFF", "FALSE", "0"):
        return fail("generated *STEP enables geometric nonlinearity")
    if "INC" in step_params:
        increment_limit = integer_token(step_params["INC"])
        if increment_limit is None or increment_limit <= 0:
            return fail("generated *STEP increment limit is invalid")

    material_cards = [card for card in cards if card["keyword"] == "MATERIAL"]
    elastic_cards = [card for card in cards if card["keyword"] == "ELASTIC"]
    if len(material_cards) != 1 or len(elastic_cards) != 1:
        return fail("generated input must contain one material and one elastic definition")
    if (
        set(material_cards[0]["params"]) != set(("NAME",))
        or str(material_cards[0]["params"].get("NAME", "")).upper()
        != material_name.upper()
    ):
        return fail("generated material card does not match the verified steel material")
    elastic_params = elastic_cards[0]["params"]
    if set(elastic_params).difference(set(("TYPE",))) or str(
        elastic_params.get("TYPE", "ISOTROPIC")
    ).upper() != "ISOTROPIC":
        return fail("generated elastic definition must be isotropic and field-independent")
    elastic_rows = elastic_cards[0]["data"]
    if len(elastic_rows) != 1:
        return fail("generated elastic definition must contain one constant property row")
    elastic_values = [value.strip() for value in elastic_rows[0].split(",")]
    while elastic_values and elastic_values[-1] == "":
        elastic_values.pop()
    if (
        len(elastic_values) != 2
        or real_token(elastic_values[0]) is None
        or real_token(elastic_values[1]) is None
        or not close(real_token(elastic_values[0]), 210000.0)
        or not close(real_token(elastic_values[1]), 0.3)
    ):
        return fail("generated elastic constants are not E=210000 MPa and nu=0.3")

    def set_scope(card):
        instance_name = str(card["params"].get("INSTANCE", "")).strip().upper()
        if instance_name:
            return "INSTANCE:" + instance_name
        if card.get("part"):
            return "PART:" + str(card["part"]).strip().upper()
        if card.get("assembly"):
            return "ASSEMBLY:" + str(card["assembly"]).strip().upper()
        return "GLOBAL"

    nodeset_definitions = {}
    for card in cards:
        if card["keyword"] != "NSET":
            continue
        name = str(card["params"].get("NSET", "")).strip().upper()
        if not name:
            return fail("generated input contains a nameless *NSET")
        key = (set_scope(card), name)
        values = nodeset_definitions.setdefault(key, [])
        tokens = [token.strip() for row in card["data"] for token in row.split(",") if token.strip()]
        if "GENERATE" in card["params"]:
            if len(tokens) % 3:
                return fail("generated node-set range is malformed")
            for index in range(0, len(tokens), 3):
                first = integer_token(tokens[index])
                last = integer_token(tokens[index + 1])
                increment = integer_token(tokens[index + 2])
                if first is None or last is None or increment is None or increment <= 0 or first > last:
                    return fail("generated node-set range is malformed")
                values.extend(range(first, last + 1, increment))
        else:
            for token in tokens:
                number = integer_token(token)
                values.append(number if number is not None else token.upper())

    def candidate_nodeset_keys(name, preferred_scope=None):
        text = str(name).strip().upper()
        qualifier = None
        local_name = text
        if "." in text:
            qualifier, local_name = text.rsplit(".", 1)
        candidates = []
        for key in nodeset_definitions:
            scope, candidate_name = key
            if candidate_name != local_name and candidate_name != text:
                continue
            if qualifier and not (scope.endswith(":" + qualifier) or candidate_name == text):
                # Abaqus commonly qualifies a part-level set by its instance name.
                if not scope.startswith("PART:"):
                    continue
            candidates.append(key)
        if preferred_scope is not None:
            preferred = [key for key in candidates if key[0] == preferred_scope]
            if preferred:
                return preferred
        return candidates

    def qualified_numeric_label(value):
        text = str(value).strip().upper()
        number = integer_token(text)
        if number is not None:
            return number
        if "." in text:
            return integer_token(text.rsplit(".", 1)[1])
        return None

    def resolve_nodeset_key(key, stack):
        if key in stack:
            return None
        result = set()
        for value in nodeset_definitions.get(key, []):
            label = qualified_numeric_label(value)
            if label is not None:
                result.add(label)
                continue
            candidates = candidate_nodeset_keys(value, key[0])
            resolved = []
            for candidate in candidates:
                labels = resolve_nodeset_key(candidate, stack | set((key,)))
                if labels is not None:
                    resolved.append(labels)
            if not resolved or any(labels != resolved[0] for labels in resolved[1:]):
                return None
            result.update(resolved[0])
        return result

    def resolve_node_target(value):
        label = qualified_numeric_label(value)
        if label is not None:
            return set((label,)) if label in mesh_coords else None
        resolved = []
        for key in candidate_nodeset_keys(value):
            labels = resolve_nodeset_key(key, set())
            if labels is not None:
                resolved.append(labels)
        if not resolved or any(labels != resolved[0] for labels in resolved[1:]):
            return None
        if not resolved[0] or not resolved[0].issubset(set(mesh_coords)):
            return None
        return resolved[0]

    expected_axial_nodes = set(
        label for label, xyz in mesh_coords.items()
        if close(xyz[1], 0.0) or close(xyz[1], 10.0)
    )
    initial_boundary_cards = []
    step_boundary_cards = []
    for card in cards:
        if card["keyword"] != "BOUNDARY":
            continue
        card_step = str(card["step"] or "").upper()
        if card_step and card_step != step_name.upper():
            return fail("a boundary condition appears outside the verified static history")
        unknown_params = set(card["params"]).difference(set(("OP",)))
        operation = str(card["params"].get("OP", "MOD")).upper()
        if unknown_params or operation not in ("MOD", "NEW"):
            return fail("generated *BOUNDARY uses unsupported parameters")
        (step_boundary_cards if card_step else initial_boundary_cards).append(card)

    effective_boundary = {}

    def apply_boundary_cards(boundary_cards, clear_first):
        if clear_first:
            effective_boundary.clear()
        for card in boundary_cards:
            if not card["data"]:
                return fail("generated *BOUNDARY contains no data")
            for row in card["data"]:
                fields = [value.strip() for value in row.split(",")]
                while fields and fields[-1] == "":
                    fields.pop()
                if len(fields) < 2 or len(fields) > 4:
                    return fail("generated boundary row is malformed")
                labels = resolve_node_target(fields[0])
                first_dof = integer_token(fields[1])
                last_dof = first_dof if len(fields) < 3 or fields[2] == "" else integer_token(fields[2])
                magnitude = 0.0 if len(fields) < 4 or fields[3] == "" else real_token(fields[3])
                if not labels:
                    return fail("generated boundary target cannot be resolved")
                if not labels.issubset(expected_axial_nodes):
                    return fail("generated boundary constrains a node away from Y=0 or Y=10")
                if first_dof != 2 or last_dof != 2 or magnitude is None or not close(magnitude, 0.0):
                    return fail("generated boundary must constrain only U2 to zero")
                for label in labels:
                    effective_boundary[(label, 2)] = 0.0
        return True

    if not apply_boundary_cards(initial_boundary_cards, False):
        return False
    if step_boundary_cards:
        operations = set(str(card["params"].get("OP", "MOD")).upper() for card in step_boundary_cards)
        if len(operations) != 1:
            return fail("generated step mixes incompatible *BOUNDARY operations")
        if not apply_boundary_cards(step_boundary_cards, "NEW" in operations):
            return False
    if set(label for label, dof in effective_boundary) != expected_axial_nodes:
        return fail("generated boundary does not constrain exactly the complete Y=0 and Y=10 edges")

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
        if card["params"].get("MATERIAL", "").upper() == material_name.upper():
            steel_coverage.update(labels)
        else:
            other_coverage.update(labels)
    if steel_coverage != expected_elements or other_coverage.intersection(expected_elements):
        return fail("CAE-generated input does not assign the verified material to every cylinder element")

    surfaces = {}
    for card in cards:
        if card["keyword"] == "SURFACE":
            name = card["params"].get("NAME", "").upper()
            if str(card["params"].get("TYPE", "")).upper() != "ELEMENT":
                return fail("generated pressure geometry must use an element surface")
            surfaces.setdefault(name, []).extend(card["data"])
    distributed = []
    for card in cards:
        if card["keyword"] != "DSLOAD":
            continue
        if str(card["step"]).upper() != step_name.upper():
            return fail("distributed load appears outside the verified static step")
        unknown_params = set(card["params"]).difference(set(("OP",)))
        operation = str(card["params"].get("OP", "MOD")).upper()
        if unknown_params or operation not in ("MOD", "NEW"):
            return fail("generated *DSLOAD uses amplitude or other unsupported parameters")
        if operation == "NEW":
            distributed = []
        distributed.extend(card["data"])
    if not distributed:
        return fail("generated input contains no distributed surface pressure")
    side_nodes = {1: (0, 1), 2: (1, 2), 3: (2, 3), 4: (3, 0)}
    expected_inner_edges = set()
    for label in connectivity:
        conn = connectivity[label][1]
        for edge in side_nodes.values():
            points = [mesh_coords[conn[index]] for index in edge]
            if all(close(point[0], 25.0) for point in points):
                expected_inner_edges.add(tuple(sorted(conn[index] for index in edge)))
    if len(expected_inner_edges) != 2:
        return fail("verified mesh does not expose two complete inner-wall segments")
    loaded_edges = set()
    for distributed_row in distributed:
        load_row = [value.strip() for value in distributed_row.split(",")]
        while load_row and load_row[-1] == "":
            load_row.pop()
        if len(load_row) != 3 or load_row[1].upper() != "P":
            return fail("generated load must use Abaqus surface pressure P")
        pressure = real_token(load_row[2])
        if pressure is None or not close(pressure, 10.0):
            return fail("generated inner pressure is not 10 MPa")
        surface_rows = surfaces.get(load_row[0].upper(), [])
        if not surface_rows:
            return fail("generated pressure surface cannot be resolved")
        for row in surface_rows:
            values = [value.strip() for value in row.split(",") if value.strip()]
            if len(values) != 2 or not values[1].upper().startswith("S"):
                return fail("generated pressure surface uses an unsupported side")
            try:
                side = int(values[1][1:])
            except Exception:
                return fail("generated pressure side is unreadable")
            labels = resolve_elset(values[0], set())
            if side not in side_nodes or not labels:
                return fail("generated pressure surface references no valid element face")
            for label in labels:
                if label not in connectivity:
                    return fail("pressure references an element outside the verified mesh")
                conn = connectivity[label][1]
                edge = side_nodes[side]
                facet = tuple(sorted(conn[index] for index in edge))
                if facet not in expected_inner_edges:
                    return fail("pressure is applied anywhere other than the inner X=25 wall")
                if facet in loaded_edges:
                    return fail("pressure regions overlap on an inner-wall segment")
                loaded_edges.add(facet)
    if loaded_edges != expected_inner_edges:
        return fail("pressure does not cover the complete two-segment inner wall")

    node_variables = set()
    element_variables = set()
    uses_preselect = False
    for card in cards:
        if str(card["step"]).upper() != step_name.upper():
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
            uses_preselect = True
    if not uses_preselect and ("U" not in node_variables or "S" not in element_variables):
        return fail("CAE field output request must include nodal U and element S")
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
    dimensionality = getattr(part, "dimensionality", None)
    embedded_space = getattr(part, "embeddedSpace", None)
    actual_space = dimensionality if dimensionality is not None else embedded_space
    if actual_space is not None and str(actual_space).upper() != "AXISYMMETRIC":
        return fail(
            "part dimensionality is not AXISYMMETRIC: dimensionality=%r embeddedSpace=%r"
            % (dimensionality, embedded_space)
        )
    if len(part.elements) != 10:
        return fail("mesh must contain ten mapped 5 mm by 5 mm elements")
    element_types = set(str(element.type).upper() for element in part.elements)
    if len(element_types) != 1 or not element_types.issubset(set(ALLOWED_TYPES)):
        return fail("all elements must use one supported CAX4/CAX8 axisymmetric quadrilateral type")
    element_type = next(iter(element_types))
    expected_nodes = 18 if element_type.startswith("CAX4") else 45
    if len(part.nodes) != expected_nodes:
        return fail("node count does not match a structured 5 mm %s mesh" % element_type)
    coords = coords_by_label(part.nodes)
    actual_points = set(
        (round(xyz[0], 6), round(xyz[1], 6)) for xyz in coords.values()
    )
    if element_type.startswith("CAX4"):
        expected_points = set(
            (float(25 + 5 * i), float(5 * j))
            for i in range(6)
            for j in range(3)
        )
    else:
        expected_points = set(
            (float(25 + 2.5 * i), float(2.5 * j))
            for i in range(11)
            for j in range(5)
            if i % 2 == 0 or j % 2 == 0
        )
    if actual_points != expected_points or len(actual_points) != len(coords):
        return fail("nodes do not form the complete linear/quadratic 5 mm structured lattice")
    boxes = set()
    attached_nodes = set()
    for element in part.elements:
        nodes = element_nodes(part, element)
        labels = set(int(node.label) for node in nodes)
        if len(labels) != (4 if element_type.startswith("CAX4") else 8):
            return fail("an element has incomplete or degenerate quadrilateral connectivity")
        attached_nodes.update(labels)
        xs = [float(node.coordinates[0]) for node in nodes]
        ys = [float(node.coordinates[1]) for node in nodes]
        box = (round(min(xs), 6), round(max(xs), 6), round(min(ys), 6), round(max(ys), 6))
        if not close(box[1] - box[0], 5.0) or not close(box[3] - box[2], 5.0):
            return fail("an element does not span one 5 mm by 5 mm mapped cell")
        middle_x = 0.5 * (box[0] + box[1])
        middle_y = 0.5 * (box[2] + box[3])
        expected_element_points = set(
            (
                (box[0], box[2]),
                (box[1], box[2]),
                (box[1], box[3]),
                (box[0], box[3]),
            )
        )
        if element_type.startswith("CAX8"):
            expected_element_points.update(
                (
                    (middle_x, box[2]),
                    (box[1], middle_y),
                    (middle_x, box[3]),
                    (box[0], middle_y),
                )
            )
        actual_element_points = set(
            (round(node.coordinates[0], 6), round(node.coordinates[1], 6))
            for node in nodes
        )
        if actual_element_points != expected_element_points:
            return fail("an element is not a complete mapped quadrilateral cell")
        boxes.add(box)
    expected_boxes = set(
        (float(25 + 5 * i), float(30 + 5 * i), float(5 * j), float(5 + 5 * j))
        for j in range(2)
        for i in range(5)
    )
    if boxes != expected_boxes or attached_nodes != set(coords):
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
        "INNER": set(label for label, xyz in coords.items() if close(xyz[0], 25.0)),
        "OUTER": set(label for label, xyz in coords.items() if close(xyz[0], 50.0)),
        "ZMIN": set(label for label, xyz in coords.items() if close(xyz[1], 0.0)),
        "ZMAX": set(label for label, xyz in coords.items() if close(xyz[1], 10.0)),
    }
    return expected


def validate_model(database):
    if len(database.models.keys()) != 1:
        return fail("CAE must contain exactly one model without decoys")
    model_name = str(database.models.keys()[0])
    model = database.models[model_name]
    meshed_parts = [model.parts[name] for name in model.parts.keys() if len(model.parts[name].elements)]
    if len(meshed_parts) != 1 or len(model.parts.keys()) != 1:
        return fail("model must contain exactly one meshed cylinder part")
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
        close(min(xs), 25.0)
        and close(max(xs), 50.0)
        and close(min(ys), 0.0)
        and close(max(ys), 10.0)
        and close(min(zs), 0.0)
        and close(max(zs), 0.0)
    ):
        return fail("part geometry is not X=25..50, Y=0..10")
    element_type = validate_structured_mesh(part)
    if not element_type:
        return False
    expected_sets = validate_sets(model, part, coords)
    if not expected_sets:
        return False

    if len(model.materials.keys()) != 1 or len(model.sections.keys()) != 1:
        return fail("analysis model must contain one material and one section")
    material_name = str(model.materials.keys()[0])
    try:
        material = model.materials[material_name]
        elastic_object = material.elastic
        elastic = elastic_object.table[0]
    except Exception:
        return fail("linear elastic material data is missing")
    if (
        str(getattr(elastic_object, "type", "")).upper() != "ISOTROPIC"
        or len(elastic_object.table) != 1
        or len(elastic) != 2
        or not close(elastic[0], 210000.0)
        or not close(elastic[1], 0.3)
    ):
        return fail("used material must be isotropic E=210000 MPa, nu=0.3")
    section = model.sections[model.sections.keys()[0]]
    if section.__class__.__name__ != "HomogeneousSolidSection" or str(section.material) != material_name:
        return fail("used section must be one homogeneous steel section")
    assignments = list(part.sectionAssignments)
    if len(assignments) != 1 or str(assignments[0].sectionName) != str(section.name):
        return fail("the complete cylinder must have one unambiguous section assignment")

    bcs = active_named_objects(model.boundaryConditions)
    step_names = [name for name in model.steps.keys() if str(name).upper() != "INITIAL"]
    if len(model.steps.keys()) != 2 or len(step_names) != 1:
        return fail("model must contain Initial and one analysis step")
    step_name = str(step_names[0])
    step = model.steps[step_name]
    if step.__class__.__name__ != "StaticStep":
        return fail("model must contain Initial and one StaticStep")
    if str(getattr(step, "nlgeom", "OFF")).upper() not in ("OFF", "FALSE", "0"):
        return fail("static analysis must be linear")
    expected_axial_nodes = expected_sets["ZMIN"].union(expected_sets["ZMAX"])
    constrained_nodes = set()
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
        if state_is_unset(getattr(bc_state, "u2State", None)) or not close(getattr(bc_state, "u2", None), 0.0):
            return fail("each axial-face BC must set U2=0")
        for component in ("u3", "ur1", "ur2", "ur3"):
            if not state_is_unset(getattr(bc_state, component + "State", None)):
                return fail("active displacement BC contains an extra constrained component")
        if not labels.issubset(expected_axial_nodes):
            return fail("an active U2 BC includes a node away from Y=0 or Y=10")
        constrained_nodes.update(labels)
    if constrained_nodes != expected_axial_nodes:
        return fail("active displacement BCs must cover exactly the complete Y=0 and Y=10 edges in U2")
    if active_objects(model.constraints) or active_objects(model.interactions) or active_objects(model.predefinedFields):
        return fail("additional constraints, interactions, or predefined fields are not allowed")

    loads = active_named_objects(model.loads)
    active_loads = []
    for load_name, load in loads:
        if load_name not in step.loadStates.keys():
            continue
        load_state = step.loadStates[load_name]
        if not state_is_active(load_state):
            continue
        if load.__class__.__name__ != "Pressure":
            return fail("only native Pressure loads are permitted")
        magnitude = getattr(load_state, "magnitude", None)
        if not close(magnitude, 10.0):
            return fail("active pressure magnitude must be 10 MPa")
        active_loads.append(load)
    if not active_loads:
        return fail("at least one active 10 MPa Pressure is required")
    connectivity = dict(
        (
            int(element.label),
            (str(element.type).upper(), tuple(int(node.label) for node in element_nodes(part, element))),
        )
        for element in part.elements
    )
    element_labels = set(connectivity)
    if JOB_NAME in database.jobs.keys():
        del database.jobs[JOB_NAME]
    job = database.Job(name=JOB_NAME, model=model_name, numCpus=1, numDomains=1)
    if not validate_input_output_request(job, element_labels, material_name, coords, connectivity, step_name):
        return False
    return {
        "model_name": model_name,
        "part": part,
        "coords": coords,
        "element_type": element_type,
        "sets": expected_sets,
        "elements": element_labels,
        "connectivity": connectivity,
        "step_time": float(getattr(step, "timePeriod", 1.0)),
        "step_name": step_name,
        "job": job,
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
        if list(odb.steps.keys()) != [model_info["step_name"]]:
            return fail("ODB must contain the CAE model's single analysis step")
        step = odb.steps[model_info["step_name"]]
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

        for name in ("U", "S"):
            if name not in frame.fieldOutputs.keys():
                return fail("ODB final frame is missing field " + name)
        all_nodes = set(model_info["coords"])
        for name in ("U",):
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
        axial_faces = model_info["sets"]["ZMIN"].union(model_info["sets"]["ZMAX"])
        for value in frame.fieldOutputs["U"].values:
            if int(value.nodeLabel) in axial_faces and abs(float(value.data[1])) > 1.0e-10:
                return fail("final U2 violates an axial-face zero-displacement BC")

        stress_counts = {}
        mises = []
        signature = {"U": {}, "S": {}}
        for name in ("U",):
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
        expected_ip = EXPECTED_IP[model_info["element_type"]]
        if set(stress_counts) != model_info["elements"] or any(count != expected_ip for count in stress_counts.values()):
            return fail("integration-point S output is incomplete or region-restricted")
        radial = max(float(value.data[0]) for value in frame.fieldOutputs["U"].values)
        maximum = max(mises) if mises else None
        if radial is None or maximum is None or not math.isfinite(radial) or not math.isfinite(maximum):
            return fail("native metrics could not be extracted")
        if not (1.0e-4 < radial < 0.02 and 10.0 < maximum < 60.0):
            return fail("native Abaqus metrics are outside physical sanity bounds")
        if compare_submitted_metrics:
            if not close(radial, SUBMITTED["radial_displacement"], rel=1.0e-3, abs_tol=2.0e-6):
                return fail("metrics.json radial_displacement does not match ODB maximum outward U1")
            if not close(maximum, SUBMITTED["max_stress"], rel=1.0e-3, abs_tol=0.05):
                return fail("metrics.json max_stress does not match ODB integration-point S")
        return {
            "metrics": {"radial_displacement": radial, "max_stress": maximum},
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
                job = model_info["job"]
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
    checker_source = checker_source.replace("__CAE_PATH__", repr(str(candidate_cae)))
    checker_source = checker_source.replace("__ODB_PATH__", repr(str(candidate_odb)))
    checker_source = checker_source.replace("__RESULT_PATH__", repr(str(result_path)))
    checker_source = checker_source.replace("__SUBMITTED__", repr(submitted_metrics))
    checker_path.write_text(checker_source, encoding="utf-8")
    passed = False
    cleanup_ok = False
    try:
        completed = subprocess.run(
            [ABAQUS_COMMAND, "cae", "noGUI=" + str(checker_path), "--"],
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
        process_cleanup_ok = cleanup_owned_processes(temp_root)
        if not process_cleanup_ok:
            log("Abaqus evaluator process cleanup was incomplete")
        cleanup_ok = remove_tree_with_retries(temp_root) and process_cleanup_ok
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


ANSYS_NUMBER = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[EeDd][-+]?\d+)?"


def ansys_number(value):
    return float(str(value).replace("D", "E").replace("d", "e"))


def parse_element_pressure_listing(text, title):
    upper = (text or "").upper()
    if (
        title not in upper
        or "ELEMENT" not in upper
        or "LKEY" not in upper
        or "FACE NODES" not in upper
        or "IMAGINARY" not in upper
    ):
        return None
    first_pattern = re.compile(
        r"^\s*(\d+)\s+(\d+)\s+(\d+)\s+(%s)\s+(%s)\s*$"
        % (ANSYS_NUMBER, ANSYS_NUMBER),
        re.IGNORECASE,
    )
    continuation_pattern = re.compile(
        r"^\s*(\d+)\s+(%s)\s+(%s)\s*$" % (ANSYS_NUMBER, ANSYS_NUMBER),
        re.IGNORECASE,
    )
    blocks = []
    current = None
    for line in (text or "").splitlines():
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
        if continuation is not None and current is not None:
            current["nodes"].append(int(continuation.group(1)))
            current["real"].append(ansys_number(continuation.group(2)))
            current["imag"].append(ansys_number(continuation.group(3)))
    return blocks if blocks else None


def pressure_block_signature(blocks, expected_nodes_per_edge):
    if not blocks:
        return None
    signature = set()
    element_keys = set()
    for block in blocks:
        element_key = (block["element"], block["lkey"])
        facet = (block["element"], frozenset(block["nodes"]))
        if (
            element_key in element_keys
            or facet in signature
            or len(block["nodes"]) != expected_nodes_per_edge
            or len(set(block["nodes"])) != expected_nodes_per_edge
            or any(abs(value) > 1.0e-12 for value in block["imag"])
            or any(
                not close_enough(value, 10.0, rel=1.0e-6, abs_tol=1.0e-6)
                for value in block["real"]
            )
        ):
            return None
        element_keys.add(element_key)
        signature.add(facet)
    return signature


def structured_ansys_lattice_matches(coords, element_code):
    actual = [(float(row[0]), float(row[1])) for row in coords.values()]
    if len(actual) != len(set((round(x, 8), round(y, 8)) for x, y in actual)):
        return False
    if element_code == 182:
        expected = [(25.0 + 5.0 * i, 5.0 * j) for j in range(3) for i in range(6)]
    elif element_code == 183:
        expected = [
            (25.0 + 2.5 * i, 2.5 * j)
            for j in range(5)
            for i in range(11)
            if not (i % 2 == 1 and j % 2 == 1)
        ]
    else:
        return False
    if len(actual) != len(expected):
        return False
    unmatched = list(actual)
    for expected_x, expected_y in expected:
        matches = [
            index
            for index, (actual_x, actual_y) in enumerate(unmatched)
            if close_enough(actual_x, expected_x, rel=1.0e-8, abs_tol=1.0e-7)
            and close_enough(actual_y, expected_y, rel=1.0e-8, abs_tol=1.0e-7)
        ]
        if len(matches) != 1:
            return False
        unmatched.pop(matches[0])
    return not unmatched


def cdb_ansys_state_is_supported(export_text, material_id):
    saw_pressure_storage = False
    active_elastic_table = False
    elastic_constants = {}
    forbidden_state = {
        "IC", "INISTATE", "INRES", "LDREAD", "LDWRITE", "LREAD", "UPGEOM",
    }
    for raw in (export_text or "").splitlines():
        line = raw.split("!", 1)[0].strip()
        if not line:
            continue
        fields = [field.strip() for field in line.split(",")]
        command = fields[0].upper()
        if command in forbidden_state:
            return False
        if command == "SFEBLOCK":
            if len(fields) < 3 or fields[2].upper() != "PRES":
                return False
            saw_pressure_storage = True
        elif command == "SFE":
            if len(fields) >= 2 and fields[1].upper() == "END":
                if len(fields) < 4 or fields[2].upper() != "LOC" or fields[3] != "-1":
                    return False
            elif len(fields) < 4 or fields[3].upper() != "PRES":
                return False
            else:
                saw_pressure_storage = True
        elif command in ("SF", "SFA", "SFL", "SFBLOCK"):
            return False
        elif command == "TB":
            if (
                active_elastic_table
                or len(fields) < 3
                or fields[1].upper() not in ("ELASTIC", "ELAS")
            ):
                return False
            try:
                table_material = int(float(fields[2]))
                temperature_count = 1 if len(fields) < 4 or not fields[3] else int(float(fields[3]))
                constant_count = 2 if len(fields) < 5 or not fields[4] else int(float(fields[4]))
            except Exception:
                return False
            table_option = "ISOT" if len(fields) < 6 or not fields[5] else fields[5].upper()
            if (
                table_material != int(material_id)
                or temperature_count != 1
                or constant_count != 2
                or table_option not in ("ISOT", "ISO")
            ):
                return False
            active_elastic_table = True
        elif command == "TBTEMP":
            if not active_elastic_table:
                return False
            try:
                temperature = ansys_number(fields[1])
            except Exception:
                return False
            if not math.isfinite(temperature) or abs(temperature) > 1.0e-12:
                return False
        elif command == "TBDATA":
            if not active_elastic_table:
                return False
            try:
                start = 1 if len(fields) < 2 or not fields[1] else int(float(fields[1]))
                values = [ansys_number(value) for value in fields[2:] if value]
            except Exception:
                return False
            if start < 1 or not values or any(not math.isfinite(value) for value in values):
                return False
            for offset, value in enumerate(values):
                slot = start + offset
                if slot not in (1, 2) or slot in elastic_constants:
                    return False
                elastic_constants[slot] = value
        elif command.startswith("TB"):
            return False
    if active_elastic_table and (
        set(elastic_constants) != {1, 2}
        or not close_enough(elastic_constants[1], 210000.0, rel=1.0e-6)
        or not close_enough(elastic_constants[2], 0.3, rel=1.0e-6)
    ):
        return False
    return saw_pressure_storage


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


def pressure_listing_is_ten(text):
    upper = (text or "").upper()
    if "LIST NODAL SURFACE LOAD PRES" in upper:
        nodal_values = []
        for line in (text or "").splitlines():
            fields = line.split()
            if len(fields) not in (3, 5):
                continue
            try:
                numbers = [
                    float(value.replace("D", "E").replace("d", "e"))
                    for value in fields
                ]
            except Exception:
                continue
            real_value, imaginary_value = numbers[-2:]
            nodal_values.append((real_value, imaginary_value))
        return len(nodal_values) >= 2 and all(
            close_enough(real_value, 10.0, rel=1.0e-6, abs_tol=1.0e-6)
            and abs(imaginary_value) <= 1.0e-10
            for real_value, imaginary_value in nodal_values
        )
    rows = [line for line in (text or "").splitlines() if "PRES" in line.upper()]
    data = []
    for line in rows:
        numbers = re.findall(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[EeDd][-+]?\d+)?", line)
        if len(numbers) >= 2:
            data.append([float(value.replace("D", "E").replace("d", "e")) for value in numbers])
    nonzero_values = [abs(value) for row in data for value in row[1:] if abs(value) > 1.0e-10]
    return bool(nonzero_values) and all(
        close_enough(value, 10.0, rel=1.0e-6, abs_tol=1.0e-6)
        for value in nonzero_values
    )


def pressure_listing_is_empty(text):
    upper = (text or "").strip().upper()
    return "NO SURFACE LOADS" in upper or upper == (
        "LIST NODAL SURFACE LOAD PRES FOR ALL SELECTED NODES"
    )


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
    _, pymapdl_reader = ansys_runtime()

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
    temp_root = Path(tempfile.mkdtemp(prefix="engiworld_task16_eval_ansys_", dir=str(desktop_dir())))
    OWNED_TEMP_DIRS.append(temp_root)
    candidate_db = temp_root / "candidate.db"
    submitted_rst = temp_root / "submitted.rst"
    shutil.copy2(model_path, candidate_db)
    shutil.copy2(result_path, submitted_rst)
    mapdl = None
    mapdl_jobname = "engiworld_task16_eval"
    process_baseline = ansys_job_process_ids(mapdl_jobname)
    semantic_passed = False
    cleanup_ok = False
    try:
        launch_mapdl, _ = ansys_runtime()

        if process_baseline is None:
            log("ANSYS evaluator could not establish a process baseline")
            return False
        try:
            rst_coords, rst_elements, rst_set_count = read_ansys_rst_mesh(submitted_rst)
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
        mapdl.resume(str(candidate_db.with_suffix("")), "db")
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
        if len(coords) not in (18, 45):
            log("ANSYS node count is not a complete structured 5 mm mesh")
            return False
        xs = [row[0] for row in node_rows]
        ys = [row[1] for row in node_rows]
        zs = [row[2] for row in node_rows]
        if not (
            close_enough(min(xs), 25.0, rel=1.0e-8)
            and close_enough(max(xs), 50.0, rel=1.0e-8)
            and close_enough(min(ys), 0.0, rel=1.0e-8)
            and close_enough(max(ys), 10.0, rel=1.0e-8)
            and close_enough(min(zs), 0.0, rel=1.0e-8)
            and close_enough(max(zs), 0.0, rel=1.0e-8)
        ):
            log("ANSYS geometry bounds are incorrect")
            return False
        element_numbers = [int(value) for value in mapdl.mesh.enum]
        if len(element_numbers) != 10:
            log("ANSYS mesh must contain ten 5 mm by 5 mm elements")
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
        type_listing = required_run(mapdl, "ETLIST,ALL").upper()
        defined_types = [
            (int(number), name)
            for number, name in re.findall(
                r"ELEMENT TYPE\s+(\d+)\s+IS\s+([A-Z0-9_]+)", type_listing
            )
        ]
        if len(defined_types) != 1 or defined_types[0][0] != type_id:
            log("ANSYS database contains an unused or mismatched decoy element type")
            return False
        material_count = try_get(mapdl, "MAT", 0, "COUNT")
        if material_count is not None and int(round(material_count)) != 1:
            log("ANSYS database contains an unused decoy material")
            return False
        if int(round(required_get(mapdl, "AREA", 0, "COUNT"))) != 1 or int(round(required_get(mapdl, "LINE", 0, "COUNT"))) != 4:
            log("ANSYS database must contain one rectangular area and its four boundary lines")
            return False
        element_code = int(round(required_get(mapdl, "ETYP", type_id, "ATTR", "ENAM")))
        if element_code not in (182, 183):
            log("actual elements are not PLANE182/PLANE183")
            return False
        element_name = "PLANE%d" % element_code
        if defined_types[0][1] != element_name:
            log("ANSYS ETLIST element name does not match the used native element code")
            return False
        expected_nodes = 18 if element_code == 182 else 45
        if len(coords) != expected_nodes:
            log("node count does not match the actual ANSYS element order")
            return False
        axisymmetric_keyopt = try_get(mapdl, "ETYP", type_id, "ATTR", "KOP3")
        if axisymmetric_keyopt is None or int(round(axisymmetric_keyopt)) != 1:
            log("actual ANSYS element type is not configured as axisymmetric")
            return False

        if not structured_ansys_lattice_matches(coords, element_code):
            log("ANSYS nodes do not form the complete linear/quadratic 5 mm structured lattice")
            return False

        nodes_per_element = 4 if element_code == 182 else 8
        boxes = set()
        attached_nodes = set()
        element_connectivity = {}
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
            element_connectivity[element] = tuple(connectivity)
            rows = [coords[label] for label in connectivity]
            exs = [row[0] for row in rows]
            eys = [row[1] for row in rows]
            box = (round(min(exs), 6), round(max(exs), 6), round(min(eys), 6), round(max(eys), 6))
            if not close_enough(box[1] - box[0], 5.0) or not close_enough(box[3] - box[2], 5.0):
                log("ANSYS element does not span one 5 mm by 5 mm structured cell")
                return False
            middle_x = 0.5 * (box[0] + box[1])
            middle_y = 0.5 * (box[2] + box[3])
            expected_element_points = {
                (box[0], box[2]),
                (box[1], box[2]),
                (box[1], box[3]),
                (box[0], box[3]),
            }
            if element_code == 183:
                expected_element_points.update(
                    {
                        (middle_x, box[2]),
                        (box[1], middle_y),
                        (middle_x, box[3]),
                        (box[0], middle_y),
                    }
                )
            actual_element_points = set((round(row[0], 6), round(row[1], 6)) for row in rows)
            if actual_element_points != expected_element_points:
                log("ANSYS element connectivity is not a complete mapped quadrilateral")
                return False
            boxes.add(box)
        expected_boxes = set(
            (float(25 + 5 * i), float(30 + 5 * i), float(5 * j), float(5 + 5 * j))
            for j in range(2)
            for i in range(5)
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
            "INNER": set(label for label, xyz in coords.items() if close_enough(xyz[0], 25.0, rel=1.0e-8)),
            "OUTER": set(label for label, xyz in coords.items() if close_enough(xyz[0], 50.0, rel=1.0e-8)),
            "ZMIN": set(label for label, xyz in coords.items() if close_enough(xyz[1], 0.0, rel=1.0e-8)),
            "ZMAX": set(label for label, xyz in coords.items() if close_enough(xyz[1], 10.0, rel=1.0e-8)),
        }
        required_run(mapdl, "ALLSEL,ALL")
        constraints = parse_listing_rows(required_run(mapdl, "DLIST,ALL"), ("UX", "UY", "UZ"))
        actual_uy = set(node for node, label, value in constraints if label == "UY" and abs(value) <= 1.0e-12)
        if actual_uy != expected_sets["ZMIN"].union(expected_sets["ZMAX"]):
            log("ANSYS UY=0 coverage must equal the Y=0 and Y=10 faces")
            return False
        if any(label == "UX" for node, label, value in constraints):
            log("ANSYS contains a forbidden radial UX constraint")
            return False
        if any(label not in ("UY",) or abs(value) > 1.0e-12 for node, label, value in constraints):
            log("ANSYS contains an extra or nonzero displacement constraint")
            return False

        if not listing_confirms_none(mapdl, "FLIST,ALL", "NO NODAL FORCES TO LIST"):
            log("ANSYS contains a forbidden nodal force")
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
        export_stem = "task16_model_audit"
        required_run(mapdl, "CDWRITE,DB,%s,cdb" % export_stem)
        export_path = temp_root / (export_stem + ".cdb")
        export_text = (
            export_path.read_text(encoding="utf-8", errors="ignore")
            if is_nonempty(export_path)
            else ""
        )
        if not export_text or not inertia_loads_are_zero(export_text):
            log("ANSYS model contains a nonzero translational or rotational inertia load")
            return False
        if not cdb_ansys_state_is_supported(export_text, material_id):
            log("ANSYS CDB contains an extra surface/initial-state load or nonlinear TB material")
            return False

        required_run(mapdl, "ALLSEL,ALL")
        sflist_blocks = parse_element_pressure_listing(
            required_run(mapdl, "SFLIST,ALL"),
            "LIST NODAL SURFACE LOAD PRES FOR ALL SELECTED NODES",
        )
        sfelist_blocks = parse_element_pressure_listing(
            required_run(mapdl, "SFELIST,ALL"),
            "LIST ELEMENT SURFACE LOAD PRES FOR ALL SELECTED ELEMENTS",
        )
        expected_inner_facets = set()
        full_inner_nodes = set()
        for element, connectivity in element_connectivity.items():
            inner_nodes = frozenset(
                label
                for label in connectivity
                if close_enough(coords[label][0], 25.0, rel=1.0e-8, abs_tol=1.0e-7)
            )
            if inner_nodes:
                expected_full_count = 2 if element_code == 182 else 3
                if len(inner_nodes) != expected_full_count:
                    log("ANSYS inner-wall element edge has incomplete node coverage")
                    return False
                endpoint_nodes = frozenset(
                    label
                    for label in connectivity[:4]
                    if close_enough(coords[label][0], 25.0, rel=1.0e-8, abs_tol=1.0e-7)
                )
                if len(endpoint_nodes) != 2:
                    log("ANSYS inner-wall element edge has incomplete corner-node coverage")
                    return False
                expected_inner_facets.add((element, endpoint_nodes))
                full_inner_nodes.update(inner_nodes)
        if (
            len(expected_inner_facets) != 2
            or full_inner_nodes != expected_sets["INNER"]
        ):
            log("ANSYS connectivity does not expose exactly two complete X=25 inner-wall edges")
            return False
        # MAPDL v261 lists only the two corner nodes for a PLANE183 face;
        # the midside node is verified above from the native connectivity.
        sflist_signature = pressure_block_signature(sflist_blocks, 2)
        sfelist_signature = pressure_block_signature(sfelist_blocks, 2)
        if (
            sflist_signature is None
            or sfelist_signature is None
            or sflist_signature != sfelist_signature
            or sflist_signature != expected_inner_facets
        ):
            log("ANSYS pressure records must equal only the two complete X=25 edges at 10 MPa")
            return False
        required_run(mapdl, "ALLSEL,ALL")

        required_run(mapdl, "FINISH")
        required_run(mapdl, "/POST1")
        mapdl.file(str(submitted_rst.with_suffix("")), "rst")
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
        radial_values = [try_get(mapdl, "NODE", label, "U", "X") for label in expected_sets["ALLNODES"]]
        radial = max(radial_values) if all(value is not None and math.isfinite(value) for value in radial_values) else None
        axial_values = [try_get(mapdl, "NODE", label, "U", "Y") for label in expected_sets["ZMIN"].union(expected_sets["ZMAX"])]
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
        if maximum is None or not math.isfinite(maximum):
            log("ANSYS stress result is unavailable")
            return False
        if not (1.0e-4 < radial < 0.02 and 10.0 < maximum < 60.0):
            log("native ANSYS metrics are outside physical sanity bounds")
            return False
        if not close_enough(radial, submitted_metrics["radial_displacement"], rel=1.0e-3, abs_tol=2.0e-6):
            log("metrics.json radial_displacement does not match RST maximum outward UX")
            return False
        if not close_enough(maximum, submitted_metrics["max_stress"], rel=1.0e-3, abs_tol=0.05):
            log("metrics.json max_stress does not match RST")
            return False
        reaction_text = required_run(mapdl, "PRRSOL,F").upper()
        if "REACTION SOLUTION LISTING" not in reaction_text or "TOTAL VALUES" not in reaction_text:
            log("ANSYS result does not expose reaction-force output")
            return False

        required_run(mapdl, "FINISH")
        mapdl.resume(str(candidate_db.with_suffix("")), "db")
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
    finally:
        for work in OWNED_TEMP_DIRS:
            if not work.exists():
                continue
            if not cleanup_owned_processes(work):
                log("final evaluator process cleanup was incomplete: %s" % work)
                passed = False
            if not remove_tree_with_retries(work):
                log("final evaluator temporary cleanup was incomplete: %s" % work)
                passed = False
    try:
        (root / "eval_detail.txt").write_text("\n".join(DETAILS) + "\n", encoding="utf-8")
        (root / "eval_result.txt").write_text("True\n" if passed else "False\n", encoding="utf-8")
    except Exception:
        pass
    sys.stdout.write("True\n" if passed else "False\n")


if __name__ == "__main__":
    main()
