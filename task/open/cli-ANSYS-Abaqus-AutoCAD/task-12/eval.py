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


TASK_ID = "c-open-abaqus-ansys-autocad-task-12-windows"
METRIC_FIELDS = ("center_deflection", "max_stress")
ABAQUS_COMMAND = r"C:\SIMULIA\Commands\abaqus.bat"
ANSYS_EXEC = r"C:\Program Files\ANSYS Inc\v261\ansys\bin\winx64\ANSYS261.exe"
POWERSHELL = r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
DESKTOP_CANDIDATES = (
    Path(os.environ.get("USERPROFILE", r"C:\Users\user")) / "Desktop",
    Path(r"C:\Users\user\Desktop"),
    Path(r"C:\Users\User\Desktop"),
)
NATIVE_SUFFIXES = {
    ".cae", ".odb", ".db", ".rst", ".rth", ".wbpj", ".wbpz",
    ".mechdb", ".agdb", ".sim", ".fil",
}
DETAILS = []
ANSYS_PROCESS_PATTERN = (
    r"^(ANSYS(261)?|ansyscl|mpiexec|hydra_service|hydra_bstrap_proxy|hydra_pmi_proxy)\.exe$"
)
ABAQUS_PROCESS_PATTERN = (
    r"^(cmd|SMA[^.]*|ABQ[^.]*|pre|standard|package|explicit|"
    r"python|pythonw|mpiexec|hydra_service|hydra_bstrap_proxy|hydra_pmi_proxy)\.exe$"
)
ANSYS_TEMP_ROOT = Path(os.environ.get("LOCALAPPDATA", r"C:\Users\user\AppData\Local")) / "Temp" / ".ansys"
ANSYS_UNTRUSTED_ENVIRONMENT_KEYS = (
    "ANS_USE_UPF",
    "ANS_USER_PATH",
    "ANS_USER_PATH_261",
    "ANSYS_MACROLIB",
    "PYTHONPATH",
    "PYTHONHOME",
)
ABAQUS_UNTRUSTED_ENVIRONMENT_KEYS = (
    "PYTHONBREAKPOINT",
    "PYTHONCASEOK",
    "PYTHONDEBUG",
    "PYTHONEXECUTABLE",
    "PYTHONHOME",
    "PYTHONINSPECT",
    "PYTHONPATH",
    "PYTHONSTARTUP",
    "PYTHONUSERBASE",
    "PYTHONVERBOSE",
    "PYTHONWARNINGS",
)
ANSYS_AUDIT_ABBREVIATIONS = (
    "ALLSEL", "ANTYPE", "AVPRIN", "CDWRITE", "CSYS", "DSYS", "ESEL",
    "EQSLV", "FILE", "FINISH", "FSUM", "NLGEOM", "NSEL", "NSLE",
    "NSORT", "OUTRES", "PRNSOL", "RESUME", "RSYS", "SET", "SOLVE",
    "USRCAL",
)


def log(message):
    DETAILS.append(str(message))


def desktop_dir():
    for path in DESKTOP_CANDIDATES:
        if path.is_dir():
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


def close_enough(actual, expected, rel=2.0e-5, abs_tol=1.0e-8):
    try:
        return math.isclose(float(actual), float(expected), rel_tol=rel, abs_tol=abs_tol)
    except Exception:
        return False


def median(values):
    ordered = sorted(float(value) for value in values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return 0.5 * (ordered[middle - 1] + ordered[middle])


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def isolated_runtime():
    flags = sys.flags
    return bool(
        getattr(flags, "isolated", 0)
        and getattr(flags, "no_user_site", 0)
        and getattr(flags, "safe_path", 0)
    )


def remove_tree(path):
    for _ in range(40):
        try:
            if path.exists():
                shutil.rmtree(str(path))
            return not path.exists()
        except Exception:
            time.sleep(0.25)
    return False


def sanitized_ansys_environment():
    environment = os.environ.copy()
    for key in ANSYS_UNTRUSTED_ENVIRONMENT_KEYS:
        environment.pop(key, None)
    return environment


def sanitized_abaqus_environment(runtime_root):
    environment = os.environ.copy()
    for key in tuple(environment):
        if key.upper().startswith("PYTHON"):
            environment.pop(key, None)
    for key in ABAQUS_UNTRUSTED_ENVIRONMENT_KEYS:
        environment.pop(key, None)
    profile = runtime_root / "profile"
    roaming = profile / "AppData" / "Roaming"
    local = profile / "AppData" / "Local"
    temporary = runtime_root / "temp"
    for path in (profile, roaming, local, temporary):
        path.mkdir(parents=True, exist_ok=True)
    profile_text = str(profile)
    drive = profile.drive or os.path.splitdrive(profile_text)[0]
    home_path = profile_text[len(drive):] if drive else profile_text
    environment.update({
        "HOME": profile_text,
        "USERPROFILE": profile_text,
        "HOMEDRIVE": drive,
        "HOMEPATH": home_path,
        "APPDATA": str(roaming),
        "LOCALAPPDATA": str(local),
        "TEMP": str(temporary),
        "TMP": str(temporary),
        "PYTHONNOUSERSITE": "1",
        "PYTHONSAFEPATH": "1",
    })
    return environment


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
    return sorted(({
        "pid": int(row["ProcessId"]),
        "parent_pid": int(row.get("ParentProcessId") or 0),
        "name": str(row.get("Name") or ""),
        "command_line": str(row.get("CommandLine") or ""),
        "creation_date": str(row.get("CreationDate") or ""),
    } for row in payload), key=lambda row: row["pid"])


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
        row["pid"], row["parent_pid"], row["creation_date"],
        row["name"], row["command_line"],
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
            update_owned_process_history(
                history, before, current, markers, seed_pids=seed_pids
            )
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
    deadline = time.monotonic() + 20.0
    while time.monotonic() < deadline:
        current = windows_processes(pattern, timeout=5.0)
        current_identities = set(process_identity(row) for row in current)
        owned = update_owned_process_history(history, before, current, markers)
        for row in sorted(owned, key=lambda value: value["pid"], reverse=True):
            terminate_matching_identity(row, pattern)
        if not owned and current_identities == baseline:
            return True
        time.sleep(0.25)
    return windows_processes(pattern, timeout=5.0) == before


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
        for pid in owned_pids if int(pid) > 0
    )


