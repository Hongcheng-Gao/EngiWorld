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
import threading
import time
import uuid
from pathlib import Path


TASK_ID = "c-open-abaqus-ansys-autocad-task-10-windows"
JOB_NAME = "Job-Torsion-B"
STEP_NAME = "Step-Torque-B"
METRIC_FIELDS = ("twist_angle", "max_stress")
ABAQUS_COMMAND = r"C:\SIMULIA\Commands\abaqus.bat"
ANSYS_EXEC = r"C:\Program Files\ANSYS Inc\v261\ansys\bin\winx64\ANSYS261.exe"
POWERSHELL = r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
TRUSTED_USER_SITE = Path(r"C:\Users\user\AppData\Roaming\Python\Python311\site-packages")
NATIVE_SUFFIXES = {
    ".cae", ".odb", ".inp", ".sim", ".fil", ".db", ".rst", ".r" + "th",
    ".cdb", ".wbpj", ".wbpz", ".mechdb", ".agdb",
}
ANSYS_RST_HEADER_SIZE = 128
ABAQUS_PROCESS_PATTERN = (
    r"^(SMALauncherLE|ABQLauncher|abq2025le|standard|pre|explicit|package|"
    r"mpiexec|hydra_service|hydra_bstrap_proxy|hydra_pmi_proxy|abq[^.]*)\.exe$"
)
DESKTOP_CANDIDATES = [
    Path(os.environ.get("USERPROFILE", r"C:\Users\user")) / "Desktop",
    Path(r"C:\Users\user\Desktop"),
    Path(r"C:\Users\User\Desktop"),
]
DETAILS = []
ANSYS_UNTRUSTED_ENVIRONMENT_KEYS = (
    "ANS_USE_UPF",
    "ANS_USER_PATH",
    "ANS_USER_PATH_261",
    "ANSYS_MACROLIB",
)
ANSYS_AUDIT_ABBREVIATIONS = (
    "ALLSEL",
    "ANTYPE",
    "BFELIST",
    "BFLIST",
    "CDWRITE",
    "CELIST",
    "CPLIST",
    "CSYS",
    "DLIST",
    "DSYS",
    "EQSLV",
    "FILE",
    "FINISH",
    "FLIST",
    "ICLIST",
    "KUSE",
    "NCNV",
    "NSEL",
    "PRRSOL",
    "RSYS",
    "SET",
    "SFALIST",
    "SFELIST",
    "SFLIST",
    "SOLVE",
    "USRCAL",
)


if os.name == "nt" and TRUSTED_USER_SITE.is_dir():
    sys.path.append(str(TRUSTED_USER_SITE))


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


def finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def percentile(values, fraction):
    ordered = sorted(float(value) for value in values)
    if not ordered or not (0.0 <= fraction <= 1.0):
        raise ValueError("invalid percentile input")
    position = fraction * (len(ordered) - 1)
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def mesh_target_statistics(edge_lengths):
    if not edge_lengths or any(not finite_number(value) or value <= 1.0e-8 for value in edge_lengths):
        return None
    values = tuple(float(value) for value in edge_lengths)
    statistics = {
        "minimum": min(values),
        "median": percentile(values, 0.5),
        "p90": percentile(values, 0.9),
        "maximum": max(values),
    }
    if not (
        statistics["minimum"] >= 0.50
        and 2.40 <= statistics["median"] <= 5.20
        and 3.00 <= statistics["p90"] <= 6.20
        and statistics["maximum"] <= 8.20
    ):
        return None
    return statistics


def close_enough(actual, expected, rel=1.0e-3, abs_tol=1.0e-8):
    try:
        return math.isclose(float(actual), float(expected), rel_tol=rel, abs_tol=abs_tol)
    except Exception:
        return False


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def require_trusted_module(module):
    origin = Path(getattr(module, "__file__", "") or "").resolve()
    trusted = TRUSTED_USER_SITE.resolve()
    try:
        origin.relative_to(trusted)
    except Exception:
        raise RuntimeError("untrusted Python module provenance: %s" % origin)


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
    if not isinstance(data, dict) or set(data) != set(METRIC_FIELDS):
        log("metrics.json must contain exactly twist_angle and max_stress")
        return None
    if any(not finite_number(data[name]) for name in METRIC_FIELDS):
        log("metrics.json values must be finite JSON numbers, not bools or strings")
        return None
    metrics = dict((name, float(data[name])) for name in METRIC_FIELDS)
    if not (3.2e-4 <= metrics["twist_angle"] <= 6.0e-4):
        log("twist_angle is outside the Task-10 cross-solver physical sanity range")
        return None
    if not (2.5 <= metrics["max_stress"] <= 8.0):
        log("max_stress is outside the Task-10 physical sanity range")
        return None
    return metrics


def files_with_suffix(root, suffix):
    try:
        return sorted(
            [path for path in root.iterdir() if path.is_file() and path.suffix.lower() == suffix],
            key=lambda path: path.name.lower(),
        )
    except Exception:
        return []


def discover_branch(root):
    caes = files_with_suffix(root, ".cae")
    odbs = files_with_suffix(root, ".odb")
    dbs = files_with_suffix(root, ".db")
    rsts = files_with_suffix(root, ".rst")
    try:
        native = sorted(
            path for path in root.iterdir()
            if path.is_file() and path.suffix.lower() in NATIVE_SUFFIXES
        )
    except Exception:
        native = []
    supported = set(caes + odbs + dbs + rsts)
    extras = [path for path in native if path not in supported]
    if extras:
        log("unsupported or extra native solver payload present: %s" % [path.name for path in extras])
        return None
    has_abaqus = bool(caes or odbs)
    has_ansys = bool(dbs or rsts)
    if has_abaqus and has_ansys:
        log("deliver exactly one solver branch")
        return None
    expected_stem = JOB_NAME.lower()
    if has_abaqus:
        if len(caes) != 1 or len(odbs) != 1:
            log("Abaqus delivery requires exactly one CAE and one ODB")
            return None
        if caes[0].stem.lower() != expected_stem or odbs[0].stem.lower() != expected_stem:
            log("Abaqus artifacts must be Job-Torsion-B.cae and Job-Torsion-B.odb")
            return None
        if not is_nonempty(caes[0]) or not is_nonempty(odbs[0]):
            log("Abaqus artifact is empty")
            return None
        return "abaqus", caes[0], odbs[0]
    if has_ansys:
        if len(dbs) != 1 or len(rsts) != 1:
            log("ANSYS delivery requires exactly one DB and one RST")
            return None
        if dbs[0].stem.lower() != expected_stem or rsts[0].stem.lower() != expected_stem:
            log("ANSYS artifacts must be Job-Torsion-B.db and Job-Torsion-B.rst")
            return None
        if not is_nonempty(dbs[0]) or not is_nonempty(rsts[0]):
            log("ANSYS artifact is empty")
            return None
        return "ansys", dbs[0], rsts[0]
    log("no supported native CAE/ODB or DB/RST pair found")
    return None


def remove_tree(path):
    for _ in range(30):
        try:
            if path.exists():
                shutil.rmtree(str(path))
            return not path.exists()
        except Exception:
            time.sleep(0.2)
    return False


def bounded_mapdl_exit(mapdl, timeout=30.0):
    if mapdl is None:
        return True
    outcome = []

    def close_session():
        try:
            mapdl.exit()
            outcome.append(True)
        except Exception:
            outcome.append(False)

    thread = threading.Thread(target=close_session)
    thread.daemon = True
    thread.start()
    thread.join(timeout=timeout)
    return not thread.is_alive() and outcome == [True]


def exact_regular_files(root, expected_names):
    try:
        expected = set(str(name) for name in expected_names)
        entries = list(root.iterdir())
        return (
            set(path.name for path in entries) == expected
            and all(
                path.is_file()
                and not path.is_symlink()
                and not (getattr(path.stat(), "st_file_attributes", 0) & 0x400)
                for path in entries
            )
        )
    except Exception:
        return False


def regular_directory_names(root):
    try:
        entries = list(root.iterdir())
        if any(
            not path.is_file()
            or path.is_symlink()
            or (getattr(path.stat(), "st_file_attributes", 0) & 0x400)
            for path in entries
        ):
            return None
        return tuple(sorted((path.name for path in entries), key=str.lower))
    except Exception:
        return None


def ansys_batch_inventory_is_valid(actual_names, jobname, staged_model_name):
    required_names = [
        jobname + ".DSP",
        jobname + ".err",
        jobname + ".esav",
        jobname + ".full",
        jobname + ".log",
        jobname + ".mntr",
        jobname + ".rst",
        str(staged_model_name),
        "task10_resolve.inp",
        "task10_resolve.out",
        "task10_status.done",
    ]
    required_names.extend((jobname + ".ldhi", jobname + ".r001", jobname + ".rdb"))
    required = set(required_names)
    optional = {jobname + ".emat", jobname + ".stat"}
    actual = set(str(value) for value in (actual_names or ()))
    return required.issubset(actual) and bool(actual & optional) and actual <= required | optional


def expected_ansys_audit_names(jobname, export_stem):
    return tuple(sorted((
        ".__tmp__.inp",
        ".__tmp__.out",
        jobname + ".bat",
        jobname + ".err",
        jobname + ".lock",
        jobname + ".log",
        jobname + ".page",
        "submitted.db",
        "submitted.rst",
        export_stem + ".cdb",
    ), key=str.lower))


def expected_ansys_post_names(jobname):
    return tuple(sorted((
        ".__tmp__.inp",
        ".__tmp__.out",
        jobname + ".db",
        jobname + ".err",
        jobname + ".log",
        "recomputed.rst",
    ), key=str.lower))


def stable_fresh_file(path, not_before_ns, settle_seconds=0.2):
    try:
        if not path.is_file() or path.is_symlink() or path.stat().st_size <= 0:
            return None
        first = (path.stat().st_size, path.stat().st_mtime_ns, sha256(path))
        time.sleep(settle_seconds)
        if not path.is_file() or path.is_symlink():
            return None
        second = (path.stat().st_size, path.stat().st_mtime_ns, sha256(path))
        if first != second or second[1] + 2_000_000_000 < int(not_before_ns):
            return None
        return {"size": second[0], "mtime_ns": second[1], "sha256": second[2]}
    except Exception:
        return None


def sanitized_ansys_environment():
    environment = os.environ.copy()
    for key in ANSYS_UNTRUSTED_ENVIRONMENT_KEYS:
        environment.pop(key, None)
    return environment


def clear_ansys_abbreviations(mapdl):
    for command in ANSYS_AUDIT_ABBREVIATIONS:
        required_run(mapdl, "*ABBR,%s," % command)


def windows_processes(pattern, timeout=30.0):
    if os.name != "nt":
        return []
    command = (
        "Get-CimInstance Win32_Process | Where-Object { $_.Name -match '%s' } | "
        "Select-Object ProcessId,ParentProcessId,Name,CommandLine,CreationDate | "
        "ConvertTo-Json -Compress" % pattern
    )
    completed = subprocess.run(
        [POWERSHELL, "-NoProfile", "-Command", command],
        text=True,
        capture_output=True,
        timeout=timeout,
        shell=False,
    )
    if completed.returncode != 0:
        raise RuntimeError("process baseline probe failed: " + completed.stderr[-500:])
    text = completed.stdout.strip()
    if not text:
        return []
    payload = json.loads(text)
    if isinstance(payload, dict):
        payload = [payload]
    return sorted(
        ({
            "pid": int(row["ProcessId"]),
            "parent_pid": int(row.get("ParentProcessId") or 0),
            "name": str(row.get("Name") or ""),
            "command_line": str(row.get("CommandLine") or ""),
            "creation_date": str(row.get("CreationDate") or ""),
        } for row in payload),
        key=lambda row: row["pid"],
    )


def terminate_owned_process(pid):
    pid = int(pid)
    if os.name != "nt" or pid <= 0:
        return False
    completed = subprocess.run(
        ["cmd", "/c", "taskkill", "/F", "/T", "/PID", str(pid)],
        text=True,
        capture_output=True,
        timeout=30,
        shell=False,
    )
    return completed.returncode == 0


def process_identity(row):
    return (
        row["pid"],
        row["parent_pid"],
        row["creation_date"],
        row["name"],
        row["command_line"],
    )


def update_owned_process_history(history, before, current, markers, seed_pids=()):
    baseline = set(process_identity(row) for row in before)
    markers = tuple(str(value).lower() for value in markers if value)
    new_rows = [row for row in current if process_identity(row) not in baseline]
    owned_pids = set(int(value) for value in seed_pids if int(value) > 0)
    owned_pids.update(
        row["pid"] for row in new_rows
        if process_identity(row) in history
        or any(marker in row["command_line"].lower() for marker in markers)
    )
    changed = True
    while changed:
        changed = False
        for row in new_rows:
            if row["pid"] not in owned_pids and row["parent_pid"] in owned_pids:
                owned_pids.add(row["pid"])
                changed = True
    for row in new_rows:
        if row["pid"] in owned_pids:
            history[process_identity(row)] = dict(row)
    return [row for row in new_rows if row["pid"] in owned_pids]


def track_owned_processes(stop_event, history, before, pattern, markers, seed_pids=()):
    while not stop_event.is_set():
        try:
            current = windows_processes(pattern, timeout=5.0)
            update_owned_process_history(history, before, current, markers, seed_pids)
        except Exception:
            pass
        stop_event.wait(0.15)


def terminate_matching_identity(row, pattern):
    current = windows_processes(pattern, timeout=5.0)
    if process_identity(row) not in set(process_identity(value) for value in current):
        return False
    return terminate_owned_process(row["pid"])


def restore_process_baseline(before, pattern, markers, owned_history=()):
    if os.name != "nt":
        return True
    markers = tuple(str(value).lower() for value in markers if value)
    baseline = set(process_identity(row) for row in before)
    history = dict((process_identity(row), dict(row)) for row in owned_history)
    deadline = time.monotonic() + 15.0
    while time.monotonic() < deadline:
        current = windows_processes(pattern, timeout=5.0)
        current_identities = set(process_identity(row) for row in current)
        owned = update_owned_process_history(history, before, current, markers)
        for row in sorted(owned, key=lambda value: value["pid"], reverse=True):
            terminate_matching_identity(row, pattern)
        if not owned and current_identities == baseline:
            return True
        time.sleep(0.25)
    current = windows_processes(pattern, timeout=5.0)
    return current == before


def write_text_result(root, passed):
    try:
        (root / "eval_detail.txt").write_text("\n".join(DETAILS) + "\n", encoding="utf-8")
        (root / "eval_result.txt").write_text("True\n" if passed else "False\n", encoding="utf-8")
    except Exception:
        pass


ABAQUS_DECK_HELPERS = r'''
ABAQUS_ALLOWED_KEYWORD_PARAMS = {
    "HEADING": set(),
    "PREPRINT": {"ECHO", "MODEL", "HISTORY", "CONTACT"},
    "PART": {"NAME"},
    "NODE": {"NSET", "SYSTEM"},
    "ELEMENT": {"TYPE", "ELSET"},
    "NSET": {"NSET", "INSTANCE", "GENERATE", "INTERNAL", "UNSORTED", "ELSET"},
    "ELSET": {"ELSET", "INSTANCE", "GENERATE", "INTERNAL", "UNSORTED"},
    "SOLID SECTION": {"ELSET", "MATERIAL"},
    "END PART": set(),
    "ASSEMBLY": {"NAME"},
    "INSTANCE": {"NAME", "PART"},
    "END INSTANCE": set(),
    "SURFACE": {"TYPE", "NAME", "INTERNAL"},
    "COUPLING": {"CONSTRAINT NAME", "REF NODE", "SURFACE"},
    "KINEMATIC": set(),
    "END ASSEMBLY": set(),
    "MATERIAL": {"NAME"},
    "ELASTIC": set(),
    "BOUNDARY": {"OP"},
    "STEP": {"NAME", "NLGEOM", "INC"},
    "STATIC": {"DIRECT"},
    "CLOAD": {"OP"},
    "RESTART": {"WRITE", "FREQUENCY"},
    "OUTPUT": {"FIELD", "HISTORY", "VARIABLE", "FREQUENCY", "NUMBER INTERVAL", "TIME INTERVAL", "TIME MARKS"},
    "NODE OUTPUT": {"NSET", "VARIABLE"},
    "ELEMENT OUTPUT": {"ELSET", "POSITION", "DIRECTIONS", "VARIABLE"},
    "END STEP": set(),
}


def abaqus_deck_error(message, line_number=None):
    if line_number is None:
        raise ValueError("generated INP: " + str(message))
    raise ValueError("generated INP line %d: %s" % (line_number, message))


def normalize_abaqus_name(value):
    return " ".join(str(value).strip().upper().split())


def parse_abaqus_keyword(line, line_number):
    pieces = [piece.strip() for piece in str(line).split(",")]
    keyword = normalize_abaqus_name(pieces[0][1:]) if pieces and pieces[0].startswith("*") else ""
    if keyword not in ABAQUS_ALLOWED_KEYWORD_PARAMS:
        abaqus_deck_error("unsupported or abbreviated keyword %r" % keyword, line_number)
    parameters = {}
    for piece in pieces[1:]:
        if not piece:
            abaqus_deck_error("empty keyword continuation or parameter", line_number)
        if "=" in piece:
            raw_name, raw_value = piece.split("=", 1)
            name = normalize_abaqus_name(raw_name)
            value = str(raw_value).strip()
            if not name or not value:
                abaqus_deck_error("malformed keyword parameter", line_number)
        else:
            name = normalize_abaqus_name(piece)
            value = None
        if name in parameters:
            abaqus_deck_error("duplicate keyword parameter %s" % name, line_number)
        if name not in ABAQUS_ALLOWED_KEYWORD_PARAMS[keyword]:
            abaqus_deck_error("unsupported or abbreviated %s parameter %s" % (keyword, name), line_number)
        parameters[name] = value
    return {"keyword": keyword, "parameters": parameters, "data": [], "line": line_number}


def parse_abaqus_input_text(text):
    if not isinstance(text, str) or not text.strip():
        abaqus_deck_error("input is empty")
    if "\x00" in text or any(ord(char) < 32 and char not in "\r\n\t" for char in text):
        abaqus_deck_error("input contains forbidden control characters")
    lines = text.splitlines()
    blocks = []
    current = None
    index = 0
    while index < len(lines):
        line_number = index + 1
        stripped = lines[index].strip()
        index += 1
        if not stripped or stripped.startswith("**"):
            continue
        if stripped.startswith("*"):
            logical = stripped
            while logical.rstrip().endswith(","):
                if index >= len(lines):
                    abaqus_deck_error("unterminated keyword continuation", line_number)
                continuation = lines[index].strip()
                index += 1
                if not continuation or continuation.startswith("*"):
                    abaqus_deck_error("malformed keyword continuation", index)
                logical += continuation
            current = parse_abaqus_keyword(logical, line_number)
            blocks.append(current)
            continue
        if current is None:
            abaqus_deck_error("data appears before the first keyword", line_number)
        current["data"].append((line_number, stripped))
    if not blocks:
        abaqus_deck_error("input has no keyword blocks")
    return blocks


def abaqus_parameter_value(block, name, required=False):
    key = normalize_abaqus_name(name)
    if required and key not in block["parameters"]:
        abaqus_deck_error("%s lacks required parameter %s" % (block["keyword"], key), block["line"])
    return block["parameters"].get(key)


def abaqus_effective_fields(line):
    return [field.strip() for field in str(line).split(",") if field.strip()]


def abaqus_number(value, line_number):
    try:
        result = float(str(value).replace("D", "E").replace("d", "e"))
    except Exception:
        abaqus_deck_error("non-numeric data value %r" % value, line_number)
    if not math.isfinite(result):
        abaqus_deck_error("non-finite numeric data", line_number)
    return result


def require_abaqus_block_count(by_name, name, minimum=None, exact=None):
    count = len(by_name.get(name, ()))
    if exact is not None and count != exact:
        abaqus_deck_error("expected exactly %d %s block(s), found %d" % (exact, name, count))
    if minimum is not None and count < minimum:
        abaqus_deck_error("expected at least %d %s block(s), found %d" % (minimum, name, count))


def abaqus_integer(value, line_number):
    if not re.fullmatch(r"[+-]?\d+", str(value).strip()):
        abaqus_deck_error("non-integer label %r" % value, line_number)
    result = int(str(value).strip())
    if result <= 0:
        abaqus_deck_error("labels and set members must be positive", line_number)
    return result


def abaqus_block_position(blocks, block):
    return next(index for index, candidate in enumerate(blocks) if candidate is block)


def abaqus_named_blocks(blocks, keyword, parameter, value, lower, upper):
    wanted = normalize_abaqus_name(value)
    return [
        block for index, block in enumerate(blocks)
        if lower < index < upper
        and block["keyword"] == keyword
        and normalize_abaqus_name(block["parameters"].get(parameter, "")) == wanted
    ]


def expand_abaqus_integer_blocks(blocks, kind):
    members = set()
    for block in blocks:
        for flag in ("GENERATE", "INTERNAL", "UNSORTED"):
            if flag in block["parameters"] and block["parameters"][flag] is not None:
                abaqus_deck_error("%s %s must be a flag" % (kind, flag), block["line"])
        generated = "GENERATE" in block["parameters"]
        for line_number, line in block["data"]:
            fields = abaqus_effective_fields(line)
            if generated:
                if len(fields) != 3:
                    abaqus_deck_error("%s GENERATE row must have start,end,increment" % kind, line_number)
                start, end, increment = [abaqus_integer(value, line_number) for value in fields]
                if increment <= 0 or end < start:
                    abaqus_deck_error("%s GENERATE range is invalid" % kind, line_number)
                values = list(range(start, end + 1, increment))
                if not values or values[-1] != end:
                    abaqus_deck_error("%s GENERATE range does not terminate exactly" % kind, line_number)
            else:
                if not fields:
                    abaqus_deck_error("empty %s membership row" % kind, line_number)
                values = [abaqus_integer(value, line_number) for value in fields]
            if len(set(values)) != len(values) or members.intersection(values):
                abaqus_deck_error("duplicate %s membership" % kind, line_number)
            members.update(values)
    return members


def abaqus_element_node_count(element_type):
    upper = normalize_abaqus_name(element_type)
    for prefix, count in (("C3D20", 20), ("C3D15", 15), ("C3D10", 10), ("C3D8", 8), ("C3D6", 6), ("C3D4", 4)):
        if upper.startswith(prefix):
            return count
    abaqus_deck_error("unsupported solid topology %s" % upper)


def abaqus_surface_face_indices(element_type, face_name):
    upper = normalize_abaqus_name(element_type)
    face = normalize_abaqus_name(face_name)
    if upper.startswith("C3D4"):
        maps = {"S1": (0,1,2), "S2": (0,3,1), "S3": (1,3,2), "S4": (2,3,0)}
    elif upper.startswith("C3D10"):
        maps = {
            "S1": (0,1,2,4,5,6), "S2": (0,3,1,7,8,4),
            "S3": (1,3,2,8,9,5), "S4": (2,3,0,9,7,6),
        }
    elif upper.startswith("C3D6"):
        maps = {"S1": (0,1,2), "S2": (3,5,4), "S3": (0,3,4,1), "S4": (1,4,5,2), "S5": (2,5,3,0)}
    elif upper.startswith("C3D15"):
        maps = {
            "S1": (0,1,2,6,7,8), "S2": (3,5,4,11,10,9),
            "S3": (0,3,4,1,12,9,13,6), "S4": (1,4,5,2,13,10,14,7),
            "S5": (2,5,3,0,14,11,12,8),
        }
    elif upper.startswith("C3D8"):
        maps = {"S1": (0,1,2,3), "S2": (4,7,6,5), "S3": (0,4,5,1), "S4": (1,5,6,2), "S5": (2,6,7,3), "S6": (3,7,4,0)}
    elif upper.startswith("C3D20"):
        maps = {
            "S1": (0,1,2,3,8,9,10,11), "S2": (4,7,6,5,15,14,13,12),
            "S3": (0,4,5,1,16,12,17,8), "S4": (1,5,6,2,17,13,18,9),
            "S5": (2,6,7,3,18,14,19,10), "S6": (3,7,4,0,19,15,16,11),
        }
    else:
        abaqus_deck_error("surface uses unsupported element type %s" % upper)
    if face not in maps:
        abaqus_deck_error("surface uses invalid face %s for %s" % (face, upper))
    return maps[face]


def audit_abaqus_input_scope(blocks):
    positions = dict((name, abaqus_block_position(blocks, next(block for block in blocks if block["keyword"] == name))) for name in (
        "HEADING", "PREPRINT", "PART", "END PART", "ASSEMBLY", "INSTANCE", "END INSTANCE",
        "END ASSEMBLY", "MATERIAL", "ELASTIC", "BOUNDARY", "STEP", "STATIC", "CLOAD", "END STEP",
    ))
    ordered = (
        "HEADING", "PREPRINT", "PART", "END PART", "ASSEMBLY", "INSTANCE", "END INSTANCE",
        "END ASSEMBLY", "MATERIAL", "ELASTIC", "BOUNDARY", "STEP", "STATIC", "CLOAD", "END STEP",
    )
    if [positions[name] for name in ordered] != sorted(positions[name] for name in ordered):
        abaqus_deck_error("keyword scopes are not in canonical CAE order")
    if positions["END INSTANCE"] != positions["INSTANCE"] + 1:
        abaqus_deck_error("INSTANCE scope must be data-only and end immediately")
    kinematic_position = next(index for index, block in enumerate(blocks) if block["keyword"] == "KINEMATIC")
    coupling_position = next(index for index, block in enumerate(blocks) if block["keyword"] == "COUPLING")
    if kinematic_position != coupling_position + 1:
        abaqus_deck_error("KINEMATIC must immediately follow COUPLING")
    part_allowed = {"NODE", "ELEMENT", "NSET", "ELSET", "SOLID SECTION"}
    assembly_allowed = {"INSTANCE", "END INSTANCE", "NODE", "NSET", "ELSET", "SURFACE", "COUPLING", "KINEMATIC"}
    step_allowed = {"STATIC", "CLOAD", "RESTART", "OUTPUT", "NODE OUTPUT", "ELEMENT OUTPUT"}
    for index, block in enumerate(blocks):
        name = block["keyword"]
        if positions["PART"] < index < positions["END PART"] and name not in part_allowed:
            abaqus_deck_error("%s is outside its allowed PART scope" % name, block["line"])
        if positions["ASSEMBLY"] < index < positions["END ASSEMBLY"] and name not in assembly_allowed:
            abaqus_deck_error("%s is outside its allowed ASSEMBLY scope" % name, block["line"])
        if positions["INSTANCE"] < index < positions["END INSTANCE"]:
            abaqus_deck_error("keyword %s is illegally nested inside INSTANCE" % name, block["line"])
        if positions["STEP"] < index < positions["END STEP"] and name not in step_allowed:
            abaqus_deck_error("%s is outside its allowed STEP scope" % name, block["line"])
        in_any = (
            positions["PART"] < index < positions["END PART"]
            or positions["ASSEMBLY"] < index < positions["END ASSEMBLY"]
            or positions["STEP"] < index < positions["END STEP"]
        )
        top_allowed = {
            "HEADING", "PREPRINT", "PART", "END PART", "ASSEMBLY", "END ASSEMBLY",
            "MATERIAL", "ELASTIC", "BOUNDARY", "STEP", "END STEP",
        }
        if not in_any and name not in top_allowed:
            abaqus_deck_error("%s is outside its allowed top-level position" % name, block["line"])
    return positions


def audit_abaqus_deck_mesh_and_regions(
    blocks, positions, expected_nodes, expected_elements, fixed_nodes, free_nodes, expected_instance
):
    part_node_blocks = [
        block for index, block in enumerate(blocks)
        if positions["PART"] < index < positions["END PART"] and block["keyword"] == "NODE"
    ]
    assembly_node_blocks = [
        block for index, block in enumerate(blocks)
        if positions["END INSTANCE"] < index < positions["END ASSEMBLY"] and block["keyword"] == "NODE"
    ]
    if len(part_node_blocks) != 1 or len(assembly_node_blocks) != 1:
        abaqus_deck_error("expected one PART NODE block and one assembly RP NODE block")
    parsed_nodes = {}
    if part_node_blocks[0]["parameters"]:
        abaqus_deck_error("PART NODE block has unsupported parameters", part_node_blocks[0]["line"])
    for line_number, line in part_node_blocks[0]["data"]:
        fields = abaqus_effective_fields(line)
        if len(fields) != 4:
            abaqus_deck_error("PART NODE row must have label,x,y,z", line_number)
        label = abaqus_integer(fields[0], line_number)
        if label in parsed_nodes:
            abaqus_deck_error("duplicate PART NODE label", line_number)
        parsed_nodes[label] = tuple(abaqus_number(value, line_number) for value in fields[1:])
    if set(parsed_nodes) != set(expected_nodes) or any(
        any(abs(parsed_nodes[label][axis] - float(expected_nodes[label][axis])) > 1.0e-7 for axis in range(3))
        for label in parsed_nodes
    ):
        abaqus_deck_error("generated PART NODE coordinates do not match the audited CAE mesh")

    parsed_elements = {}
    for index, block in enumerate(blocks):
        if not (positions["PART"] < index < positions["END PART"]) or block["keyword"] != "ELEMENT":
            continue
        if set(block["parameters"]) != {"TYPE"}:
            abaqus_deck_error("ELEMENT block has unsupported set or input parameters", block["line"])
        element_type = normalize_abaqus_name(block["parameters"]["TYPE"])
        width = abaqus_element_node_count(element_type) + 1
        values = []
        for line_number, line in block["data"]:
            fields = abaqus_effective_fields(line)
            values.extend((abaqus_integer(value, line_number), line_number) for value in fields)
        if not values or len(values) % width:
            abaqus_deck_error("ELEMENT connectivity records have invalid width", block["line"])
        for offset in range(0, len(values), width):
            row = values[offset:offset + width]
            label = row[0][0]
            if label in parsed_elements:
                abaqus_deck_error("duplicate ELEMENT label", row[0][1])
            parsed_elements[label] = (element_type, tuple(item[0] for item in row[1:]))
    normalized_expected = dict(
        (int(label), (normalize_abaqus_name(row[0]), tuple(int(value) for value in row[1])))
        for label, row in expected_elements.items()
    )
    if parsed_elements != normalized_expected:
        abaqus_deck_error("generated ELEMENT topology does not match the audited CAE mesh")

    instance = next(block for block in blocks if block["keyword"] == "INSTANCE")
    part = next(block for block in blocks if block["keyword"] == "PART")
    if set(instance["parameters"]) != {"NAME", "PART"} or normalize_abaqus_name(instance["parameters"]["NAME"]) != normalize_abaqus_name(expected_instance) or normalize_abaqus_name(instance["parameters"]["PART"]) != normalize_abaqus_name(part["parameters"].get("NAME", "")):
        abaqus_deck_error("INSTANCE does not match the audited CAE instance", instance["line"])
    if instance["data"]:
        abaqus_deck_error("INSTANCE transformation data are unsupported by this global-coordinate contract", instance["line"])
    assembly_node = assembly_node_blocks[0]
    if assembly_node["parameters"] or len(assembly_node["data"]) != 1:
        abaqus_deck_error("assembly must contain exactly one explicit RP node", assembly_node["line"])
    rp_fields = abaqus_effective_fields(assembly_node["data"][0][1])
    if len(rp_fields) != 4:
        abaqus_deck_error("assembly RP NODE row must have label,x,y,z", assembly_node["data"][0][0])
    rp_label = abaqus_integer(rp_fields[0], assembly_node["data"][0][0])
    rp_xyz = tuple(abaqus_number(value, assembly_node["data"][0][0]) for value in rp_fields[1:])
    if any(abs(rp_xyz[axis] - (0.0, 72.0, 0.0)[axis]) > 1.0e-8 for axis in range(3)):
        abaqus_deck_error("assembly RP is not at (0,72,0)", assembly_node["data"][0][0])

    for index, block in enumerate(blocks):
        if block["keyword"] not in ("NSET", "ELSET"):
            continue
        if block["keyword"] == "NSET" and "ELSET" in block["parameters"]:
            abaqus_deck_error("set aliases are not accepted in the frozen deck contract", block["line"])
        members = expand_abaqus_integer_blocks([block], block["keyword"])
        if block["keyword"] == "NSET":
            if positions["PART"] < index < positions["END PART"]:
                if "INSTANCE" in block["parameters"]:
                    abaqus_deck_error("PART NSET cannot name an assembly instance", block["line"])
                universe = set(expected_nodes)
            else:
                if "INSTANCE" in block["parameters"]:
                    if normalize_abaqus_name(block["parameters"]["INSTANCE"]) != normalize_abaqus_name(expected_instance):
                        abaqus_deck_error("assembly NSET names an unexpected instance", block["line"])
                    universe = set(expected_nodes)
                else:
                    universe = {rp_label}
        else:
            if positions["PART"] < index < positions["END PART"] and "INSTANCE" in block["parameters"]:
                abaqus_deck_error("PART ELSET cannot name an assembly instance", block["line"])
            if positions["END INSTANCE"] < index < positions["END ASSEMBLY"] and "INSTANCE" in block["parameters"] and normalize_abaqus_name(block["parameters"]["INSTANCE"]) != normalize_abaqus_name(expected_instance):
                abaqus_deck_error("assembly ELSET names an unexpected instance", block["line"])
            universe = set(expected_elements)
        if not members.issubset(universe):
            abaqus_deck_error("%s contains an undefined or out-of-scope member" % block["keyword"], block["line"])

    section = next(block for block in blocks if block["keyword"] == "SOLID SECTION")
    section_sets = abaqus_named_blocks(
        blocks, "ELSET", "ELSET", section["parameters"]["ELSET"], positions["PART"], positions["END PART"]
    )
    if expand_abaqus_integer_blocks(section_sets, "section ELSET") != set(expected_elements):
        abaqus_deck_error("SOLID SECTION ELSET does not cover every and only shaft element")
    boundary = next(block for block in blocks if block["keyword"] == "BOUNDARY")
    boundary_name = abaqus_effective_fields(boundary["data"][0][1])[0]
    boundary_sets = abaqus_named_blocks(
        blocks, "NSET", "NSET", boundary_name, positions["END INSTANCE"], positions["END ASSEMBLY"]
    )
    if not boundary_sets or any(
        normalize_abaqus_name(block["parameters"].get("INSTANCE", "")) != normalize_abaqus_name(expected_instance)
        for block in boundary_sets
    ) or expand_abaqus_integer_blocks(boundary_sets, "boundary NSET") != set(fixed_nodes):
        abaqus_deck_error("Encastre NSET is not exactly the complete Y=0 face")

    coupling = next(block for block in blocks if block["keyword"] == "COUPLING")
    rp_sets = abaqus_named_blocks(
        blocks, "NSET", "NSET", coupling["parameters"]["REF NODE"], positions["END INSTANCE"], positions["END ASSEMBLY"]
    )
    if not rp_sets or any("INSTANCE" in block["parameters"] for block in rp_sets) or expand_abaqus_integer_blocks(rp_sets, "RP NSET") != {rp_label}:
        abaqus_deck_error("coupling REF NODE does not resolve to the unique assembly RP")
    surface = next(block for block in blocks if block["keyword"] == "SURFACE")
    if normalize_abaqus_name(surface["parameters"].get("NAME", "")) != normalize_abaqus_name(coupling["parameters"]["SURFACE"]):
        abaqus_deck_error("COUPLING surface reference is unresolved", coupling["line"])
    if normalize_abaqus_name(surface["parameters"].get("TYPE", "")) != "ELEMENT":
        abaqus_deck_error("coupling surface is not element-based", surface["line"])
    if "INTERNAL" in surface["parameters"] and surface["parameters"]["INTERNAL"] is not None:
        abaqus_deck_error("SURFACE INTERNAL must be a flag", surface["line"])
    surface_nodes = set()
    used_faces = set()
    for line_number, line in surface["data"]:
        fields = abaqus_effective_fields(line)
        if len(fields) != 2:
            abaqus_deck_error("SURFACE row must have ELSET,face", line_number)
        surface_sets = abaqus_named_blocks(
            blocks, "ELSET", "ELSET", fields[0], positions["END INSTANCE"], positions["END ASSEMBLY"]
        )
        if not surface_sets or any(
            normalize_abaqus_name(block["parameters"].get("INSTANCE", "")) != normalize_abaqus_name(expected_instance)
            for block in surface_sets
        ):
            abaqus_deck_error("SURFACE ELSET is unresolved or belongs to another instance", line_number)
        for element_label in expand_abaqus_integer_blocks(surface_sets, "surface ELSET"):
            if element_label not in parsed_elements or (element_label, normalize_abaqus_name(fields[1])) in used_faces:
                abaqus_deck_error("SURFACE contains an invalid or duplicate element face", line_number)
            used_faces.add((element_label, normalize_abaqus_name(fields[1])))
            element_type, connectivity = parsed_elements[element_label]
            surface_nodes.update(connectivity[index] for index in abaqus_surface_face_indices(element_type, fields[1]))
    if surface_nodes != set(free_nodes):
        abaqus_deck_error("COUPLING surface is not exactly the complete Y=72 face")
    expected_free_faces = set()
    for element_label, (element_type, connectivity) in parsed_elements.items():
        for face_name in ("S1", "S2", "S3", "S4", "S5", "S6"):
            try:
                face_nodes = tuple(connectivity[index] for index in abaqus_surface_face_indices(element_type, face_name))
            except ValueError:
                continue
            if set(face_nodes).issubset(set(free_nodes)):
                expected_free_faces.add((element_label, face_name))
    if used_faces != expected_free_faces:
        abaqus_deck_error("COUPLING surface faces do not exactly cover the free end")
    return {"part_nodes": len(parsed_nodes), "part_elements": len(parsed_elements), "surface_nodes": len(surface_nodes)}


def audit_abaqus_input_deck(
    path, allowed_element_types, expected_nodes=None, expected_elements=None,
    fixed_nodes=None, free_nodes=None, expected_instance=None,
):
    with open(path, "rb") as stream:
        raw = stream.read()
    if not raw.endswith(b"\n"):
        abaqus_deck_error("input lacks a final newline")
    if any(value > 127 for value in raw):
        abaqus_deck_error("input is not 7-bit ASCII")
    if any(len(line.rstrip(b"\r")) > 256 for line in raw.split(b"\n")):
        abaqus_deck_error("input contains a line longer than 256 characters")
    text = raw.decode("ascii")
    blocks = parse_abaqus_input_text(text)
    by_name = {}
    for block in blocks:
        by_name.setdefault(block["keyword"], []).append(block)
    for name in (
        "HEADING", "PREPRINT", "PART", "SOLID SECTION", "END PART",
        "ASSEMBLY", "INSTANCE", "END INSTANCE", "SURFACE", "COUPLING",
        "KINEMATIC", "END ASSEMBLY", "MATERIAL", "ELASTIC", "BOUNDARY",
        "STEP", "STATIC", "CLOAD", "RESTART", "END STEP",
    ):
        require_abaqus_block_count(by_name, name, exact=1)
    require_abaqus_block_count(by_name, "NODE", minimum=2)
    require_abaqus_block_count(by_name, "ELEMENT", minimum=1)
    require_abaqus_block_count(by_name, "NSET", minimum=2)
    require_abaqus_block_count(by_name, "ELSET", minimum=2)
    require_abaqus_block_count(by_name, "OUTPUT", minimum=1)
    if blocks[0]["keyword"] != "HEADING" or blocks[-1]["keyword"] != "END STEP":
        abaqus_deck_error("HEADING and END STEP must delimit the complete input")
    for name in ("END PART", "END INSTANCE", "END ASSEMBLY", "END STEP"):
        for block in by_name.get(name, ()):
            if block["parameters"] or block["data"]:
                abaqus_deck_error("%s must not carry parameters or data" % name, block["line"])
    positions = audit_abaqus_input_scope(blocks)

    preprint = by_name["PREPRINT"][0]
    if set(preprint["parameters"]) != {"ECHO", "MODEL", "HISTORY", "CONTACT"} or any(
        normalize_abaqus_name(value) != "NO" for value in preprint["parameters"].values()
    ):
        abaqus_deck_error("PREPRINT contract is not the closed no-echo form", preprint["line"])
    for block in by_name["ELEMENT"]:
        element_type = normalize_abaqus_name(abaqus_parameter_value(block, "TYPE", required=True))
        if element_type not in set(normalize_abaqus_name(value) for value in allowed_element_types):
            abaqus_deck_error("unsupported solid element type %s" % element_type, block["line"])
        if not block["data"]:
            abaqus_deck_error("ELEMENT block is empty", block["line"])

    material = by_name["MATERIAL"][0]
    if set(material["parameters"]) != {"NAME"} or normalize_abaqus_name(material["parameters"]["NAME"]) != "STEEL":
        abaqus_deck_error("exactly one Steel material is required", material["line"])
    elastic = by_name["ELASTIC"][0]
    if elastic["parameters"] or len(elastic["data"]) != 1:
        abaqus_deck_error("Steel must have one isotropic ELASTIC row", elastic["line"])
    elastic_fields = abaqus_effective_fields(elastic["data"][0][1])
    if len(elastic_fields) != 2:
        abaqus_deck_error("ELASTIC row must contain only E and nu", elastic["data"][0][0])
    if abs(abaqus_number(elastic_fields[0], elastic["data"][0][0]) - 210000.0) > 0.01 or abs(
        abaqus_number(elastic_fields[1], elastic["data"][0][0]) - 0.3
    ) > 1.0e-8:
        abaqus_deck_error("ELASTIC row is not E=210000 MPa, nu=0.3", elastic["data"][0][0])
    section = by_name["SOLID SECTION"][0]
    if set(section["parameters"]) != {"ELSET", "MATERIAL"} or normalize_abaqus_name(section["parameters"]["MATERIAL"]) != "STEEL":
        abaqus_deck_error("SOLID SECTION is not bound only to Steel", section["line"])
    if any(abaqus_effective_fields(line) for line_number, line in section["data"]):
        abaqus_deck_error("SOLID SECTION has unsupported property data", section["line"])

    coupling = by_name["COUPLING"][0]
    if set(coupling["parameters"]) != {"CONSTRAINT NAME", "REF NODE", "SURFACE"} or coupling["data"]:
        abaqus_deck_error("COUPLING is not an unqualified whole-surface coupling", coupling["line"])
    kinematic = by_name["KINEMATIC"][0]
    kinematic_rows = [abaqus_effective_fields(line) for line_number, line in kinematic["data"]]
    if kinematic["parameters"] or (kinematic_rows and kinematic_rows != [["1", "6"]]):
        abaqus_deck_error("KINEMATIC coupling is not the complete 1-6 DOF form", kinematic["line"])
    boundary = by_name["BOUNDARY"][0]
    if set(boundary["parameters"]) not in (set(), {"OP"}) or (
        "OP" in boundary["parameters"] and normalize_abaqus_name(boundary["parameters"]["OP"]) != "NEW"
    ):
        abaqus_deck_error("BOUNDARY has unsupported parameters", boundary["line"])
    if len(boundary["data"]) != 1:
        abaqus_deck_error("exactly one Encastre boundary row is required", boundary["line"])
    boundary_fields = abaqus_effective_fields(boundary["data"][0][1])
    if len(boundary_fields) != 2 or normalize_abaqus_name(boundary_fields[1]) != "ENCASTRE":
        abaqus_deck_error("BOUNDARY row is not a complete Encastre", boundary["data"][0][0])

    step = by_name["STEP"][0]
    if "NAME" not in step["parameters"] or normalize_abaqus_name(step["parameters"]["NAME"]) != "STEP-TORQUE-B":
        abaqus_deck_error("STEP name is not Step-Torque-B", step["line"])
    if set(step["parameters"]) - {"NAME", "NLGEOM", "INC"}:
        abaqus_deck_error("STEP has unsupported parameters", step["line"])
    if "NLGEOM" in step["parameters"] and normalize_abaqus_name(step["parameters"]["NLGEOM"]) != "NO":
        abaqus_deck_error("STEP must use small-deflection NLGEOM=NO", step["line"])
    if "INC" in step["parameters"]:
        inc = abaqus_number(step["parameters"]["INC"], step["line"])
        if inc < 1.0 or abs(inc - round(inc)) > 1.0e-9:
            abaqus_deck_error("STEP INC is not a positive integer", step["line"])
    static = by_name["STATIC"][0]
    if set(static["parameters"]) not in (set(), {"DIRECT"}) or len(static["data"]) != 1:
        abaqus_deck_error("STATIC must have one standard increment row", static["line"])
    static_values = [abaqus_number(value, static["data"][0][0]) for value in abaqus_effective_fields(static["data"][0][1])]
    if not 1 <= len(static_values) <= 4 or any(value <= 0.0 for value in static_values):
        abaqus_deck_error("STATIC increment data are invalid", static["data"][0][0])
    if len(static_values) >= 2 and abs(static_values[1] - 1.0) > 1.0e-12:
        abaqus_deck_error("STATIC total time is not 1.0", static["data"][0][0])
    cload = by_name["CLOAD"][0]
    if set(cload["parameters"]) not in (set(), {"OP"}) or (
        "OP" in cload["parameters"] and normalize_abaqus_name(cload["parameters"]["OP"]) != "NEW"
    ) or len(cload["data"]) != 1:
        abaqus_deck_error("exactly one unamplified CLOAD row is required", cload["line"])
    cload_fields = abaqus_effective_fields(cload["data"][0][1])
    if len(cload_fields) != 3 or normalize_abaqus_name(cload_fields[0]) != normalize_abaqus_name(coupling["parameters"]["REF NODE"]):
        abaqus_deck_error("CLOAD does not target the coupling reference node", cload["data"][0][0])
    if abs(abaqus_number(cload_fields[1], cload["data"][0][0]) - 5.0) > 1.0e-12 or abs(
        abaqus_number(cload_fields[2], cload["data"][0][0]) - 920.0
    ) > 1.0e-5:
        abaqus_deck_error("CLOAD is not global CM2=+920 N*mm", cload["data"][0][0])
    restart = by_name["RESTART"][0]
    if set(restart["parameters"]) != {"WRITE", "FREQUENCY"} or restart["parameters"]["WRITE"] is not None or abs(
        abaqus_number(restart["parameters"]["FREQUENCY"], restart["line"])
    ) > 1.0e-12 or restart["data"]:
        abaqus_deck_error("RESTART must be disabled with WRITE,FREQUENCY=0", restart["line"])
    for output in by_name["OUTPUT"]:
        modes = set(output["parameters"]) & {"FIELD", "HISTORY"}
        if len(modes) != 1 or output["parameters"][next(iter(modes))] is not None:
            abaqus_deck_error("OUTPUT is neither a field nor history request", output["line"])
        if "VARIABLE" in output["parameters"] and normalize_abaqus_name(output["parameters"]["VARIABLE"]) not in ("PRESELECT", "ALL"):
            abaqus_deck_error("OUTPUT uses an unsupported variable preset", output["line"])
    mesh_audit = None
    expected_values = (expected_nodes, expected_elements, fixed_nodes, free_nodes, expected_instance)
    if any(value is not None for value in expected_values):
        if any(value is None for value in expected_values):
            abaqus_deck_error("deck/CAE cross-check inputs are incomplete")
        mesh_audit = audit_abaqus_deck_mesh_and_regions(
            blocks, positions, expected_nodes, expected_elements, fixed_nodes, free_nodes, expected_instance
        )
    return {
        "block_count": len(blocks),
        "keywords": tuple(block["keyword"] for block in blocks),
        "element_types": tuple(sorted(set(
            normalize_abaqus_name(block["parameters"]["TYPE"]) for block in by_name["ELEMENT"]
        ))),
        "mesh_audit": mesh_audit,
    }
'''