def restore_ansys_temp_inventory(before, markers=(), owned_pids=()):
    if before is None:
        log("ANSYS .ansys temporary cleanup refused without a captured baseline")
        return False
    try:
        current = ansys_temp_inventory()
        new_keys = sorted(set(current) - set(before), key=lambda value: value.count("/"), reverse=True)
        owned_keys = {
            key for key in new_keys
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


def read_metrics(root):
    path = root / "metrics.json"
    if not is_nonempty(path):
        log("metrics.json is missing")
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        log("metrics.json is invalid JSON: %s" % exc)
        return None
    if not isinstance(data, dict) or set(data) != set(METRIC_FIELDS):
        log("metrics.json must contain exactly center_deflection and max_stress")
        return None
    if any(not finite_number(data[name]) for name in METRIC_FIELDS):
        log("metrics.json values must be finite JSON numbers")
        return None
    metrics = dict((name, float(data[name])) for name in METRIC_FIELDS)
    if not (-0.8 <= metrics["center_deflection"] <= -0.1):
        log("center_deflection is outside the Task-12 signed physical range")
        return None
    if not (10.0 <= metrics["max_stress"] <= 1000.0):
        log("max_stress is outside the Task-12 physical range")
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
    extras = [path.name for path in native if path not in supported]
    if extras:
        log("unsupported or extra native solver payload present: %s" % extras)
        return None
    has_abaqus = bool(caes or odbs)
    has_ansys = bool(dbs or rsts)
    if has_abaqus and has_ansys:
        log("deliver exactly one solver branch")
        return None
    if has_abaqus:
        if len(caes) != 1 or len(odbs) != 1:
            log("Abaqus delivery requires exactly one CAE and one ODB")
            return None
        if caes[0].stem.lower() != odbs[0].stem.lower():
            log("Abaqus CAE and ODB stems do not match")
            return None
        if not is_nonempty(caes[0]) or not is_nonempty(odbs[0]):
            log("Abaqus artifact is empty")
            return None
        return "abaqus", caes[0], odbs[0]
    if has_ansys:
        if len(dbs) != 1 or len(rsts) != 1:
            log("ANSYS delivery requires exactly one DB and one RST")
            return None
        if dbs[0].stem.lower() != rsts[0].stem.lower():
            log("ANSYS DB and RST stems do not match")
            return None
        if not is_nonempty(dbs[0]) or not is_nonempty(rsts[0]):
            log("ANSYS artifact is empty")
            return None
        return "ansys", dbs[0], rsts[0]
    log("no supported native CAE/ODB or DB/RST pair found")
    return None


def write_results(root, passed):
    try:
        (root / "eval_detail.txt").write_text("\n".join(DETAILS) + "\n", encoding="utf-8")
        (root / "eval_result.txt").write_text("True\n" if passed else "False\n", encoding="utf-8")
    except Exception:
        pass


ABAQUS_CHECKER = r'''# -*- coding: utf-8 -*-
from __future__ import print_function

import builtins
import hashlib
import json
import math
import os
import re
import shutil
import traceback

from abaqus import *
from abaqusConstants import *
from caeModules import *
from odbAccess import openOdb

CAE_PATH = __CAE_PATH__
ODB_PATH = __ODB_PATH__
METRICS = __METRICS__
AUDIT_ROOT = __AUDIT_ROOT__
SOLVE_ROOT = __SOLVE_ROOT__
POST_ROOT = __POST_ROOT__
RESULT_PATH = __RESULT_PATH__
JOB_SUFFIX = __JOB_SUFFIX__
DETAILS = []


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


def close(actual, expected, rel=2.0e-5, absolute=1.0e-8):
    try:
        return math.isclose(float(actual), float(expected), rel_tol=rel, abs_tol=absolute)
    except Exception:
        return False


def median(values):
    ordered = sorted(float(value) for value in values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return 0.5 * (ordered[middle - 1] + ordered[middle])


def file_sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            digest.update(block)
    return digest.hexdigest()


def flatten(value, identity):
    rows = []
    pending = []
    try:
        pending.extend(list(value))
    except Exception:
        pending.append(value)
    seen = set()
    while pending:
        item = pending.pop()
        if hasattr(item, identity):
            marker = (ci(getattr(item, "instanceName", "")), getattr(item, identity))
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
    try:
        return flatten(entity.nodes, "label")
    except Exception:
        return []


def region_name(region):
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
        r"name\s*=\s*['\"]([^'\"]+)",
        r"setName\s*=\s*['\"]([^'\"]+)",
        r"surfaceName\s*=\s*['\"]([^'\"]+)['\"]",
    ):
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return None


def repo_ci(repository, name):
    try:
        for key in repository.keys():
            if ci(key) == ci(name):
                return repository[key]
    except Exception:
        pass
    return None


def resolve_region(model, instance, region):
    if entity_nodes(region):
        return region
    name = region_name(region)
    matches = []
    for owner in (model.rootAssembly, instance, getattr(instance, "part", None)):
        if owner is None:
            continue
        for repo_name in ("sets", "allSets", "surfaces", "allSurfaces"):
            value = repo_ci(getattr(owner, repo_name, {}), name)
            if value is not None:
                matches.append(value)
    signatures = set(frozenset(int(node.label) for node in entity_nodes(value)) for value in matches)
    if not matches or len(signatures) != 1:
        return fail("CAE analysis region cannot be resolved uniquely")
    return matches[0]


def state_component(state, name):
    value = getattr(state, name, None)
    marker = ci(getattr(state, name + "State", ""))
    if marker in ("UNSET", "FREED", "DEACTIVATED"):
        return None
    if value is None:
        return None
    if ci(value) == "SET":
        return 0.0
    try:
        return float(value)
    except Exception:
        return None


def components(state):
    result = []
    for name in ("u1", "u2"):
        result.append(state_component(state, name))
    return tuple(result)


def element_nodes(owner, element):
    try:
        return list(element.getNodes())
    except Exception:
        return [owner.nodes[int(index)] for index in element.connectivity]


def element_spec(element_type):
    upper = ci(element_type)
    if not re.match(r"^CAX(?:3|4|6|8)(?:R|RH|H)?$", upper):
        return None
    if upper.startswith("CAX3") or upper.startswith("CAX6"):
        count = 6 if upper.startswith("CAX6") else 3
        return count, 3, ((0, 1), (1, 2), (2, 0)), ((3, 0, 1), (4, 1, 2), (5, 2, 0)) if count == 6 else ()
    count = 8 if upper.startswith("CAX8") else 4
    return count, 4, ((0, 1), (1, 2), (2, 3), (3, 0)), ((4, 0, 1), (5, 1, 2), (6, 2, 3), (7, 3, 0)) if count == 8 else ()


def polygon_area(points):
    area = 0.0
    for index in range(len(points)):
        x1, y1 = points[index][:2]
        x2, y2 = points[(index + 1) % len(points)][:2]
        area += x1 * y2 - x2 * y1
    return abs(area) * 0.5


def mesh_topology(owner):
    result = {}
    for element in owner.elements:
        label = int(element.label)
        nodes = element_nodes(owner, element)
        if label in result:
            return None
        result[label] = (ci(element.type), tuple(int(node.label) for node in nodes))
    return result


def audit_mesh(part, instance):
    part_coords = dict((int(node.label), tuple(float(v) for v in node.coordinates) + (0.0,)) for node in part.nodes)
    part_coords = dict((key, value[:3]) for key, value in part_coords.items())
    instance_coords = dict((int(node.label), tuple(float(v) for v in node.coordinates) + (0.0,)) for node in instance.nodes)
    instance_coords = dict((key, value[:3]) for key, value in instance_coords.items())
    if not part_coords or set(part_coords) != set(instance_coords):
        return fail("CAE part/instance meshes are absent or label-incompatible")
    if any(any(not close(part_coords[label][axis], instance_coords[label][axis], rel=0.0, absolute=1.0e-9) for axis in range(3)) for label in part_coords):
        return fail("dependent instance coordinates differ from the saved part mesh")
    topology = mesh_topology(part)
    if not topology or topology != mesh_topology(instance):
        return fail("CAE part and instance element topology/types differ")
    rows = list(part_coords.values())
    bounds = ((min(v[0] for v in rows), max(v[0] for v in rows)), (min(v[1] for v in rows), max(v[1] for v in rows)), (min(v[2] for v in rows), max(v[2] for v in rows)))
    expected = ((0.0, 50.0), (0.0, 1.0), (0.0, 0.0))
    if any(not close(bounds[i][j], expected[i][j], rel=0.0, absolute=1.0e-7) for i in range(3) for j in range(2)):
        return fail("axisymmetric cross-section bounds are not X=0..50, Y=0..1 mm")
    try:
        seed = float(part.getPartSeeds(SIZE))
    except Exception:
        seed = None
    if seed is not None and seed > 0.0 and not close(seed, 2.0, rel=0.0, absolute=0.12):
        return fail("saved Abaqus global mesh seed is not approximately 2 mm")
    total_area = 0.0
    attached = set()
    radial_edges = []
    edge_owners = {}
    edge_full_nodes = {}
    edge_endpoints = {}
    for element in part.elements:
        spec = element_spec(element.type)
        nodes = element_nodes(part, element)
        if spec is None or len(nodes) != spec[0]:
            return fail("mesh contains a non-structural CAX continuum element: %s" % element.type)
        _, corners, edges, midsides = spec
        labels = tuple(int(node.label) for node in nodes)
        if len(set(labels)) != len(labels) or any(label not in part_coords for label in labels):
            return fail("CAX element connectivity is invalid")
        attached.update(labels)
        total_area += polygon_area([part_coords[label] for label in labels[:corners]])
        midside_by_edge = dict((frozenset((a, b)), middle) for middle, a, b in midsides)
        for a, b in edges:
            key = frozenset((labels[a], labels[b]))
            edge_owners.setdefault(key, []).append(int(element.label))
            full = {labels[a], labels[b]}
            middle = midside_by_edge.get(frozenset((a, b)))
            if middle is not None:
                full.add(labels[middle])
            edge_full_nodes.setdefault(key, []).append(frozenset(full))
            edge_endpoints.setdefault(key, (labels[a], labels[b]))
            dx = abs(part_coords[labels[a]][0] - part_coords[labels[b]][0])
            dy = abs(part_coords[labels[a]][1] - part_coords[labels[b]][1])
            if dx > 1.0e-8 and dy <= 1.0e-8:
                radial_edges.append(dx)
        for middle, a, b in midsides:
            midpoint = tuple((part_coords[labels[a]][axis] + part_coords[labels[b]][axis]) / 2.0 for axis in range(3))
            if any(abs(part_coords[labels[middle]][axis] - midpoint[axis]) > 1.0e-7 for axis in range(3)):
                return fail("quadratic CAX midside node is not at its edge midpoint")
    if attached != set(part_coords) or any(len(value) > 2 for value in edge_owners.values()):
        return fail("CAX mesh contains unattached nodes or non-manifold edges")
    if any(len(values) == 2 and values[0] != values[1] for values in edge_full_nodes.values()):
        return fail("adjacent quadratic CAX elements do not share the same midside node")
    boundary_lengths = {(0, 0.0): 0.0, (0, 50.0): 0.0, (1, 0.0): 0.0, (1, 1.0): 0.0}
    neighbors = dict((label, set()) for label in topology)
    for key, owners in edge_owners.items():
        if len(owners) == 2:
            neighbors[owners[0]].add(owners[1])
            neighbors[owners[1]].add(owners[0])
            continue
        a, b = edge_endpoints[key]
        planes = [(axis, value) for axis, value in boundary_lengths if abs(part_coords[a][axis] - value) <= 1.0e-7 and abs(part_coords[b][axis] - value) <= 1.0e-7]
        if len(planes) != 1:
            return fail("CAX mesh has an interior hole or off-domain exterior edge")
        boundary_lengths[planes[0]] += math.sqrt(builtins.sum((part_coords[a][axis] - part_coords[b][axis]) ** 2 for axis in range(2)))
    expected_lengths = {(0, 0.0): 1.0, (0, 50.0): 1.0, (1, 0.0): 50.0, (1, 1.0): 50.0}
    if any(not close(boundary_lengths[key], expected_lengths[key], rel=1.0e-6, absolute=0.01) for key in expected_lengths):
        return fail("CAX mesh exterior does not cover exactly the four rectangle boundaries")
    reached = set()
    pending = [next(iter(neighbors))]
    while pending:
        current = pending.pop()
        if current in reached:
            continue
        reached.add(current)
        pending.extend(neighbors[current] - reached)
    if reached != set(neighbors):
        return fail("CAX plate mesh is not one edge-connected cross-section")
    if not close(total_area, 50.0, rel=1.0e-6, absolute=0.01):
        return fail("CAX elements do not fill the complete 50 x 1 mm section")
    if not radial_edges:
        return fail("actual radial element spacing is unavailable")
    radial_median = median(radial_edges)
    representative_fraction = builtins.sum(
        1 for value in radial_edges if 1.25 <= value <= 2.75
    ) / float(len(radial_edges))
    if (
        min(radial_edges) < 0.1
        or max(radial_edges) > 4.0
        or not (1.5 <= radial_median <= 2.5)
        or representative_fraction < 0.6
    ):
        return fail(
            "actual radial element spacing is not representatively approximately 2 mm"
        )
    axis = set(label for label, xyz in part_coords.items() if abs(xyz[0]) <= 1.0e-7)
    outer = set(label for label, xyz in part_coords.items() if abs(xyz[0] - 50.0) <= 1.0e-7)
    top = set(label for label, xyz in part_coords.items() if abs(xyz[1] - 1.0) <= 1.0e-7)
    center = [label for label in axis & top]
    if len(axis) < 2 or len(outer) < 2 or len(top) < 20 or len(center) != 1:
        return fail("mesh does not expose complete axis, outer, top and center-top node sets")
    return {
        "coords": part_coords,
        "topology": topology,
        "axis": axis,
        "outer": outer,
        "top": top,
        "center": center[0],
        "area": total_area,
        "seed": seed,
        "radial_edge_median": radial_median,
        "radial_edge_representative_fraction": representative_fraction,
    }


def audit_material(model, part):
    valid = set()
    for name in model.materials.keys():
        material = model.materials[name]
        try:
            elastic = material.elastic
            table = elastic.table
        except Exception:
            continue
        if (
            ci(getattr(elastic, "type", "")) == "ISOTROPIC"
            and len(table) == 1
            and len(table[0]) == 2
            and close(table[0][0], 210000.0, rel=1.0e-6, absolute=1.0e-5)
            and close(table[0][1], 0.3, rel=1.0e-6, absolute=1.0e-8)
        ):
            valid.add(ci(name))
    if not valid:
        return fail("CAE lacks linear elastic steel E=210000 MPa, nu=0.3")
    assignments = list(part.sectionAssignments)
    if len(assignments) != 1:
        return fail("plate must have exactly one section assignment")
    section = repo_ci(model.sections, getattr(assignments[0], "sectionName", ""))
    if section is None or ci(getattr(section, "material", "")) not in valid:
        return fail("plate section is not bound to the specified steel")
    return {"materials": sorted(valid), "section": str(assignments[0].sectionName)}


def audit_process(model, instance, mesh):
    steps = [name for name in model.steps.keys() if ci(name) != "INITIAL"]
    if len(steps) != 1 or "STATIC" not in ci(model.steps[steps[0]].__class__.__name__):
        return fail("CAE must contain exactly one static analysis step")
    if bool(getattr(model.steps[steps[0]], "nlgeom", False)):
        return fail("static plate analysis must be linear (nlgeom off)")
    bc_rows = []
    for name in model.boundaryConditions.keys():
        bc = model.boundaryConditions[name]
        region = resolve_region(model, instance, getattr(bc, "region", None))
        if region is None:
            return None
        state = repo_ci(model.steps[steps[0]].boundaryConditionStates, name)
        if state is None or ci(getattr(state, "status", "")) in (
            "DEACTIVATED",
            "NOT_YET_ACTIVE",
        ):
            return fail("boundary condition is inactive in the analysis step")
        bc_rows.append(
            (
                frozenset(int(node.label) for node in entity_nodes(region)),
                components(state),
                name,
                bc.__class__.__name__,
                repr(getattr(state, "u1State", None)),
                repr(getattr(state, "u2State", None)),
            )
        )
    if len(bc_rows) != 2:
        return fail("CAE must contain exactly the axis symmetry BC and outer clamp BC")
    axis_rows = [row for row in bc_rows if row[0] == frozenset(mesh["axis"])]
    outer_rows = [row for row in bc_rows if row[0] == frozenset(mesh["outer"])]
    if len(axis_rows) != 1 or axis_rows[0][1] != (0.0, None):
        return fail(
            "axis X=0 must constrain radial U1 only; parsed BC rows=%r"
            % [
                (len(row[0]), row[1], row[2], row[3], row[4], row[5])
                for row in bc_rows
            ]
        )
    if len(outer_rows) != 1 or outer_rows[0][1] != (0.0, 0.0):
        return fail("outer X=50 edge must constrain U1=U2=0")
    if axis_rows[0] is outer_rows[0]:
        return fail("axis and outer constraints are not independent")
    loads = [model.loads[name] for name in model.loads.keys()]
    if len(loads) != 1 or "PRESSURE" not in ci(loads[0].__class__.__name__):
        return fail("CAE must contain exactly one pressure load")
    load = loads[0]
    if ci(getattr(load, "distributionType", "")) != "UNIFORM":
        return fail("pressure distributionType must be UNIFORM")
    field = getattr(load, "field", None)
    if field is not None and ci(field) not in ("", "NONE", "UNSET"):
        return fail("uniform pressure must not reference a field")
    load_state = repo_ci(model.steps[steps[0]].loadStates, getattr(load, "name", ""))
    if load_state is None or ci(getattr(load_state, "status", "")) in (
        "DEACTIVATED",
        "NOT_YET_ACTIVE",
    ):
        return fail("pressure is inactive in the analysis step")
    if ci(getattr(load_state, "magnitudeState", "")) in ("UNSET", "FREED") or not close(
        getattr(load_state, "magnitude", None),
        0.1,
        rel=1.0e-7,
        absolute=1.0e-9,
    ):
        return fail("top pressure magnitude is not 0.1 MPa")
    surface = resolve_region(model, instance, getattr(load, "region", None))
    surface_nodes = set(int(node.label) for node in entity_nodes(surface)) if surface is not None else set()
    if surface_nodes != mesh["top"]:
        return fail("pressure surface is not the complete Y=1 edge")
    if model.interactions.keys() or model.constraints.keys() or model.predefinedFields.keys():
        return fail("CAE contains substitute interactions, constraints, or predefined fields")
    return {
        "step": steps[0],
        "pressure": 0.1,
        "bc_count": 2,
    }


def odb_mesh(odb):
    populated = []
    for name in odb.rootAssembly.instances.keys():
        instance = odb.rootAssembly.instances[name]
        if len(instance.nodes) or len(instance.elements):
            populated.append((ci(name), instance))
    if len(populated) != 1:
        return fail("ODB must contain exactly one populated instance")
    name, instance = populated[0]
    coords = dict((int(node.label), (tuple(float(v) for v in node.coordinates) + (0.0,))[:3]) for node in instance.nodes)
    topology = dict((int(element.label), (ci(element.type), tuple(int(v) for v in element.connectivity))) for element in instance.elements)
    return name, coords, topology


def value_data(value):
    try:
        data = value.data
    except Exception:
        try:
            data = value.dataDouble
        except Exception:
            return ()
    try:
        return tuple(float(v) for v in data)
    except Exception:
        try:
            return (float(data),)
        except Exception:
            return ()


def integer_or(value, default):
    try:
        return int(value)
    except Exception:
        return default


def field_signature(field):
    rows = []
    for value in field.values:
        data = value_data(value)
        if not data or any(not finite(v) for v in data):
            return None
        rows.append(
            (
                ci(getattr(getattr(value, "instance", None), "name", "")),
                integer_or(getattr(value, "nodeLabel", None), -1),
                integer_or(getattr(value, "elementLabel", None), -1),
                ci(getattr(value, "position", "")),
                integer_or(getattr(value, "integrationPoint", None), 0),
                data,
            )
        )
    return tuple(sorted(rows))


def odb_result(path, expected_coords, expected_topology, center_label, outer_labels):
    odb = openOdb(path=path, readOnly=True)
    try:
        status = ci(getattr(odb.diagnosticData, "jobStatus", ""))
        if status and "COMPLETED" not in status:
            return fail("ODB job status is not completed")
        if len(odb.steps.keys()) != 1:
            return fail("ODB must contain exactly one analysis step")
        step = odb.steps[odb.steps.keys()[0]]
        if not step.frames or float(step.frames[-1].frameValue) <= 0.0:
            return fail("ODB lacks a completed positive-time result frame")
        instance_name, coords, topology = odb_mesh(odb)
        if set(coords) != set(expected_coords) or topology != expected_topology:
            return fail("CAE and ODB node labels or CAX topology/types differ")
        if any(any(not close(coords[label][axis], expected_coords[label][axis], rel=0.0, absolute=1.0e-9) for axis in range(3)) for label in coords):
            return fail("CAE and ODB node coordinates differ")
        frame = step.frames[-1]
        if any(name not in frame.fieldOutputs.keys() for name in ("U", "S", "RF")):
            return fail("ODB final frame lacks U, S or RF")
        u_sig = field_signature(frame.fieldOutputs["U"])
        s_sig = field_signature(frame.fieldOutputs["S"])
        if not u_sig or not s_sig:
            return fail("ODB U/S output contains missing or non-finite data")
        center_values = [value for value in frame.fieldOutputs["U"].values if ci(getattr(getattr(value, "instance", None), "name", "")) == instance_name and int(getattr(value, "nodeLabel", -1)) == int(center_label)]
        if len(center_values) != 1 or len(value_data(center_values[0])) < 2:
            return fail("ODB has no unique center-top displacement")
        center = value_data(center_values[0])[1]
        if not (-0.8 <= center <= -0.1):
            return fail("center-top U2 has the wrong sign or implausible magnitude")
        mises = []
        covered = set()
        for value in frame.fieldOutputs["S"].values:
            if ci(getattr(getattr(value, "instance", None), "name", "")) != instance_name or "INTEGRATION_POINT" not in ci(getattr(value, "position", "")):
                continue
            try:
                candidate = float(value.mises)
            except Exception:
                continue
            if finite(candidate):
                mises.append(candidate)
                covered.add(int(value.elementLabel))
        if not mises or covered != set(expected_topology):
            return fail("integration-point Mises stress does not cover every CAX element")
        maximum = max(mises)
        if not (20.0 <= maximum <= 400.0):
            return fail("maximum integration-point Mises stress is implausible")
        rf = [value for value in frame.fieldOutputs["RF"].values if ci(getattr(getattr(value, "instance", None), "name", "")) == instance_name and int(getattr(value, "nodeLabel", -1)) in outer_labels]
        if len(rf) != len(outer_labels):
            return fail("outer-edge reaction field is incomplete")
        reaction_y = builtins.sum(value_data(value)[1] for value in rf)
        expected_reaction = math.pi * 50.0 * 50.0 * 0.1
        if not close(reaction_y, expected_reaction, rel=3.0e-3, absolute=1.5):
            return fail("outer reaction does not balance the top pressure resultant")
        return {"metrics": {"center_deflection": center, "max_stress": maximum}, "signature": {"u": u_sig, "s": s_sig}, "reaction_y": reaction_y}
    finally:
        odb.close()


def signatures_match(left, right):
    for field in ("u", "s"):
        a = left[field]
        b = right[field]
        if len(a) != len(b):
            return False
        for row_a, row_b in zip(a, b):
            if row_a[:-1] != row_b[:-1] or len(row_a[-1]) != len(row_b[-1]):
                return False
            if any(not close(x, y, rel=7.0e-4, absolute=2.0e-7) for x, y in zip(row_a[-1], row_b[-1])):
                return False
    return True


def input_keyword(line):
    fields = [field.strip() for field in line.strip()[1:].split(",")]
    name = fields[0].upper()
    parameters = {}
    flags = set()
    for field in fields[1:]:
        if not field:
            continue
        if "=" in field:
            key, value = field.split("=", 1)
            parameters[key.strip().upper()] = value.strip().upper()
        else:
            flags.add(field.upper())
    return name, parameters, flags


def audit_canonical_dsload(deck):
    dsload_blocks = []
    current = None
    forbidden_load_keywords = {
        "CLOAD", "DLOAD", "DLOAD FILE", "DSFLUX", "DFLUX",
        "BODY FORCE", "GRAVITY", "CENTRIF", "CONNECTOR LOAD",
    }
    for raw in deck.splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("**"):
            continue
        if stripped.startswith("*"):
            name, parameters, flags = input_keyword(stripped)
            current = None
            if name == "DISTRIBUTION" or name.startswith("DISTRIBUTION "):
                return fail("fresh input contains a DISTRIBUTION definition")
            if name in forbidden_load_keywords:
                return fail("fresh input contains an additional load keyword: *%s" % name)
            if name == "DSLOAD":
                unknown = set(parameters) - {"OP", "AMPLITUDE"}
                operation = parameters.get("OP")
                amplitude = parameters.get("AMPLITUDE")
                if (
                    flags
                    or unknown
                    or (operation is not None and operation not in ("NEW", "MOD"))
                    or ("AMPLITUDE" in parameters and not amplitude)
                ):
                    return fail(
                        "canonical *DSLOAD contains USER, DISTRIBUTION, or an unsupported parameter"
                    )
                current = []
                dsload_blocks.append(
                    {
                        "rows": current,
                        "op": operation,
                        "amplitude": amplitude,
                    }
                )
            continue
        if current is not None:
            current.append(stripped)
    if len(dsload_blocks) != 1 or len(dsload_blocks[0]["rows"]) != 1:
        return fail("fresh input must contain exactly one single-row *DSLOAD block")
    block = dsload_blocks[0]
    fields = [field.strip() for field in block["rows"][0].split(",")]
    if len(fields) != 3 or not fields[0] or fields[1].upper() != "P":
        return fail("fresh input *DSLOAD must contain one canonical surface, P, magnitude row")
    try:
        magnitude = float(fields[2].replace("D", "E").replace("d", "e"))
    except Exception:
        return fail("fresh input *DSLOAD pressure magnitude is not numeric")
    if not close(magnitude, 0.1, rel=1.0e-7, absolute=1.0e-9):
        return fail("fresh input *DSLOAD pressure magnitude is not 0.1 MPa")
    return {
        "surface": fields[0],
        "load_type": "P",
        "magnitude": magnitude,
        "op": block["op"],
        "amplitude": block["amplitude"],
    }


def main():
    ok = False
    report = {}
    try:
        openMdb(pathName=CAE_PATH)
        populated = []
        for name in mdb.models.keys():
            model = mdb.models[name]
            parts = [model.parts[key] for key in model.parts.keys() if len(model.parts[key].elements)]
            instances = [model.rootAssembly.instances[key] for key in model.rootAssembly.instances.keys() if len(model.rootAssembly.instances[key].elements)]
            if parts or instances:
                populated.append((name, model, parts, instances))
        if len(populated) != 1:
            raise RuntimeError("CAE must contain exactly one populated analysis model")
        model_name, model, parts, instances = populated[0]
        if len(parts) != 1 or len(instances) != 1:
            raise RuntimeError("analysis model must contain one meshed cross-section part and one instance")
        if bool(getattr(model.keywordBlock, "edited", False)):
            raise RuntimeError("CAE keywordBlock contains manual edits")
        part = parts[0]
        instance = instances[0]
        # Restored Abaqus 2025 Part objects do not expose a stable readable
        # dimensionality/modelingSpace member. Axisymmetry is enforced below
        # from every active CAX element, the CAE/ODB topology, and the fresh
        # *ELEMENT, TYPE=CAX input deck.
        if getattr(part, "type", None) != DEFORMABLE_BODY:
            raise RuntimeError(
                "part is not deformable: type=%r expected_type=%r"
                % (
                    getattr(part, "type", None),
                    DEFORMABLE_BODY,
                )
            )
        mesh = audit_mesh(part, instance)
        material = audit_material(model, part)
        process = audit_process(model, instance, mesh) if mesh else None
        if not mesh or not material or not process:
            raise RuntimeError("CAE Task-12 semantics failed")
        submitted = odb_result(ODB_PATH, mesh["coords"], mesh["topology"], mesh["center"], mesh["outer"])
        if not submitted:
            raise RuntimeError("submitted ODB audit failed")
        for name in ("center_deflection", "max_stress"):
            tolerance = 2.0e-7 if name == "center_deflection" else 2.0e-5
            if not close(submitted["metrics"][name], METRICS[name], rel=2.0e-5, absolute=tolerance):
                raise RuntimeError("metrics.json %s does not match submitted ODB" % name)
        os.chdir(AUDIT_ROOT)
        source_job_name = "Task12-Eval-Source-" + JOB_SUFFIX
        if source_job_name in mdb.jobs.keys():
            del mdb.jobs[source_job_name]
        source_job = mdb.Job(name=source_job_name, model=model_name, numCpus=1, numDomains=1, scratch=AUDIT_ROOT)
        source_job.writeInput(consistencyChecking=ON)
        input_path = os.path.join(AUDIT_ROOT, source_job_name + ".inp")
        if not os.path.isfile(input_path) or os.path.getsize(input_path) <= 0:
            raise RuntimeError("CAE could not generate a fresh input deck")
        with open(input_path, "r") as stream:
            deck = stream.read().upper()
        required = ("*ELEMENT, TYPE=CAX", "*ELASTIC", "*SOLID SECTION", "*STATIC", "*BOUNDARY")
        forbidden = ("*PLASTIC", "*HYPERELASTIC", "*VISCOELASTIC", "*CREEP", "*DAMAGE", "*GRAVITY", "*CONTACT", "*COUPLING", "*INITIAL CONDITIONS")
        if any(token not in deck for token in required) or any(token in deck for token in forbidden):
            raise RuntimeError("fresh CAE input deck lacks required Task-12 records or contains substitutes")
        dsload = audit_canonical_dsload(deck)
        if not dsload:
            raise RuntimeError("fresh CAE input pressure audit failed")
        if (
            dsload.get("amplitude") is not None
            and repo_ci(model.amplitudes, dsload["amplitude"]) is None
        ):
            raise RuntimeError(
                "fresh input pressure amplitude is absent from the saved CAE amplitude repository"
            )
        input_hash = file_sha256(input_path)
        frozen_path = os.path.join(SOLVE_ROOT, "task12_frozen.inp")
        shutil.copyfile(input_path, frozen_path)
        if file_sha256(frozen_path) != input_hash:
            raise RuntimeError("frozen input differs from audited CAE input")
        os.chdir(SOLVE_ROOT)
        recheck_name = "Task12-Eval-Recheck-" + JOB_SUFFIX
        recheck_job = mdb.JobFromInputFile(name=recheck_name, inputFileName=frozen_path, numCpus=1, numDomains=1, scratch=SOLVE_ROOT)
        recheck_job.submit(consistencyChecking=ON)
        recheck_job.waitForCompletion()
        fresh_odb = os.path.join(SOLVE_ROOT, recheck_name + ".odb")
        if not os.path.isfile(fresh_odb) or os.path.getsize(fresh_odb) <= 0:
            raise RuntimeError("isolated fresh Abaqus solve did not produce an ODB")
        post_odb = os.path.join(POST_ROOT, "recomputed.odb")
        shutil.copyfile(fresh_odb, post_odb)
        recomputed = odb_result(post_odb, mesh["coords"], mesh["topology"], mesh["center"], mesh["outer"])
        if not recomputed or not signatures_match(submitted["signature"], recomputed["signature"]):
            raise RuntimeError("submitted ODB U/S fields differ from isolated CAE re-solve")
        for name in ("center_deflection", "max_stress"):
            tolerance = 3.0e-7 if name == "center_deflection" else 6.0e-4
            if not close(submitted["metrics"][name], recomputed["metrics"][name], rel=7.0e-4, absolute=tolerance):
                raise RuntimeError("submitted ODB metric differs from isolated CAE re-solve")
        if file_sha256(input_path) != input_hash or file_sha256(frozen_path) != input_hash:
            raise RuntimeError("audited Abaqus input changed during evaluation")
        report = {"mesh_area": mesh["area"], "mesh_seed": mesh["seed"], "radial_edge_median": mesh["radial_edge_median"], "radial_edge_representative_fraction": mesh["radial_edge_representative_fraction"], "material": material, "process": process, "dsload": dsload, "native_metrics": submitted["metrics"], "recomputed_metrics": recomputed["metrics"], "input_sha256": input_hash}
        ok = True
    except Exception:
        DETAILS.append(traceback.format_exc())
    try:
        with open(RESULT_PATH, "w") as stream:
            json.dump({"passed": ok, "details": DETAILS, "report": report}, stream, indent=2, sort_keys=True)
    except Exception:
        pass
    print("True" if ok else "False")


if __name__ == "__main__":
    main()
'''


def run_abaqus_checker(cae_path, odb_path, metrics):
    token = uuid.uuid4().hex
    control_root = None
    audit_root = None
    submitted_root = None
    solve_root = None
    post_root = None
    audit_job_name = "Task12-Eval-Source-" + token[:12]
    recheck_job_name = "Task12-Eval-Recheck-" + token[:12]
    markers = (token, audit_job_name, recheck_job_name)
    baseline = None
    owned_history = {}
    tracker_stop = None
    tracker = None
    tracker_seed_pids = []
    process = None
    semantic_ok = False
    process_ok = False
    tracker_ok = False
    temp_ok = False
    try:
        original_hashes = (sha256(cae_path), sha256(odb_path))
        control_root = Path(tempfile.mkdtemp(prefix="eval_cli_task12_abaqus_control_%s_" % token))
        audit_root = Path(tempfile.mkdtemp(prefix="eval_cli_task12_abaqus_audit_%s_" % token))
        submitted_root = Path(tempfile.mkdtemp(prefix="eval_cli_task12_abaqus_submitted_%s_" % token))
        solve_root = Path(tempfile.mkdtemp(prefix="eval_cli_task12_abaqus_solve_%s_" % token))
        post_root = Path(tempfile.mkdtemp(prefix="eval_cli_task12_abaqus_post_%s_" % token))
        runtime_root = control_root / "runtime"
        runtime_root.mkdir()
        staged_cae = audit_root / "source.cae"
        staged_odb = submitted_root / "submitted.odb"
        checker = control_root / "checker.py"
        result = control_root / "result.json"
        roots = (control_root, audit_root, submitted_root, solve_root, post_root)
        markers = markers + tuple(str(path) for path in roots)
        baseline = windows_processes(ABAQUS_PROCESS_PATTERN)
        tracker_stop = threading.Event()
        tracker = threading.Thread(
            target=track_owned_processes,
            args=(
                tracker_stop, owned_history, baseline, ABAQUS_PROCESS_PATTERN,
                markers, tracker_seed_pids,
            ),
        )
        tracker.daemon = True
        tracker.start()
        shutil.copyfile(str(cae_path), str(staged_cae))
        shutil.copyfile(str(odb_path), str(staged_odb))
        if (sha256(staged_cae), sha256(staged_odb)) != original_hashes:
            raise RuntimeError("Abaqus staging hashes do not match submitted artifacts")
        source = ABAQUS_CHECKER
        replacements = {
            "__CAE_PATH__": repr(str(staged_cae)),
            "__ODB_PATH__": repr(str(staged_odb)),
            "__METRICS__": repr(metrics),
            "__AUDIT_ROOT__": repr(str(audit_root)),
            "__SOLVE_ROOT__": repr(str(solve_root)),
            "__POST_ROOT__": repr(str(post_root)),
            "__RESULT_PATH__": repr(str(result)),
            "__JOB_SUFFIX__": repr(token[:12]),
        }
        for marker, value in replacements.items():
            source = source.replace(marker, value)
        checker.write_text(source, encoding="utf-8")
        checker_hash = sha256(checker)
        environment = sanitized_abaqus_environment(runtime_root)
        process = subprocess.Popen(
            [ABAQUS_COMMAND, "cae", "noGUI=" + str(checker)],
            cwd=str(control_root), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL, text=True, shell=False, env=environment,
        )
        tracker_seed_pids.append(process.pid)
        update_owned_process_history(
            owned_history,
            baseline,
            windows_processes(ABAQUS_PROCESS_PATTERN, timeout=5.0),
            markers,
            seed_pids=(process.pid,),
        )
        try:
            stdout, stderr = process.communicate(timeout=1200)
        except subprocess.TimeoutExpired:
            if os.name == "nt":
                subprocess.run(["taskkill.exe", "/PID", str(process.pid), "/T", "/F"], capture_output=True, text=True)
            else:
                process.kill()
            process.communicate(timeout=30)
            raise RuntimeError("Abaqus checker timed out")
        log("Abaqus checker returncode=%s" % process.returncode)
        if stdout:
            log("Abaqus stdout tail=" + stdout[-1200:])
        if stderr:
            log("Abaqus stderr tail=" + stderr[-1200:])
        if not is_nonempty(result):
            raise RuntimeError("Abaqus checker did not produce a result report")
        payload = json.loads(result.read_text(encoding="utf-8"))
        for detail in payload.get("details", []):
            log("Abaqus: " + str(detail))
        semantic_ok = process.returncode == 0 and payload.get("passed") is True
        if sha256(checker) != checker_hash:
            log("Abaqus checker source changed during evaluation")
            semantic_ok = False
        if (sha256(cae_path), sha256(odb_path)) != original_hashes:
            log("submitted Abaqus artifacts changed during evaluation")
            semantic_ok = False
    except Exception as exc:
        log("Abaqus evaluator failed: %s" % exc)
        semantic_ok = False
    finally:
        if process is not None and process.poll() is None:
            try:
                update_owned_process_history(
                    owned_history,
                    baseline or [],
                    windows_processes(ABAQUS_PROCESS_PATTERN, timeout=5.0),
                    markers,
                    seed_pids=(process.pid,),
                )
                terminate_owned_process(process.pid)
            except Exception as exc:
                log("Abaqus launcher termination failed: %s" % exc)
        if tracker is not None:
            time.sleep(2.0)
        if tracker_stop is not None:
            tracker_stop.set()
        if tracker is not None:
            tracker.join(timeout=6.0)
            tracker_ok = not tracker.is_alive()
            if not tracker_ok:
                log("Abaqus process tracker did not stop")
        else:
            log("Abaqus process tracker was not started")
        if baseline is not None:
            try:
                process_ok = restore_process_baseline(
                    baseline, ABAQUS_PROCESS_PATTERN, markers, owned_history.values()
                )
            except Exception as exc:
                log("Abaqus process cleanup failed: %s" % exc)
        else:
            log("Abaqus process cleanup skipped because no baseline was captured")
        roots = tuple(
            path for path in (control_root, audit_root, submitted_root, solve_root, post_root)
            if path is not None
        )
        temp_results = [remove_tree(path) for path in roots]
        temp_ok = len(roots) == 5 and all(temp_results)
        if not temp_ok:
            log("Abaqus evaluator temporary directory cleanup was incomplete")
    return semantic_ok and process_ok and tracker_ok and temp_ok


def parse_cdb_constraints_and_forces(text):
    constraints = []
    forces = []
    active = None
    for raw in text.splitlines():
        line = raw.strip()
        upper = line.upper()
        if upper.startswith("DBLOCK,"):
            active = "D"
            continue
        if upper.startswith("FBLOCK,"):
            active = "F"
            continue
        if active and (upper.startswith("/GO") or line == "-1"):
            active = None
            continue
        if not active or not line or line.startswith("("):
            continue
        match = re.match(r"^(\d+)\s+([A-Z0-9]+)\s+([-+0-9.EeDd]+)", line)
        if not match:
            continue
        row = (int(match.group(1)), match.group(2).upper(), float(match.group(3).replace("D", "E").replace("d", "e")))
        if active == "D":
            constraints.append(row)
        else:
            forces.append(row)
    return constraints, forces


def apdl_path(path):
    return str(path).replace("\\", "/")


def ansys_resume_hardening_commands():
    return (
        "/PSEARCH,OFF",
        *("*ABBR,%s," % command for command in ANSYS_AUDIT_ABBREVIATIONS),
        "USRCAL,NONE",
    )


def parse_ansys_cdb(text):
    lines = text.splitlines()
    type_codes = {}
    type_keyopts = {}
    coords = {}
    elements = {}
    element_attributes = {}
    materials = {}
    properties = {}
    tb_tables = {}
    active_tb = None
    index = 0
    while index < len(lines):
        stripped = lines[index].strip()
        upper = stripped.upper()
        if upper.startswith("ETBLOCK,"):
            index += 1
            while index < len(lines):
                row = lines[index].strip()
                if row == "-1":
                    break
                if row and not row.startswith("("):
                    values = re.findall(r"[-+]?\d+", row)
                    if len(values) >= 2:
                        if len(values) != 21:
                            raise RuntimeError("CDB ETBLOCK record does not contain exactly 18 KEYOPT values plus INOPR")
                        type_id = int(values[0])
                        if type_id <= 0 or type_id in type_codes:
                            raise RuntimeError("duplicate or invalid CDB element type")
                        if int(values[20]) not in (0, 1):
                            raise RuntimeError("CDB ETBLOCK INOPR value is invalid")
                        type_codes[type_id] = int(values[1])
                        type_keyopts[type_id] = tuple(int(value) for value in values[2:20])
                index += 1
        elif upper.startswith("NBLOCK,"):
            index += 1
            while index < len(lines):
                row = lines[index]
                stripped_row = row.strip()
                if stripped_row == "-1" or stripped_row.upper().startswith("N,UNBL"):
                    break
                if stripped_row and not stripped_row.startswith("("):
                    try:
                        label = int(row[:9])
                        xyz = []
                        for offset in (27, 48, 69):
                            field = row[offset:offset + 21].strip()
                            xyz.append(float(field.replace("D", "E")) if field else 0.0)
                        if label <= 0 or label in coords:
                            raise RuntimeError("duplicate or invalid CDB node")
                        coords[label] = tuple(xyz)
                    except Exception as exc:
                        raise RuntimeError("invalid CDB NBLOCK row: %r (%s)" % (row, exc))
                index += 1
        elif upper.startswith("EBLOCK,"):
            index += 1
            pending = []
            while index < len(lines):
                row = lines[index].strip()
                if row == "-1":
                    break
                if row and not row.startswith("("):
                    pending.extend(int(value) for value in re.findall(r"[-+]?\d+", row))
                    while len(pending) >= 11:
                        node_count = int(pending[8])
                        record_size = 11 + node_count
                        if node_count <= 0 or node_count > 64:
                            raise RuntimeError("invalid CDB element node count")
                        if len(pending) < record_size:
                            break
                        record = pending[:record_size]
                        pending = pending[record_size:]
                        material_id = int(record[0])
                        type_id = int(record[1])
                        real_id = int(record[2])
                        section_id = int(record[3])
                        label = int(record[10])
                        code = type_codes.get(type_id)
                        connectivity = tuple(int(value) for value in record[11:])
                        if code is None or label <= 0 or label in elements:
                            raise RuntimeError("invalid CDB element identity/type")
                        elements[label] = (code, connectivity)
                        materials[label] = material_id
                        element_attributes[label] = (type_id, real_id, section_id)
                index += 1
            if pending:
                raise RuntimeError("incomplete CDB EBLOCK record")
        elif upper.startswith("MPDATA,"):
            fields = [field.strip() for field in stripped.split(",")]
            if len(fields) >= 7:
                label = fields[3].upper()
                material_id = int(fields[4])
                if int(fields[5]) != 1 or any(field for field in fields[7:]):
                    raise RuntimeError("MPDATA record contains unsupported slots or coefficients")
                key = (material_id, label)
                if key in properties:
                    raise RuntimeError("duplicate MPDATA material property")
                properties[key] = float(fields[6].replace("D", "E"))
        elif upper.startswith("TB,"):
            fields = [field.strip() for field in stripped.split(",")]
            if len(fields) < 3:
                raise RuntimeError("invalid TB material record")
            material_id = int(fields[2])
            if material_id <= 0:
                raise RuntimeError("invalid TB material identifier")
            active_tb = {
                "label": fields[1].upper(),
                "ntemp": fields[3] if len(fields) > 3 else "",
                "npts": fields[4] if len(fields) > 4 else "",
                "option": fields[5].upper() if len(fields) > 5 else "",
                "temperatures": [],
                "data": [],
            }
            tb_tables.setdefault(material_id, []).append(active_tb)
        elif upper.startswith("TBTEMP,"):
            if active_tb is None:
                raise RuntimeError("TBTEMP appears without an active TB table")
            fields = [field.strip() for field in stripped.split(",")]
            values = [float(field.replace("D", "E")) for field in fields[1:] if field]
            if not values:
                raise RuntimeError("empty TBTEMP material record")
            active_tb["temperatures"].extend(values)
        elif upper.startswith("TBFIELD,"):
            if active_tb is None:
                raise RuntimeError("TBFIELD appears without an active TB table")
            fields = [field.strip() for field in stripped.split(",")]
            if len(fields) != 3 or fields[1].upper() != "TEMPS":
                raise RuntimeError("unsupported TBFIELD material dependency")
            active_tb["temperatures"].append(float(fields[2].replace("D", "E")))
        elif upper.startswith("TBDATA,"):
            if active_tb is None:
                raise RuntimeError("TBDATA appears without an active TB table")
            fields = [field.strip() for field in stripped.split(",")]
            if len(fields) < 3:
                raise RuntimeError("invalid TBDATA material record")
            start = int(fields[1]) if fields[1] else 1
            values = tuple(float(field.replace("D", "E")) for field in fields[2:] if field)
            if not values:
                raise RuntimeError("empty TBDATA material record")
            active_tb["data"].append((start, values))
        index += 1
    constraints, forces = parse_cdb_constraints_and_forces(text)
    if not type_codes or not coords or not elements:
        raise RuntimeError("CDB does not contain a complete FE model")
    return (
        coords, elements, element_attributes, type_keyopts, materials,
        properties, tb_tables, constraints, forces,
    )


def parse_ansys_live_status(path, expected_elements):
    if not is_nonempty(path):
        raise RuntimeError("ANSYS element live-status listing is missing")
    statuses = {}
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        fields = raw.split()
        if len(fields) != 2:
            continue
        try:
            label_value = float(fields[0].replace("D", "E"))
            label = int(label_value)
            value = float(fields[1].replace("D", "E"))
        except Exception:
            continue
        if not finite_number(label_value) or label_value != label or label <= 0 or label in statuses or not finite_number(value):
            raise RuntimeError("ANSYS element live-status listing is invalid")
        statuses[label] = value
    if set(statuses) != set(expected_elements):
        missing = sorted(set(expected_elements) - set(statuses))
        unexpected = sorted(set(statuses) - set(expected_elements))
        raise RuntimeError(
            "ANSYS element live-status listing does not cover exactly the CDB elements: "
            "listed=%d expected=%d missing=%r unexpected=%r" % (
                len(statuses), len(expected_elements), missing[:20], unexpected[:20]
            )
        )
    if any(not close_enough(value, 1.0, rel=0.0, abs_tol=1.0e-12) for value in statuses.values()):
        log("ANSYS DB contains killed or inactive solid elements")
        return None
    return statuses


def run_ansys_batch(root, input_path, output_path, jobname, nonce, baseline, owned_history, timeout=600):
    process = subprocess.Popen(
        [
            ANSYS_EXEC, "-b", "-np", "1", "-s", "noread",
            "-j", jobname, "-dir", str(root),
            "-i", str(input_path), "-o", str(output_path),
        ],
        cwd=str(root),
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
        (jobname, str(root), nonce),
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
        raise RuntimeError("ANSYS isolated batch timed out: %s" % jobname)
    output = output_path.read_text(encoding="utf-8", errors="replace") if is_nonempty(output_path) else ""
    if stdout:
        log("ANSYS batch stdout tail=" + stdout[-800:])
    if stderr:
        log("ANSYS batch stderr tail=" + stderr[-800:])
    if process.returncode != 0 or "*** ERROR ***" in output.upper():
        raise RuntimeError("ANSYS batch failed: job=%s rc=%s output=%r" % (jobname, process.returncode, output[-5000:]))
    return output


def parse_ansys_numeric_listing(path, columns, expected_nodes):
    rows = {}
    text = path.read_text(encoding="utf-8", errors="replace") if is_nonempty(path) else ""
    numeric_samples = []
    raw_numeric_samples = []
    scalar = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[DE][+-]?\d+)?"
    row_pattern = re.compile(
        r"^\s*(\d+)\s+" + r"\s*".join("(%s)" % scalar for _ in range(columns)) + r"\s*$",
        re.IGNORECASE,
    )
    for raw in text.splitlines():
        if re.match(r"^\s*\d+\s+", raw) and len(raw_numeric_samples) < 12:
            raw_numeric_samples.append(raw[:240])
        match = row_pattern.match(raw)
        if match is not None and len(numeric_samples) < 12:
            numeric_samples.append(raw[:240])
        if match is None:
            continue
        try:
            label = int(match.group(1))
            values = tuple(float(value.replace("D", "E")) for value in match.groups()[1:])
        except Exception:
            continue
        if not all(finite_number(value) for value in values):
            raise RuntimeError("ANSYS result listing contains non-finite data: %s" % path.name)
        if label not in expected_nodes:
            raise RuntimeError("ANSYS result listing contains an unexpected node %d: %s" % (label, path.name))
        if label in rows:
            raise RuntimeError("ANSYS result listing contains duplicate node %d: %s" % (label, path.name))
        rows[label] = values
    if set(rows) != set(expected_nodes):
        missing = sorted(set(expected_nodes) - set(rows))
        unexpected = sorted(set(rows) - set(expected_nodes))
        raise RuntimeError(
            "ANSYS result listing does not cover every solid node: %s "
            "parsed=%d expected=%d missing=%r unexpected=%r samples=%r raw_samples=%r" % (
                path.name, len(rows), len(expected_nodes), missing[:20],
                unexpected[:20], numeric_samples, raw_numeric_samples,
            )
        )
    return rows


def task12_cdb_forbidden(text):
    forbidden = {
        "INISTATE", "INRES", "LDREAD", "LREAD", "UPGEOM", "BF", "BFA",
        "BFE", "BFEBLOCK", "BFBLOCK", "BFV", "FBLOCK", "F", "CE",
        "CERIG", "CEINTF", "CP", "CPCYC", "CPINTF", "TBMODIF", "TBPT",
    }
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("!") or stripped.startswith("/"):
            continue
        fields = [field.strip() for field in stripped.split(",")]
        name = fields[0].upper()
        if name in forbidden:
            return True
        if name in {"ACEL", "OMEGA", "DOMEGA", "CGOMEGA", "CGOMGA", "DCGOMG", "ALPHAD", "BETAD", "DMPRAT", "DMPSTR"}:
            values = []
            try:
                values = [float(value.replace("D", "E")) for value in fields[1:] if value]
            except Exception:
                return True
            if any(abs(value) > 1.0e-12 for value in values):
                return True
    return False


def parse_task12_sfeblock(text):
    rows = []
    active = False
    for raw in text.splitlines():
        stripped = raw.strip()
        upper = stripped.upper()
        if upper.startswith("SFEBLOCK,"):
            fields = [value.strip().upper() for value in stripped.split(",")]
            if len(fields) < 3 or fields[2] != "PRES" or active:
                raise RuntimeError("CDB contains an unsupported or duplicate surface-load block")
            active = True
            continue
        if active and (upper.startswith("SFE,END") or stripped == "-1"):
            active = False
            continue
        if not active or not stripped or stripped.startswith("("):
            continue
        fields = stripped.split()
        if len(fields) != 7:
            raise RuntimeError("CDB pressure block row has an unexpected shape")
        rows.append((int(fields[0]), int(fields[1]), int(fields[2]), tuple(float(value.replace("D", "E")) for value in fields[3:])))
    if active:
        raise RuntimeError("CDB pressure block is unterminated")
    return rows


def task12_ansys_element_spec(code, connectivity):
    code = int(code)
    if code == 182 and len(connectivity) == 4:
        return 4, ((0, 1), (1, 2), (2, 3), (3, 0)), ()
    if code == 183 and len(connectivity) == 6:
        return 3, ((0, 1), (1, 2), (2, 0)), ((3, 0, 1), (4, 1, 2), (5, 2, 0))
    if code == 183 and len(connectivity) == 8:
        return 4, ((0, 1), (1, 2), (2, 3), (3, 0)), ((4, 0, 1), (5, 1, 2), (6, 2, 3), (7, 3, 0))
    return None


TASK12_ANSYS_FACE_ENDPOINT_INDICES = {
    (182, 4, 1): (1, 0),
    (182, 4, 2): (2, 1),
    (182, 4, 3): (3, 2),
    (182, 4, 4): (0, 3),
    (183, 8, 1): (1, 0),
    (183, 8, 2): (2, 1),
    (183, 8, 3): (3, 2),
    (183, 8, 4): (0, 3),
    (183, 6, 1): (1, 0),
    (183, 6, 2): (2, 1),
    (183, 6, 3): (0, 2),
}


def task12_ansys_face_endpoint_indices(code, connectivity, face):
    return TASK12_ANSYS_FACE_ENDPOINT_INDICES.get(
        (int(code), len(connectivity), int(face))
    )


def task12_ansys_keyopts_valid(code, connectivity, keyopts):
    if len(keyopts) != 18:
        return False
    if int(code) == 182 and len(connectivity) == 4:
        allowed = {
            1: {0, 1, 2, 3},
            3: {1},
            6: {0, 1},
            15: {0},
            17: {0, 4},
        }
    elif int(code) == 183 and len(connectivity) == 8:
        allowed = {
            1: {0},
            3: {1},
            6: {0, 1},
            15: {0},
            17: {0, 4},
        }
    elif int(code) == 183 and len(connectivity) == 6:
        allowed = {
            1: {1},
            3: {1},
            6: {0, 1},
            15: {0},
            17: {0, 4},
        }
    else:
        return False
    return all(
        value in allowed.get(number, {0})
        for number, value in enumerate(keyopts, start=1)
    )


def audit_task12_ansys_mesh(coords, elements):
    rows = list(coords.values())
    expected = ((0.0, 50.0), (0.0, 1.0), (0.0, 0.0))
    bounds = tuple((min(row[axis] for row in rows), max(row[axis] for row in rows)) for axis in range(3))
    if any(not close_enough(bounds[i][j], expected[i][j], rel=0.0, abs_tol=1.0e-7) for i in range(3) for j in range(2)):
        log("ANSYS mesh bounds are not the 0..50 x 0..1 mm axisymmetric section")
        return None
    attached = set()
    stress_nodes = set()
    area = 0.0
    radial_edges = []
    edge_owners = {}
    edge_full_nodes = {}
    edge_endpoints = {}
    top_exterior_edges = set()
    for label, (code, connectivity) in elements.items():
        spec = task12_ansys_element_spec(code, connectivity)
        if spec is None:
            log("ANSYS mesh contains a non-PLANE182/183 or incomplete element: %s" % label)
            return None
        corners, edges, midsides = spec
        if len(set(connectivity)) != len(connectivity) or any(node not in coords for node in connectivity):
            log("ANSYS PLANE element connectivity is invalid")
            return None
        attached.update(connectivity)
        stress_nodes.update(connectivity[:corners])
        points = [coords[node] for node in connectivity[:corners]]
        polygon = 0.0
        for index in range(corners):
            x1, y1 = points[index][:2]
            x2, y2 = points[(index + 1) % corners][:2]
            polygon += x1 * y2 - x2 * y1
        area += abs(polygon) * 0.5
        midside_by_edge = dict((frozenset((a, b)), middle) for middle, a, b in midsides)
        for a, b in edges:
            key = frozenset((connectivity[a], connectivity[b]))
            edge_owners.setdefault(key, []).append(label)
            full = {connectivity[a], connectivity[b]}
            middle = midside_by_edge.get(frozenset((a, b)))
            if middle is not None:
                full.add(connectivity[middle])
            edge_full_nodes.setdefault(key, []).append(frozenset(full))
            edge_endpoints.setdefault(key, (connectivity[a], connectivity[b]))
            dx = abs(coords[connectivity[a]][0] - coords[connectivity[b]][0])
            dy = abs(coords[connectivity[a]][1] - coords[connectivity[b]][1])
            if dx > 1.0e-8 and dy <= 1.0e-8:
                radial_edges.append(dx)
        for middle, a, b in midsides:
            midpoint = tuple((coords[connectivity[a]][axis] + coords[connectivity[b]][axis]) / 2.0 for axis in range(3))
            if any(abs(coords[connectivity[middle]][axis] - midpoint[axis]) > 1.0e-7 for axis in range(3)):
                log("ANSYS PLANE183 midside node is not at its straight-edge midpoint")
                return None
    if attached != set(coords) or any(len(owners) > 2 for owners in edge_owners.values()):
        log("ANSYS mesh contains unattached nodes or non-manifold edges")
        return None
    if any(len(values) == 2 and values[0] != values[1] for values in edge_full_nodes.values()):
        log("adjacent PLANE183 elements do not share identical midside nodes")
        return None
    boundary_lengths = {(0, 0.0): 0.0, (0, 50.0): 0.0, (1, 0.0): 0.0, (1, 1.0): 0.0}
    neighbors = dict((label, set()) for label in elements)
    for key, owners in edge_owners.items():
        if len(owners) == 2:
            neighbors[owners[0]].add(owners[1])
            neighbors[owners[1]].add(owners[0])
            continue
        a, b = edge_endpoints[key]
        planes = [(axis, value) for axis, value in boundary_lengths if abs(coords[a][axis] - value) <= 1.0e-7 and abs(coords[b][axis] - value) <= 1.0e-7]
        if len(planes) != 1:
            log("ANSYS mesh has an interior hole or off-domain exterior edge")
            return None
        plane = planes[0]
        boundary_lengths[plane] += math.sqrt(sum((coords[a][axis] - coords[b][axis]) ** 2 for axis in range(2)))
        if plane == (1, 1.0):
            top_exterior_edges.add((owners[0], key))
    expected_lengths = {(0, 0.0): 1.0, (0, 50.0): 1.0, (1, 0.0): 50.0, (1, 1.0): 50.0}
    if any(not close_enough(boundary_lengths[key], expected_lengths[key], rel=1.0e-6, abs_tol=0.01) for key in expected_lengths):
        log("ANSYS mesh exterior does not cover exactly the rectangle boundary")
        return None
    reached = set()
    pending = [next(iter(neighbors))]
    while pending:
        current = pending.pop()
        if current in reached:
            continue
        reached.add(current)
        pending.extend(neighbors[current] - reached)
    if reached != set(neighbors):
        log("ANSYS plate mesh is not one edge-connected cross-section")
        return None
    if not close_enough(area, 50.0, rel=1.0e-6, abs_tol=0.01):
        log("ANSYS PLANE elements do not fill the 50 x 1 mm cross-section")
        return None
    if not radial_edges:
        log("ANSYS radial mesh spacing is unavailable")
        return None
    radial_median = median(radial_edges)
    representative_fraction = sum(
        1 for value in radial_edges if 1.25 <= value <= 2.75
    ) / float(len(radial_edges))
    if (
        min(radial_edges) < 0.1
        or max(radial_edges) > 4.0
        or not (1.5 <= radial_median <= 2.5)
        or representative_fraction < 0.6
    ):
        log("ANSYS radial mesh spacing is not representatively approximately 2 mm")
        return None
    axis = set(label for label, xyz in coords.items() if abs(xyz[0]) <= 1.0e-7)
    outer = set(label for label, xyz in coords.items() if abs(xyz[0] - 50.0) <= 1.0e-7)
    top = set(label for label, xyz in coords.items() if abs(xyz[1] - 1.0) <= 1.0e-7)
    center = list(axis & top)
    if len(axis) < 2 or len(outer) < 2 or len(top) < 20 or len(center) != 1:
        log("ANSYS mesh lacks complete axis, outer, top, or center-top node sets")
        return None
    return {
        "axis": axis,
        "outer": outer,
        "top": top,
        "center": center[0],
        "area": area,
        "stress_nodes": stress_nodes,
        "top_exterior_edges": top_exterior_edges,
        "radial_edge_median": radial_median,
        "radial_edge_representative_fraction": representative_fraction,
    }


def audit_task12_ansys_cdb(cdb_path, live_status_path):
    text = cdb_path.read_text(encoding="utf-8", errors="ignore")
    if task12_cdb_forbidden(text):
        log("ANSYS DB contains an initial state, body/nodal load, coupling, or nonzero inertia")
        return None
    (
        coords, elements, attributes, type_keyopts, materials,
        properties, tb_tables, constraints, forces,
    ) = parse_ansys_cdb(text)
    if forces or parse_ansys_live_status(live_status_path, elements) is None:
        log("ANSYS DB contains nodal forces or inactive elements")
        return None
    mesh = audit_task12_ansys_mesh(coords, elements)
    if mesh is None:
        return None
    used_types = set()
    for label, (code, connectivity) in elements.items():
        type_id = attributes[label][0]
        used_types.add(type_id)
        keyopts = type_keyopts.get(type_id, ())
        if not task12_ansys_keyopts_valid(code, connectivity, keyopts):
            log("ANSYS PLANE182/183 KEYOPT values are not in the supported axisymmetric whitelist")
            return None
    structural = {"EX", "EY", "EZ", "PRXY", "PRYZ", "PRXZ", "NUXY", "NUYZ", "NUXZ", "GXY", "GYZ", "GXZ"}
    for material_id in set(materials.values()):
        labels = set(label for mid, label in properties if mid == material_id)
        poissons = labels & {"PRXY", "NUXY"}
        if material_id in tb_tables or not poissons or labels & structural != {"EX"} | poissons:
            log("ANSYS plate material is not a single MP isotropic elastic definition")
            return None
        if not close_enough(properties.get((material_id, "EX")), 210000.0, rel=1.0e-6, abs_tol=1.0e-5) or any(not close_enough(properties.get((material_id, label)), 0.3, rel=1.0e-6, abs_tol=1.0e-8) for label in poissons):
            log("ANSYS assigned material is not E=210000 MPa and nu=0.3")
            return None
    expected_constraints = set((node, "UX", 0.0) for node in mesh["axis"])
    expected_constraints.update((node, dof, 0.0) for node in mesh["outer"] for dof in ("UX", "UY"))
    if set(constraints) != expected_constraints:
        log("ANSYS constraints are not exactly axis UX=0 plus outer UX=UY=0")
        return None
    pressure_rows = parse_task12_sfeblock(text)
    grouped = {}
    for element, face, key, values in pressure_rows:
        if element not in elements:
            log("ANSYS pressure references an unknown element")
            return None
        grouped.setdefault((element, face), []).append((key, values))
    loaded_edges = set()
    for (element, face), rows in grouped.items():
        keys = [key for key, _values in rows]
        real_keys = [key for key in keys if key in (0, 1)]
        if (
            len(keys) != len(set(keys))
            or len(real_keys) != 1
            or any(key not in (0, 1, 2) for key in keys)
        ):
            log("ANSYS pressure face does not contain one real SFE row and optional imaginary row")
            return None
        real_row = [values for key, values in rows if key in (0, 1)][0]
        imaginary_rows = [values for key, values in rows if key == 2]
        if (
            not close_enough(real_row[0], 0.1, rel=1.0e-7, abs_tol=1.0e-9)
            or not close_enough(real_row[1], 0.1, rel=1.0e-7, abs_tol=1.0e-9)
            or any(abs(value) > 1.0e-12 for value in real_row[2:])
            or any(abs(value) > 1.0e-12 for row in imaginary_rows for value in row)
        ):
            log("ANSYS top pressure values are not uniformly 0.1 MPa")
            return None
        code, connectivity = elements[element]
        endpoint_indices = task12_ansys_face_endpoint_indices(code, connectivity, face)
        if endpoint_indices is None:
            log("ANSYS pressure uses an unsupported PLANE element face mapping")
            return None
        loaded_edges.add(
            (element, frozenset(connectivity[index] for index in endpoint_indices))
        )
    if loaded_edges != mesh["top_exterior_edges"]:
        log("ANSYS pressure faces do not exactly match the actual Y=1 exterior edges")
        return None
    return {"coords": coords, "elements": elements, "mesh_info": mesh, "used_types": sorted(used_types)}


def write_task12_ansys_export(path, model_path, stem, nonce):
    path.write_text("\n".join((
        "/BATCH", "/COM,TASK12_EXPORT_BEGIN_%s" % nonce,
        "RESUME,'%s','db'" % apdl_path(model_path.with_suffix("")),
        *ansys_resume_hardening_commands(), "FINISH", "/PREP7", "ALLSEL,ALL", "CSYS,0", "DSYS,0",
        "*GET,T12ECNT,ELEM,0,COUNT", "T12EID=0", "*CFOPEN,%s_live,txt" % stem,
        "*DO,T12I,1,T12ECNT", "T12EID=ELNEXT(T12EID)", "*GET,T12LIVE,ELEM,T12EID,ATTR,LIVE",
        "*VWRITE,T12EID,T12LIVE", "(F20.0,1X,E24.16)", "*ENDDO", "*CFCLOS",
        "CDWRITE,DB,%s,cdb" % stem, "FINISH", "/COM,TASK12_EXPORT_END_%s" % nonce,
        "/EXIT,NOSAVE", "",
    )), encoding="ascii")


def write_task12_ansys_post(path, model_path, result_path, prefix, nonce, center_node):
    path.write_text("\n".join((
        "/BATCH", "/COM,TASK12_POST_BEGIN_%s" % nonce,
        "RESUME,'%s','db'" % apdl_path(model_path.with_suffix("")),
        *ansys_resume_hardening_commands(), "FINISH", "/POST1",
        "FILE,'%s','rst'" % apdl_path(result_path.with_suffix("")), "SET,LAST",
        "*GET,T12ANTY,ACTIVE,0,ANTY", "RSYS,0", "/GRAPHICS,FULL", "AVPRIN,0", "ALLSEL,ALL",
        "*GET,T12TIME,ACTIVE,0,SET,TIME", "*GET,T12NSET,ACTIVE,0,SET,NSET",
        "*GET,T12CENTER,NODE,%d,U,Y" % int(center_node),
        "ESEL,ALL", "NSLE,S", "NSORT,S,EQV,0,1,ALL", "*GET,T12MISES,SORT,0,MAX",
        "ALLSEL,ALL", "NSEL,S,LOC,X,50", "FSUM",
        "*GET,T12FX,FSUM,0,ITEM,FX", "*GET,T12FY,FSUM,0,ITEM,FY", "ALLSEL,ALL",
        "/OUTPUT,%s_u,txt" % prefix, "PRNSOL,U,COMP", "/OUTPUT",
        "/OUTPUT,%s_s,txt" % prefix, "PRNSOL,S,PRIN", "/OUTPUT",
        "*CFOPEN,%s_metrics,json" % prefix, "*VWRITE", "('{')",
        "*VWRITE,T12TIME,T12NSET,T12ANTY,T12CENTER,T12MISES",
        "('  \"time\": ',E24.16,', \"result_sets\": ',E24.16,', \"analysis_type\": ',E24.16,', \"center_deflection\": ',E24.16,', \"max_stress\": ',E24.16,',')",
        "*VWRITE,T12FX,T12FY", "('  \"reaction\": [',E24.16,',',E24.16,']')",
        "*VWRITE", "('}')", "*CFCLOS", "FINISH", "/COM,TASK12_POST_END_%s" % nonce,
        "/EXIT,NOSAVE", "",
    )), encoding="ascii")


def write_task12_ansys_resolve(path, model_path, nonce):
    path.write_text("\n".join((
        "/BATCH", "/COM,TASK12_RESOLVE_BEGIN_%s" % nonce,
        "RESUME,'%s','db'" % apdl_path(model_path.with_suffix("")),
        *ansys_resume_hardening_commands(), "FINISH", "/SOLU", "ANTYPE,STATIC,NEW",
        "NLGEOM,OFF", "EQSLV,SPARSE", "NSUBST,1,1,1", "OUTRES,ALL,ALL",
        "ALLSEL,ALL", "SOLVE", "FINISH", "/COM,TASK12_RESOLVE_END_%s" % nonce,
        "/EXIT,NOSAVE", "",
    )), encoding="ascii")


def read_task12_ansys_post(root, prefix, expected_nodes, expected_stress_nodes):
    path = root / (prefix + "_metrics.json")
    if not is_nonempty(path):
        raise RuntimeError("ANSYS post metrics were not written")
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if set(payload) != {"time", "result_sets", "analysis_type", "center_deflection", "max_stress", "reaction"}:
        raise RuntimeError("ANSYS post metrics have unexpected keys")
    if any(not finite_number(payload[name]) for name in ("time", "result_sets", "analysis_type", "center_deflection", "max_stress")):
        raise RuntimeError("ANSYS post scalar is non-finite")
    if not isinstance(payload["reaction"], list) or len(payload["reaction"]) != 2 or any(not finite_number(value) for value in payload["reaction"]):
        raise RuntimeError("ANSYS outer reaction vector is invalid")
    payload["reaction"] = tuple(float(value) for value in payload["reaction"])
    for name in ("time", "result_sets", "analysis_type", "center_deflection", "max_stress"):
        payload[name] = float(payload[name])
    payload["u"] = parse_ansys_numeric_listing(root / (prefix + "_u.txt"), 4, expected_nodes)
    payload["s"] = parse_ansys_numeric_listing(
        root / (prefix + "_s.txt"), 5, expected_stress_nodes
    )
    return payload


def task12_ansys_post_valid(payload):
    if not close_enough(payload["analysis_type"], 0.0, rel=0.0, abs_tol=1.0e-12) or payload["time"] <= 0.0 or payload["result_sets"] < 1.0:
        log("ANSYS RST is not a completed static structural result")
        return False
    if not (-0.8 <= payload["center_deflection"] <= -0.1):
        log("ANSYS center-top UY has wrong direction or implausible magnitude")
        return False
    if not (20.0 <= payload["max_stress"] <= 600.0):
        log("ANSYS nodally averaged maximum SEQV is implausible")
        return False
    expected = math.pi * 50.0 * 50.0 * 0.1
    if not close_enough(payload["reaction"][1], -expected, rel=3.0e-3, abs_tol=1.5) or abs(payload["reaction"][0]) > 20.0:
        log("ANSYS outer reaction does not balance negative-Y top pressure")
        return False
    return True


def task12_ansys_posts_match(left, right):
    for name in ("center_deflection", "max_stress"):
        tolerance = 3.0e-7 if name == "center_deflection" else 8.0e-4
        if not close_enough(left[name], right[name], rel=7.0e-4, abs_tol=tolerance):
            return False
    if any(not close_enough(left["reaction"][index], right["reaction"][index], rel=7.0e-4, abs_tol=0.02) for index in range(2)):
        return False
    for name in ("u", "s"):
        if set(left[name]) != set(right[name]):
            return False
        for label in left[name]:
            if len(left[name][label]) != len(right[name][label]) or any(not close_enough(a, b, rel=7.0e-4, abs_tol=3.0e-7) for a, b in zip(left[name][label], right[name][label])):
                return False
    return True


def run_ansys_checker(model_path, result_path, metrics):
    token = uuid.uuid4().hex
    audit_root = solve_root = post_root = None
    audit_job = "e12audit_" + token[:12]
    solve_job = "e12solve_" + token[:12]
    post_job = "e12post_" + token[:12]
    markers = (token, audit_job, solve_job, post_job)
    baseline = None
    owned_history = {}
    tracker_stop = tracker = None
    ansys_temp_before = None
    semantic_ok = process_ok = tracker_ok = temp_ok = ansys_temp_ok = False
    try:
        original_hashes = (sha256(model_path), sha256(result_path))
        audit_root = Path(tempfile.mkdtemp(prefix="eval_cli_task12_ansys_audit_%s_" % token))
        solve_root = Path(tempfile.mkdtemp(prefix="eval_cli_task12_ansys_solve_%s_" % token))
        post_root = Path(tempfile.mkdtemp(prefix="eval_cli_task12_ansys_post_%s_" % token))
        staged_model = audit_root / "source.db"
        staged_result = audit_root / "submitted.rst"
        solve_model = solve_root / "source.db"
        post_model = post_root / "source.db"
        post_result = post_root / "submitted.rst"
        markers = markers + (str(audit_root), str(solve_root), str(post_root))
        baseline = windows_processes(ANSYS_PROCESS_PATTERN)
        ansys_temp_before = ansys_temp_inventory()
        tracker_stop = threading.Event()
        tracker = threading.Thread(target=track_owned_processes, args=(tracker_stop, owned_history, baseline, ANSYS_PROCESS_PATTERN, markers))
        tracker.daemon = True
        tracker.start()
        shutil.copy2(str(model_path), str(staged_model))
        shutil.copy2(str(result_path), str(staged_result))
        shutil.copy2(str(model_path), str(solve_model))
        if (sha256(staged_model), sha256(staged_result), sha256(solve_model)) != (original_hashes[0], original_hashes[1], original_hashes[0]):
            raise RuntimeError("ANSYS staging hashes do not match submitted artifacts")
        nonce = uuid.uuid4().hex
        export_input = audit_root / "task12_export.inp"
        export_output = audit_root / "task12_export.out"
        export_stem = "task12_eval_export"
        write_task12_ansys_export(export_input, staged_model, export_stem, nonce)
        export_text = run_ansys_batch(audit_root, export_input, export_output, audit_job, nonce, baseline, owned_history)
        if "TASK12_EXPORT_BEGIN_%s" % nonce not in export_text or "TASK12_EXPORT_END_%s" % nonce not in export_text:
            raise RuntimeError("ANSYS DB export markers are incomplete")
        model = audit_task12_ansys_cdb(audit_root / (export_stem + ".cdb"), audit_root / (export_stem + "_live.txt"))
        if model is None:
            raise RuntimeError("ANSYS DB Task-12 semantic audit failed")
        expected_nodes = set(model["coords"])
        expected_stress_nodes = set(model["mesh_info"]["stress_nodes"])
        center_node = model["mesh_info"]["center"]
        submitted_nonce = uuid.uuid4().hex
        submitted_input = audit_root / "task12_submitted_post.inp"
        submitted_output = audit_root / "task12_submitted_post.out"
        write_task12_ansys_post(submitted_input, staged_model, staged_result, "submitted", submitted_nonce, center_node)
        submitted_text = run_ansys_batch(audit_root, submitted_input, submitted_output, audit_job, submitted_nonce, baseline, owned_history)
        if "TASK12_POST_BEGIN_%s" % submitted_nonce not in submitted_text or "TASK12_POST_END_%s" % submitted_nonce not in submitted_text:
            raise RuntimeError("ANSYS submitted RST post markers are incomplete")
        submitted = read_task12_ansys_post(
            audit_root, "submitted", expected_nodes, expected_stress_nodes
        )
        if not task12_ansys_post_valid(submitted):
            raise RuntimeError("ANSYS submitted RST physical/result audit failed")
        for name in METRIC_FIELDS:
            tolerance = 2.0e-7 if name == "center_deflection" else 3.0e-5
            if not close_enough(submitted[name], metrics[name], rel=2.0e-5, abs_tol=tolerance):
                raise RuntimeError("metrics.json %s does not match submitted RST" % name)
        resolve_nonce = uuid.uuid4().hex
        resolve_input = solve_root / "task12_resolve.inp"
        resolve_output = solve_root / "task12_resolve.out"
        fresh_result = solve_root / (solve_job + ".rst")
        write_task12_ansys_resolve(resolve_input, solve_model, resolve_nonce)
        resolve_text = run_ansys_batch(solve_root, resolve_input, resolve_output, solve_job, resolve_nonce, baseline, owned_history)
        if ("TASK12_RESOLVE_BEGIN_%s" % resolve_nonce not in resolve_text or "TASK12_RESOLVE_END_%s" % resolve_nonce not in resolve_text or "RUN COMPLETED" not in resolve_text or re.search(r"\*\*\* LOAD STEP\s+1\s+SUBSTEP\s+1\s+COMPLETED", resolve_text) is None or "NUMBER OF ERROR   MESSAGES ENCOUNTERED=          0" not in resolve_text or not is_nonempty(fresh_result)):
            raise RuntimeError("isolated ANSYS DB re-solve failed")
        shutil.copy2(str(solve_model), str(post_model))
        shutil.copy2(str(fresh_result), str(post_result))
        if sha256(post_model) != original_hashes[0] or sha256(post_result) != sha256(fresh_result):
            raise RuntimeError("ANSYS fresh re-solve staging hashes do not match")
        recheck_nonce = uuid.uuid4().hex
        recheck_input = post_root / "task12_rechecked_post.inp"
        recheck_output = post_root / "task12_rechecked_post.out"
        write_task12_ansys_post(recheck_input, post_model, post_result, "rechecked", recheck_nonce, center_node)
        recheck_text = run_ansys_batch(post_root, recheck_input, recheck_output, post_job, recheck_nonce, baseline, owned_history)
        if "TASK12_POST_BEGIN_%s" % recheck_nonce not in recheck_text or "TASK12_POST_END_%s" % recheck_nonce not in recheck_text:
            raise RuntimeError("ANSYS fresh RST post markers are incomplete")
        rechecked = read_task12_ansys_post(
            post_root, "rechecked", expected_nodes, expected_stress_nodes
        )
        if not task12_ansys_post_valid(rechecked) or not task12_ansys_posts_match(submitted, rechecked):
            raise RuntimeError("submitted RST U/S fields differ from isolated DB re-solve")
        if (sha256(model_path), sha256(result_path)) != original_hashes:
            raise RuntimeError("submitted ANSYS artifacts changed during evaluation")
        semantic_ok = True
    except Exception as exc:
        log("ANSYS Task-12 evaluator failed: %s" % exc)
    finally:
        if tracker is not None:
            time.sleep(2.0)
        if tracker_stop is not None:
            tracker_stop.set()
        if tracker is not None:
            tracker.join(timeout=6.0)
            tracker_ok = not tracker.is_alive()
            if not tracker_ok:
                log("ANSYS process tracker did not stop")
        else:
            log("ANSYS process tracker was not started")
        if baseline is not None:
            try:
                process_ok = restore_process_baseline(baseline, ANSYS_PROCESS_PATTERN, markers, owned_history.values())
            except Exception as exc:
                log("ANSYS process cleanup failed: %s" % exc)
        else:
            log("ANSYS process cleanup skipped without a baseline")
        roots = tuple(path for path in (audit_root, solve_root, post_root) if path is not None)
        temp_results = [remove_tree(path) for path in roots]
        temp_ok = len(roots) == 3 and all(temp_results)
        if not temp_ok:
            log("ANSYS evaluator temporary directory cleanup was incomplete")
        if ansys_temp_before is not None:
            ansys_temp_ok = restore_ansys_temp_inventory(ansys_temp_before, markers + tuple(path.name for path in roots), tuple(row.get("pid", 0) for row in owned_history.values()))
        else:
            log("ANSYS .ansys cleanup skipped without a baseline")
    return semantic_ok and process_ok and tracker_ok and temp_ok and ansys_temp_ok


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
        log("evaluating Abaqus 2025 native Task-12 branch")
        return run_abaqus_checker(branch[1], branch[2], metrics), root
    log("evaluating ANSYS MAPDL 2026 R1 native Task-12 branch")
    return run_ansys_checker(branch[1], branch[2], metrics), root


def main():
    root = desktop_dir()
    passed = False
    if not isolated_runtime():
        log("evaluator requires absolute Python 3.11 isolated mode (-I)")
        write_results(root, False)
        sys.stdout.write("False\n")
        return
    try:
        passed, root = evaluate()
    except Exception as exc:
        log("unhandled evaluator failure: %s" % exc)
        passed = False
    write_results(root, passed)
    sys.stdout.write("True\n" if passed else "False\n")


if __name__ == "__main__":
    main()