ABAQUS_CHECKER = r'''
# -*- coding: utf-8 -*-
from __future__ import print_function

import builtins
import json
import math
import os
import re
import hashlib
import shutil
import time
import traceback

from abaqus import mdb, openMdb
from abaqusConstants import KINEMATIC, OFF, ON, SIZE
from caeModules import *
from odbAccess import openOdb

CAE_PATH = __CAE_PATH__
ODB_PATH = __ODB_PATH__
RESULT_PATH = __RESULT_PATH__
RECHECK_JOB = __RECHECK_JOB__
AUDIT_ROOT = __AUDIT_ROOT__
SOLVE_ROOT = __SOLVE_ROOT__
POST_ROOT = __POST_ROOT__
JOB_NAME = "Job-Torsion-B"
STEP_NAME = "Step-Torque-B"
METRICS = __METRICS__
DETAILS = []
ALLOWED_TYPES = (
    "C3D4", "C3D4H", "C3D10", "C3D10H", "C3D10M", "C3D10MH",
    "C3D6", "C3D6H", "C3D15", "C3D15H",
    "C3D8", "C3D8R", "C3D8I", "C3D8H", "C3D8RH",
    "C3D20", "C3D20R", "C3D20H", "C3D20RH",
)

__DECK_HELPERS__


def fail(message):
    DETAILS.append(str(message))
    return None


def ci(value):
    try:
        return str(value).strip().upper()
    except Exception:
        return ""


def finite(value):
    try:
        return math.isfinite(float(value))
    except Exception:
        return False


def close(actual, expected, rel=1.0e-3, absolute=1.0e-8):
    try:
        return math.isclose(float(actual), float(expected), rel_tol=rel, abs_tol=absolute)
    except Exception:
        return False


def file_sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        while True:
            block = stream.read(1048576)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def bool_on(value):
    if isinstance(value, (int, float)):
        return abs(float(value) - 1.0) <= 1.0e-12
    return ci(value) in ("ON", "TRUE", "1", "1.0")


def numbers(value):
    out = []
    if isinstance(value, (int, float)):
        return [float(value)]
    try:
        for item in value:
            out.extend(numbers(item))
    except Exception:
        try:
            out.append(float(value))
        except Exception:
            pass
    return out


def optional_moment_component(value):
    if value is None or ci(value) == "UNSET":
        return 0.0
    try:
        result = float(value)
    except Exception:
        return None
    return result if math.isfinite(result) else None


def repository_value_ci(repository, name):
    if not name:
        return None
    try:
        for key in repository.keys():
            if ci(key) == ci(name):
                return repository[key]
    except Exception:
        pass
    return None


def region_name(region):
    if isinstance(region, (str, bytes)):
        return str(region)
    for attr in ("name", "setName", "surfaceName"):
        try:
            value = getattr(region, attr)
            if value:
                return str(value)
        except Exception:
            pass
    text = repr(region)
    for pattern in (
        r"^\(\s*['\"]([^'\"]+)['\"]\s*,",
        r"name\s*=\s*['\"]([^'\"]+)['\"]",
        r"setName\s*=\s*['\"]([^'\"]+)['\"]",
        r"surfaceName\s*=\s*['\"]([^'\"]+)['\"]",
    ):
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return None


def resolve_region(owner, region, kind):
    name = region_name(region)
    repository = getattr(owner, "surfaces" if kind == "surface" else "sets", {})
    resolved = repository_value_ci(repository, name)
    return resolved if resolved is not None else region


def flatten_entities(value, identity_attr):
    rows = []
    pending = []
    try:
        pending.extend(list(value))
    except Exception:
        pending.append(value)
    seen = set()
    while pending:
        item = pending.pop()
        if hasattr(item, identity_attr):
            marker = (getattr(item, "instanceName", ""), getattr(item, identity_attr))
            if marker not in seen:
                seen.add(marker)
                rows.append(item)
            continue
        try:
            pending.extend(list(item))
        except Exception:
            pass
    return rows


def entity_nodes(entity):
    nodes = []
    try:
        nodes.extend(flatten_entities(entity.nodes, "label"))
    except Exception:
        pass
    for attr in ("faces", "side1Faces", "side2Faces"):
        try:
            faces = list(getattr(entity, attr))
        except Exception:
            continue
        for face in faces:
            try:
                nodes.extend(flatten_entities(face.getNodes(), "label"))
            except Exception:
                pass
    unique = {}
    for node in nodes:
        unique[(str(getattr(node, "instanceName", "")), int(node.label))] = node
    return list(unique.values())


def entity_cells(entity):
    try:
        return flatten_entities(entity.cells, "index")
    except Exception:
        return []


def coordinates(value):
    for attr in ("pointOn", "point", "coordinates"):
        try:
            observed = getattr(value, attr)
        except Exception:
            continue
        attempts = []
        try:
            attempts.append(tuple(float(observed[index]) for index in range(3)))
        except Exception:
            pass
        try:
            attempts.append(tuple(float(item) for item in observed))
        except Exception:
            pass
        numeric = tuple(numbers(observed))
        if numeric:
            attempts.append(numeric)
        for found in attempts:
            if len(found) == 3 and all(finite(item) for item in found):
                return tuple(float(item) for item in found)
    return None


def reference_point_rows(assembly):
    rows = []
    try:
        for key in assembly.referencePoints.keys():
            value = assembly.referencePoints[key]
            rows.append((str(key), value, coordinates(value), repr(value)))
    except Exception:
        pass
    return rows


def reference_point_signature(value, repository_rows):
    xyz = coordinates(value)
    identity = [row for row in repository_rows if value is row[1] or repr(value) == row[3]]
    key = identity[0][0] if len(identity) == 1 else None
    if xyz is None and len(identity) == 1:
        xyz = identity[0][2]
    matches = [] if xyz is None else [
        row for row in repository_rows
        if row[2] is not None and all(close(row[2][i], xyz[i], rel=0.0, absolute=1.0e-7) for i in range(3))
    ]
    if len(matches) == 1:
        key = matches[0][0]
    return (key, xyz)


def region_reference_points(region):
    try:
        values = list(region.referencePoints)
    except Exception:
        return []
    flattened = flatten_entities(values, "pointOn")
    return flattened if flattened else values


def step_repository_states(model, step_names, repository_attr, object_name):
    rows = []
    for step_name in step_names:
        step = repository_value_ci(model.steps, step_name)
        if step is None:
            continue
        state = repository_value_ci(getattr(step, repository_attr, {}), object_name)
        if state is not None:
            rows.append((str(step_name), state))
    return rows


def state_at(history_object, step_name):
    try:
        return history_object.getState(step_name)
    except Exception:
        pass
    try:
        return history_object.states[step_name]
    except Exception:
        return None


def history_states(history_object, step_names):
    rows = []
    seen = set()
    for step_name in step_names:
        state = state_at(history_object, step_name)
        if state is None or id(state) in seen:
            continue
        seen.add(id(state))
        rows.append((str(step_name), state))
    return rows


def state_is_active(state):
    status = ci(getattr(state, "status", ""))
    return not any(token in status for token in ("NOT_YET_ACTIVE", "DEACTIVATED", "INACTIVE", "SUPPRESSED"))


def first_attr(objects, attr):
    for value in objects:
        try:
            observed = getattr(value, attr)
            if observed is not None:
                return observed
        except Exception:
            pass
    return None


def moment_component(objects, attr):
    for value in objects:
        try:
            observed = getattr(value, attr)
        except Exception:
            continue
        converted = optional_moment_component(observed)
        if converted is not None and (converted != 0.0 or ci(observed) != "UNSET"):
            return converted
    return 0.0


def region_labels(region):
    result = set()
    for attr in ("nodes", "referencePoints"):
        try:
            pending = list(getattr(region, attr))
            while pending:
                item = pending.pop()
                label = getattr(item, "label", getattr(item, "id", None))
                if label is not None:
                    result.add(int(label))
                    continue
                try:
                    pending.extend(list(item))
                except Exception:
                    pass
        except Exception:
            pass
    return result


def instance_coords(model):
    rows = {}
    for name in model.rootAssembly.instances.keys():
        instance = model.rootAssembly.instances[name]
        for node in instance.nodes:
            rows[(ci(name), int(node.label))] = tuple(float(value) for value in node.coordinates)
    return rows


def bbox(coords):
    rows = list(coords.values())
    return tuple((min(row[i] for row in rows), max(row[i] for row in rows)) for i in range(3))


def radial(point):
    return math.sqrt(float(point[0]) ** 2 + float(point[2]) ** 2)


def element_nodes(owner, element):
    try:
        return list(element.getNodes())
    except Exception:
        return [owner.nodes[int(index)] for index in element.connectivity]


def tet_volume(a, b, c, d):
    ab = tuple(b[i] - a[i] for i in range(3))
    ac = tuple(c[i] - a[i] for i in range(3))
    ad = tuple(d[i] - a[i] for i in range(3))
    cross = (
        ac[1] * ad[2] - ac[2] * ad[1],
        ac[2] * ad[0] - ac[0] * ad[2],
        ac[0] * ad[1] - ac[1] * ad[0],
    )
    return abs(builtins.sum(ab[i] * cross[i] for i in range(3))) / 6.0


def corner_spec(element_type):
    upper = ci(element_type)
    if upper.startswith("C3D4"):
        faces = tuple((face, face) for face in ((0,1,2),(0,3,1),(1,3,2),(2,3,0)))
        return 4, faces, ((0,1),(0,2),(0,3),(1,2),(1,3),(2,3))
    if upper.startswith("C3D10"):
        faces = (
            ((0,1,2),(0,1,2,4,5,6)),
            ((0,3,1),(0,3,1,7,8,4)),
            ((1,3,2),(1,3,2,8,9,5)),
            ((2,3,0),(2,3,0,9,7,6)),
        )
        return 4, faces, ((0,1),(0,2),(0,3),(1,2),(1,3),(2,3))
    if upper.startswith("C3D6"):
        faces = tuple((face, face) for face in ((0,1,2),(3,5,4),(0,3,4,1),(1,4,5,2),(2,5,3,0)))
        return 6, faces, ((0,1),(1,2),(2,0),(3,4),(4,5),(5,3),(0,3),(1,4),(2,5))
    if upper.startswith("C3D15"):
        faces = (
            ((0,1,2),(0,1,2,6,7,8)),
            ((3,5,4),(3,5,4,11,10,9)),
            ((0,3,4,1),(0,3,4,1,12,9,13,6)),
            ((1,4,5,2),(1,4,5,2,13,10,14,7)),
            ((2,5,3,0),(2,5,3,0,14,11,12,8)),
        )
        return 6, faces, ((0,1),(1,2),(2,0),(3,4),(4,5),(5,3),(0,3),(1,4),(2,5))
    if upper.startswith("C3D8"):
        faces = tuple((face, face) for face in ((0,1,2,3),(4,7,6,5),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)))
        return 8, faces, ((0,1),(1,2),(2,3),(3,0),(4,5),(5,6),(6,7),(7,4),(0,4),(1,5),(2,6),(3,7))
    if upper.startswith("C3D20"):
        faces = (
            ((0,1,2,3),(0,1,2,3,8,9,10,11)),
            ((4,7,6,5),(4,7,6,5,15,14,13,12)),
            ((0,4,5,1),(0,4,5,1,16,12,17,8)),
            ((1,5,6,2),(1,5,6,2,17,13,18,9)),
            ((2,6,7,3),(2,6,7,3,18,14,19,10)),
            ((3,7,4,0),(3,7,4,0,19,15,16,11)),
        )
        return 8, faces, ((0,1),(1,2),(2,3),(3,0),(4,5),(5,6),(6,7),(7,4),(0,4),(1,5),(2,6),(3,7))
    return None


def element_volume(points, corners):
    p = points[:corners]
    if corners == 4:
        return tet_volume(p[0], p[1], p[2], p[3])
    if corners == 6:
        return (
            tet_volume(p[0], p[1], p[2], p[3])
            + tet_volume(p[1], p[2], p[4], p[3])
            + tet_volume(p[2], p[4], p[5], p[3])
        )
    return (
        tet_volume(p[0], p[1], p[3], p[4])
        + tet_volume(p[1], p[2], p[3], p[6])
        + tet_volume(p[1], p[3], p[4], p[6])
        + tet_volume(p[1], p[4], p[5], p[6])
        + tet_volume(p[3], p[4], p[6], p[7])
    )


def audit_cad_geometry(part):
    if len(part.cells) != 1 or len(part.faces) != 3:
        return fail("shaft CAD is not one solid cell with two ends and one cylindrical face")
    try:
        properties = part.getMassProperties(useMesh=False)
        volume = float(properties["volume"])
        centroid = tuple(float(value) for value in properties["volumeCentroid"])
    except Exception:
        return fail("shaft CAD volume or volume centroid is unreadable")
    expected_volume = math.pi * 36.0 * 72.0
    if not close(volume, expected_volume, rel=2.0e-6, absolute=0.02):
        return fail("shaft CAD volume is not the exact d12 x L72 cylinder")
    if len(centroid) != 3 or any(
        not close(centroid[index], (0.0, 36.0, 0.0)[index], rel=0.0, absolute=1.0e-5)
        for index in range(3)
    ):
        return fail("shaft CAD volume centroid is not (0,36,0)")
    circular_edges = []
    for edge in part.edges:
        try:
            radius = float(edge.getRadius())
        except Exception:
            continue
        if close(radius, 6.0, rel=0.0, absolute=1.0e-5):
            circular_edges.append(edge)
    try:
        if len(circular_edges) != 2 or any(
            len(edge.getVertices()) != 1 for edge in circular_edges
        ):
            return fail("shaft CAD does not have exactly two closed radius-6 circular cap edges")
        circular_indices = set(int(edge.index) for edge in circular_edges)
        lateral_faces = [
            face
            for face in part.faces
            if circular_indices.issubset(set(int(index) for index in face.getEdges()))
        ]
        if len(lateral_faces) != 1:
            return fail("shaft CAD has no unique lateral face bounded by both cap circles")
        curvature = lateral_faces[0].getCurvature(
            point=tuple(float(value) for value in lateral_faces[0].pointOn[0])
        )
        principal = sorted(
            abs(float(curvature[name])) for name in ("curvature1", "curvature2")
        )
    except Exception:
        return fail("shaft CAD circular-edge or lateral-curvature evidence is unreadable")
    if principal[0] > 1.0e-7 or not close(
        principal[1], 1.0 / 6.0, rel=0.0, absolute=1.0e-5
    ):
        return fail("shaft CAD lateral face is not an analytic radius-6 cylinder")
    return {
        "volume": volume,
        "centroid": centroid,
        "cell_count": 1,
        "face_count": 3,
        "circular_edge_count": 2,
        "principal_curvatures": tuple(principal),
    }


def audit_mesh(part, assembly_coords):
    if "DEFORMABLE" not in ci(getattr(part, "type", "")) or not len(part.cells):
        return fail("shaft part is not a 3D deformable solid")
    dimensionality = ci(getattr(part, "dimensionality", ""))
    if dimensionality and "THREE_D" not in dimensionality:
        return fail("shaft part dimensionality is not THREE_D")
    try:
        global_seed = float(part.getPartSeeds(SIZE))
    except Exception:
        return fail("global mesh seed is unreadable")
    if not close(global_seed, 4.0, rel=0.0, absolute=0.01):
        return fail("global mesh seed is not 4 mm")
    part_coords = dict((int(node.label), tuple(float(v) for v in node.coordinates)) for node in part.nodes)
    if not part_coords or not assembly_coords:
        return fail("mesh coordinates are unavailable")
    bounds = bbox(assembly_coords)
    if not close(bounds[1][0], 0.0, rel=0.0, absolute=0.12) or not close(
        bounds[1][1], 72.0, rel=0.0, absolute=0.12
    ):
        return fail("assembly axial bounds are not Y=0..72 mm")
    assembly_radii = [radial(point) for point in assembly_coords.values()]
    if (
        not assembly_radii
        or max(assembly_radii) < 5.88
        or max(assembly_radii) > 6.12
        or any(value > 6.12 for value in assembly_radii)
    ):
        return fail("assembly radial extent is not the centered radius-6 shaft")
    face_owners = {}
    element_labels = set()
    element_neighbors = {}
    corner_connectivity = set()
    total_volume = 0.0
    attached = set()
    edge_lengths = []
    for element in part.elements:
        element_label = int(element.label)
        if element_label in element_labels:
            return fail("mesh contains duplicate element labels")
        element_labels.add(element_label)
        element_neighbors[element_label] = set()
        if ci(element.type) not in ALLOWED_TYPES:
            return fail("non-supported 3D solid element type: %s" % element.type)
        spec = corner_spec(element.type)
        nodes = element_nodes(part, element)
        if spec is None or len(nodes) < spec[0]:
            return fail("solid connectivity is incomplete")
        labels = tuple(int(node.label) for node in nodes[:spec[0]])
        if len(set(labels)) != len(labels) or any(label not in part_coords for label in labels):
            return fail("solid connectivity is degenerate")
        corner_key = frozenset(labels)
        if corner_key in corner_connectivity:
            return fail("mesh contains duplicate solid corner connectivity")
        corner_connectivity.add(corner_key)
        attached.update(int(node.label) for node in nodes)
        points = [part_coords[label] for label in labels]
        volume = element_volume(points, spec[0])
        if volume <= 1.0e-9:
            return fail("solid element has zero volume")
        total_volume += volume
        for first, second in spec[2]:
            length = math.sqrt(builtins.sum((points[first][i] - points[second][i]) ** 2 for i in range(3)))
            edge_lengths.append(length)
        all_labels = tuple(int(node.label) for node in nodes)
        for corner_indices, full_indices in spec[1]:
            key = frozenset(all_labels[index] for index in corner_indices)
            face_owners.setdefault(key, []).append(
                (element_label, tuple(all_labels[index] for index in full_indices))
            )
    if attached != set(part_coords):
        return fail("mesh contains unattached nodes")
    if any(len(owners) not in (1, 2) for owners in face_owners.values()):
        return fail("mesh contains non-manifold faces")
    for owners in face_owners.values():
        if len(owners) != 2:
            continue
        first, second = owners
        if frozenset(first[1]) != frozenset(second[1]):
            return fail("quadratic mesh has a nonconforming shared midside face")
        element_neighbors[first[0]].add(second[0])
        element_neighbors[second[0]].add(first[0])
    pending = [next(iter(element_labels))] if element_labels else []
    reached = set()
    while pending:
        current = pending.pop()
        if current in reached:
            continue
        reached.add(current)
        pending.extend(element_neighbors[current] - reached)
    if reached != element_labels:
        return fail("shaft solid mesh is not one face-connected body")
    ordered_edges = sorted(edge_lengths)
    if not ordered_edges:
        return fail("solid mesh edge lengths are unavailable")
    def edge_percentile(fraction):
        position = fraction * (len(ordered_edges) - 1)
        lower = int(math.floor(position))
        upper = int(math.ceil(position))
        if lower == upper:
            return ordered_edges[lower]
        weight = position - lower
        return ordered_edges[lower] * (1.0 - weight) + ordered_edges[upper] * weight
    edge_median = edge_percentile(0.5)
    edge_p90 = edge_percentile(0.9)
    if not (
        ordered_edges[0] >= 0.50
        and 2.40 <= edge_median <= 5.20
        and 3.00 <= edge_p90 <= 6.20
        and ordered_edges[-1] <= 8.20
    ):
        return fail("solid mesh edge distribution is inconsistent with a 4 mm target")
    exterior = [owners[0][1] for owners in face_owners.values() if len(owners) == 1]
    end0 = set()
    end72 = set()
    lateral_faces = 0
    for face in exterior:
        points = [part_coords[label] for label in face]
        if all(abs(point[1]) <= 0.12 for point in points):
            end0.update(face)
        elif all(abs(point[1] - 72.0) <= 0.12 for point in points):
            end72.update(face)
        else:
            lateral_faces += 1
            if any(abs(radial(point) - 6.0) > 0.60 for point in points):
                return fail("an exterior lateral face is not on the radius-6 outer cylinder; hollow or wrong geometry")
    exact_volume = math.pi * 36.0 * 72.0
    if not (0.84 * exact_volume < total_volume < 1.03 * exact_volume):
        return fail("solid mesh volume is not the complete d12 x L72 cylinder")
    if len(end0) < 6 or len(end72) < 6 or lateral_faces < 10:
        return fail("complete shaft end/lateral surfaces were not found")
    return {
        "part_coords": part_coords,
        "fixed_part_nodes": end0,
        "free_part_nodes": end72,
        "volume": total_volume,
        "edge_statistics": {
            "minimum": ordered_edges[0],
            "median": edge_median,
            "p90": edge_p90,
            "maximum": ordered_edges[-1],
        },
    }


def material_and_section(model, part):
    matches = []
    for name in model.materials.keys():
        material = model.materials[name]
        try:
            e_value, nu_value = material.elastic.table[0][:2]
        except Exception:
            continue
        if ci(name) == "STEEL" and close(e_value, 210000.0, rel=1.0e-5) and close(nu_value, 0.3, rel=1.0e-5):
            matches.append(name)
    if len(matches) != 1:
        return fail("exactly one Steel material with E=210000 MPa and nu=0.3 is required")
    try:
        assignments = list(part.sectionAssignments)
    except Exception:
        return fail("part section assignments are unreadable")
    covered = set()
    coverage_readable = True
    for assignment in assignments:
        section_name = getattr(assignment, "sectionName", "")
        try:
            section = model.sections[section_name]
        except Exception:
            return fail("assigned section is missing")
        if "SOLID" not in ci(section.__class__.__name__) or ci(getattr(section, "material", "")) != "STEEL":
            return fail("every assigned section must be a homogeneous solid Steel section")
        cells = entity_cells(assignment.region)
        if not cells:
            resolved = resolve_region(part, assignment.region, "set")
            cells = entity_cells(resolved)
        if not cells:
            coverage_readable = False
            continue
        covered.update(int(cell.index) for cell in cells)
    if coverage_readable and covered != set(int(cell.index) for cell in part.cells):
        return fail("Steel solid section does not cover the entire shaft")
    return {"coverage_readable": coverage_readable, "covered_cells": covered}


def map_region_to_part_labels(assembly, region, kind="set"):
    resolved = resolve_region(assembly, region, kind)
    return set(int(node.label) for node in entity_nodes(resolved))


def six_dof_fixed(objects):
    for name in ("u1", "u2", "u3", "ur1", "ur2", "ur3"):
        values = [ci(getattr(value, name, "")) for value in objects]
        if not any(value in ("SET", "FIXED", "0", "0.0") for value in values):
            return False
    return True


def audit_process(model, part, instance, mesh_info):
    if STEP_NAME not in model.steps.keys() or "STATIC" not in ci(model.steps[STEP_NAME].__class__.__name__):
        return fail("Step-Torque-B is not a Static, General step")
    if len(model.steps.keys()) != 2:
        return fail("the model must contain only Initial and Step-Torque-B")
    step = model.steps[STEP_NAME]
    if bool_on(getattr(step, "nlgeom", OFF)):
        return fail("Step-Torque-B must use small-deflection NLGEOM=OFF")
    try:
        if not close(float(step.timePeriod), 1.0, rel=0.0, absolute=1.0e-12):
            return fail("Step-Torque-B total time is not 1.0")
    except Exception:
        return fail("Step-Torque-B total time is unreadable")
    fixed_expected = mesh_info["fixed_part_nodes"]
    matching_bcs = []
    active_bcs = []
    for name in model.boundaryConditions.keys():
        bc = model.boundaryConditions[name]
        if bool(getattr(bc, "suppressed", False)):
            continue
        states = history_states(bc, ("Initial", STEP_NAME))
        states.extend(step_repository_states(model, ("Initial", STEP_NAME), "boundaryConditionStates", name))
        evidence = [bc] + [state for step_name, state in states]
        target_states = [state for step_name, state in states if ci(step_name) == ci(STEP_NAME)]
        propagated_type_bc = (
            ci(bc.__class__.__name__) == "TYPEBC"
            and any(ci(state.__class__.__name__) == "TYPEBCSTATE" and ci(getattr(state, "status", "")) == "PROPAGATED" for state in target_states)
        )
        if target_states and not any(state_is_active(state) for state in target_states):
            continue
        active_bcs.append(bc)
        if "ENCASTRE" not in ci(bc.__class__.__name__) and not six_dof_fixed(evidence) and not propagated_type_bc:
            return fail("only an Encastre boundary condition is allowed")
        labels = map_region_to_part_labels(model.rootAssembly, bc.region)
        if labels == fixed_expected:
            matching_bcs.append(bc)
    if len(matching_bcs) != 1 or len(active_bcs) != 1:
        return fail("Y=0 complete end face must have exactly one Encastre BC")
    rp_rows = reference_point_rows(model.rootAssembly)
    if len(rp_rows) != 1:
        return fail("exactly one assembly reference point is required")
    rp_key = rp_rows[0][0]
    rp_set = repository_value_ci(model.rootAssembly.sets, "RP-1")
    rp_set_values = region_reference_points(rp_set) if rp_set is not None else []
    rp_signatures = [reference_point_signature(value, rp_rows) for value in rp_set_values]
    if len(rp_signatures) != 1 or rp_signatures[0][0] != rp_key:
        return fail("RP-1 set does not reference the unique assembly reference point")
    couplings = []
    for name in model.constraints.keys():
        constraint = model.constraints[name]
        if bool(getattr(constraint, "suppressed", False)):
            continue
        if "COUPLING" not in ci(constraint.__class__.__name__):
            return fail("an unsupported additional constraint is present")
        if ci(getattr(constraint, "couplingType", "")) != "KINEMATIC":
            return fail("end coupling is not kinematic")
        surface_labels = map_region_to_part_labels(model.rootAssembly, constraint.surface, "surface")
        control = resolve_region(model.rootAssembly, constraint.controlPoint, "set")
        control_signatures = [reference_point_signature(value, rp_rows) for value in region_reference_points(control)]
        same_rp = len(control_signatures) == 1 and control_signatures[0][0] == rp_key
        if surface_labels == mesh_info["free_part_nodes"] and same_rp:
            for dof in ("u1", "u2", "u3", "ur1", "ur2", "ur3"):
                if not bool_on(getattr(constraint, dof, "")):
                    return fail("kinematic coupling does not constrain all required DOFs")
            couplings.append(constraint)
    active_constraints = [
        model.constraints[name] for name in model.constraints.keys()
        if not bool(getattr(model.constraints[name], "suppressed", False))
    ]
    if active_constraints and (len(couplings) != 1 or len(active_constraints) != 1):
        return fail("when exposed by the CAE repository, exactly one RP-to-complete-Y72-face kinematic coupling is required")
    if not active_constraints:
        DETAILS.append("CAE constraints repository is empty; coupling acceptance is deferred to the freshly generated and structurally audited INP")
    loads = []
    for name in model.loads.keys():
        load = model.loads[name]
        if bool(getattr(load, "suppressed", False)):
            continue
        states = history_states(load, ("Initial", STEP_NAME))
        states.extend(step_repository_states(model, ("Initial", STEP_NAME), "loadStates", name))
        target_states = [state for step_name, state in states if ci(step_name) == ci(STEP_NAME)]
        if target_states and not any(state_is_active(state) for state in target_states):
            continue
        if "MOMENT" not in ci(load.__class__.__name__):
            return fail("an unsupported additional load is present")
        evidence = [load] + [state for step_name, state in states]
        create_step = ci(first_attr(evidence, "createStepName"))
        if not target_states and create_step != ci(STEP_NAME):
            return fail("moment is not active in Step-Torque-B")
        load_region = resolve_region(model.rootAssembly, first_attr(evidence, "region"), "set")
        load_signatures = [reference_point_signature(value, rp_rows) for value in region_reference_points(load_region)]
        same_rp = len(load_signatures) == 1 and load_signatures[0][0] == rp_key
        if not same_rp:
            return fail("moment is not applied to RP-1")
        cm1 = moment_component(evidence, "cm1")
        cm2 = moment_component(evidence, "cm2")
        cm3 = moment_component(evidence, "cm3")
        if None in (cm1, cm2, cm3) or not close(cm2, 920.0, rel=1.0e-6, absolute=1.0e-5) or abs(cm1) > 1.0e-10 or abs(cm3) > 1.0e-10:
            return fail("RP moment is not exactly global +Y CM2=920 N*mm")
        loads.append(load)
    if len(loads) != 1:
        return fail("exactly one RP moment load is required")
    if len(model.interactions.keys()) or len(model.predefinedFields.keys()):
        return fail("unexpected interaction or predefined field is present")
    return {"rp_key": rp_key}


def odb_mesh(odb, target_instance_name):
    coords = {}
    connectivity = {}
    matching = [name for name in odb.rootAssembly.instances.keys() if ci(name) == ci(target_instance_name)]
    if len(matching) != 1:
        return coords, connectivity
    name = matching[0]
    instance = odb.rootAssembly.instances[name]
    for node in instance.nodes:
        coords[(ci(name), int(node.label))] = tuple(float(value) for value in node.coordinates)
    for element in instance.elements:
        connectivity[(ci(name), int(element.label))] = (ci(element.type), tuple(int(value) for value in element.connectivity))
    return coords, connectivity


def flatten_odb_entities(value, identity_attr):
    rows = []
    pending = []
    try:
        pending.extend(list(value))
    except Exception:
        pending.append(value)
    while pending:
        item = pending.pop()
        if hasattr(item, identity_attr):
            rows.append(item)
            continue
        try:
            pending.extend(list(item))
        except Exception:
            pass
    return rows


def odb_section_and_material(odb, target_instance_name, expected_elements):
    matching = [name for name in odb.rootAssembly.instances.keys() if ci(name) == ci(target_instance_name)]
    if len(matching) != 1:
        return False
    instance = odb.rootAssembly.instances[matching[0]]
    expected_labels = set(label for name, label in expected_elements if name == ci(target_instance_name))
    covered = set()
    for assignment in instance.sectionAssignments:
        try:
            section = odb.sections[assignment.sectionName]
        except Exception:
            return False
        if ci(getattr(section, "material", "")) != "STEEL":
            return False
        elements = flatten_odb_entities(getattr(assignment.region, "elements", ()), "label")
        covered.update(int(element.label) for element in elements)
    if covered != expected_labels:
        return False
    try:
        material = next(odb.materials[name] for name in odb.materials.keys() if ci(name) == "STEEL")
        e_value, nu_value = material.elastic.table[0][:2]
    except Exception:
        return False
    return close(e_value, 210000.0, rel=1.0e-5) and close(nu_value, 0.3, rel=1.0e-5)


def field_signature(field):
    rows = []
    for value in field.values:
        data = tuple(float(item) for item in numbers(getattr(value, "data", ())))
        if not data or any(not finite(item) for item in data):
            return None
        rows.append((
            ci(getattr(value, "instance", None).name if getattr(value, "instance", None) else "ASSEMBLY"),
            int(getattr(value, "nodeLabel", getattr(value, "elementLabel", 0)) or 0),
            ci(getattr(value, "position", "")),
            int(getattr(value, "integrationPoint", 0) or 0),
            int(getattr(value, "sectionPoint", 0).number if getattr(value, "sectionPoint", None) else 0),
            data,
        ))
    return sorted(rows)


def flatten_odb_nodes(value):
    rows = []
    try:
        items = list(value)
    except Exception:
        items = [value]
    for item in items:
        if hasattr(item, "label") and hasattr(item, "coordinates"):
            rows.append(item)
            continue
        try:
            rows.extend(flatten_odb_nodes(item))
        except Exception:
            pass
    return rows


def odb_reference_point_set(odb):
    repositories = getattr(odb.rootAssembly, "nodeSets", {})
    candidates = []
    for name in repositories.keys():
        if ci(name) != "RP-1" and "RP" not in ci(name):
            continue
        node_set = repositories[name]
        nodes = flatten_odb_nodes(getattr(node_set, "nodes", ()))
        if len(nodes) != 1:
            continue
        coords = tuple(float(value) for value in nodes[0].coordinates)
        if len(coords) != 3 or any(abs(coords[i] - (0.0, 72.0, 0.0)[i]) > 1.0e-7 for i in range(3)):
            continue
        candidates.append((0 if ci(name) == "RP-1" else 1, ci(name), node_set, nodes[0]))
    candidates.sort(key=lambda row: (row[0], row[1]))
    exact = [row for row in candidates if row[0] == 0]
    if len(exact) == 1:
        return exact[0][2], exact[0][3]
    if not exact and len(candidates) == 1:
        return candidates[0][2], candidates[0][3]
    return None, None


def odb_result(path, expected_mesh, fixed_labels, target_instance_name, require_completed=True):
    odb = openOdb(path=path, readOnly=True)
    try:
        status = ci(getattr(odb.diagnosticData, "jobStatus", ""))
        if require_completed and "COMPLETED_SUCCESSFULLY" not in status and status != "COMPLETED":
            return fail("ODB job status is not COMPLETED_SUCCESSFULLY")
        if STEP_NAME not in odb.steps.keys() or len(odb.steps.keys()) != 1:
            return fail("ODB does not contain exactly Step-Torque-B")
        step = odb.steps[STEP_NAME]
        if len(step.frames) < 2:
            return fail("ODB static step has no completed result frame")
        if not close(float(step.frames[-1].frameValue), 1.0, rel=0.0, absolute=1.0e-10):
            return fail("ODB final result time is not 1.0")
        coords, connectivity = odb_mesh(odb, target_instance_name)
        expected_coords, expected_connectivity = expected_mesh
        coords_match = set(coords) == set(expected_coords) and all(
            all(close(coords[key][axis], expected_coords[key][axis], rel=0.0, absolute=1.0e-9) for axis in range(3))
            for key in coords
        )
        if not coords_match or connectivity != expected_connectivity:
            return fail("CAE and ODB meshes are not identical")
        if not odb_section_and_material(odb, target_instance_name, set(connectivity)):
            return fail("ODB Steel solid section does not cover the complete shaft")
        frame = step.frames[-1]
        required = ("U", "UR", "RF", "RM", "S")
        if any(name not in frame.fieldOutputs.keys() for name in required):
            return fail("ODB lacks complete U/UR/RF/RM/S output")
        signatures = dict((name, field_signature(frame.fieldOutputs[name])) for name in required)
        if any(signatures[name] is None for name in required):
            return fail("ODB contains missing or non-finite required field data")
        rp_set, rp_node = odb_reference_point_set(odb)
        if rp_set is None or rp_node is None:
            return fail("ODB does not identify one RP-1 node at (0,72,0)")
        try:
            ur_values = list(frame.fieldOutputs["UR"].getSubset(region=rp_set).values)
        except Exception:
            ur_values = [
                value for value in frame.fieldOutputs["UR"].values
                if int(getattr(value, "nodeLabel", -1)) == int(rp_node.label)
                and getattr(value, "instance", None) is None
            ]
        if len(ur_values) != 1:
            return fail("ODB RP-1 set does not contain exactly one UR result")
        rp_rotation = numbers(ur_values[0].data)
        if len(rp_rotation) < 3:
            return fail("ODB RP-1 rotational displacement vector is incomplete")
        twist = abs(float(rp_rotation[1]))
        if not (3.2e-4 <= twist <= 6.0e-4):
            return fail("native RP UR2 magnitude is outside the Task-10 physical range")
        if any(abs(float(value)) > max(1.0e-7, abs(twist) * 0.01) for i, value in enumerate(rp_rotation[:3]) if i != 1):
            return fail("RP rotation is not about global Y")
        mises = []
        stress_elements = set()
        for value in frame.fieldOutputs["S"].values:
            if ci(getattr(getattr(value, "instance", None), "name", "")) not in set(key[0] for key in connectivity):
                continue
            if "INTEGRATION_POINT" not in ci(getattr(value, "position", "")):
                continue
            candidate = getattr(value, "mises", None)
            if candidate is not None and finite(candidate):
                mises.append(float(candidate))
                stress_elements.add((ci(value.instance.name), int(value.elementLabel)))
        if not mises:
            return fail("ODB has no finite Mises stress invariant")
        if stress_elements != set(connectivity):
            missing = sorted(set(connectivity) - stress_elements)
            extra = sorted(stress_elements - set(connectivity))
            return fail("ODB Mises stress does not cover every shaft element: expected=%d observed=%d missing=%r extra=%r" % (
                len(set(connectivity)), len(stress_elements), missing[:12], extra[:12]
            ))
        max_mises = max(mises)
        if not (2.5 <= max_mises <= 8.0):
            return fail("native ODB maximum Mises is outside the task range: %r (count=%d)" % (max_mises, len(mises)))
        reaction_force = [0.0, 0.0, 0.0]
        reaction_moment_y = 0.0
        fixed_hits = set()
        for value in frame.fieldOutputs["RF"].values:
            instance_name = ci(getattr(getattr(value, "instance", None), "name", ""))
            key = (instance_name, int(value.nodeLabel))
            if key not in fixed_labels:
                continue
            data = numbers(value.data)
            if len(data) < 3:
                return fail("fixed-face RF vector is incomplete")
            fixed_hits.add(key)
            xyz = coords[key]
            for i in range(3):
                reaction_force[i] += float(data[i])
            reaction_moment_y += xyz[2] * float(data[0]) - xyz[0] * float(data[2])
        if fixed_hits != fixed_labels:
            return fail("ODB RF does not cover every fixed-end node")
        if not close(reaction_moment_y, -920.0, rel=2.0e-3, absolute=1.0):
            return fail("fixed-end reaction moment does not balance +920 N*mm")
        if math.sqrt(builtins.sum(value * value for value in reaction_force)) > 2.0:
            return fail("fixed-end force resultant is inconsistent with pure torque")
        all_frame_fields = []
        for frame_index, candidate_frame in enumerate(step.frames):
            candidate_signatures = {}
            for name in required:
                if name not in candidate_frame.fieldOutputs.keys():
                    continue
                candidate_signatures[name] = field_signature(candidate_frame.fieldOutputs[name])
                if candidate_signatures[name] is None:
                    return fail("ODB contains non-finite required field history")
            all_frame_fields.append((
                int(getattr(candidate_frame, "incrementNumber", frame_index)),
                float(getattr(candidate_frame, "frameValue", float("nan"))),
                candidate_signatures,
            ))
        return {
            "metrics": {"twist_angle": twist, "max_stress": max_mises},
            "signature": {
                "mesh": (coords, connectivity),
                "fields": signatures,
                "all_frame_fields": tuple(all_frame_fields),
                "frames": tuple(
                    (
                        int(getattr(candidate, "incrementNumber", index)),
                        float(getattr(candidate, "frameValue", float("nan"))),
                    )
                    for index, candidate in enumerate(step.frames)
                ),
            },
            "reaction_moment_y": reaction_moment_y,
        }
    finally:
        odb.close()


def signatures_match(left, right):
    if (
        left["mesh"] != right["mesh"]
        or left["frames"] != right["frames"]
        or set(left["fields"]) != set(right["fields"])
        or len(left.get("all_frame_fields", ())) != len(right.get("all_frame_fields", ()))
    ):
        return False
    for name in left["fields"]:
        a = left["fields"][name]
        b = right["fields"][name]
        if len(a) != len(b):
            return False
        for row_a, row_b in zip(a, b):
            if row_a[:-1] != row_b[:-1] or len(row_a[-1]) != len(row_b[-1]):
                return False
            if any(not close(x, y, rel=2.0e-5, absolute=2.0e-8) for x, y in zip(row_a[-1], row_b[-1])):
                return False
    for frame_a, frame_b in zip(left["all_frame_fields"], right["all_frame_fields"]):
        if frame_a[:2] != frame_b[:2] or set(frame_a[2]) != set(frame_b[2]):
            return False
        for name in frame_a[2]:
            a = frame_a[2][name]
            b = frame_b[2][name]
            if len(a) != len(b):
                return False
            for row_a, row_b in zip(a, b):
                if row_a[:-1] != row_b[:-1] or len(row_a[-1]) != len(row_b[-1]):
                    return False
                if any(not close(x, y, rel=2.0e-5, absolute=2.0e-8) for x, y in zip(row_a[-1], row_b[-1])):
                    return False
    return True


def main():
    ok = False
    deck_audit = None
    cad_geometry = None
    generated_hash = None
    frozen_hash = None
    keyword_block_edited = None
    try:
        openMdb(pathName=CAE_PATH)
        if JOB_NAME not in mdb.jobs.keys():
            raise RuntimeError("CAE does not retain Job-Torsion-B")
        job_model = str(getattr(mdb.jobs[JOB_NAME], "model", ""))
        matching_models = [name for name in mdb.models.keys() if ci(name) == ci(job_model)]
        if len(matching_models) != 1:
            raise RuntimeError("Job-Torsion-B is not bound to exactly one saved model")
        model = mdb.models[matching_models[0]]
        keyword_block_edited = bool(getattr(model.keywordBlock, "edited", False))
        if keyword_block_edited:
            raise RuntimeError("CAE keywordBlock contains manual edits")
        if len(model.parts.keys()) != 1 or len(model.rootAssembly.instances.keys()) != 1:
            raise RuntimeError("CAE must contain one shaft part and one instance")
        part = model.parts[model.parts.keys()[0]]
        instance = model.rootAssembly.instances[model.rootAssembly.instances.keys()[0]]
        coords = instance_coords(model)
        cad_geometry = audit_cad_geometry(part)
        if not cad_geometry:
            raise RuntimeError("CAE native CAD geometry audit failed")
        mesh_info = audit_mesh(part, coords)
        if not mesh_info or not material_and_section(model, part):
            raise RuntimeError("CAE model audit failed")
        process = audit_process(model, part, instance, mesh_info)
        if not process:
            raise RuntimeError("CAE process audit failed")
        expected_part_elements = dict(
            (int(element.label),
             (ci(element.type), tuple(int(node.label) for node in element_nodes(part, element))))
            for element in part.elements
        )
        odb_mesh_expected = (
            dict(((ci(instance.name), label), xyz) for label, xyz in mesh_info["part_coords"].items()),
            dict(
                ((ci(instance.name), label), value)
                for label, value in expected_part_elements.items()
            ),
        )
        fixed_labels = set((ci(instance.name), label) for label in mesh_info["fixed_part_nodes"])
        submitted = odb_result(ODB_PATH, odb_mesh_expected, fixed_labels, instance.name)
        if not submitted:
            raise RuntimeError("submitted ODB audit failed")
        for name in ("twist_angle", "max_stress"):
            tolerance = 2.0e-7 if name == "twist_angle" else 2.0e-5
            if not close(submitted["metrics"][name], METRICS[name], rel=2.0e-5, absolute=tolerance):
                raise RuntimeError("metrics.json %s does not match native ODB" % name)

        os.chdir(AUDIT_ROOT)
        mdb.jobs[JOB_NAME].writeInput(consistencyChecking=ON)
        generated_path = os.path.join(AUDIT_ROOT, JOB_NAME + ".inp")
        if not os.path.isfile(generated_path) or os.path.getsize(generated_path) <= 0:
            raise RuntimeError("writeInput(consistencyChecking=ON) did not create the generated INP")
        if bool(getattr(model.keywordBlock, "edited", False)):
            raise RuntimeError("CAE keywordBlock became edited while generating the INP")
        deck_audit = audit_abaqus_input_deck(
            generated_path,
            ALLOWED_TYPES,
            mesh_info["part_coords"],
            expected_part_elements,
            mesh_info["fixed_part_nodes"],
            mesh_info["free_part_nodes"],
            instance.name,
        )
        generated_hash = file_sha256(generated_path)
        frozen_path = os.path.join(SOLVE_ROOT, "frozen.inp")
        shutil.copyfile(generated_path, frozen_path)
        frozen_hash = file_sha256(frozen_path)
        if generated_hash != frozen_hash:
            raise RuntimeError("frozen INP is not byte-identical to the audited generated INP")
        solve_entries = sorted(os.listdir(SOLVE_ROOT), key=lambda value: value.lower())
        if solve_entries != ["frozen.inp"] or os.path.islink(frozen_path) or not os.path.isfile(frozen_path):
            raise RuntimeError("solve root is not the exact frozen-INP domain before submission")
        if os.listdir(POST_ROOT):
            raise RuntimeError("post root is not empty before the fresh solve")

        os.chdir(SOLVE_ROOT)
        solve_started = time.time()
        recheck_job = mdb.JobFromInputFile(name=RECHECK_JOB, inputFileName=frozen_path)
        recheck_job.submit(consistencyChecking=ON)
        recheck_job.waitForCompletion()
        solved_path = os.path.join(SOLVE_ROOT, RECHECK_JOB + ".odb")
        if not os.path.isfile(solved_path) or os.path.getsize(solved_path) <= 0:
            raise RuntimeError("isolated JobFromInputFile re-solve did not create an ODB")
        if os.path.getmtime(solved_path) < solve_started - 2.0:
            raise RuntimeError("isolated JobFromInputFile ODB is not fresh")
        if file_sha256(generated_path) != generated_hash or file_sha256(frozen_path) != frozen_hash:
            raise RuntimeError("audited or frozen INP changed during isolated re-solve")
        rechecked_path = os.path.join(POST_ROOT, "recomputed.odb")
        shutil.copyfile(solved_path, rechecked_path)
        if file_sha256(rechecked_path) != file_sha256(solved_path):
            raise RuntimeError("post-processing ODB is not byte-identical to the fresh solve ODB")
        os.chdir(POST_ROOT)
        rechecked = odb_result(rechecked_path, odb_mesh_expected, fixed_labels, instance.name)
        if not rechecked or not signatures_match(submitted["signature"], rechecked["signature"]):
            raise RuntimeError("submitted ODB fields do not match isolated frozen-INP re-solve")
        for name in ("twist_angle", "max_stress"):
            tolerance = 2.0e-7 if name == "twist_angle" else 5.0e-4
            if not close(submitted["metrics"][name], rechecked["metrics"][name], rel=5.0e-4, absolute=tolerance):
                raise RuntimeError("submitted ODB %s does not match isolated CAE re-solve" % name)
        ok = True
    except Exception:
        DETAILS.append(traceback.format_exc())
        ok = False
    try:
        with open(RESULT_PATH, "w") as stream:
            json.dump({
                "passed": bool(ok),
                "details": DETAILS,
                "deck_audit": deck_audit,
                "cad_geometry": cad_geometry,
                "generated_inp_sha256": generated_hash,
                "frozen_inp_sha256": frozen_hash,
                "keyword_block_edited": keyword_block_edited,
            }, stream, indent=2, sort_keys=True)
    except Exception:
        pass
    print("True" if ok else "False")


if __name__ == "__main__":
    main()
'''


def run_abaqus_checker(cae_path, odb_path, submitted_metrics):
    token = uuid.uuid4().hex
    control_root = Path(tempfile.mkdtemp(prefix="eval_cli_task10_abaqus_control_%s_" % token))
    audit_root = Path(tempfile.mkdtemp(prefix="eval_cli_task10_abaqus_audit_%s_" % token))
    submitted_root = Path(tempfile.mkdtemp(prefix="eval_cli_task10_abaqus_submitted_%s_" % token))
    solve_root = Path(tempfile.mkdtemp(prefix="eval_cli_task10_abaqus_solve_%s_" % token))
    post_root = Path(tempfile.mkdtemp(prefix="eval_cli_task10_abaqus_post_%s_" % token))
    staged_cae = audit_root / "source.cae"
    staged_odb = submitted_root / "submitted.odb"
    checker = control_root / "checker.py"
    result = control_root / "result.json"
    recheck_job = "eval_task10_abq_" + token[:16]
    original_hashes = (sha256(cae_path), sha256(odb_path))
    baseline = []
    launcher = None
    owned_history = {}
    tracker_stop = None
    tracker = None
    semantic_ok = False
    process_ok = False
    temp_ok = False
    try:
        shutil.copy2(str(cae_path), str(staged_cae))
        shutil.copy2(str(odb_path), str(staged_odb))
        if (
            not exact_regular_files(control_root, ())
            or not exact_regular_files(audit_root, (staged_cae.name,))
            or not exact_regular_files(submitted_root, (staged_odb.name,))
            or not exact_regular_files(solve_root, ())
            or not exact_regular_files(post_root, ())
        ):
            raise RuntimeError("Abaqus isolation roots are not initially exact regular-file domains")
        baseline = windows_processes(ABAQUS_PROCESS_PATTERN)
        source = ABAQUS_CHECKER.replace("__DECK_HELPERS__", ABAQUS_DECK_HELPERS)
        source = source.replace("__CAE_PATH__", repr(str(staged_cae)))
        source = source.replace("__ODB_PATH__", repr(str(staged_odb)))
        source = source.replace("__RESULT_PATH__", repr(str(result)))
        source = source.replace("__RECHECK_JOB__", repr(recheck_job))
        source = source.replace("__AUDIT_ROOT__", repr(str(audit_root)))
        source = source.replace("__SOLVE_ROOT__", repr(str(solve_root)))
        source = source.replace("__POST_ROOT__", repr(str(post_root)))
        source = source.replace("__METRICS__", repr(submitted_metrics))
        checker.write_text(source, encoding="utf-8")
        if not exact_regular_files(control_root, (checker.name,)):
            raise RuntimeError("Abaqus control root was altered before launch")
        launcher = subprocess.Popen(
            [ABAQUS_COMMAND, "cae", "noGUI=" + str(checker)],
            cwd=str(control_root),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=False,
        )
        tracker_stop = threading.Event()
        tracker = threading.Thread(
            target=track_owned_processes,
            args=(
                tracker_stop,
                owned_history,
                baseline,
                ABAQUS_PROCESS_PATTERN,
                (
                    token,
                    str(control_root),
                    str(audit_root),
                    str(submitted_root),
                    str(solve_root),
                    str(post_root),
                    recheck_job,
                ),
                (launcher.pid,),
            ),
        )
        tracker.daemon = True
        tracker.start()
        try:
            stdout, stderr = launcher.communicate(timeout=1200)
        except subprocess.TimeoutExpired:
            if launcher.poll() is None:
                terminate_owned_process(launcher.pid)
            stdout, stderr = launcher.communicate(timeout=30)
            log("Abaqus checker timed out")
            return False
        log("Abaqus checker returncode=%s" % launcher.returncode)
        if stdout:
            log("Abaqus stdout tail=" + stdout[-1000:])
        if stderr:
            log("Abaqus stderr tail=" + stderr[-1000:])
        if not is_nonempty(result):
            log("Abaqus checker did not create its result JSON")
            return False
        payload = json.loads(result.read_text(encoding="utf-8"))
        for message in payload.get("details", []):
            log("Abaqus: " + str(message))
        semantic_ok = launcher.returncode == 0 and payload.get("passed") is True
        expected_solve = (
            "frozen.inp",
            recheck_job + ".com",
            recheck_job + ".dat",
            recheck_job + ".log",
            recheck_job + ".msg",
            recheck_job + ".odb",
            recheck_job + ".prt",
            recheck_job + ".sta",
        )
        root_contracts = (
            (control_root, ("abaqus_acis.log", checker.name, result.name)),
            (audit_root, (staged_cae.name, JOB_NAME + ".inp")),
            (submitted_root, (staged_odb.name,)),
            (solve_root, expected_solve),
            (post_root, ("recomputed.odb",)),
        )
        for root, expected in root_contracts:
            if not exact_regular_files(root, expected):
                log("Abaqus root inventory mismatch at %s: %r" % (root, regular_directory_names(root)))
                semantic_ok = False
        generated = audit_root / (JOB_NAME + ".inp")
        frozen = solve_root / "frozen.inp"
        if (
            not is_nonempty(generated)
            or not is_nonempty(frozen)
            or sha256(generated) != sha256(frozen)
            or payload.get("generated_inp_sha256") != sha256(generated)
            or payload.get("frozen_inp_sha256") != sha256(frozen)
            or not isinstance(payload.get("deck_audit"), dict)
            or not isinstance(payload.get("cad_geometry"), dict)
        ):
            log("Abaqus audited/frozen input-deck evidence is incomplete")
            semantic_ok = False
        if sha256(staged_odb) != original_hashes[1]:
            log("staged submitted Abaqus ODB changed during evaluation")
            semantic_ok = False
        if (sha256(cae_path), sha256(odb_path)) != original_hashes:
            log("submitted Abaqus artifacts changed during evaluation")
            semantic_ok = False
    except Exception as exc:
        log("Abaqus evaluator failed: %s" % exc)
        semantic_ok = False
    finally:
        if tracker_stop is not None:
            tracker_stop.set()
        if tracker is not None:
            tracker.join(timeout=6.0)
        if launcher is not None and launcher.poll() is None:
            terminate_owned_process(launcher.pid)
        try:
            process_ok = restore_process_baseline(
                baseline,
                ABAQUS_PROCESS_PATTERN,
                (
                    token,
                    str(control_root),
                    str(audit_root),
                    str(submitted_root),
                    str(solve_root),
                    str(post_root),
                    recheck_job,
                ),
                owned_history.values(),
            )
        except Exception as exc:
            log("Abaqus process cleanup failed: %s" % exc)
        if not process_ok:
            log("Abaqus solver process baseline was not restored exactly")
        temp_results = [
            remove_tree(path)
            for path in (control_root, audit_root, submitted_root, solve_root, post_root)
        ]
        temp_ok = all(temp_results)
        if not temp_ok:
            log("Abaqus temporary directory cleanup was incomplete")
    return semantic_ok and process_ok and temp_ok


ANSYS_PROCESS_PATTERN = (
    r"^(ANSYS(261)?|ansyscl|mpiexec|hydra_service|hydra_bstrap_proxy|hydra_pmi_proxy)\.exe$"
)
ANSYS_NUMBER = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[EeDd][-+]?\d+)?"
ANSYS_TEMP_ROOT = Path(os.environ.get("LOCALAPPDATA", r"C:\Users\user\AppData\Local")) / "Temp" / ".ansys"


def ansys_number(value):
    return float(str(value).replace("D", "E").replace("d", "e"))


def ansys_temp_inventory():
    if not ANSYS_TEMP_ROOT.exists():
        return {}
    if not ANSYS_TEMP_ROOT.is_dir():
        raise RuntimeError("Windows .ansys Temp entry is not a directory")
    rows = {}
    for path in sorted(ANSYS_TEMP_ROOT.rglob("*"), key=lambda value: str(value).lower()):
        relative = str(path.relative_to(ANSYS_TEMP_ROOT)).replace("\\", "/")
        rows[relative.lower()] = (relative, path.is_file(), path.is_dir())
    return rows


def ansys_temp_entry_is_owned(relative, markers, owned_pids):
    lower = str(relative).lower()
    if any(str(marker).lower() in lower for marker in markers if marker):
        return True
    return any(
        re.search(r"(?<!\d)%d(?!\d)" % int(pid), lower)
        for pid in owned_pids
        if int(pid) > 0
    )


def restore_ansys_temp_inventory(before, markers=(), owned_pids=()):
    if before is None:
        log("ANSYS .ansys temporary cleanup refused without a captured baseline")
        return False
    try:
        current = ansys_temp_inventory()
        new_keys = sorted(set(current) - set(before), key=lambda value: value.count("/"), reverse=True)
        owned_keys = {
            key
            for key in new_keys
            if ansys_temp_entry_is_owned(current[key][0], markers, owned_pids)
        }
        for key in new_keys:
            relative, is_file, is_dir = current[key]
            prefix = key.rstrip("/") + "/"
            descendants = [candidate for candidate in new_keys if candidate.startswith(prefix)]
            if is_dir and descendants and all(candidate in owned_keys for candidate in descendants):
                owned_keys.add(key)
        unknown = [current[key][0] for key in new_keys if key not in owned_keys]
        for key in new_keys:
            if key not in owned_keys:
                continue
            relative, is_file, is_dir = current[key]
            path = ANSYS_TEMP_ROOT.joinpath(*relative.split("/"))
            if is_file:
                path.unlink()
            elif is_dir:
                path.rmdir()
        after = ansys_temp_inventory()
        if unknown:
            log("ANSYS .ansys contains unowned new entries; refused deletion: %r" % unknown[:20])
        return (
            not unknown
            and set(after) == set(before)
            and all(after[key][1:] == before[key][1:] for key in before)
        )
    except Exception as exc:
        log("ANSYS .ansys temporary cleanup failed: %s" % exc)
        return False


def required_run(mapdl, command):
    output = mapdl.run(command)
    text = "" if output is None else str(output)
    upper = text.upper()
    if "*** ERROR ***" in upper or "UNKNOWN COMMAND" in upper or "IS NOT A RECOGNIZED" in upper:
        raise RuntimeError("MAPDL command failed: %s\n%s" % (command, text[-1000:]))
    return text


def required_input_strings(mapdl, commands):
    output = mapdl.input_strings(commands)
    text = "" if output is None else str(output)
    upper = text.upper()
    if "*** ERROR ***" in upper or "UNKNOWN COMMAND" in upper or "IS NOT A RECOGNIZED" in upper:
        raise RuntimeError("MAPDL input block failed: %s" % text[-3000:])
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
        raise RuntimeError("MAPDL *GET failed: %r" % (args,))
    return value


def write_ansys_resolve_input(path, staged_model, jobname, nonce, solid_type_ids, nonlinear=False):
    model_stem = str(staged_model.with_suffix(""))
    solid_type_ids = tuple(sorted(set(int(value) for value in solid_type_ids)))
    if (
        not re.fullmatch(r"[0-9a-f]{32}", nonce)
        or not solid_type_ids
        or any(value <= 0 for value in solid_type_ids)
        or any(character in model_stem + jobname for character in ("'", "\n", "\r", ","))
    ):
        raise RuntimeError("unsafe ANSYS batch path or job name")
    solid_selection = tuple(
        "ESEL,%s,TYPE,,%d" % ("S" if index == 0 else "A", type_id)
        for index, type_id in enumerate(solid_type_ids)
    )
    path.write_text(
        "\n".join((
            "/BATCH",
            "FINISH",
            "/PSEARCH,OFF",
            "RESUME,'%s','db'" % model_stem,
            "/PSEARCH,OFF",
            *("*ABBR,%s," % command for command in ANSYS_AUDIT_ABBREVIATIONS),
            "USRCAL,NONE",
            "*DEL,ALL,_PRM",
            "/FILNAME,%s,1" % jobname,
            "/PREP7",
            "ALLSEL,ALL",
            *solid_selection,
            "CM,TASK10_SOLID,ELEM",
            "ALLSEL,ALL",
            "SHPP,ON",
            "FINISH",
            "/SOLU",
            "ANTYPE,STATIC,NEW",
            "ALLSEL,ALL",
            "NLGEOM,%s" % ("ON" if nonlinear else "OFF"),
            "NROPT,FULL",
            "AUTOTS,OFF",
            "TIME,1",
            "NSUBST,1,1,1",
            "NEQIT,15",
            "CNVTOL,-1",
            "NCNV,1",
            "EQSLV,SPARSE",
            "KUSE,-1",
            "OUTRES,ERASE",
            "OUTRES,NSOL,ALL",
            "OUTRES,RSOL,ALL",
            "OUTRES,STRS,ALL",
            "OUTRES,NAR,ALL,TASK10_SOLID",
            "/COM,TASK10_RESOLVE_BEGIN_%s" % nonce,
            "SOLVE",
            "*GET,T10CNVG,ACTIVE,0,SOLU,CNVG",
            "*GET,T10NCMLS,ACTIVE,0,SOLU,NCMLS",
            "*GET,T10NCMSS,ACTIVE,0,SOLU,NCMSS",
            "*GET,T10NCMIT,ACTIVE,0,SOLU,NCMIT",
            "/COM,TASK10_RESOLVE_SOLVED_%s" % nonce,
            "FINISH",
            "/POST1",
            "FILE,%s,rst" % jobname,
            "SET,LAST",
            "*GET,T10ANTY,ACTIVE,0,ANTY",
            "*GET,T10LSTP,ACTIVE,0,SET,LSTP",
            "*GET,T10SBST,ACTIVE,0,SET,SBSTEP",
            "*GET,T10TIME,ACTIVE,0,SET,TIME",
            "*GET,T10NSET,ACTIVE,0,SET,NSET",
            "*CFOPEN,task10_status,tmp",
            "*VWRITE",
            "('%s')" % ("TASK10_STATUS_BEGIN_" + nonce),
            "*VWRITE,T10CNVG,T10ANTY,T10LSTP,T10SBST,T10TIME,T10NSET,T10NCMLS,T10NCMSS,T10NCMIT",
            "(E24.16,',',E24.16,',',E24.16,',',E24.16,',',E24.16,',',E24.16,',',E24.16,',',E24.16,',',E24.16)",
            "*VWRITE",
            "('%s')" % ("TASK10_STATUS_END_" + nonce),
            "*CFCLOS",
            "FINISH",
            "/RENAME,task10_status,tmp,,task10_status,done",
            "/COM,TASK10_RESOLVE_END_%s" % nonce,
            "/EXIT,NOSAVE",
            "",
        )),
        encoding="ascii",
    )


def run_ansys_batch_resolve(
    staged_model,
    solve_root,
    jobname,
    require_convergence,
    baseline,
    owned_history,
    solid_type_ids,
    timeout=600,
):
    nonce = uuid.uuid4().hex
    input_path = solve_root / "task10_resolve.inp"
    output_path = solve_root / "task10_resolve.out"
    status_path = solve_root / "task10_status.done"
    result_path = solve_root / (jobname + ".rst")
    write_ansys_resolve_input(
        input_path,
        staged_model,
        jobname,
        nonce,
        solid_type_ids,
        nonlinear=require_convergence,
    )
    if not exact_regular_files(solve_root, (staged_model.name, input_path.name)):
        raise RuntimeError("ANSYS solve directory is not an isolated DB-plus-input root")
    started_ns = time.time_ns()
    process = subprocess.Popen(
        [
            ANSYS_EXEC,
            "-b",
            "-np",
            "1",
            "-s",
            "noread",
            "-j",
            jobname,
            "-dir",
            str(solve_root),
            "-i",
            str(input_path),
            "-o",
            str(output_path),
        ],
        cwd=str(solve_root),
        env=sanitized_ansys_environment(),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        shell=False,
    )
    update_owned_process_history(
        owned_history,
        baseline,
        windows_processes(ANSYS_PROCESS_PATTERN, timeout=5.0),
        (jobname, str(solve_root), nonce),
        seed_pids=(process.pid,),
    )
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        terminate_owned_process(process.pid)
        try:
            process.communicate(timeout=30)
        except Exception:
            pass
        raise RuntimeError("ANSYS isolated batch re-solve timed out")
    if stdout:
        log("ANSYS batch stdout tail=" + stdout[-1000:])
    if stderr:
        log("ANSYS batch stderr tail=" + stderr[-1000:])
    output = output_path.read_text(encoding="utf-8", errors="replace") if is_nonempty(output_path) else ""
    status_identity = stable_fresh_file(status_path, started_ns)
    result_identity = stable_fresh_file(result_path, started_ns)
    status_text = status_path.read_text(encoding="ascii", errors="strict") if status_identity is not None else ""
    status = parse_ansys_batch_status(status_text, nonce)
    if process.returncode != 0:
        raise RuntimeError(
            "ANSYS isolated batch re-solve returned %s; status=%r; output_tail=%r"
            % (process.returncode, status_text[-1000:], output[-5000:])
        )
    completions = parse_ansys_batch_completions(output)
    output_contract = ansys_batch_output_contract(
        output, nonce, jobname, input_path, solve_root
    )
    if not all(output_contract.values()) or completions is None:
        raise RuntimeError(
            "ANSYS isolated batch output does not prove a completed error-free solve; "
            "contract=%r; status=%r; output_tail=%r"
            % (output_contract, status_text[-1000:], output[-5000:])
        )
    if status is None:
        raise RuntimeError(
            "ANSYS isolated batch status is missing or malformed: %r" % status_text[-1000:]
        )
    if result_identity is None:
        raise RuntimeError("ANSYS isolated batch did not produce a fresh stable RST")
    if not ansys_batch_convergence_is_acceptable(status, require_convergence):
        raise RuntimeError("ANSYS isolated batch convergence flag is invalid: %r" % status)
    if status["analysis_type"] != 0 or status["load_step"] != 1:
        raise RuntimeError("ANSYS isolated batch did not finish the required static load step")
    if status["substep"] <= 0 or status["set"] <= 0 or status["time"] <= 0.0:
        raise RuntimeError("ANSYS isolated batch final result metadata is invalid")
    final_names = regular_directory_names(solve_root)
    if not ansys_batch_inventory_is_valid(final_names, jobname, staged_model.name):
        raise RuntimeError(
            "ANSYS isolated batch root inventory is outside the learned clean v261 whitelist: "
            "actual=%r" % (final_names,)
        )
    final_completion = completions[-1]
    if (
        final_completion["load_step"] != status["load_step"]
        or final_completion["substep"] != status["substep"]
        or final_completion["cumulative_iterations"] != status["cumulative_iterations"]
        or status["cumulative_load_steps"] != status["load_step"]
        or status["number_substeps"] != status["substep"]
    ):
        raise RuntimeError(
            "ANSYS isolated batch completion/status records disagree: completion=%r status=%r"
            % (final_completion, status)
        )
    return status, result_path, result_identity


_NUMBERED_LISTING_ROW = re.compile(r"^\s*\d+(?:\s|$)")
_CDB_COMMAND = re.compile(r"^\s*([*/A-Z][A-Z0-9_*/]*)\s*(?:,|$)", re.IGNORECASE)
_STATUS_TITLE = re.compile(
    r"^\s*S\s+O\s+L\s+U\s+T\s+I\s+O\s+N\s+O\s+P\s+T\s+I\s+O\s+N\s+S\s*$",
    re.IGNORECASE,
)
_NLGEOM_STATUS = re.compile(
    r"^\s*NONLINEAR\s+GEOMETRIC\s+EFFECTS(?:\s*\.)+\s*(ON|OFF)\s*$",
    re.IGNORECASE,
)


class CdbCommand:
    __slots__ = ("line_number", "name", "text")

    def __init__(self, line_number, name, text):
        self.line_number = int(line_number)
        self.name = str(name)
        self.text = str(text)


def normalized_listing_line(value):
    return re.sub(r"\s+", " ", str(value).strip()).upper().rstrip(". :;")


def listing_confirms_empty(text, markers):
    if not isinstance(text, str) or not text.strip() or "\x00" in text:
        return False
    if isinstance(markers, str):
        markers = (markers,)
    try:
        expected = set(
            normalized_listing_line(marker)
            for marker in markers
            if isinstance(marker, str) and marker.strip()
        )
    except TypeError:
        return False
    if not expected:
        return False
    lines = text.splitlines()
    observed = [normalized_listing_line(line) for line in lines]
    return (
        sum(line in expected for line in observed) == 1
        and not any(_NUMBERED_LISTING_ROW.match(line) for line in lines)
    )


def scan_cdb_commands(cdb_text):
    if not isinstance(cdb_text, str) or not cdb_text.strip() or "\x00" in cdb_text:
        return None
    commands = []
    for line_number, raw in enumerate(cdb_text.splitlines(), 1):
        line = raw.split("!", 1)[0].strip()
        if not line:
            continue
        match = _CDB_COMMAND.match(line)
        if match is None:
            continue
        name = match.group(1).upper()
        if name in ("/COM", "/COMMENT") or name.startswith("C***"):
            continue
        commands.append(CdbCommand(line_number, name, line))
    return tuple(commands) if commands else None


def cdb_has_any_command(cdb_text, names):
    commands = scan_cdb_commands(cdb_text)
    if commands is None:
        return None
    expected = set(str(name).upper() for name in names)
    return any(command.name in expected for command in commands)


def cdb_task10_result_controls(cdb_text):
    commands = scan_cdb_commands(cdb_text)
    if commands is None:
        return None
    required = {"NSOL", "RSOL", "STRS", "NAR"}
    controls = {}
    for command in commands:
        if command.name != "OUTRES":
            continue
        fields = [field.strip() for field in command.text.split(",")]
        if len(fields) < 3:
            return None
        item = fields[1].upper()
        if item not in required:
            continue
        frequency = fields[2].upper()
        component = fields[3].upper() if len(fields) > 3 else ""
        frequency_ok = frequency in ("ALL", "LAST")
        if not frequency_ok:
            try:
                frequency_ok = close_enough(
                    ansys_number(frequency), 1.0, rel=0.0, abs_tol=0.0
                )
            except Exception:
                frequency_ok = False
        if (
            item in controls
            or not frequency_ok
            or (component and re.fullmatch(r"[A-Z][A-Z0-9_]{0,31}", component) is None)
        ):
            return None
        controls[item] = {"frequency": frequency, "component": component}
    return controls if set(controls) == required else None


def cdb_material_is_constant_steel(cdb_text, material_id):
    commands = scan_cdb_commands(cdb_text)
    if commands is None:
        return False
    temperatures = {}
    properties = {}
    for command in commands:
        fields = [field.strip() for field in command.text.split(",")]
        if command.name == "MPTEMP":
            try:
                if fields[1].upper() != "UNBL":
                    return False
                start = int(float(fields[2]))
                count = int(float(fields[3]))
                values = [ansys_number(token) for token in fields[4:] if token]
            except Exception:
                return False
            if start < 1 or count < 1 or len(values) != count:
                return False
            for offset, value in enumerate(values):
                temperatures[start + offset] = value
            continue
        if command.name == "MPDATA":
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
            if label not in ("EX", "NUXY", "PRXY", "DENS") or count < 1 or len(values) != count:
                return False
            for offset, value in enumerate(values):
                slot = start + offset
                if slot not in temperatures or abs(temperatures[slot]) > 1.0e-12:
                    return False
                properties.setdefault(label, []).append(value)
            continue
        if command.name == "TB":
            try:
                row_material = int(float(fields[2]))
            except Exception:
                return False
            if row_material == int(material_id):
                return False
        if command.name == "MP":
            try:
                row_material = int(float(fields[2]))
            except Exception:
                return False
            if row_material == int(material_id):
                return False
    elastic = set(properties) - {"DENS"}
    if elastic not in ({"EX", "NUXY"}, {"EX", "PRXY"}, {"EX", "NUXY", "PRXY"}):
        return False
    if any(not close_enough(value, 210000.0, rel=1.0e-6) for value in properties["EX"]):
        return False
    for label in elastic - {"EX"}:
        if any(not close_enough(value, 0.3, rel=1.0e-6) for value in properties[label]):
            return False
    if "DENS" in properties and (
        any(value <= 0.0 for value in properties["DENS"])
        or any(not close_enough(value, properties["DENS"][0], rel=1.0e-12, abs_tol=1.0e-20) for value in properties["DENS"][1:])
    ):
        return False
    return True


def cdb_has_forbidden_task10_state(cdb_text):
    commands = scan_cdb_commands(cdb_text)
    if commands is None:
        return None
    forbidden = {
        "IC", "INISTATE", "INRES", "LDREAD", "LREAD", "UPGEOM",
        "BF", "BFA", "BFE", "BFEBLOCK", "BFBLOCK", "BFV",
        "SF", "SFA", "SFE", "SFEBLOCK", "SFBLOCK", "SFL",
        "SECCONTROL", "SECBLOCK", "SECDATA", "SECFUNCTION", "SECJOINT",
        "SECLOCK", "SECNUM", "SECOFFSET", "SECREAD", "SECTYPE", "SECWRITE", "SSBT",
        "TUNIF", "AIRL", "/UCMD", "/UPF",
    }
    for command in commands:
        fields = [field.strip() for field in command.text.split(",")]
        if command.name in forbidden:
            return True
        if command.name == "TREF":
            values = [ansys_number(token) for token in fields[1:] if token]
            if not values or any(abs(value) > 1.0e-12 for value in values):
                return True
        elif command.name == "BFUNIF":
            values = [token for token in fields[2:] if token]
            if (
                len(fields) < 3
                or fields[1].upper() != "TEMP"
                or not values
                or any(token.upper() != "_TINY" for token in values)
            ):
                return True
        elif command.name in ("ACEL", "OMEGA", "DOMEGA", "CGOMEGA", "CGOMGA", "DCGOMG"):
            try:
                values = [ansys_number(token) for token in fields[1:] if token]
            except Exception:
                return True
            if not values or any(abs(value) > 1.0e-12 for value in values):
                return True
        elif command.name in ("CMACEL", "CMOMEGA", "CMDOMEGA"):
            try:
                values = [ansys_number(token) for token in fields[2:] if token]
            except Exception:
                return True
            if len(fields) < 3 or not fields[1] or not values or any(abs(value) > 1.0e-12 for value in values):
                return True
        elif command.name == "IRLF":
            try:
                values = [ansys_number(token) for token in fields[1:] if token]
            except Exception:
                return True
            if not values or any(abs(value) > 1.0e-12 for value in values):
                return True
        elif command.name in ("ALPHAD", "BETAD", "DMPRAT", "DMPSTR"):
            try:
                values = [ansys_number(token) for token in fields[1:] if token]
            except Exception:
                return True
            if not values or any(abs(value) > 1.0e-12 for value in values):
                return True
        elif command.name == "NEQIT":
            if any(token.upper() == "FORCE" for token in fields[2:] if token):
                return True
        elif command.name == "KUSE":
            try:
                values = [ansys_number(token) for token in fields[1:] if token]
            except Exception:
                return True
            if len(values) != 1 or values[0] not in (0.0, -1.0):
                return True
    return False


def parse_constraint_listing(text):
    upper = (text or "").upper()
    if "LIST CONSTRAINTS FOR SELECTED NODES" not in upper or "NODE" not in upper:
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
        rows.append((
            int(match.group(1)),
            match.group(2).upper(),
            ansys_number(match.group(3)),
            ansys_number(match.group(4)),
        ))
    return rows


def parse_force_listing(text):
    upper = (text or "").upper()
    if "LIST NODAL FORCES" not in upper and "NODAL FORCE" not in upper:
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
        rows.append((
            int(match.group(1)),
            match.group(2).upper(),
            ansys_number(match.group(3)),
            ansys_number(match.group(4)),
        ))
    return rows


def parse_result_sets(text):
    upper = (text or "").upper()
    if "INDEX OF DATA SETS ON RESULTS FILE" not in upper:
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
        rows.append({
            "set": int(match.group(1)),
            "time": ansys_number(match.group(2)),
            "load_step": int(match.group(3)),
            "substep": int(match.group(4)),
            "cumulative": int(match.group(5)),
        })
    return rows if rows else None


def valid_result_set_index(rows):
    if not isinstance(rows, list) or not rows:
        return False
    expected = list(range(1, len(rows) + 1))
    if [row.get("set") for row in rows] != expected:
        return False
    if any(
        row.get("load_step") != 1
        or not isinstance(row.get("substep"), int)
        or row["substep"] <= 0
        or not isinstance(row.get("cumulative"), int)
        or row["cumulative"] <= 0
        or not finite_number(row.get("time"))
        for row in rows
    ):
        return False
    if any(
        rows[index]["substep"] <= rows[index - 1]["substep"]
        or rows[index]["time"] <= rows[index - 1]["time"]
        or rows[index]["cumulative"] <= rows[index - 1]["cumulative"]
        for index in range(1, len(rows))
    ):
        return False
    return True


def result_set_indices_match(left, right):
    if not valid_result_set_index(left) or not valid_result_set_index(right):
        return False
    if len(left) != len(right):
        return False
    for first, second in zip(left, right):
        if any(first[key] != second[key] for key in ("set", "load_step", "substep", "cumulative")):
            return False
        if not close_enough(first["time"], second["time"], rel=1.0e-9, abs_tol=1.0e-12):
            return False
    return True


def parse_ansys_batch_status(text, nonce):
    lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
    if (
        not re.fullmatch(r"[0-9a-f]{32}", str(nonce))
        or len(lines) != 3
        or lines[0] != "TASK10_STATUS_BEGIN_" + nonce
        or lines[2] != "TASK10_STATUS_END_" + nonce
    ):
        return None
    fields = [field.strip() for field in lines[1].split(",")]
    if len(fields) != 9:
        return None
    try:
        values = [ansys_number(field) for field in fields]
    except Exception:
        return None
    if any(not math.isfinite(value) for value in values):
        return None
    (
        cnvg,
        analysis_type,
        load_step,
        substep,
        result_time,
        result_set,
        cumulative_load_steps,
        number_substeps,
        cumulative_iterations,
    ) = values
    integer_values = (
        analysis_type,
        load_step,
        substep,
        result_set,
        cumulative_load_steps,
        number_substeps,
        cumulative_iterations,
    )
    if any(abs(value - round(value)) > 1.0e-9 for value in integer_values):
        return None
    return {
        "converged": cnvg,
        "analysis_type": int(round(analysis_type)),
        "load_step": int(round(load_step)),
        "substep": int(round(substep)),
        "time": result_time,
        "set": int(round(result_set)),
        "cumulative_load_steps": int(round(cumulative_load_steps)),
        "number_substeps": int(round(number_substeps)),
        "cumulative_iterations": int(round(cumulative_iterations)),
    }


def ansys_batch_convergence_is_acceptable(status, require_convergence):
    if not isinstance(status, dict):
        return False
    value = status.get("converged")
    return value in (0.0, 1.0) and (not require_convergence or value == 1.0)


_ANSYS_BATCH_COMPLETION = re.compile(
    r"^\s*\*{3}\s+LOAD\s+STEP\s+(\d+)\s+SUBSTEP\s+(\d+)\s+"
    r"COMPLETED\.\s+CUM\s+ITER\s*=\s*(\d+)\s*$",
    re.IGNORECASE | re.MULTILINE,
)


def parse_ansys_batch_completions(text):
    if not isinstance(text, str) or not text.strip() or "\x00" in text:
        return None
    rows = tuple(
        {
            "load_step": int(match.group(1)),
            "substep": int(match.group(2)),
            "cumulative_iterations": int(match.group(3)),
        }
        for match in _ANSYS_BATCH_COMPLETION.finditer(text)
    )
    if not rows or any(
        row["load_step"] <= 0
        or row["substep"] <= 0
        or row["cumulative_iterations"] <= 0
        for row in rows
    ):
        return None
    if any(
        (row["load_step"], row["substep"]) <=
        (rows[index - 1]["load_step"], rows[index - 1]["substep"])
        or row["cumulative_iterations"] <= rows[index - 1]["cumulative_iterations"]
        for index, row in enumerate(rows[1:], 1)
    ):
        return None
    return rows


def unique_output_value(text, pattern):
    values = re.findall(pattern, text or "", flags=re.IGNORECASE | re.MULTILINE)
    return values[0].strip() if len(values) == 1 else None


def exact_output_line_occurs_once(text, value):
    pattern = r"^\s*%s\s*$" % re.escape(str(value))
    return len(re.findall(pattern, text or "", flags=re.IGNORECASE | re.MULTILINE)) == 1


def ansys_batch_output_is_complete(text, nonce, jobname, input_path, solve_root):
    return all(
        ansys_batch_output_contract(text, nonce, jobname, input_path, solve_root).values()
    )


def ansys_batch_output_contract(text, nonce, jobname, input_path, solve_root):
    upper = (text or "").upper()
    forbidden = (
        "ERROR TERMINATION",
        "*** ERROR ***",
        "RUN ABORTED",
        "SOLUTION NOT CONVERGED",
        "DID NOT CONVERGE",
        "FAILS TO CONVERGE",
        "UNCONVERGED",
        "UNKNOWN COMMAND",
        "UNKNOWN LABEL",
        "UNRECOGNIZED",
        "RESUME COMMAND IS IGNORED",
        "UNABLE TO OPEN FILE",
        "DOF LIMIT",
        "DIVERGED",
        "LINKED BY LICENSEE",
        "LINKED BY /UPF",
        "ANS_USE_UPF",
        "ANS_USER_PATH",
    )
    error_counts = re.findall(
        r"NUMBER OF ERROR\s+MESSAGES ENCOUNTERED\s*=\s*(\d+)\b", upper
    )
    release = unique_output_value(text, r"^Release:\s*([^\r\n]+)$")
    observed_job = unique_output_value(text, r"^Job Name:\s*([^\r\n]+)$")
    observed_input = unique_output_value(text, r"^Input File:\s*([^\r\n]+)$")
    observed_root = unique_output_value(text, r"^Working Directory:\s*([^\r\n]+)$")
    return {
        "nonce": re.fullmatch(r"[0-9a-f]{32}", str(nonce)) is not None,
        "zero_errors": len(error_counts) == 1 and error_counts[0] == "0",
        "one_solve": upper.count("MAPDL SOLVE    COMMAND") == 1,
        "one_run_completed": upper.count("RUN COMPLETED") == 1,
        "begin_nonce": exact_output_line_occurs_once(
            text, "TASK10_RESOLVE_BEGIN_" + nonce
        ),
        "solved_nonce": exact_output_line_occurs_once(
            text, "TASK10_RESOLVE_SOLVED_" + nonce
        ),
        "end_nonce": exact_output_line_occurs_once(
            text, "TASK10_RESOLVE_END_" + nonce
        ),
        "release": (
            release is not None
            and "2026 R1" in release.upper()
            and "BUILD: 26.1" in release.upper()
        ),
        "job": observed_job == jobname,
        "input": (
            observed_input is not None
            and Path(observed_input).resolve() == Path(input_path).resolve()
        ),
        "working_directory": (
            observed_root is not None
            and Path(observed_root).resolve() == Path(solve_root).resolve()
        ),
        "completion": parse_ansys_batch_completions(text) is not None,
        "no_forbidden_text": not any(marker in upper for marker in forbidden),
    }


def parse_reaction_listing(text, expected_nodes):
    upper = (text or "").upper()
    if "REACTION SOLUTION LISTING" not in upper or "TOTAL VALUES" not in upper:
        return None
    pattern = re.compile(
        r"^\s*(\d+)\s+(%s)\s*(%s)\s*(%s)\s*$" % (ANSYS_NUMBER, ANSYS_NUMBER, ANSYS_NUMBER),
        re.MULTILINE | re.IGNORECASE,
    )
    rows = {}
    for match in pattern.finditer(text or ""):
        label = int(match.group(1))
        values = tuple(ansys_number(match.group(index)) for index in (2, 3, 4))
        if label in rows or any(not math.isfinite(value) for value in values):
            return None
        rows[label] = values
    return rows if set(rows) == set(expected_nodes) else None


def read_ansys_rst(result_path):
    if not ansys_rst_preflight(result_path):
        raise RuntimeError("RST binary preflight failed")
    from ansys.mapdl import reader as pymapdl_reader

    require_trusted_module(pymapdl_reader)

    result = pymapdl_reader.read_binary(str(result_path))
    node_labels = [int(value) for value in result.mesh.nnum]
    node_rows = [tuple(float(value) for value in row[:3]) for row in result.mesh.nodes]
    if len(node_labels) != len(set(node_labels)):
        raise RuntimeError("RST contains duplicate node labels")
    coords = dict(zip(node_labels, node_rows))
    if any(
        label <= 0 or len(row) != 3 or any(not math.isfinite(value) for value in row)
        for label, row in coords.items()
    ):
        raise RuntimeError("RST contains an invalid node-coordinate record")
    type_codes = dict((int(row[0]), int(row[1])) for row in result.mesh.ekey)
    elements = {}
    auxiliary = {}
    for record in result.mesh.elem:
        type_reference = int(record[1])
        label = int(record[8])
        code = type_codes.get(type_reference)
        if label <= 0 or code not in (21, 170, 174, 184, 185, 186, 187):
            raise RuntimeError("RST contains an unsupported element")
        node_count = {21: 1, 170: 1, 174: 8, 184: 2, 185: 8, 186: 20, 187: 10}[code]
        connectivity = tuple(int(value) for value in record[10:10 + node_count])
        if any(value <= 0 for value in connectivity) or label in elements or label in auxiliary:
            raise RuntimeError("RST element connectivity is incomplete or duplicated")
        if code in (21, 170, 174, 184):
            auxiliary[label] = (code, connectivity)
        else:
            elements[label] = (code, connectivity)
    referenced_nodes = {
        node
        for _, connectivity in tuple(elements.values()) + tuple(auxiliary.values())
        for node in connectivity
    }
    if not referenced_nodes or not referenced_nodes.issubset(coords):
        raise RuntimeError("RST element connectivity references a missing coordinate")
    # The v261 reader can expose an extra, unreferenced coordinate record.
    # Only nodes in the native element table are part of the result mesh.
    coords = {node: coords[node] for node in referenced_nodes}
    times = [float(value) for value in result.time_values]
    if len(times) != int(result.nsets) or not times or any(not math.isfinite(value) for value in times):
        raise RuntimeError("RST result-set metadata is incomplete")
    if "ENS :" not in str(result.available_results).upper():
        raise RuntimeError("RST does not advertise native element-nodal stress")
    ens_history = []
    for result_index in range(int(result.nsets)):
        stress_labels, stress_rows, stress_nodes = result.element_stress(result_index)
        labels = [int(value) for value in stress_labels]
        if not set(elements).issubset(set(labels)) or not set(labels).issubset(set(elements) | set(auxiliary)) or len(labels) != len(set(labels)):
            raise RuntimeError("RST element stress does not cover every element")
        ens = {}
        for index, label in enumerate(labels):
            if label in auxiliary:
                continue
            code, connectivity = elements[label]
            corner_indices = ansys_corner_indices(code, connectivity)
            if corner_indices is None:
                raise RuntimeError("RST solid topology is unsupported")
            expected_nodes = tuple(connectivity[index] for index in corner_indices)
            expected_count = len(expected_nodes)
            row_nodes = tuple(int(value) for value in stress_nodes[index])
            rows = list(stress_rows[index])
            if (
                len(row_nodes) != expected_count
                or set(row_nodes) != set(expected_nodes)
                or len(rows) != expected_count
            ):
                raise RuntimeError("RST native stress node coverage is incomplete")
            values = []
            for row in rows:
                components = tuple(float(value) for value in row)
                if len(components) != 6 or any(not math.isfinite(value) for value in components):
                    raise RuntimeError("RST stress component record is invalid")
                values.extend(components)
            ens[label] = (code, row_nodes, tuple(values))
        ens_history.append(ens)
    return coords, elements, auxiliary, int(result.nsets), times, tuple(ens_history)


def ansys_rst_preflight(result_path):
    try:
        path = Path(result_path)
        if not path.is_file() or path.is_symlink():
            log("ANSYS RST preflight requires a regular, non-symlink result file")
            return False
        size = path.stat().st_size
        if size < ANSYS_RST_HEADER_SIZE:
            log("ANSYS RST preflight rejected a truncated header: %d bytes" % size)
            return False
        with path.open("rb") as stream:
            header = stream.read(ANSYS_RST_HEADER_SIZE)
    except Exception as exc:
        log("ANSYS RST preflight could not inspect the submitted result: %s" % exc)
        return False
    declared_words = int.from_bytes(header[112:116], "little", signed=False)
    if not (
        len(header) == ANSYS_RST_HEADER_SIZE
        and header[:4] == b"\x64\x00\x00\x00"
        and header[4:8] == b"\x00\x00\x00\x80"
        and header[12:16] == b"\xff\xff\xff\xff"
        and declared_words > 0
        and declared_words <= size // 4
    ):
        log(
            "ANSYS RST preflight rejected an invalid or truncated binary range: "
            "actual=%d bytes declared=%d words" % (size, declared_words)
        )
        return False
    return True


def material_matches(mapdl, material_id):
    ex = try_get(mapdl, "EX", material_id, "TEMP", 0)
    nu = try_get(mapdl, "PRXY", material_id, "TEMP", 0)
    if nu is None:
        nu = try_get(mapdl, "NUXY", material_id, "TEMP", 0)
    if ex is not None and nu is not None:
        return close_enough(ex, 210000.0, rel=1.0e-6) and close_enough(nu, 0.3, rel=1.0e-6)
    tb_ex = try_get(mapdl, "ELASTIC", material_id, "TEMP", 0, "CONST", 1, "ISOT")
    tb_nu = try_get(mapdl, "ELASTIC", material_id, "TEMP", 0, "CONST", 2, "ISOT")
    return (
        tb_ex is not None and tb_nu is not None
        and close_enough(tb_ex, 210000.0, rel=1.0e-6)
        and close_enough(tb_nu, 0.3, rel=1.0e-6)
    )


def ansys_tet_volume(a, b, c, d):
    return abs(ansys_tet_signed_volume6(a, b, c, d)) / 6.0


def ansys_tet_signed_volume6(a, b, c, d):
    ab = tuple(b[i] - a[i] for i in range(3))
    ac = tuple(c[i] - a[i] for i in range(3))
    ad = tuple(d[i] - a[i] for i in range(3))
    cross = (
        ac[1] * ad[2] - ac[2] * ad[1],
        ac[2] * ad[0] - ac[0] * ad[2],
        ac[0] * ad[1] - ac[1] * ad[0],
    )
    return sum(ab[i] * cross[i] for i in range(3))


_HEX8_GAUSS_COORDINATES = tuple(
    (xi, eta, zeta)
    for xi in (-1.0 / math.sqrt(3.0), 1.0 / math.sqrt(3.0))
    for eta in (-1.0 / math.sqrt(3.0), 1.0 / math.sqrt(3.0))
    for zeta in (-1.0 / math.sqrt(3.0), 1.0 / math.sqrt(3.0))
) + ((0.0, 0.0, 0.0),)


def ansys_hex8_signed_jacobian(points, xi, eta, zeta):
    if len(points) != 8:
        return None
    derivatives = []
    for signs in (
        (-1, -1, -1),
        (1, -1, -1),
        (1, 1, -1),
        (-1, 1, -1),
        (-1, -1, 1),
        (1, -1, 1),
        (1, 1, 1),
        (-1, 1, 1),
    ):
        sx, sy, sz = signs
        derivatives.append((
            sx * (1.0 + sy * eta) * (1.0 + sz * zeta) / 8.0,
            sy * (1.0 + sx * xi) * (1.0 + sz * zeta) / 8.0,
            sz * (1.0 + sx * xi) * (1.0 + sy * eta) / 8.0,
        ))
    jacobian = [[0.0, 0.0, 0.0] for _ in range(3)]
    for point, derivative in zip(points, derivatives):
        for row, weight in enumerate(derivative):
            for column in range(3):
                jacobian[row][column] += weight * point[column]
    return (
        jacobian[0][0] * (jacobian[1][1] * jacobian[2][2] - jacobian[1][2] * jacobian[2][1])
        - jacobian[0][1] * (jacobian[1][0] * jacobian[2][2] - jacobian[1][2] * jacobian[2][0])
        + jacobian[0][2] * (jacobian[1][0] * jacobian[2][1] - jacobian[1][1] * jacobian[2][0])
    )


def ansys_solid_shape(code, connectivity):
    if code == 185 and len(connectivity) == 8:
        if len(set(connectivity)) == 8:
            return "hex8"
        if (
            connectivity[2] == connectivity[3]
            and connectivity[6] == connectivity[7]
            and len(set(connectivity[index] for index in (0, 1, 2, 4, 5, 6))) == 6
        ):
            return "prism6"
        if (
            connectivity[2] == connectivity[3]
            and len(set(connectivity[index] for index in (4, 5, 6, 7))) == 1
            and len(set(connectivity[index] for index in (0, 1, 2, 4))) == 4
        ):
            return "tet4"
        if (
            len(set(connectivity[index] for index in (4, 5, 6, 7))) == 1
            and len(set(connectivity[index] for index in (0, 1, 2, 3, 4))) == 5
        ):
            return "pyramid5"
        return None
    if code == 186 and len(connectivity) == 20:
        if len(set(connectivity)) == 20:
            return "hex20"
        prism_representatives = (0, 1, 2, 4, 5, 6, 8, 9, 11, 12, 13, 15, 16, 17, 18)
        if (
            connectivity[2] == connectivity[3] == connectivity[10]
            and connectivity[6] == connectivity[7] == connectivity[14]
            and connectivity[18] == connectivity[19]
            and len(set(connectivity[index] for index in prism_representatives))
            == len(prism_representatives)
        ):
            return "prism15"
        tetra_representatives = (0, 1, 2, 4, 8, 9, 11, 16, 17, 18)
        if (
            connectivity[2] == connectivity[3] == connectivity[10]
            and len(set(connectivity[index] for index in (4, 5, 6, 7, 12, 13, 14, 15))) == 1
            and connectivity[18] == connectivity[19]
            and len(set(connectivity[index] for index in tetra_representatives))
            == len(tetra_representatives)
        ):
            return "tet10_186"
        pyramid_representatives = (0, 1, 2, 3, 4, 8, 9, 10, 11, 16, 17, 18, 19)
        if (
            len(set(connectivity[index] for index in (4, 5, 6, 7, 12, 13, 14, 15))) == 1
            and len(set(connectivity[index] for index in pyramid_representatives))
            == len(pyramid_representatives)
        ):
            return "pyramid13"
        return None
    if code == 187 and len(connectivity) == 10 and len(set(connectivity)) == 10:
        return "tet10"
    return None


def ansys_corner_indices(code, connectivity):
    shape = ansys_solid_shape(code, connectivity)
    return {
        "hex8": (0, 1, 2, 3, 4, 5, 6, 7),
        "hex20": (0, 1, 2, 3, 4, 5, 6, 7),
        "prism6": (0, 1, 2, 4, 5, 6),
        "prism15": (0, 1, 2, 4, 5, 6),
        "tet4": (0, 1, 2, 4),
        "tet10": (0, 1, 2, 3),
        "tet10_186": (0, 1, 2, 4),
        "pyramid5": (0, 1, 2, 3, 4),
        "pyramid13": (0, 1, 2, 3, 4),
    }.get(shape)


_WEDGE6_SAMPLE_COORDINATES = tuple(
    (r, s, t)
    for r, s in ((1.0 / 6.0, 1.0 / 6.0), (2.0 / 3.0, 1.0 / 6.0), (1.0 / 6.0, 2.0 / 3.0))
    for t in (-1.0 / math.sqrt(3.0), 1.0 / math.sqrt(3.0))
) + ((1.0 / 3.0, 1.0 / 3.0, 0.0),)


def ansys_wedge6_signed_jacobian(points, r, s, t):
    if len(points) != 6:
        return None
    derivatives = (
        (-(1.0 - t) / 2.0, -(1.0 - t) / 2.0, -(1.0 - r - s) / 2.0),
        ((1.0 - t) / 2.0, 0.0, -r / 2.0),
        (0.0, (1.0 - t) / 2.0, -s / 2.0),
        (-(1.0 + t) / 2.0, -(1.0 + t) / 2.0, (1.0 - r - s) / 2.0),
        ((1.0 + t) / 2.0, 0.0, r / 2.0),
        (0.0, (1.0 + t) / 2.0, s / 2.0),
    )
    jacobian = [[0.0, 0.0, 0.0] for _ in range(3)]
    for point, derivative in zip(points, derivatives):
        for row, weight in enumerate(derivative):
            for column in range(3):
                jacobian[row][column] += weight * point[column]
    return (
        jacobian[0][0] * (jacobian[1][1] * jacobian[2][2] - jacobian[1][2] * jacobian[2][1])
        - jacobian[0][1] * (jacobian[1][0] * jacobian[2][2] - jacobian[1][2] * jacobian[2][0])
        + jacobian[0][2] * (jacobian[1][0] * jacobian[2][1] - jacobian[1][1] * jacobian[2][0])
    )


def ansys_element_signed_jacobians(code, connectivity, coords):
    try:
        shape = ansys_solid_shape(code, connectivity)
        if shape in ("hex8", "hex20"):
            points = [coords[label] for label in connectivity[:8]]
            return tuple(
                ansys_hex8_signed_jacobian(points, *location)
                for location in _HEX8_GAUSS_COORDINATES
            )
        indices = ansys_corner_indices(code, connectivity)
        points = [coords[connectivity[index]] for index in indices]
        if shape in ("tet4", "tet10", "tet10_186"):
            return (ansys_tet_signed_volume6(*points),)
        if shape in ("prism6", "prism15"):
            return tuple(
                ansys_wedge6_signed_jacobian(points, *location)
                for location in _WEDGE6_SAMPLE_COORDINATES
            )
        if shape in ("pyramid5", "pyramid13"):
            return (
                ansys_tet_signed_volume6(points[0], points[1], points[2], points[4]),
                ansys_tet_signed_volume6(points[0], points[2], points[3], points[4]),
            )
    except (KeyError, IndexError, TypeError):
        return None
    return None


def ansys_element_volume(code, connectivity, coords):
    shape = ansys_solid_shape(code, connectivity)
    indices = ansys_corner_indices(code, connectivity)
    points = [coords[connectivity[index]] for index in indices]
    if shape in ("tet4", "tet10", "tet10_186"):
        return ansys_tet_volume(points[0], points[1], points[2], points[3])
    if shape in ("prism6", "prism15"):
        return (
            ansys_tet_volume(points[0], points[1], points[2], points[3])
            + ansys_tet_volume(points[1], points[2], points[4], points[3])
            + ansys_tet_volume(points[2], points[4], points[5], points[3])
        )
    if shape in ("pyramid5", "pyramid13"):
        return (
            ansys_tet_volume(points[0], points[1], points[2], points[4])
            + ansys_tet_volume(points[0], points[2], points[3], points[4])
        )
    return (
        ansys_tet_volume(points[0], points[1], points[3], points[4])
        + ansys_tet_volume(points[1], points[2], points[3], points[6])
        + ansys_tet_volume(points[1], points[3], points[4], points[6])
        + ansys_tet_volume(points[1], points[4], points[5], points[6])
        + ansys_tet_volume(points[3], points[4], points[6], points[7])
    )


def ansys_element_topology(code, connectivity):
    shape = ansys_solid_shape(code, connectivity)
    if shape == "hex8":
        faces = (
            ((0, 1, 2, 3), (0, 1, 2, 3)),
            ((4, 7, 6, 5), (4, 7, 6, 5)),
            ((0, 4, 5, 1), (0, 4, 5, 1)),
            ((1, 5, 6, 2), (1, 5, 6, 2)),
            ((2, 6, 7, 3), (2, 6, 7, 3)),
            ((3, 7, 4, 0), (3, 7, 4, 0)),
        )
        edges = ((0,1),(1,2),(2,3),(3,0),(4,5),(5,6),(6,7),(7,4),(0,4),(1,5),(2,6),(3,7))
    elif shape == "hex20":
        faces = (
            ((0, 1, 2, 3), (0, 1, 2, 3, 8, 9, 10, 11)),
            ((4, 7, 6, 5), (4, 7, 6, 5, 12, 13, 14, 15)),
            ((0, 4, 5, 1), (0, 4, 5, 1, 16, 12, 17, 8)),
            ((1, 5, 6, 2), (1, 5, 6, 2, 17, 13, 18, 9)),
            ((2, 6, 7, 3), (2, 6, 7, 3, 18, 14, 19, 10)),
            ((3, 7, 4, 0), (3, 7, 4, 0, 19, 15, 16, 11)),
        )
        edges = ((0,1),(1,2),(2,3),(3,0),(4,5),(5,6),(6,7),(7,4),(0,4),(1,5),(2,6),(3,7))
    elif shape == "prism6":
        faces = tuple(
            (face, face)
            for face in (
                (0, 1, 2),
                (4, 6, 5),
                (0, 4, 5, 1),
                (1, 5, 6, 2),
                (2, 6, 4, 0),
            )
        )
        edges = ((0,1),(1,2),(2,0),(4,5),(5,6),(6,4),(0,4),(1,5),(2,6))
    elif shape == "prism15":
        faces = (
            ((0, 1, 2), (0, 1, 2, 8, 9, 11)),
            ((4, 6, 5), (4, 6, 5, 15, 13, 12)),
            ((0, 4, 5, 1), (0, 4, 5, 1, 16, 12, 17, 8)),
            ((1, 5, 6, 2), (1, 5, 6, 2, 17, 13, 18, 9)),
            ((2, 6, 4, 0), (2, 6, 4, 0, 18, 15, 16, 11)),
        )
        edges = ((0,1),(1,2),(2,0),(4,5),(5,6),(6,4),(0,4),(1,5),(2,6))
    elif shape == "tet4":
        faces = tuple(
            (face, face)
            for face in ((0, 1, 4), (1, 2, 4), (2, 0, 4), (0, 2, 1))
        )
        edges = ((0,1),(0,2),(0,4),(1,2),(1,4),(2,4))
    elif shape == "tet10_186":
        faces = (
            ((0, 1, 2), (0, 1, 2, 8, 9, 11)),
            ((0, 4, 1), (0, 4, 1, 16, 17, 8)),
            ((1, 4, 2), (1, 4, 2, 17, 18, 9)),
            ((2, 4, 0), (2, 4, 0, 18, 16, 11)),
        )
        edges = ((0,1),(0,2),(0,4),(1,2),(1,4),(2,4))
    elif shape == "pyramid5":
        faces = tuple(
            (face, face)
            for face in ((0, 1, 2, 3), (0, 4, 1), (1, 4, 2), (2, 4, 3), (3, 4, 0))
        )
        edges = ((0,1),(1,2),(2,3),(3,0),(0,4),(1,4),(2,4),(3,4))
    elif shape == "pyramid13":
        faces = (
            ((0, 1, 2, 3), (0, 1, 2, 3, 8, 9, 10, 11)),
            ((0, 4, 1), (0, 4, 1, 16, 17, 8)),
            ((1, 4, 2), (1, 4, 2, 17, 18, 9)),
            ((2, 4, 3), (2, 4, 3, 18, 19, 10)),
            ((3, 4, 0), (3, 4, 0, 19, 16, 11)),
        )
        edges = ((0,1),(1,2),(2,3),(3,0),(0,4),(1,4),(2,4),(3,4))
    elif shape == "tet10":
        faces = (
            ((0, 1, 2), (0, 1, 2, 4, 5, 6)),
            ((0, 3, 1), (0, 3, 1, 7, 8, 4)),
            ((1, 3, 2), (1, 3, 2, 8, 9, 5)),
            ((2, 3, 0), (2, 3, 0, 9, 7, 6)),
        )
        edges = ((0,1),(0,2),(0,3),(1,2),(1,3),(2,3))
    else:
        return None
    return (
        tuple((tuple(connectivity[index] for index in corners), tuple(connectivity[index] for index in full)) for corners, full in faces),
        tuple((connectivity[first], connectivity[second]) for first, second in edges),
    )


def ansys_connectivity_is_valid(code, connectivity, coords):
    expected = {21: 1, 170: 1, 174: 8, 184: 2, 185: 8, 186: 20, 187: 10}.get(code)
    if expected is None or len(connectivity) != expected:
        return False
    if any(node <= 0 or node not in coords for node in connectivity):
        return False
    if code == 174:
        # MAPDL stores triangular CONTA174 faces in the eight-node record by
        # repeating corner slots; six unique nodes is normal for SOLID187 faces.
        return len(set(connectivity[:3])) == 3 and 3 <= len(set(connectivity)) <= 8
    if code in (185, 186, 187):
        return ansys_solid_shape(code, connectivity) is not None
    return len(set(connectivity)) == expected


def cdb_constraint_equations(text):
    equations = []
    current = None
    for raw in (text or "").splitlines():
        line = raw.split("!", 1)[0].strip()
        if not line:
            continue
        fields = [value.strip() for value in line.split(",")]
        if fields[0].upper() != "CE":
            continue
        if len(fields) >= 3 and fields[1].upper() == "UNBL":
            record = fields[2].upper()
            if record == "DEFI":
                if len(fields) < 6:
                    return None
                try:
                    term_count = int(float(fields[3]))
                    constant = ansys_number(fields[5])
                except Exception:
                    return None
                if term_count <= 0 or not math.isfinite(constant):
                    return None
                current = {"constant": constant, "terms": [], "term_count": term_count}
                equations.append(current)
                continue
            if record == "NODE":
                if current is None:
                    return None
                terms = fields[3:]
                for index in range(0, len(terms), 3):
                    chunk = terms[index:index + 3]
                    if len(chunk) < 3 or not chunk[0]:
                        continue
                    try:
                        node = int(float(chunk[0]))
                        dof = chunk[1].upper()
                        coefficient = ansys_number(chunk[2])
                    except Exception:
                        return None
                    if node <= 0 or dof not in ("UX", "UY", "UZ", "ROTX", "ROTY", "ROTZ") or not math.isfinite(coefficient):
                        return None
                    current["terms"].append((node, dof, coefficient))
                continue
            return None
        if len(fields) < 4:
            return None
        equation_id = fields[1]
        if equation_id:
            try:
                constant = ansys_number(fields[2]) if fields[2] else 0.0
            except Exception:
                return None
            if not math.isfinite(constant):
                return None
            current = {"constant": constant, "terms": []}
            equations.append(current)
        if current is None:
            return None
        terms = fields[3:]
        for index in range(0, len(terms), 3):
            chunk = terms[index:index + 3]
            if len(chunk) < 3 or not chunk[0]:
                continue
            try:
                node = int(float(chunk[0]))
                dof = chunk[1].upper()
                coefficient = ansys_number(chunk[2])
            except Exception:
                return None
            if node <= 0 or dof not in ("UX", "UY", "UZ", "ROTX", "ROTY", "ROTZ") or not math.isfinite(coefficient):
                return None
            current["terms"].append((node, dof, coefficient))
    if any(
        "term_count" in equation and len(equation["terms"]) != equation["term_count"]
        for equation in equations
    ):
        return None
    return equations


def cdb_element_type_records(text):
    records = {}
    in_block = False
    saw_block = False
    saw_end = False
    for raw in (text or "").splitlines():
        line = raw.split("!", 1)[0].strip()
        if not line:
            continue
        if not in_block:
            if line.upper().startswith("ETBLOCK,"):
                if saw_block:
                    return None
                saw_block = True
                in_block = True
            continue
        if line.startswith("("):
            continue
        fields = line.split()
        if fields == ["-1"]:
            saw_end = True
            in_block = False
            continue
        if len(fields) != 21:
            return None
        try:
            values = tuple(int(field) for field in fields)
        except ValueError:
            return None
        type_id, code = values[:2]
        if type_id <= 0 or code <= 0 or type_id in records:
            return None
        records[type_id] = (code, values[2:])
    return records if saw_block and saw_end and records else None


def cdb_keyopt(records, type_id, keyopt):
    if not isinstance(records, dict) or not 1 <= int(keyopt) <= 19:
        return None
    record = records.get(int(type_id))
    if record is None or len(record[1]) != 19:
        return None
    return int(record[1][int(keyopt) - 1])


def cdb_has_command(text, command):
    return re.search(
        r"^\s*%s\s*," % re.escape(command),
        text or "",
        re.MULTILINE | re.IGNORECASE,
    ) is not None


def ansys_nlgeom_state(status_text):
    if not isinstance(status_text, str) or not status_text.strip() or "\x00" in status_text:
        return None
    lines = status_text.splitlines()
    if sum(bool(_STATUS_TITLE.fullmatch(line)) for line in lines) != 1:
        return None
    values = [
        match.group(1).upper()
        for line in lines
        for match in [_NLGEOM_STATUS.fullmatch(line)]
        if match is not None
    ]
    if not values:
        has_label = any(
            re.match(r"^\s*NONLINEAR\s+GEOMETRIC\s+EFFECTS\b", line, re.IGNORECASE)
            for line in lines
        )
        normalized = "\n".join(lines).upper()
        complete_default_off = all(marker in normalized for marker in (
            "ANALYSIS TYPE",
            "STATIC (STEADY-STATE)",
            "GLOBALLY ASSEMBLED MATRIX",
            "L O A D   S T E P   O P T I O N S",
            "LOAD STEP NUMBER",
            "TIME AT END OF THE LOAD STEP",
            "NUMBER OF SUBSTEPS",
            "DATABASE OUTPUT CONTROLS",
            "ITEM",
            "FREQUENCY",
            "ALL",
        ))
        return False if complete_default_off and not has_label else None
    return values[0] == "ON" if len(values) == 1 else None


def normalized_equation(equation, slave_node, slave_dof):
    combined = {}
    for node, dof, coefficient in equation["terms"]:
        key = (node, dof)
        combined[key] = combined.get(key, 0.0) + coefficient
    combined = dict((key, value) for key, value in combined.items() if abs(value) > 1.0e-12)
    scale = combined.get((slave_node, slave_dof))
    if scale is None or abs(scale) <= 1.0e-12:
        return None
    return dict((key, value / scale) for key, value in combined.items())


def rigid_equation_signature(slave_node, slave_dof, pilot, coords):
    dx = coords[slave_node][0] - coords[pilot][0]
    dy = coords[slave_node][1] - coords[pilot][1]
    dz = coords[slave_node][2] - coords[pilot][2]
    expected = {
        "UX": {
            (slave_node, "UX"): 1.0,
            (pilot, "UX"): -1.0,
            (pilot, "ROTY"): -dz,
            (pilot, "ROTZ"): dy,
        },
        "UY": {
            (slave_node, "UY"): 1.0,
            (pilot, "UY"): -1.0,
            (pilot, "ROTX"): dz,
            (pilot, "ROTZ"): -dx,
        },
        "UZ": {
            (slave_node, "UZ"): 1.0,
            (pilot, "UZ"): -1.0,
            (pilot, "ROTX"): -dy,
            (pilot, "ROTY"): dx,
        },
    }[slave_dof]
    return dict((key, value) for key, value in expected.items() if abs(value) > 1.0e-12)


def equation_matches(actual, expected):
    return set(actual) == set(expected) and all(
        close_enough(actual[key], expected[key], rel=1.0e-7, abs_tol=1.0e-9)
        for key in expected
    )


def audit_ansys_coupling(export_text, pilot, free_nodes, coords):
    if re.search(r"^\s*CP\s*,", export_text or "", re.MULTILINE | re.IGNORECASE):
        return False
    equations = cdb_constraint_equations(export_text)
    if not equations or len(equations) != 3 * len(free_nodes):
        return False
    allowed_nodes = set(free_nodes) | {pilot}
    matched = set()
    for equation in equations:
        if abs(equation["constant"]) > 1.0e-12:
            return False
        nodes = set(term[0] for term in equation["terms"])
        if not nodes or not nodes.issubset(allowed_nodes) or pilot not in nodes:
            return False
        slaves = nodes - {pilot}
        if len(slaves) != 1:
            return False
        slave = next(iter(slaves))
        candidates = []
        for dof in ("UX", "UY", "UZ"):
            normalized = normalized_equation(equation, slave, dof)
            expected = rigid_equation_signature(slave, dof, pilot, coords)
            if normalized is not None and equation_matches(normalized, expected):
                candidates.append(dof)
        if len(candidates) != 1 or (slave, candidates[0]) in matched:
            return False
        matched.add((slave, candidates[0]))
    return matched == set((node, dof) for node in free_nodes for dof in ("UX", "UY", "UZ"))


def audit_ansys_mpc184_spider(auxiliary, pilot, free_nodes):
    if len(auxiliary) != len(free_nodes) or any(code != 184 for code, connectivity in auxiliary.values()):
        return False
    covered = []
    for code, connectivity in auxiliary.values():
        if len(connectivity) != 2 or pilot not in connectivity:
            return False
        other = connectivity[1] if connectivity[0] == pilot else connectivity[0]
        if other == pilot or other not in free_nodes:
            return False
        covered.append(other)
    return len(covered) == len(set(covered)) and set(covered) == set(free_nodes)


def inertia_loads_are_zero(export_text):
    irlf_state = None
    airl_active = False
    pattern = re.compile(
        r"^\s*(ACEL|OMEGA|DOMEGA|CGOMEGA|CGOMGA|DCGOMG|CMACEL|CMOMEGA|CMDOMEGA)\s*,(.*)$",
        re.MULTILINE | re.IGNORECASE,
    )
    for match in pattern.finditer(export_text or ""):
        fields = [field.strip() for field in match.group(2).split(",")]
        if match.group(1).upper().startswith("CM"):
            fields = fields[1:]
        for field in fields:
            if not field:
                continue
            try:
                value = ansys_number(field)
            except Exception:
                return False
            if not math.isfinite(value) or abs(value) > 1.0e-12:
                return False
    for raw in (export_text or "").splitlines():
        fields = [field.strip() for field in raw.split("!", 1)[0].strip().split(",")]
        if not fields or not fields[0]:
            continue
        command = fields[0].upper()
        if command == "IRLF":
            try:
                irlf_state = ansys_number(fields[1])
            except Exception:
                return False
        elif command == "AIRL":
            if len(fields) < 2 or not fields[1]:
                return False
            token = fields[1].upper()
            try:
                airl_active = abs(ansys_number(token)) > 1.0e-12
            except Exception:
                airl_active = token == "AUTO"
    return irlf_state != 1.0 and not airl_active


def ansys_saved_nar_signature(mapdl, solid_type_ids, expected_corner_nodes, signature_path):
    solid_type_ids = tuple(sorted(set(int(value) for value in solid_type_ids)))
    expected_corner_nodes = set(int(value) for value in expected_corner_nodes)
    if not solid_type_ids or not expected_corner_nodes or signature_path.exists():
        log(
            "ANSYS NAR precondition failed: solid_types=%r expected_nodes=%d path_exists=%r"
            % (solid_type_ids, len(expected_corner_nodes), signature_path.exists())
        )
        return None
    signature_stem = str(signature_path.with_suffix(""))
    if any(character in signature_stem for character in ("'", ",", "\n", "\r")):
        log("ANSYS NAR signature path contains an unsafe character")
        return None
    selection = [
        "ESEL,%s,TYPE,,%d" % ("S" if index == 0 else "A", type_id)
        for index, type_id in enumerate(solid_type_ids)
    ]
    commands = "\n".join((
        "ALLSEL,ALL",
        *selection,
        "NSLE,S,CORNER",
        "*GET,T10SC,NODE,0,COUNT",
        "*DIM,T10SX,ARRAY,1",
        "*DIM,T10SY,ARRAY,1",
        "*DIM,T10SZ,ARRAY,1",
        "*DIM,T10SXY,ARRAY,1",
        "*DIM,T10SYZ,ARRAY,1",
        "*DIM,T10SXZ,ARRAY,1",
        "*DIM,T10SEQV,ARRAY,1",
        "T10SID=0",
        "*CFOPEN,'%s','txt'" % signature_stem,
        "*DO,T10II,1,T10SC",
        "T10SID=NDNEXT(T10SID)",
        "*VGET,T10SX(1),NODE,T10SID,S,X,NAR",
        "*VGET,T10SY(1),NODE,T10SID,S,Y,NAR",
        "*VGET,T10SZ(1),NODE,T10SID,S,Z,NAR",
        "*VGET,T10SXY(1),NODE,T10SID,S,XY,NAR",
        "*VGET,T10SYZ(1),NODE,T10SID,S,YZ,NAR",
        "*VGET,T10SXZ(1),NODE,T10SID,S,XZ,NAR",
        "*VGET,T10SEQV(1),NODE,T10SID,S,EQV,NAR",
        "*VWRITE,T10SID,T10SX(1),T10SY(1),T10SZ(1),T10SXY(1),T10SYZ(1),T10SXZ(1),T10SEQV(1)",
        "('S,',8(E24.16,','))",
        "*ENDDO",
        "*CFCLOS",
        "ALLSEL,ALL",
    ))
    try:
        required_input_strings(mapdl, commands)
        if not is_nonempty(signature_path):
            log("ANSYS NAR signature file was not created: %s" % signature_path)
            return None
        rows = {}
        raw_lines = signature_path.read_text(encoding="utf-8", errors="replace").splitlines()
        for line_number, raw in enumerate(raw_lines, 1):
            fields = [field.strip() for field in raw.split(",") if field.strip()]
            if not fields or fields[0] != "S":
                continue
            if len(fields) != 9:
                log("ANSYS NAR signature line %d has %d fields: %r" % (line_number, len(fields), raw[:300]))
                return None
            values = tuple(ansys_number(value) for value in fields[1:])
            node = int(round(values[0]))
            if (
                not close_enough(values[0], node, rel=0.0, abs_tol=1.0e-7)
                or node in rows
                or any(not finite_number(value) for value in values[1:])
                or values[-1] < 0.0
            ):
                log("ANSYS NAR signature line %d is invalid: %r" % (line_number, values))
                return None
            rows[node] = values[1:]
        if set(rows) != expected_corner_nodes:
            log(
                "ANSYS NAR signature node mismatch: rows=%d expected=%d missing=%r extra=%r raw_lines=%d"
                % (
                    len(rows),
                    len(expected_corner_nodes),
                    sorted(expected_corner_nodes - set(rows))[:12],
                    sorted(set(rows) - expected_corner_nodes)[:12],
                    len(raw_lines),
                )
            )
            return None
        return rows
    finally:
        try:
            signature_path.unlink()
        except FileNotFoundError:
            pass


def ansys_nodal_signature(mapdl, nodes, nar_stress):
    signature = {}
    for node in sorted(nodes):
        displacement = tuple(try_get(mapdl, "NODE", node, "U", comp) for comp in ("X", "Y", "Z"))
        if any(value is None for value in displacement):
            return None
        stress = nar_stress.get(node)
        signature[node] = (displacement, stress)
    return signature


def ansys_signature_matches(left, right):
    if left is None or right is None or set(left) != set(right):
        return False
    for node in left:
        for first, second in zip(left[node][0], right[node][0]):
            if not close_enough(first, second, rel=2.0e-4, abs_tol=2.0e-8):
                return False
        if (left[node][1] is None) != (right[node][1] is None):
            return False
        if left[node][1] is not None:
            for first, second in zip(left[node][1], right[node][1]):
                if not close_enough(first, second, rel=2.0e-4, abs_tol=2.0e-6):
                    return False
    return True


def ens_matches(left, right):
    if left is None or right is None or set(left) != set(right):
        return False
    for element in left:
        if left[element][:-1] != right[element][:-1] or len(left[element][-1]) != len(right[element][-1]):
            return False
        if any(not close_enough(a, b, rel=2.0e-5, abs_tol=2.0e-8) for a, b in zip(left[element][-1], right[element][-1])):
            return False
    return True


def reaction_matches(left, right):
    if left is None or right is None or set(left) != set(right):
        return False
    return all(
        all(close_enough(a, b, rel=2.0e-4, abs_tol=2.0e-6) for a, b in zip(left[node], right[node]))
        for node in left
    )


def ansys_result_signature(
    mapdl,
    coords,
    solid_nodes,
    solid_corner_nodes,
    solid_type_ids,
    fixed_nodes,
    pilot,
    nar_signature_path,
):
    required_run(mapdl, "RSYS,0")
    required_run(mapdl, "AVPRIN,0")
    required_run(mapdl, "ALLSEL,ALL")
    nar_stress = ansys_saved_nar_signature(
        mapdl, solid_type_ids, solid_corner_nodes, nar_signature_path
    )
    if nar_stress is None:
        log("ANSYS result signature: saved shaft-solid corner NAR stress extraction is incomplete")
        return None
    required_run(mapdl, "ALLSEL,ALL")
    nodal = ansys_nodal_signature(mapdl, solid_nodes, nar_stress)
    if nodal is None:
        log("ANSYS result signature: shaft nodal U extraction is incomplete")
        return None
    twist = try_get(mapdl, "NODE", pilot, "ROT", "Y")
    rotx = try_get(mapdl, "NODE", pilot, "ROT", "X")
    rotz = try_get(mapdl, "NODE", pilot, "ROT", "Z")
    if twist is None or rotx is None or rotz is None:
        log(
            "ANSYS result signature: pilot ROTX/ROTY/ROTZ extraction is incomplete: "
            "ROTX=%r ROTY=%r ROTZ=%r" % (rotx, twist, rotz)
        )
        return None
    if twist <= 0.0 or not (3.2e-4 <= twist <= 5.0e-4):
        log("ANSYS result signature: pilot ROTY is outside the physical range: %r" % twist)
        return None
    if abs(rotx) > max(1.0e-7, abs(twist) * 0.01) or abs(rotz) > max(1.0e-7, abs(twist) * 0.01):
        log("ANSYS result signature: pilot off-axis rotation is excessive: ROTX=%r ROTZ=%r" % (rotx, rotz))
        return None
    mises = [nar_stress[node][-1] for node in sorted(solid_corner_nodes)]
    if not mises or not (2.5 <= max(mises) <= 8.0):
        log("ANSYS result signature: maximum solid-corner NAR equivalent stress is missing or outside the physical range: %r" % (max(mises) if mises else None))
        return None
    required_run(mapdl, "NSEL,NONE")
    for node in sorted(fixed_nodes):
        required_run(mapdl, "NSEL,A,NODE,,%d" % node)
    reaction_listing = required_run(mapdl, "PRRSOL,F")
    reactions = parse_reaction_listing(reaction_listing, fixed_nodes)
    required_run(mapdl, "ALLSEL,ALL")
    if reactions is None:
        log("ANSYS result signature: fixed-face PRRSOL,F output is incomplete or unreadable: %r" % reaction_listing[-1200:])
        return None
    resultant = [sum(values[index] for values in reactions.values()) for index in range(3)]
    reaction_moment_y = sum(
        coords[node][2] * reactions[node][0] - coords[node][0] * reactions[node][2]
        for node in fixed_nodes
    )
    if not close_enough(reaction_moment_y, -920.0, rel=2.0e-3, abs_tol=1.0):
        log("ANSYS result signature: fixed-face reaction moment is not -920 N*mm: %r" % reaction_moment_y)
        return None
    if math.sqrt(sum(value * value for value in resultant)) > 2.0:
        log("ANSYS result signature: fixed-face resultant force is not near zero: %r" % resultant)
        return None
    return {
        "metrics": {"twist_angle": abs(twist), "max_stress": max(mises)},
        "nodal": nodal,
        "reactions": reactions,
        "reaction_moment_y": reaction_moment_y,
    }


def run_ansys_checker(model_path, result_path, submitted_metrics):
    if not ansys_rst_preflight(result_path):
        return False
    token = uuid.uuid4().hex
    audit_root = Path(tempfile.mkdtemp(prefix="eval_cli_task10_ansys_audit_%s_" % token))
    solve_root = Path(tempfile.mkdtemp(prefix="eval_cli_task10_ansys_solve_%s_" % token))
    post_root = Path(tempfile.mkdtemp(prefix="eval_cli_task10_ansys_post_%s_" % token))
    staged_model = audit_root / "submitted.db"
    staged_result = audit_root / "submitted.rst"
    solve_model = solve_root / "source.db"
    post_result = post_root / "recomputed.rst"
    jobname = "e10audit_" + token[:12]
    solve_jobname = "e10solve_" + token[:12]
    post_jobname = "e10post_" + token[:12]
    original_hashes = None
    baseline = None
    mapdl = None
    owned_history = {}
    tracker_stop = None
    tracker = None
    semantic_ok = False
    process_ok = False
    temp_ok = False
    ansys_temp_ok = False
    ansys_temp_before = None
    try:
        ansys_temp_before = ansys_temp_inventory()
        baseline = windows_processes(ANSYS_PROCESS_PATTERN)
        import ansys.mapdl.core as pymapdl_core

        require_trusted_module(pymapdl_core)
        launch_mapdl = pymapdl_core.launch_mapdl

        original_hashes = (sha256(model_path), sha256(result_path))
        shutil.copy2(str(model_path), str(staged_model))
        shutil.copy2(str(result_path), str(staged_result))
        shutil.copy2(str(model_path), str(solve_model))
        if (
            not exact_regular_files(audit_root, (staged_model.name, staged_result.name))
            or not exact_regular_files(solve_root, (solve_model.name,))
            or not exact_regular_files(post_root, ())
            or sha256(staged_model) != original_hashes[0]
            or sha256(staged_result) != original_hashes[1]
            or sha256(solve_model) != original_hashes[0]
        ):
            raise RuntimeError("ANSYS isolated audit/solve/post roots failed staging validation")
        rst_coords, rst_elements, rst_auxiliary, rst_count, rst_times, rst_ens = read_ansys_rst(staged_result)
        tracker_stop = threading.Event()
        tracker = threading.Thread(
            target=track_owned_processes,
            args=(
                tracker_stop,
                owned_history,
                baseline,
                ANSYS_PROCESS_PATTERN,
                (
                    token,
                    str(audit_root),
                    str(solve_root),
                    str(post_root),
                    jobname,
                    solve_jobname,
                    post_jobname,
                ),
            ),
        )
        tracker.daemon = True
        tracker.start()
        mapdl = launch_mapdl(
            exec_file=ANSYS_EXEC,
            jobname=jobname,
            run_location=str(audit_root),
            nproc=1,
            override=True,
            cleanup_on_exit=True,
            additional_switches="-s noread",
            replace_env_vars=sanitized_ansys_environment(),
            start_timeout=180,
        )
        required_run(mapdl, "/PSEARCH,OFF")
        mapdl.resume(str(staged_model.with_suffix("")), "db")
        required_run(mapdl, "/PSEARCH,OFF")
        clear_ansys_abbreviations(mapdl)
        required_run(mapdl, "USRCAL,NONE")
        required_run(mapdl, "FINISH")
        required_run(mapdl, "/PREP7")
        required_run(mapdl, "ALLSEL,ALL")
        required_run(mapdl, "CSYS,0")
        required_run(mapdl, "DSYS,0")
        volume_count = int(round(required_get(mapdl, "VOLU", 0, "COUNT")))
        required_run(mapdl, "VSUM")
        cad_volume = required_get(mapdl, "VOLU", 0, "VOLU")
        cad_centroid = tuple(
            required_get(mapdl, "VOLU", 0, "CENT", component)
            for component in ("X", "Y", "Z")
        )
        expected_cad_volume = math.pi * 36.0 * 72.0
        if volume_count < 1:
            log("ANSYS DB must retain at least one solid-model volume")
            return False
        if not close_enough(cad_volume, expected_cad_volume, rel=2.0e-6, abs_tol=0.02):
            log("ANSYS DB solid-model volume is not the exact d12 x L72 cylinder: %r" % cad_volume)
            return False
        if any(
            not close_enough(cad_centroid[index], (0.0, 36.0, 0.0)[index], rel=0.0, abs_tol=1.0e-5)
            for index in range(3)
        ):
            log("ANSYS DB solid-model centroid is not (0,36,0): %r" % (cad_centroid,))
            return False
        if int(round(required_get(mapdl, "ACTIVE", 0, "ANTY"))) != 0:
            log("ANSYS DB analysis type is not static")
            return False
        node_labels = [int(value) for value in mapdl.mesh.nnum]
        node_rows = [tuple(float(value) for value in row[:3]) for row in mapdl.mesh.nodes]
        coords = dict(zip(node_labels, node_rows))
        element_labels = [int(value) for value in mapdl.mesh.enum]
        if not coords or not element_labels:
            log("ANSYS mesh is empty")
            return False
        elements = {}
        auxiliary = {}
        auxiliary_type_ids = {}
        auxiliary_real_ids = {}
        solid_type_ids = set()
        solid_corner_nodes = set()
        material_ids = set()
        attached = set()
        edge_lengths = []
        face_owners = {}
        solid_neighbors = {}
        solid_corner_connectivity = set()
        total_volume = 0.0
        for element in element_labels:
            if required_get(mapdl, "ELEM", element, "ATTR", "LIVE") != 1.0:
                log("ANSYS contains an inactive solid element")
                return False
            type_id = int(round(required_get(mapdl, "ELEM", element, "ATTR", "TYPE")))
            material_id = int(round(required_get(mapdl, "ELEM", element, "ATTR", "MAT")))
            code = int(round(required_get(mapdl, "ETYP", type_id, "ATTR", "ENAM")))
            if code not in (21, 170, 174, 184, 185, 186, 187):
                log("ANSYS elements are not supported 3D mechanical solids")
                return False
            if code not in (21, 170, 174, 184) and material_id <= 0:
                log("ANSYS solid element has no material")
                return False
            count = {21: 1, 170: 1, 174: 8, 184: 2, 185: 8, 186: 20, 187: 10}[code]
            connectivity = tuple(
                int(round(required_get(mapdl, "ELEM", element, "NODE", position)))
                for position in range(1, count + 1)
            )
            if not ansys_connectivity_is_valid(code, connectivity, coords):
                log("ANSYS element connectivity is invalid")
                return False
            if code in (21, 170, 174, 184):
                auxiliary[element] = (code, connectivity)
                auxiliary_type_ids[element] = type_id
                auxiliary_real_ids[element] = int(round(required_get(mapdl, "ELEM", element, "ATTR", "REAL")))
                continue
            elements[element] = (code, connectivity)
            solid_type_ids.add(type_id)
            solid_neighbors[element] = set()
            corner_indices = ansys_corner_indices(code, connectivity)
            corner_nodes = tuple(connectivity[index] for index in corner_indices)
            solid_corner_nodes.update(corner_nodes)
            corner_key = frozenset(corner_nodes)
            if corner_key in solid_corner_connectivity:
                log("ANSYS mesh contains duplicate solid corner connectivity")
                return False
            solid_corner_connectivity.add(corner_key)
            material_ids.add(material_id)
            attached.update(connectivity)
            signed_jacobians = ansys_element_signed_jacobians(code, connectivity, coords)
            if signed_jacobians is None or any(
                not finite_number(value) for value in signed_jacobians
            ):
                log("ANSYS solid element signed Jacobian is unreadable")
                return False
            corner_points = [coords[node] for node in corner_nodes]
            edge_scale = max(
                math.sqrt(sum((left[i] - right[i]) ** 2 for i in range(3)))
                for index, left in enumerate(corner_points)
                for right in corner_points[index + 1:]
            )
            orientation_tolerance = 1.0e-12 * max(1.0, edge_scale ** 3)
            jacobian_signs = set(
                1 if value > orientation_tolerance else -1 if value < -orientation_tolerance else 0
                for value in signed_jacobians
            )
            if 0 in jacobian_signs or len(jacobian_signs) != 1:
                log("ANSYS solid element has a folded or zero sampled Jacobian")
                return False
            volume = ansys_element_volume(code, connectivity, coords)
            if volume <= 1.0e-9:
                log("ANSYS contains a zero-volume solid")
                return False
            total_volume += volume
            topology = ansys_element_topology(code, connectivity)
            if topology is None:
                log("ANSYS solid topology is unsupported")
                return False
            for first, second in topology[1]:
                distance = math.sqrt(sum((coords[first][i] - coords[second][i]) ** 2 for i in range(3)))
                edge_lengths.append(distance)
            for corners, full_face in topology[0]:
                face_owners.setdefault(frozenset(corners), []).append((element, tuple(full_face)))
        if elements != rst_elements or auxiliary != rst_auxiliary:
            log("ANSYS DB and RST element types/connectivity do not match")
            return False
        edge_statistics = mesh_target_statistics(edge_lengths)
        if edge_statistics is None:
            log("ANSYS solid edge distribution is inconsistent with a 4 mm target")
            return False
        coordinate_mismatches = []
        if set(coords) == set(rst_coords):
            coordinate_mismatches = [
                (
                    node,
                    coords[node],
                    rst_coords[node],
                    max(abs(a - b) for a, b in zip(coords[node], rst_coords[node])),
                )
                for node in coords
                if any(
                    not close_enough(a, b, rel=1.0e-8, abs_tol=1.0e-8)
                    for a, b in zip(coords[node], rst_coords[node])
                )
            ]
        if set(coords) != set(rst_coords) or coordinate_mismatches:
            db_only = sorted(set(coords) - set(rst_coords))
            rst_only = sorted(set(rst_coords) - set(coords))
            log(
                "ANSYS DB and RST node coordinates do not match: labels=%d/%d "
                "db_only=%r rst_only=%r examples=%r"
                % (
                    len(coords),
                    len(rst_coords),
                    db_only[:12],
                    rst_only[:12],
                    coordinate_mismatches[:3],
                )
            )
            return False
        pilot_nodes = set(coords) - attached
        if len(pilot_nodes) != 1:
            log("ANSYS requires exactly one unmeshed pilot/reference node")
            return False
        pilot = next(iter(pilot_nodes))
        if any(abs(coords[pilot][i] - (0.0, 72.0, 0.0)[i]) > 1.0e-6 for i in range(3)):
            log("ANSYS pilot node is not at the Y=72 shaft center")
            return False
        solid_nodes = attached
        solid_rows = [coords[node] for node in solid_nodes]
        bounds = tuple((min(row[i] for row in solid_rows), max(row[i] for row in solid_rows)) for i in range(3))
        expected_bounds = ((-6.0, 6.0), (0.0, 72.0), (-6.0, 6.0))
        if any(
            not close_enough(actual[0], expected[0], rel=0.0, abs_tol=0.12)
            or not close_enough(actual[1], expected[1], rel=0.0, abs_tol=0.12)
            for actual, expected in zip(bounds, expected_bounds)
        ):
            log("ANSYS solid bounds are not the d12 x L72 global-Y shaft")
            return False
        if any(math.sqrt(coords[node][0] ** 2 + coords[node][2] ** 2) > 6.60 for node in solid_nodes):
            log("ANSYS solid node lies outside the radius-6 cylinder")
            return False
        expected_volume = math.pi * 36.0 * 72.0
        if not (0.84 * expected_volume < total_volume < 1.03 * expected_volume):
            log("ANSYS mesh does not fill the complete solid cylinder")
            return False
        if any(len(owners) not in (1, 2) for owners in face_owners.values()):
            log("ANSYS solid mesh contains a non-manifold face")
            return False
        for owners in face_owners.values():
            if len(owners) != 2:
                continue
            first, second = owners
            if frozenset(first[1]) != frozenset(second[1]):
                log("ANSYS quadratic mesh has a nonconforming shared midside face")
                return False
            solid_neighbors[first[0]].add(second[0])
            solid_neighbors[second[0]].add(first[0])
        pending = [next(iter(elements))] if elements else []
        reached = set()
        while pending:
            current = pending.pop()
            if current in reached:
                continue
            reached.add(current)
            pending.extend(solid_neighbors[current] - reached)
        if reached != set(elements):
            log("ANSYS shaft solid mesh is not one face-connected body")
            return False
        exterior = [owners[0][1] for owners in face_owners.values() if len(owners) == 1]
        fixed_nodes = set()
        free_nodes = set()
        lateral_faces = 0
        for face in exterior:
            points = [coords[node] for node in face]
            if all(abs(point[1]) <= 0.12 for point in points):
                fixed_nodes.update(face)
            elif all(abs(point[1] - 72.0) <= 0.12 for point in points):
                free_nodes.update(face)
            else:
                lateral_faces += 1
                if any(abs(math.sqrt(point[0] ** 2 + point[2] ** 2) - 6.0) > 0.60 for point in points):
                    log("ANSYS exterior face is not on an end or the radius-6 cylinder; hollow or wrong geometry")
                    return False
        if len(fixed_nodes) < 6 or len(free_nodes) < 6:
            log("ANSYS complete end faces cannot be identified")
            return False
        if lateral_faces < 10:
            log("ANSYS complete cylinder lateral surface cannot be identified")
            return False
        if any(not material_matches(mapdl, material_id) for material_id in material_ids):
            log("ANSYS material is not Steel E=210000 MPa, nu=0.3")
            return False
        for node in sorted(coords):
            angles = tuple(required_get(mapdl, "NODE", node, "ANG", component) for component in ("XY", "YZ", "ZX"))
            if any(abs(angle) > 1.0e-8 for angle in angles):
                log("ANSYS nodal coordinate systems are not global")
                return False
        constraints = parse_constraint_listing(required_run(mapdl, "DLIST,ALL"))
        actual_constraints = {}
        if constraints is None:
            log("ANSYS DLIST output is unreadable")
            return False
        for node, label, real, imag in constraints:
            if (
                node not in fixed_nodes
                or label not in ("UX", "UY", "UZ", "ROTX", "ROTY", "ROTZ")
                or abs(real) > 1.0e-12
                or abs(imag) > 1.0e-12
                or label in actual_constraints.get(node, set())
            ):
                log("ANSYS contains a non-Encastre displacement constraint: %r" % ((node, label, real, imag),))
                return False
            actual_constraints.setdefault(node, set()).add(label)
        if set(actual_constraints) != set(fixed_nodes) or any(
            labels != {"UX", "UY", "UZ"} for labels in actual_constraints.values()
        ):
            log("ANSYS constraints do not Encastre every complete Y=0 node")
            return False
        loads = parse_force_listing(required_run(mapdl, "FLIST,ALL"))
        if loads is None or loads != [(pilot, "MY", 920.0, 0.0)]:
            log("ANSYS load is not exactly pilot-node global MY=920 N*mm")
            return False
        for command, forbidden in (
            ("SFLIST,ALL", ("PRES",)),
            ("SFELIST,ALL", ("PRES",)),
            ("BFLIST,ALL", ("TEMP", "FORC")),
            ("BFELIST,ALL", ("TEMP", "FORC")),
        ):
            output = required_run(mapdl, command).upper()
            if any(token in output and "NO " not in output for token in forbidden):
                log("ANSYS contains an additional load category: %s" % command)
                return False
        export_stem = "task10_audit_" + token[:8]
        required_run(mapdl, "CDWRITE,DB,%s,cdb" % export_stem)
        export_path = audit_root / (export_stem + ".cdb")
        if not is_nonempty(export_path):
            log("ANSYS DB could not be exported for CE audit")
            return False
        export_text = export_path.read_text(encoding="utf-8", errors="ignore")
        cdb_type_records = cdb_element_type_records(export_text)
        if cdb_type_records is None:
            log("ANSYS CDB ETBLOCK is missing or malformed")
            return False
        if cdb_has_forbidden_task10_state(export_text) is not False:
            log("ANSYS CDB contains an extra load, temperature, damping, initial state, or layered section")
            return False
        if any(not cdb_material_is_constant_steel(export_text, material_id) for material_id in material_ids):
            log("ANSYS assigned material is not zero-temperature constant isotropic Steel")
            return False
        result_controls = cdb_task10_result_controls(export_text)
        if result_controls is None:
            log("ANSYS DB does not persist final NSOL, RSOL, STRS, and NAR result controls")
            return False
        nar_component = result_controls["NAR"]["component"]
        if nar_component:
            required_run(mapdl, "ALLSEL,ALL")
            required_run(mapdl, "CMSEL,S,%s,ELEM" % nar_component)
            nar_elements = set(int(value) for value in mapdl.mesh.enum)
            required_run(mapdl, "ALLSEL,ALL")
            if nar_elements != set(elements):
                log("ANSYS saved NAR component does not cover exactly every shaft solid element")
                return False
        for command, markers in (
            ("SFLIST,ALL", ("NO SURFACE LOADS TO LIST", "NO NODAL SURFACE LOADS TO LIST")),
            ("SFELIST,ALL", ("NO SURFACE LOADS TO LIST", "NO ELEMENT SURFACE LOADS TO LIST")),
            ("SFALIST,ALL", ("NO SURFACE LOADS ON AREAS TO LIST", "NO SURFACE LOADS TO LIST")),
            ("BFLIST,ALL", ("NO NODAL BODY FORCES TO LIST",)),
            ("BFELIST,ALL", ("NO ELEMENT BODY FORCES TO LIST",)),
            ("ICLIST,ALL", ("NO INITIAL CONDITIONS TO LIST",)),
        ):
            if not listing_confirms_empty(required_run(mapdl, command), markers):
                log("ANSYS contains an extra or unreadable load/state category: %s" % command)
                return False
        auxiliary_codes = set(value[0] for value in auxiliary.values())
        if auxiliary_codes in (set(), {21}):
            if auxiliary_codes == {21} and (
                len(auxiliary) != 1 or next(iter(auxiliary.values())) != (21, (pilot,))
            ):
                log("ANSYS MASS21 helper is not attached only to the pilot node")
                return False
            if cdb_has_any_command(export_text, ("CP",)) is not False or not listing_confirms_empty(
                required_run(mapdl, "CPLIST,ALL"), ("NO COUPLED SETS TO LIST",)
            ):
                log("ANSYS CERIG construction contains an additional CP constraint")
                return False
            if not audit_ansys_coupling(export_text, pilot, free_nodes, coords):
                log("ANSYS pilot constraint equations do not kinematically couple the complete Y=72 face")
                return False
            parsed_equations = cdb_constraint_equations(export_text)
            if parsed_equations is None or len(parsed_equations) != 3 * len(free_nodes):
                log("ANSYS CERIG CDB constraint-equation count is incomplete")
                return False
        elif auxiliary_codes == {170, 174}:
            target_elements = dict(
                (label, value) for label, value in auxiliary.items() if value[0] == 170
            )
            contact_elements = dict(
                (label, value) for label, value in auxiliary.items() if value[0] == 174
            )
            if len(target_elements) != 1 or not contact_elements:
                log("ANSYS CONTA174/TARGE170 rigid-surface MPC pair is incomplete")
                return False
            target_label, target_value = next(iter(target_elements.items()))
            if target_value[1] != (pilot,):
                log("ANSYS TARGE170 PILO element does not resolve to the unique loaded pilot")
                return False
            contact_nodes = set(
                node for code, connectivity in contact_elements.values() for node in connectivity
            )
            if contact_nodes != set(free_nodes):
                log("ANSYS CONTA174 surface does not cover exactly the complete Y=72 solid face")
                return False
            contact_reals = set(auxiliary_real_ids[label] for label in contact_elements)
            target_real = auxiliary_real_ids[target_label]
            if len(contact_reals) != 1 or target_real <= 0 or contact_reals != {target_real}:
                log("ANSYS CONTA174 and TARGE170 do not share exactly one positive real set")
                return False
            contact_types = set(auxiliary_type_ids[label] for label in contact_elements)
            target_types = {auxiliary_type_ids[target_label]}
            if any(
                cdb_type_records.get(type_id, (None,))[0] != 174
                or cdb_keyopt(cdb_type_records, type_id, 2) != 2
                or cdb_keyopt(cdb_type_records, type_id, 4) != 2
                or cdb_keyopt(cdb_type_records, type_id, 12) not in (5, 6)
                for type_id in contact_types
            ):
                log("ANSYS CONTA174 is not bonded rigid-surface MPC mode KEYOPT(2)=2, KEYOPT(4)=2, KEYOPT(12)=5/6")
                return False
            if any(
                cdb_type_records.get(type_id, (None,))[0] != 170
                or cdb_keyopt(cdb_type_records, type_id, 2) != 1
                or cdb_keyopt(cdb_type_records, type_id, 4) != 111111
                for type_id in target_types
            ):
                log("ANSYS TARGE170 is not a six-DOF one-node PILO target")
                return False
            if cdb_has_any_command(export_text, ("CE", "CP")) is not False:
                log("ANSYS contact MPC branch contains an additional CE or CP constraint")
                return False
            if not listing_confirms_empty(required_run(mapdl, "CELIST,ALL"), ("NO CONSTRAINT EQUATIONS TO LIST",)) or not listing_confirms_empty(
                required_run(mapdl, "CPLIST,ALL"), ("NO COUPLED SETS TO LIST",)
            ):
                log("ANSYS contact MPC branch contains an additional CE or CP constraint")
                return False
        elif auxiliary_codes == {184}:
            if cdb_has_any_command(export_text, ("CE", "CP")) is not False:
                log("ANSYS MPC184 spider contains additional CE or CP constraints")
                return False
            if not listing_confirms_empty(required_run(mapdl, "CELIST,ALL"), ("NO CONSTRAINT EQUATIONS TO LIST",)) or not listing_confirms_empty(
                required_run(mapdl, "CPLIST,ALL"), ("NO COUPLED SETS TO LIST",)
            ):
                log("ANSYS MPC184 spider DB contains additional CE or CP constraints")
                return False
            if not audit_ansys_mpc184_spider(auxiliary, pilot, free_nodes):
                log("ANSYS MPC184 rigid-beam spider does not cover the complete Y=72 face exactly once")
                return False
            type_ids = set(auxiliary_type_ids.values())
            if any(
                cdb_type_records.get(type_id, (None,))[0] != 184
                or cdb_keyopt(cdb_type_records, type_id, 1) != 1
                or cdb_keyopt(cdb_type_records, type_id, 2) != 0
                for type_id in type_ids
            ):
                log("ANSYS MPC184 spider is not a direct-elimination six-DOF rigid beam")
                return False
        else:
            log("ANSYS coupling helper elements are not a supported CERIG, CONTA174/TARGE170 MPC, or MPC184 implementation")
            return False
        required_run(mapdl, "FINISH")
        required_run(mapdl, "/SOLU")
        solution_status = required_run(mapdl, "/STATUS,SOLU")
        nlgeom_state = ansys_nlgeom_state(solution_status)
        if nlgeom_state is None:
            log("ANSYS saved NLGEOM state is unreadable: %r" % solution_status[-2400:])
            return False
        if nlgeom_state:
            log("Task-10 requires static small-deflection coupling with NLGEOM=OFF")
            return False
        required_run(mapdl, "FINISH")
        required_run(mapdl, "/CLEAR,NOSTART")
        required_run(mapdl, "/POST1")
        mapdl.file(str(staged_result.with_suffix("")), "rst")
        submitted_set_listing = required_run(mapdl, "SET,LIST")
        sets = parse_result_sets(submitted_set_listing)
        if not valid_result_set_index(sets) or len(sets) != rst_count:
            log("ANSYS RST result-set index is invalid: %r" % submitted_set_listing[-3000:])
            return False
        if len(rst_times) != len(sets) or any(
            not close_enough(rst_times[index], row["time"], rel=1.0e-9, abs_tol=1.0e-12)
            for index, row in enumerate(sets)
        ):
            log("ANSYS RST binary and SET,LIST time indices do not agree")
            return False
        mapdl.set("LAST")
        if int(round(required_get(mapdl, "ACTIVE", 0, "ANTY"))) != 0:
            log("ANSYS RST is not a static analysis")
            return False
        if not close_enough(sets[-1]["time"], 1.0, rel=0.0, abs_tol=1.0e-10):
            log("ANSYS submitted RST final result time is not 1.0")
            return False
        submitted = ansys_result_signature(
            mapdl,
            coords,
            solid_nodes,
            solid_corner_nodes,
            solid_type_ids,
            fixed_nodes,
            pilot,
            audit_root / "task10_nar_signature.txt",
        )
        if submitted is None:
            log("ANSYS RST lacks valid ROTY/S/RF torque response")
            return False
        for name in METRIC_FIELDS:
            tolerance = 2.0e-7 if name == "twist_angle" else 2.0e-5
            if not close_enough(submitted["metrics"][name], submitted_metrics[name], rel=2.0e-5, abs_tol=tolerance):
                log("metrics.json %s does not match native RST" % name)
                return False
        audit_names = regular_directory_names(audit_root)
        expected_audit_names = expected_ansys_audit_names(jobname, export_stem)
        if audit_names != expected_audit_names:
            raise RuntimeError(
                "ANSYS audit root inventory is not the learned clean v261 set: "
                "actual=%r expected=%r" % (audit_names, expected_audit_names)
            )
        required_run(mapdl, "FINISH")
        if not bounded_mapdl_exit(mapdl):
            raise RuntimeError("ANSYS audit MAPDL session did not exit within the deadline")
        mapdl = None
        batch_status, rechecked_path, rechecked_identity = run_ansys_batch_resolve(
            solve_model,
            solve_root,
            solve_jobname,
            require_convergence=nlgeom_state,
            baseline=baseline,
            owned_history=owned_history,
            solid_type_ids=solid_type_ids,
        )
        if not is_nonempty(rechecked_path):
            log("ANSYS isolated DB re-solve did not create an RST")
            return False
        post_started_ns = time.time_ns()
        shutil.copyfile(str(rechecked_path), str(post_result))
        post_identity = stable_fresh_file(post_result, post_started_ns)
        if (
            post_identity is None
            or post_identity["sha256"] != rechecked_identity["sha256"]
            or not exact_regular_files(post_root, (post_result.name,))
        ):
            log("ANSYS fresh RST could not be isolated in the postprocessing root")
            return False
        re_coords, re_elements, re_auxiliary, re_count, re_times, re_ens = read_ansys_rst(post_result)
        if (
            re_coords != rst_coords
            or re_elements != rst_elements
            or re_auxiliary != rst_auxiliary
            or re_count != len(re_times)
            or not re_times
            or any(
                not finite_number(value)
                or (index and value <= re_times[index - 1])
                for index, value in enumerate(re_times)
            )
        ):
            log("ANSYS isolated re-solve mesh or result metadata is invalid")
            return False
        final_set = sets[-1]
        re_final_set = None
        if batch_status is None:
            log("ANSYS isolated batch status is missing")
            return False
        # The independent solve may choose a different legal substep history;
        # its completion must agree with the final set in its own RST.
        re_final_set = {
            "set": re_count,
            "load_step": 1,
            "substep": None,
            "time": re_times[-1],
        }
        if (
            batch_status["set"] != re_final_set["set"]
            or batch_status["load_step"] != re_final_set["load_step"]
            or not close_enough(batch_status["time"], 1.0, rel=0.0, abs_tol=1.0e-10)
            or not close_enough(batch_status["time"], re_final_set["time"], rel=1.0e-9, abs_tol=1.0e-12)
        ):
            log("ANSYS isolated batch did not reach its own final result set")
            return False
        mapdl = launch_mapdl(
            exec_file=ANSYS_EXEC,
            jobname=post_jobname,
            run_location=str(post_root),
            nproc=1,
            override=True,
            cleanup_on_exit=True,
            additional_switches="-s noread",
            replace_env_vars=sanitized_ansys_environment(),
            start_timeout=180,
        )
        required_run(mapdl, "/CLEAR,NOSTART")
        required_run(mapdl, "/PSEARCH,OFF")
        required_run(mapdl, "/POST1")
        mapdl.file(str(post_result.with_suffix("")), "rst")
        rechecked_sets = parse_result_sets(required_run(mapdl, "SET,LIST"))
        if (
            not valid_result_set_index(rechecked_sets)
            or len(rechecked_sets) != re_count
            or any(
                not close_enough(row["time"], re_times[index], rel=1.0e-9, abs_tol=1.0e-12)
                for index, row in enumerate(rechecked_sets)
            )
        ):
            log("ANSYS isolated result-set metadata is invalid")
            return False
        mapdl.set("LAST")
        if not close_enough(rechecked_sets[-1]["time"], 1.0, rel=0.0, abs_tol=1.0e-10):
            log("ANSYS isolated RST final result time is not 1.0")
            return False
        rechecked = ansys_result_signature(
            mapdl,
            coords,
            solid_nodes,
            solid_corner_nodes,
            solid_type_ids,
            fixed_nodes,
            pilot,
            post_root / "task10_nar_signature.txt",
        )
        if (
            rechecked is None
            or not ansys_signature_matches(submitted["nodal"], rechecked["nodal"])
            or not reaction_matches(submitted["reactions"], rechecked["reactions"])
            or not ens_matches(rst_ens[-1], re_ens[-1])
        ):
            log("ANSYS submitted final RST fields do not match an isolated DB re-solve")
            return False
        for name in METRIC_FIELDS:
            tolerance = 2.0e-7 if name == "twist_angle" else 5.0e-4
            if not close_enough(submitted["metrics"][name], rechecked["metrics"][name], rel=5.0e-4, abs_tol=tolerance):
                log("ANSYS submitted RST %s does not match isolated DB re-solve" % name)
                return False
        if (
            original_hashes is None
            or (sha256(model_path), sha256(result_path)) != original_hashes
            or sha256(rechecked_path) != rechecked_identity["sha256"]
            or sha256(post_result) != post_identity["sha256"]
        ):
            log("submitted ANSYS artifacts changed during evaluation")
            return False
        post_names = regular_directory_names(post_root)
        expected_post_names = expected_ansys_post_names(post_jobname)
        if post_names != expected_post_names:
            raise RuntimeError(
                "ANSYS post root inventory is not the learned clean v261 set: "
                "actual=%r expected=%r" % (post_names, expected_post_names)
            )
        semantic_ok = True
    except Exception as exc:
        log("ANSYS evaluator failed: %s" % exc)
        semantic_ok = False
    finally:
        if mapdl is not None:
            bounded_mapdl_exit(mapdl)
        if tracker is not None:
            time.sleep(2.0)
        if tracker_stop is not None:
            tracker_stop.set()
        if tracker is not None:
            tracker.join(timeout=6.0)
        if baseline is not None:
            try:
                process_ok = restore_process_baseline(
                    baseline,
                    ANSYS_PROCESS_PATTERN,
                    (
                        token,
                        str(audit_root),
                        str(solve_root),
                        str(post_root),
                        jobname,
                        solve_jobname,
                        post_jobname,
                    ),
                    owned_history.values(),
                )
            except Exception as exc:
                log("ANSYS process cleanup failed: %s" % exc)
        else:
            log("ANSYS process cleanup skipped because no baseline was captured")
        temp_results = [remove_tree(path) for path in (audit_root, solve_root, post_root)]
        temp_ok = all(temp_results)
        if not temp_ok:
            log("ANSYS temporary directory cleanup was incomplete")
        if ansys_temp_before is not None:
            ansys_temp_ok = restore_ansys_temp_inventory(
                ansys_temp_before,
                (
                    token,
                    jobname,
                    solve_jobname,
                    post_jobname,
                    audit_root.name,
                    solve_root.name,
                    post_root.name,
                ),
                tuple(row.get("pid", 0) for row in owned_history.values()),
            )
        else:
            log("ANSYS .ansys cleanup skipped because no baseline was captured")
    return semantic_ok and process_ok and temp_ok and ansys_temp_ok


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
        log("evaluating Abaqus 2025 native torsion branch")
        return run_abaqus_checker(branch[1], branch[2], metrics), root
    log("evaluating ANSYS MAPDL 2026 R1 native torsion branch")
    return run_ansys_checker(branch[1], branch[2], metrics), root


def main():
    passed = False
    root = desktop_dir()
    try:
        passed, root = evaluate()
    except Exception as exc:
        log("unhandled evaluator failure: %s" % exc)
        passed = False
    write_text_result(root, passed)
    sys.stdout.write("True\n" if passed else "False\n")


if __name__ == "__main__":
    main()
