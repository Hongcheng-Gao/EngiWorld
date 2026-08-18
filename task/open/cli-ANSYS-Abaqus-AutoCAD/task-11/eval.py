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


TASK_ID = "c-open-abaqus-ansys-autocad-task-11-windows"
METRIC_FIELDS = ("tip_displacement", "max_mises")
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
        log("metrics.json must contain exactly tip_displacement and max_mises")
        return None
    if any(not finite_number(data[name]) for name in METRIC_FIELDS):
        log("metrics.json values must be finite JSON numbers")
        return None
    metrics = dict((name, float(data[name])) for name in METRIC_FIELDS)
    if not (-0.35 <= metrics["tip_displacement"] <= -0.08):
        log("tip_displacement is outside the Task-11 signed physical range")
        return None
    if not (10.0 <= metrics["max_mises"] <= 1000.0):
        log("max_mises is outside the Task-11 physical range")
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
ALLOWED_TYPES = ("C3D4", "C3D6", "C3D8", "C3D10", "C3D15", "C3D20")
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


def file_sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            digest.update(block)
    return digest.hexdigest()


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
    ):
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return None


def resolve_region(owner, region):
    if entity_nodes(region) or entity_elements(region) or entity_cells(region):
        return region
    name = region_name(region)
    resolved = repository_value_ci(getattr(owner, "sets", {}), name)
    return resolved if resolved is not None else region


def resolve_analysis_region(model, instance, region):
    if entity_nodes(region) or entity_elements(region) or entity_cells(region):
        return region
    name = region_name(region)
    candidates = []
    for owner in (model.rootAssembly, instance, getattr(instance, "part", None)):
        if owner is None:
            continue
        for repository_name in ("sets", "allSets"):
            resolved = repository_value_ci(getattr(owner, repository_name, {}), name)
            if resolved is not None:
                candidates.append((resolved, frozenset(int(node.label) for node in entity_nodes(resolved))))
    if not candidates:
        return region
    signatures = set(signature for _, signature in candidates)
    if len(signatures) != 1:
        return fail("analysis region name resolves to conflicting node sets")
    return candidates[0][0]


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
            marker = (str(getattr(item, "instanceName", "")), getattr(item, identity_attr))
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
        return flatten_entities(entity.nodes, "label")
    except Exception:
        return []


def entity_cells(entity):
    try:
        return flatten_entities(entity.cells, "index")
    except Exception:
        return []


def entity_elements(entity):
    try:
        return flatten_entities(entity.elements, "label")
    except Exception:
        return []


def object_components(obj, names):
    values = []
    for name in names:
        value = getattr(obj, name, None)
        if value is None or ci(value) in ("UNSET", "FREED"):
            values.append(0.0)
            continue
        try:
            values.append(float(value))
        except Exception:
            return None
    return tuple(values)


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
    if upper.startswith("C3D4") or upper.startswith("C3D10"):
        return 4, ((0,1,2),(0,3,1),(1,3,2),(2,3,0)), ((0,1),(0,2),(0,3),(1,2),(1,3),(2,3))
    if upper.startswith("C3D6") or upper.startswith("C3D15"):
        return 6, ((0,1,2),(3,5,4),(0,3,4,1),(1,4,5,2),(2,5,3,0)), ((0,1),(1,2),(2,0),(3,4),(4,5),(5,3),(0,3),(1,4),(2,5))
    if upper.startswith("C3D8") or upper.startswith("C3D20"):
        return 8, ((0,1,2,3),(4,7,6,5),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)), ((0,1),(1,2),(2,3),(3,0),(4,5),(5,6),(6,7),(7,4),(0,4),(1,5),(2,6),(3,7))
    return None


def expected_node_count(element_type):
    upper = ci(element_type)
    for prefix, count in (
        ("C3D20", 20), ("C3D15", 15), ("C3D10", 10),
        ("C3D8", 8), ("C3D6", 6), ("C3D4", 4),
    ):
        if upper.startswith(prefix):
            return count
    return None


def midside_edge_spec(element_type):
    upper = ci(element_type)
    if upper.startswith("C3D10"):
        return ((4,0,1),(5,1,2),(6,2,0),(7,0,3),(8,1,3),(9,2,3))
    if upper.startswith("C3D15"):
        return ((6,0,1),(7,1,2),(8,2,0),(9,3,4),(10,4,5),(11,5,3),(12,0,3),(13,1,4),(14,2,5))
    if upper.startswith("C3D20"):
        return ((8,0,1),(9,1,2),(10,2,3),(11,3,0),(12,4,5),(13,5,6),(14,6,7),(15,7,4),(16,0,4),(17,1,5),(18,2,6),(19,3,7))
    return ()


def mesh_topology(owner):
    result = {}
    for element in owner.elements:
        label = int(element.label)
        nodes = element_nodes(owner, element)
        if label in result or not nodes:
            return None
        result[label] = (ci(element.type), tuple(int(node.label) for node in nodes))
    return result


def polygon_area(coords, labels):
    points = [coords[label] for label in labels]
    if len(points) < 3:
        return 0.0
    area = 0.0
    origin = points[0]
    for index in range(1, len(points) - 1):
        a = tuple(points[index][axis] - origin[axis] for axis in range(3))
        b = tuple(points[index + 1][axis] - origin[axis] for axis in range(3))
        cross = (
            a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0],
        )
        area += 0.5 * math.sqrt(builtins.sum(value * value for value in cross))
    return area


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


def percentile(values, fraction):
    ordered = sorted(float(value) for value in values)
    position = fraction * (len(ordered) - 1)
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def audit_geometry(part):
    if "DEFORMABLE" not in ci(getattr(part, "type", "")):
        return fail("the beam part is not deformable")
    if not len(part.cells):
        if len(part.nodes) and len(part.elements):
            return {"source": "orphan_mesh", "volume": None, "centroid": None}
        return fail("the beam part contains neither solid geometry nor a solid mesh")
    try:
        properties = part.getMassProperties(useMesh=False)
        volume = float(properties["volume"])
        centroid = tuple(float(value) for value in properties["volumeCentroid"])
    except Exception:
        return fail("native CAD volume properties are unreadable")
    if not close(volume, 10000.0, rel=1.0e-6, absolute=0.02):
        return fail("native CAD volume is not 10 x 10 x 100 mm")
    return {"source": "cad", "volume": volume, "centroid": centroid}


def audit_mesh(part, instance):
    part_coords = dict((int(node.label), tuple(float(v) for v in node.coordinates)) for node in part.nodes)
    instance_coords = dict((int(node.label), tuple(float(v) for v in node.coordinates)) for node in instance.nodes)
    if not part_coords or set(part_coords) != set(instance_coords):
        return fail("part and assembly meshes are unavailable or label-incompatible")
    part_topology = mesh_topology(part)
    instance_topology = mesh_topology(instance)
    if not part_topology or part_topology != instance_topology:
        return fail("part and assembly element topology/types are not identical")
    analysis_coords = instance_coords
    rows = list(analysis_coords.values())
    bounds = tuple((min(row[i] for row in rows), max(row[i] for row in rows)) for i in range(3))
    expected_bounds = ((0.0, 10.0), (0.0, 10.0), (0.0, 100.0))
    if any(not close(bounds[i][j], expected_bounds[i][j], rel=0.0, absolute=1.0e-7) for i in range(3) for j in range(2)):
        return fail("mesh bounds are not X/Y=0..10 and Z=0..100 mm")
    try:
        global_seed = float(part.getPartSeeds(SIZE))
    except Exception:
        global_seed = None
    if global_seed is not None and global_seed > 0.0 and not close(global_seed, 5.0, rel=0.0, absolute=0.15):
        return fail("saved Abaqus global mesh seed is not approximately 5 mm")
    face_owners = {}
    face_corners = {}
    face_nodes = {}
    neighbors = {}
    attached = set()
    edge_lengths = []
    total_volume = 0.0
    connectivity = {}
    for element in part.elements:
        label = int(element.label)
        if label in connectivity:
            return fail("mesh contains duplicate element labels")
        spec = corner_spec(element.type)
        nodes = element_nodes(part, element)
        expected_count = expected_node_count(element.type)
        if (
            spec is None or not ci(element.type).startswith(ALLOWED_TYPES)
            or expected_count is None or len(nodes) != expected_count
        ):
            return fail("unsupported or incomplete 3D continuum element: %s" % element.type)
        corners, faces, edges = spec
        element_labels = tuple(int(node.label) for node in nodes)
        labels = element_labels[:corners]
        if len(set(element_labels)) != len(element_labels) or any(label_value not in analysis_coords for label_value in element_labels):
            return fail("solid element connectivity is invalid")
        connectivity[label] = (ci(element.type), element_labels)
        neighbors[label] = set()
        attached.update(int(node.label) for node in nodes)
        points = [analysis_coords[value] for value in labels]
        volume = element_volume(points, corners)
        if not finite(volume) or volume <= 1.0e-9:
            return fail("solid element has zero or invalid volume")
        total_volume += volume
        for a, b in edges:
            edge_lengths.append(math.sqrt(builtins.sum((points[a][i] - points[b][i]) ** 2 for i in range(3))))
        for middle, a, b in midside_edge_spec(element.type):
            midpoint = tuple((analysis_coords[element_labels[a]][axis] + analysis_coords[element_labels[b]][axis]) / 2.0 for axis in range(3))
            if any(abs(analysis_coords[element_labels[middle]][axis] - midpoint[axis]) > 1.0e-7 for axis in range(3)):
                return fail("quadratic solid midside node is not at its straight-edge midpoint")
        for face in faces:
            key = frozenset(labels[index] for index in face)
            face_owners.setdefault(key, []).append(label)
            face_corners.setdefault(key, tuple(labels[index] for index in face))
            full_indices = list(face)
            for middle, a, b in midside_edge_spec(element.type):
                if a in face and b in face:
                    full_indices.append(middle)
            face_nodes.setdefault(key, []).append(tuple(element_labels[index] for index in full_indices))
    if attached != set(analysis_coords):
        return fail("mesh contains unattached nodes")
    if any(len(owners) > 2 for owners in face_owners.values()):
        return fail("mesh contains non-manifold solid faces")
    for face, owners in face_owners.items():
        if len(face_nodes.get(face, ())) != len(owners):
            return fail("solid face connectivity is incomplete")
        if len(owners) == 2 and frozenset(face_nodes[face][0]) != frozenset(face_nodes[face][1]):
            return fail("quadratic elements do not share identical full face connectivity")
    boundary_planes = (
        (0, 0.0), (0, 10.0), (1, 0.0), (1, 10.0),
        (2, 0.0), (2, 100.0),
    )
    expected_areas = {
        (0, 0.0): 1000.0, (0, 10.0): 1000.0,
        (1, 0.0): 1000.0, (1, 10.0): 1000.0,
        (2, 0.0): 100.0, (2, 100.0): 100.0,
    }
    actual_areas = dict((plane, 0.0) for plane in expected_areas)
    for face, owners in face_owners.items():
        if len(owners) != 1:
            continue
        planes = [
            (axis, value) for axis, value in boundary_planes
            if all(abs(analysis_coords[label][axis] - value) <= 1.0e-7 for label in face_nodes[face][0])
        ]
        if len(planes) != 1:
            return fail("mesh contains an internal hole or an off-domain exterior face")
        actual_areas[planes[0]] += polygon_area(analysis_coords, face_corners[face])
    if any(
        not close(actual_areas[plane], expected_areas[plane], rel=1.0e-6, absolute=0.02)
        for plane in expected_areas
    ):
        return fail("mesh exterior faces do not cover exactly the six beam surfaces")
    for owners in face_owners.values():
        if len(owners) == 2:
            neighbors[owners[0]].add(owners[1])
            neighbors[owners[1]].add(owners[0])
    pending = [next(iter(neighbors))] if neighbors else []
    reached = set()
    while pending:
        current = pending.pop()
        if current in reached:
            continue
        reached.add(current)
        pending.extend(neighbors[current] - reached)
    if reached != set(neighbors):
        return fail("beam mesh is not one face-connected 3D solid")
    if not close(total_volume, 10000.0, rel=1.0e-6, absolute=0.02):
        return fail("solid mesh does not fill the complete beam volume")
    if not edge_lengths:
        return fail("mesh edge lengths are unavailable")
    median = percentile(edge_lengths, 0.5)
    p90 = percentile(edge_lengths, 0.9)
    if min(edge_lengths) < 1.0 or not (3.4 <= median <= 6.6) or p90 > 8.8 or max(edge_lengths) > 10.2:
        return fail("actual solid mesh is inconsistent with an approximately 5 mm global target")
    fixed = set(label for label, xyz in analysis_coords.items() if abs(xyz[2]) <= 1.0e-7)
    load = set(label for label, xyz in analysis_coords.items() if all(abs(xyz[i] - (5.0, 10.0, 100.0)[i]) <= 1.0e-7 for i in range(3)))
    if not fixed or len(load) != 1:
        return fail("mesh does not expose the complete Z=0 face and unique load point")
    return {
        "coords": analysis_coords,
        "connectivity": connectivity,
        "fixed": fixed,
        "load": next(iter(load)),
        "edge_statistics": {"minimum": min(edge_lengths), "median": median, "p90": p90, "maximum": max(edge_lengths)},
        "volume": total_volume,
    }


def audit_material(model, part):
    steel_names = set()
    for name in model.materials.keys():
        material = model.materials[name]
        try:
            elastic_rows = list(material.elastic.table)
            e_value, nu_value = elastic_rows[0][:2]
        except Exception:
            continue
        dependencies = int(getattr(material.elastic, "dependencies", 0) or 0)
        elastic_type = ci(getattr(material.elastic, "type", "ISOTROPIC"))
        no_compression = bool(getattr(material.elastic, "noCompression", False))
        no_tension = bool(getattr(material.elastic, "noTension", False))
        if (
            len(elastic_rows) == 1 and dependencies == 0 and elastic_type in ("", "ISOTROPIC")
            and not no_compression and not no_tension
            and close(e_value, 210000.0, rel=1.0e-6) and close(nu_value, 0.3, rel=1.0e-6)
        ):
            steel_names.add(ci(name))
    if not steel_names:
        return fail("no linear elastic material has E=210000 MPa and nu=0.3")
    try:
        assignments = list(part.sectionAssignments)
    except Exception:
        return fail("solid section assignments are unreadable")
    if not assignments:
        return fail("the beam has no solid section assignment")
    covered_cells = set()
    covered_elements = set()
    for assignment in assignments:
        try:
            section = model.sections[assignment.sectionName]
        except Exception:
            return fail("an assigned section is missing")
        if "SOLID" not in ci(section.__class__.__name__) or ci(getattr(section, "material", "")) not in steel_names:
            return fail("every assigned section must use the specified elastic steel")
        cells = entity_cells(resolve_region(part, assignment.region))
        elements = entity_elements(resolve_region(part, assignment.region))
        covered_cells.update(int(cell.index) for cell in cells)
        covered_elements.update(int(element.label) for element in elements)
    complete_cells = bool(len(part.cells)) and covered_cells == set(int(cell.index) for cell in part.cells)
    complete_elements = bool(len(part.elements)) and covered_elements == set(int(element.label) for element in part.elements)
    coverage_readable = bool(covered_cells or covered_elements)
    if coverage_readable and not complete_cells and not complete_elements:
        return fail("specified steel section does not cover the complete beam")
    for name in model.materials.keys():
        if ci(name) not in steel_names:
            continue
        material = model.materials[name]
        for attr in ("plastic", "hyperelastic", "hyperfoam", "viscoelastic", "creep", "damageInitiation"):
            try:
                prop = getattr(material, attr)
                table = getattr(prop, "table", ())
                if prop is not None and (not hasattr(prop, "table") or len(table)):
                    return fail("assigned steel material contains a non-linear constitutive property: %s" % attr)
            except Exception:
                pass
    return {"steel_names": sorted(steel_names), "coverage": "cells" if complete_cells else ("elements" if complete_elements else "deferred_to_fresh_input")}


def history_value(obj, step_name, attr):
    candidates = [obj]
    try:
        candidates.append(obj.getState(step_name))
    except Exception:
        pass
    for candidate in reversed(candidates):
        if candidate is None:
            continue
        value = getattr(candidate, attr, None)
        if value is not None:
            return value
    return None


def history_state(obj, step_name):
    try:
        return obj.getState(step_name)
    except Exception:
        return None


def repository_state(model, step_name, repository_name, object_name):
    step = repository_value_ci(model.steps, step_name)
    if step is None:
        return None
    return repository_value_ci(getattr(step, repository_name, {}), object_name)


def first_value(objects, attr):
    for obj in objects:
        if obj is None:
            continue
        try:
            value = getattr(obj, attr)
        except Exception:
            continue
        if value is not None:
            if ci(value) == "UNCHANGED":
                continue
            return value
    return None


def state_is_active(state):
    status = ci(getattr(state, "status", ""))
    return not any(token in status for token in ("DEACTIVATED", "INACTIVE", "SUPPRESSED", "NOT_YET_ACTIVE"))


def amplitude_final_factor(model, amplitude_name, step):
    if amplitude_name is None or ci(amplitude_name) in ("", "UNSET"):
        return 1.0
    amplitude = repository_value_ci(model.amplitudes, amplitude_name)
    if amplitude is None:
        return None
    class_name = ci(amplitude.__class__.__name__)
    if "TABULAR" not in class_name and "SMOOTHSTEP" not in class_name:
        return None
    try:
        rows = [(float(row[0]), float(row[1])) for row in amplitude.data]
        target = float(step.timePeriod)
    except Exception:
        return None
    if not rows or any(not finite(value) for row in rows for value in row):
        return None
    if any(rows[index][0] <= rows[index - 1][0] for index in range(1, len(rows))):
        return None
    if target <= rows[0][0]:
        final_value = rows[0][1]
    elif target >= rows[-1][0]:
        final_value = rows[-1][1]
    else:
        final_value = None
        for index in range(1, len(rows)):
            left, right = rows[index - 1], rows[index]
            if left[0] <= target <= right[0]:
                fraction = (target - left[0]) / (right[0] - left[0])
                if "SMOOTHSTEP" in class_name:
                    fraction = fraction ** 3 * (10.0 - 15.0 * fraction + 6.0 * fraction ** 2)
                final_value = left[1] + fraction * (right[1] - left[1])
                break
        if final_value is None:
            return None
    return final_value if finite(final_value) else None


def audit_process(model, instance, mesh_info):
    real_steps = [name for name in model.steps.keys() if ci(name) != "INITIAL"]
    if len(real_steps) != 1 or "STATIC" not in ci(model.steps[real_steps[0]].__class__.__name__):
        return fail("model must contain exactly one Static, General analysis step")
    step_name = real_steps[0]
    constrained = set()
    active_bcs = []
    bc_debug = []
    for name in model.boundaryConditions.keys():
        bc = model.boundaryConditions[name]
        state = repository_state(model, step_name, "boundaryConditionStates", name) or history_state(bc, step_name)
        initial_state = repository_state(model, "Initial", "boundaryConditionStates", name)
        evidence = (state, initial_state, bc)
        if bool(getattr(bc, "suppressed", False)) or (state is not None and not state_is_active(state)):
            continue
        active_bcs.append(bc)
        bc_region = resolve_analysis_region(model, instance, getattr(bc, "region", None))
        bc_labels = set(int(node.label) for node in entity_nodes(bc_region))
        if not bc_labels or not bc_labels.issubset(mesh_info["fixed"]):
            return fail("a boundary condition acts outside the complete Z=0 face")
        if "ENCASTRE" in ci(bc.__class__.__name__):
            for label in bc_labels:
                for dof in (1, 2, 3):
                    constrained.add((label, dof))
            continue
        if "DISPLACEMENT" not in ci(bc.__class__.__name__):
            return fail("an unsupported boundary-condition type is present")
        bc_debug.append((
            ci(bc.__class__.__name__), sorted(bc_labels),
            [(attr, repr(getattr(bc, attr, None)), repr(first_value(evidence, attr))) for attr in ("u1", "u2", "u3")],
            repr(state),
        ))
        for dof, attr in enumerate(("u1", "u2", "u3"), 1):
            raw = first_value(evidence, attr)
            if raw is None or ci(raw) in ("UNSET", "FREED"):
                continue
            try:
                value = float(raw)
            except Exception:
                return fail("a translational boundary value is unreadable")
            if abs(value) > 1.0e-12:
                return fail("a translational boundary value is nonzero")
            for label in bc_labels:
                constrained.add((label, dof))
    expected_constraints = set((label, dof) for label in mesh_info["fixed"] for dof in (1, 2, 3))
    if not active_bcs or constrained != expected_constraints:
        return fail("boundary conditions do not set U1=U2=U3=0 on exactly the complete Z=0 face: constrained=%r expected=%r debug=%r" % (
            sorted(constrained), sorted(expected_constraints), bc_debug,
        ))
    active_loads = []
    for name in model.loads.keys():
        candidate = model.loads[name]
        if bool(getattr(candidate, "suppressed", False)):
            continue
        state = repository_state(model, step_name, "loadStates", name) or history_state(candidate, step_name)
        if state is not None and not state_is_active(state):
            continue
        active_loads.append((name, candidate, state))
    if len(active_loads) != 1 or "CONCENTRATEDFORCE" not in ci(active_loads[0][1].__class__.__name__):
        return fail("exactly one active ConcentratedForce is required")
    load_name, load, load_state = active_loads[0]
    load_evidence = (load_state, load)
    load_region = resolve_analysis_region(model, instance, load.region)
    load_labels = set(int(node.label) for node in entity_nodes(load_region))
    if load_labels != {mesh_info["load"]}:
        return fail("concentrated force is not applied only at (5,10,100)")
    values = tuple(first_value(load_evidence, attr) for attr in ("cf1", "cf2", "cf3"))
    converted = []
    for value in values:
        if value is None or ci(value) in ("UNSET", "FREED"):
            converted.append(0.0)
        else:
            try:
                converted.append(float(value))
            except Exception:
                return fail("concentrated force components are unreadable")
    local_csys = first_value(load_evidence, "localCsys")
    if local_csys is not None and ci(local_csys) not in ("", "NONE"):
        return fail("concentrated force is not expressed in the global coordinate system")
    follower = first_value(load_evidence, "follower")
    if follower is not None and ci(follower) in ("ON", "TRUE", "1", "1.0"):
        return fail("concentrated force must remain in the global -Y direction")
    distribution = first_value(load_evidence, "distributionType")
    if distribution is not None and ci(distribution) not in ("", "UNIFORM"):
        return fail("concentrated force uses an unsupported spatial distribution")
    amplitude_factor = amplitude_final_factor(model, first_value(load_evidence, "amplitude"), model.steps[step_name])
    if amplitude_factor is None:
        return fail("concentrated force amplitude is unreadable at the end of the static step")
    effective = tuple(value * amplitude_factor for value in converted)
    if not close(effective[1], -100.0, rel=1.0e-7, absolute=1.0e-7) or abs(effective[0]) > 1.0e-10 or abs(effective[2]) > 1.0e-10:
        return fail("final concentrated force is not exactly global CF2=-100 N")
    if len(model.interactions.keys()) or len(model.constraints.keys()) or len(model.predefinedFields.keys()):
        return fail("pressure, gravity, coupling, contact, or other substitute state is not allowed")
    return {"step_name": step_name}


def odb_mesh(odb):
    populated = []
    for name in odb.rootAssembly.instances.keys():
        instance = odb.rootAssembly.instances[name]
        if len(instance.nodes) or len(instance.elements):
            populated.append((name, instance))
    if len(populated) != 1:
        return None
    name, instance = populated[0]
    coords = dict((int(node.label), tuple(float(value) for value in node.coordinates)) for node in instance.nodes)
    connectivity = dict((int(element.label), (ci(element.type), tuple(int(value) for value in element.connectivity))) for element in instance.elements)
    return ci(name), coords, connectivity


def field_signature(field):
    rows = []
    for value in field.values:
        data = tuple(float(item) for item in field_value_data(value))
        if not data or any(not finite(item) for item in data):
            return None
        rows.append((
            ci(getattr(getattr(value, "instance", None), "name", "ASSEMBLY")),
            int(getattr(value, "nodeLabel", getattr(value, "elementLabel", 0)) or 0),
            ci(getattr(value, "position", "")),
            int(getattr(value, "integrationPoint", 0) or 0),
            data,
        ))
    return sorted(rows)


def field_value_data(value):
    for attr in ("data", "dataDouble"):
        try:
            found = numbers(getattr(value, attr))
            if found:
                return found
        except Exception:
            pass
    return []


def field_value_mises(value):
    for attr in ("mises", "misesDouble"):
        try:
            found = float(getattr(value, attr))
            if finite(found):
                return found
        except Exception:
            pass
    return None


def odb_result(path, expected_coords, expected_connectivity, load_label):
    odb = openOdb(path=path, readOnly=True)
    try:
        status = ci(getattr(odb.diagnosticData, "jobStatus", ""))
        if "COMPLETED_SUCCESSFULLY" not in status and status != "COMPLETED":
            return fail("ODB job status is not completed successfully")
        if len(odb.steps.keys()) != 1:
            return fail("ODB must contain exactly one analysis step")
        step = odb.steps[odb.steps.keys()[0]]
        if not step.frames:
            return fail("ODB contains no completed result frame")
        mesh = odb_mesh(odb)
        if mesh is None:
            return fail("ODB does not contain exactly one populated solid instance")
        instance_name, coords, connectivity = mesh
        if set(coords) != set(expected_coords) or any(any(not close(coords[label][i], expected_coords[label][i], rel=0.0, absolute=1.0e-9) for i in range(3)) for label in coords):
            return fail("CAE and ODB node coordinates are not identical")
        if connectivity != expected_connectivity:
            return fail("CAE and ODB element topology/types are not identical")
        frame = step.frames[-1]
        if "U" not in frame.fieldOutputs.keys() or "S" not in frame.fieldOutputs.keys():
            return fail("ODB final frame lacks U or S field output")
        u_signature = field_signature(frame.fieldOutputs["U"])
        s_signature = field_signature(frame.fieldOutputs["S"])
        if u_signature is None or s_signature is None:
            return fail("ODB U/S fields contain missing or non-finite data")
        tip_values = [
            value for value in frame.fieldOutputs["U"].values
            if ci(getattr(getattr(value, "instance", None), "name", "")) == instance_name
            and int(getattr(value, "nodeLabel", -1)) == int(load_label)
        ]
        if len(tip_values) != 1:
            return fail("ODB has no unique U result at the load node")
        tip_data = field_value_data(tip_values[0])
        if len(tip_data) < 3:
            return fail("ODB load-node displacement vector is incomplete")
        tip = float(tip_data[1])
        if not (-0.35 <= tip <= -0.08):
            return fail("native signed tip UY is outside the Task-11 physical range")
        mises = []
        covered = set()
        for value in frame.fieldOutputs["S"].values:
            if ci(getattr(getattr(value, "instance", None), "name", "")) != instance_name:
                continue
            if "INTEGRATION_POINT" not in ci(getattr(value, "position", "")):
                continue
            candidate = field_value_mises(value)
            if candidate is not None and finite(candidate):
                mises.append(float(candidate))
                covered.add(int(value.elementLabel))
        if not mises or covered != set(expected_connectivity):
            return fail("ODB integration-point Mises output does not cover every beam element")
        max_mises = max(mises)
        if not (10.0 <= max_mises <= 1000.0):
            return fail("native ODB maximum integration-point Mises is outside the Task-11 range")
        return {
            "metrics": {"tip_displacement": tip, "max_mises": max_mises},
            "signature": {"u": u_signature, "s": s_signature},
            "instance": instance_name,
        }
    finally:
        odb.close()


def signatures_match(left, right):
    for name in ("u", "s"):
        a = left[name]
        b = right[name]
        if len(a) != len(b):
            return False
        for row_a, row_b in zip(a, b):
            if row_a[:-1] != row_b[:-1] or len(row_a[-1]) != len(row_b[-1]):
                return False
            if any(not close(x, y, rel=5.0e-4, absolute=2.0e-7) for x, y in zip(row_a[-1], row_b[-1])):
                return False
    return True


def input_keyword(line):
    fields = [field.strip() for field in line.strip()[1:].split(",")]
    name = fields[0].upper()
    params = {}
    flags = set()
    for field in fields[1:]:
        if "=" in field:
            key, value = field.split("=", 1)
            params[key.strip().upper()] = value.strip()
        elif field:
            flags.add(field.upper())
    return name, params, flags


def audit_input_sections(input_path, expected_elements, steel_names):
    with open(input_path, "r") as stream:
        lines = stream.readlines()
    elsets = {}
    sections = []
    current = None
    element_continuation = False
    for raw in lines:
        stripped = raw.strip()
        if stripped.startswith("*") and not stripped.startswith("**"):
            name, params, flags = input_keyword(stripped)
            current = None
            element_continuation = False
            if name == "ELSET" and params.get("ELSET"):
                current = (params["ELSET"].upper(), "GENERATE" if "GENERATE" in flags else "ELSET")
                elsets.setdefault(current[0], [])
            elif name == "ELEMENT" and params.get("ELSET"):
                current = (params["ELSET"].upper(), "ELEMENT")
                elsets.setdefault(current[0], [])
            elif name == "SOLID SECTION":
                sections.append((params.get("ELSET", "").upper(), params.get("MATERIAL", "").upper()))
            continue
        if current is None or not stripped or stripped.startswith("**"):
            continue
        tokens = [token.strip() for token in stripped.split(",") if token.strip()]
        if current[1] == "ELEMENT":
            if not element_continuation:
                try:
                    elsets[current[0]].append(int(tokens[0]))
                except Exception:
                    return fail("fresh input contains an invalid element label")
            element_continuation = raw.rstrip().endswith(",")
        elif current[1] == "GENERATE":
            try:
                values = [int(token) for token in tokens]
            except Exception:
                return fail("fresh input contains an invalid generated element set")
            if len(values) % 3:
                return fail("fresh input contains an incomplete generated element set")
            for index in range(0, len(values), 3):
                start, end, increment = values[index:index + 3]
                if increment <= 0 or end < start:
                    return fail("fresh input contains an invalid generated element-set range")
                elsets[current[0]].extend(range(start, end + 1, increment))
        else:
            for token in tokens:
                try:
                    elsets[current[0]].append(int(token))
                except Exception:
                    elsets[current[0]].append(token.upper())

    def resolve(name, pending):
        if name in pending or name not in elsets:
            return None
        result = set()
        for value in elsets[name]:
            if isinstance(value, int):
                result.add(value)
            else:
                nested = resolve(value, pending | {name})
                if nested is None:
                    return None
                result.update(nested)
        return result

    if not sections:
        return fail("fresh input contains no solid section")
    covered = set()
    for elset_name, material_name in sections:
        if material_name not in set(steel_names):
            return fail("fresh input assigns a non-specified material to solid elements")
        labels = resolve(elset_name, set())
        if labels is None:
            return fail("fresh input solid-section element set is unresolved")
        covered.update(labels)
    if covered != set(expected_elements):
        return fail("fresh input steel solid sections do not cover exactly every beam element")
    return {"covered_elements": len(covered), "section_count": len(sections)}


def main():
    ok = False
    report = {}
    try:
        openMdb(pathName=CAE_PATH)
        populated_models = []
        for name in mdb.models.keys():
            model = mdb.models[name]
            populated_parts = [model.parts[key] for key in model.parts.keys() if len(model.parts[key].elements)]
            populated_instances = [model.rootAssembly.instances[key] for key in model.rootAssembly.instances.keys() if len(model.rootAssembly.instances[key].elements)]
            if populated_parts or populated_instances:
                populated_models.append((name, model, populated_parts, populated_instances))
        if len(populated_models) != 1:
            raise RuntimeError("CAE must contain exactly one populated analysis model")
        model_name, model, parts, instances = populated_models[0]
        if len(parts) != 1 or len(instances) != 1:
            raise RuntimeError("analysis model must contain one meshed beam part and one instance")
        if bool(getattr(model.keywordBlock, "edited", False)):
            raise RuntimeError("CAE keywordBlock contains manual edits")
        part = parts[0]
        instance = instances[0]
        geometry = audit_geometry(part)
        mesh_info = audit_mesh(part, instance)
        material = audit_material(model, part)
        process = audit_process(model, instance, mesh_info) if mesh_info else None
        if not geometry or not mesh_info or not material or not process:
            raise RuntimeError("CAE model semantics failed")
        expected_connectivity = mesh_info["connectivity"]
        submitted = odb_result(ODB_PATH, mesh_info["coords"], expected_connectivity, mesh_info["load"])
        if not submitted:
            raise RuntimeError("submitted ODB audit failed")
        for name in ("tip_displacement", "max_mises"):
            tolerance = 2.0e-7 if name == "tip_displacement" else 2.0e-5
            if not close(submitted["metrics"][name], METRICS[name], rel=2.0e-5, absolute=tolerance):
                raise RuntimeError("metrics.json %s does not match the native ODB" % name)
        os.chdir(AUDIT_ROOT)
        audit_job_name = "Task11-Eval-Source-" + JOB_SUFFIX
        if audit_job_name in mdb.jobs.keys():
            del mdb.jobs[audit_job_name]
        audit_job = mdb.Job(
            name=audit_job_name, model=model_name, numCpus=1, numDomains=1,
            scratch=AUDIT_ROOT,
        )
        audit_job.writeInput(consistencyChecking=ON)
        input_path = os.path.join(AUDIT_ROOT, audit_job_name + ".inp")
        if not os.path.isfile(input_path) or os.path.getsize(input_path) <= 0:
            raise RuntimeError("CAE could not generate a fresh input deck")
        with open(input_path, "r") as stream:
            deck_upper = stream.read().upper()
        forbidden_keywords = (
            "*PLASTIC", "*HYPERELASTIC", "*HYPERFOAM", "*VISCOELASTIC",
            "*CREEP", "*DAMAGE INITIATION", "*INITIAL CONDITIONS", "*GRAVITY",
            "*DLOAD", "*DSLOAD", "*PRESSURE PENETRATION", "*COUPLING", "*CONTACT",
        )
        if any(keyword in deck_upper for keyword in forbidden_keywords):
            raise RuntimeError("fresh CAE input contains a non-linear material or substitute load/interaction")
        input_sections = audit_input_sections(input_path, set(mesh_info["connectivity"]), material["steel_names"])
        if not input_sections:
            raise RuntimeError("fresh CAE input section coverage failed")
        input_hash = file_sha256(input_path)
        frozen_path = os.path.join(SOLVE_ROOT, "task11_frozen.inp")
        shutil.copyfile(input_path, frozen_path)
        if file_sha256(frozen_path) != input_hash:
            raise RuntimeError("frozen input deck differs from the audited CAE deck")
        os.chdir(SOLVE_ROOT)
        recheck_name = "Task11-Eval-Recheck-" + JOB_SUFFIX
        recheck_job = mdb.JobFromInputFile(
            name=recheck_name, inputFileName=frozen_path, numCpus=1,
            numDomains=1, scratch=SOLVE_ROOT,
        )
        recheck_job.submit(consistencyChecking=ON)
        recheck_job.waitForCompletion()
        fresh_odb = os.path.join(SOLVE_ROOT, recheck_name + ".odb")
        if not os.path.isfile(fresh_odb) or os.path.getsize(fresh_odb) <= 0:
            raise RuntimeError("isolated CAE re-solve did not produce an ODB")
        post_odb = os.path.join(POST_ROOT, "recomputed.odb")
        shutil.copyfile(fresh_odb, post_odb)
        os.chdir(POST_ROOT)
        rechecked = odb_result(post_odb, mesh_info["coords"], expected_connectivity, mesh_info["load"])
        if not rechecked or not signatures_match(submitted["signature"], rechecked["signature"]):
            raise RuntimeError("submitted ODB fields do not match an isolated CAE re-solve")
        for name in ("tip_displacement", "max_mises"):
            tolerance = 2.0e-7 if name == "tip_displacement" else 5.0e-4
            if not close(submitted["metrics"][name], rechecked["metrics"][name], rel=5.0e-4, absolute=tolerance):
                raise RuntimeError("submitted ODB %s does not match the isolated CAE re-solve" % name)
        if file_sha256(input_path) != input_hash or file_sha256(frozen_path) != input_hash:
            raise RuntimeError("audited input deck changed during evaluation")
        report = {
            "geometry": geometry,
            "mesh": {"volume": mesh_info["volume"], "edge_statistics": mesh_info["edge_statistics"]},
            "material": material,
            "input_sections": input_sections,
            "process": process,
            "native_metrics": submitted["metrics"],
            "recomputed_metrics": rechecked["metrics"],
            "input_sha256": input_hash,
        }
        ok = True
    except Exception:
        DETAILS.append(traceback.format_exc())
        ok = False
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
    audit_job_name = "Task11-Eval-Source-" + token[:12]
    recheck_job_name = "Task11-Eval-Recheck-" + token[:12]
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
        control_root = Path(tempfile.mkdtemp(prefix="eval_cli_task11_abaqus_control_%s_" % token))
        audit_root = Path(tempfile.mkdtemp(prefix="eval_cli_task11_abaqus_audit_%s_" % token))
        submitted_root = Path(tempfile.mkdtemp(prefix="eval_cli_task11_abaqus_submitted_%s_" % token))
        solve_root = Path(tempfile.mkdtemp(prefix="eval_cli_task11_abaqus_solve_%s_" % token))
        post_root = Path(tempfile.mkdtemp(prefix="eval_cli_task11_abaqus_post_%s_" % token))
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


def ansys_corner_spec(code):
    if int(code) == 187:
        return 4, ((0,1),(0,2),(0,3),(1,2),(1,3),(2,3)), ((0,1,2),(0,3,1),(1,3,2),(2,3,0))
    if int(code) in (185, 186):
        return 8, ((0,1),(1,2),(2,3),(3,0),(4,5),(5,6),(6,7),(7,4),(0,4),(1,5),(2,6),(3,7)), ((0,1,2,3),(4,7,6,5),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0))
    return None


def ansys_expected_node_count(code):
    return {185: 8, 186: 20, 187: 10}.get(int(code))


def ansys_midside_edge_spec(code):
    if int(code) == 187:
        return ((4,0,1),(5,1,2),(6,2,0),(7,0,3),(8,1,3),(9,2,3))
    if int(code) == 186:
        return ((8,0,1),(9,1,2),(10,2,3),(11,3,0),(12,4,5),(13,5,6),(14,6,7),(15,7,4),(16,0,4),(17,1,5),(18,2,6),(19,3,7))
    return ()


def tet_volume(a, b, c, d):
    ab = tuple(b[i] - a[i] for i in range(3))
    ac = tuple(c[i] - a[i] for i in range(3))
    ad = tuple(d[i] - a[i] for i in range(3))
    cross = (
        ac[1] * ad[2] - ac[2] * ad[1],
        ac[2] * ad[0] - ac[0] * ad[2],
        ac[0] * ad[1] - ac[1] * ad[0],
    )
    return abs(sum(ab[i] * cross[i] for i in range(3))) / 6.0


def solid_volume(points, corners):
    if corners == 4:
        return tet_volume(points[0], points[1], points[2], points[3])
    return (
        tet_volume(points[0], points[1], points[3], points[4])
        + tet_volume(points[1], points[2], points[3], points[6])
        + tet_volume(points[1], points[3], points[4], points[6])
        + tet_volume(points[1], points[4], points[5], points[6])
        + tet_volume(points[3], points[4], points[6], points[7])
    )


def ansys_polygon_area(coords, labels):
    points = [coords[label] for label in labels]
    if len(points) < 3:
        return 0.0
    area = 0.0
    origin = points[0]
    for index in range(1, len(points) - 1):
        a = tuple(points[index][axis] - origin[axis] for axis in range(3))
        b = tuple(points[index + 1][axis] - origin[axis] for axis in range(3))
        cross = (
            a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0],
        )
        area += 0.5 * math.sqrt(sum(value * value for value in cross))
    return area


def percentile(values, fraction):
    ordered = sorted(float(value) for value in values)
    position = fraction * (len(ordered) - 1)
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def audit_ansys_mesh(coords, elements):
    if not coords or not elements:
        log("ANSYS mesh is empty")
        return None
    rows = list(coords.values())
    bounds = tuple((min(row[i] for row in rows), max(row[i] for row in rows)) for i in range(3))
    expected = ((0.0, 10.0), (0.0, 10.0), (0.0, 100.0))
    if any(not close_enough(bounds[i][j], expected[i][j], rel=0.0, abs_tol=1.0e-7) for i in range(3) for j in range(2)):
        log("ANSYS mesh bounds are not X/Y=0..10 and Z=0..100 mm")
        return None
    face_owners = {}
    face_corners = {}
    face_nodes = {}
    neighbors = {}
    attached = set()
    edge_lengths = []
    volume = 0.0
    for label, (code, connectivity) in elements.items():
        spec = ansys_corner_spec(code)
        expected_count = ansys_expected_node_count(code)
        if spec is None or expected_count is None or len(connectivity) != expected_count:
            log("ANSYS mesh contains a non-SOLID185/186/187 element: label=%s code=%s nodes=%s" % (label, code, len(connectivity)))
            return None
        corners, edges, faces = spec
        labels = tuple(connectivity[:corners])
        if len(set(connectivity)) != len(connectivity) or any(node not in coords for node in connectivity):
            log("ANSYS solid element connectivity is invalid")
            return None
        points = [coords[node] for node in labels]
        value = solid_volume(points, corners)
        if not finite_number(value) or value <= 1.0e-9:
            log("ANSYS solid element has invalid volume")
            return None
        volume += value
        attached.update(connectivity)
        neighbors[label] = set()
        for a, b in edges:
            edge_lengths.append(math.sqrt(sum((points[a][i] - points[b][i]) ** 2 for i in range(3))))
        for middle, a, b in ansys_midside_edge_spec(code):
            midpoint = tuple((coords[connectivity[a]][axis] + coords[connectivity[b]][axis]) / 2.0 for axis in range(3))
            if any(abs(coords[connectivity[middle]][axis] - midpoint[axis]) > 1.0e-7 for axis in range(3)):
                log("ANSYS quadratic solid midside node is not at its straight-edge midpoint")
                return None
        for face in faces:
            key = frozenset(labels[index] for index in face)
            face_owners.setdefault(key, []).append(label)
            face_corners.setdefault(key, tuple(labels[index] for index in face))
            full_indices = list(face)
            for middle, a, b in ansys_midside_edge_spec(code):
                if a in face and b in face:
                    full_indices.append(middle)
            face_nodes.setdefault(key, []).append(tuple(connectivity[index] for index in full_indices))
    if attached != set(coords):
        log("ANSYS mesh contains unattached nodes")
        return None
    if any(len(owners) > 2 for owners in face_owners.values()):
        log("ANSYS mesh contains non-manifold faces")
        return None
    for face, owners in face_owners.items():
        if len(face_nodes.get(face, ())) != len(owners):
            log("ANSYS solid face connectivity is incomplete")
            return None
        if len(owners) == 2 and frozenset(face_nodes[face][0]) != frozenset(face_nodes[face][1]):
            log("ANSYS quadratic elements do not share identical full face connectivity")
            return None
    boundary_planes = (
        (0, 0.0), (0, 10.0), (1, 0.0), (1, 10.0),
        (2, 0.0), (2, 100.0),
    )
    expected_areas = {
        (0, 0.0): 1000.0, (0, 10.0): 1000.0,
        (1, 0.0): 1000.0, (1, 10.0): 1000.0,
        (2, 0.0): 100.0, (2, 100.0): 100.0,
    }
    actual_areas = dict((plane, 0.0) for plane in expected_areas)
    for face, owners in face_owners.items():
        if len(owners) != 1:
            continue
        planes = [
            (axis, value) for axis, value in boundary_planes
            if all(abs(coords[label][axis] - value) <= 1.0e-7 for label in face_nodes[face][0])
        ]
        if len(planes) != 1:
            log("ANSYS mesh contains an internal hole or an off-domain exterior face")
            return None
        actual_areas[planes[0]] += ansys_polygon_area(coords, face_corners[face])
    if any(
        not close_enough(actual_areas[plane], expected_areas[plane], rel=1.0e-6, abs_tol=0.02)
        for plane in expected_areas
    ):
        log("ANSYS exterior faces do not cover exactly the six beam surfaces")
        return None
    for owners in face_owners.values():
        if len(owners) == 2:
            neighbors[owners[0]].add(owners[1])
            neighbors[owners[1]].add(owners[0])
    pending = [next(iter(neighbors))]
    reached = set()
    while pending:
        current = pending.pop()
        if current in reached:
            continue
        reached.add(current)
        pending.extend(neighbors[current] - reached)
    if reached != set(neighbors):
        log("ANSYS beam mesh is not one face-connected solid")
        return None
    if not close_enough(volume, 10000.0, rel=1.0e-6, abs_tol=0.02):
        log("ANSYS mesh does not fill the complete beam volume")
        return None
    median = percentile(edge_lengths, 0.5)
    p90 = percentile(edge_lengths, 0.9)
    if min(edge_lengths) < 1.0 or not (3.4 <= median <= 6.6) or p90 > 8.8 or max(edge_lengths) > 10.2:
        log("ANSYS mesh is inconsistent with an approximately 5 mm global target")
        return None
    fixed = set(label for label, xyz in coords.items() if abs(xyz[2]) <= 1.0e-7)
    load = [label for label, xyz in coords.items() if all(abs(xyz[i] - (5.0, 10.0, 100.0)[i]) <= 1.0e-7 for i in range(3))]
    if not fixed or len(load) != 1:
        log("ANSYS mesh lacks the complete fixed face or unique load point")
        return None
    return {
        "fixed": fixed,
        "load": load[0],
        "volume": volume,
        "edge_statistics": {"minimum": min(edge_lengths), "median": median, "p90": p90, "maximum": max(edge_lengths)},
    }


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


def cdb_has_forbidden_state(text):
    forbidden = {
        "INISTATE", "INRES", "LDREAD", "LREAD", "UPGEOM",
        "BF", "BFA", "BFE", "BFEBLOCK", "BFBLOCK", "BFV",
        "SF", "SFA", "SFE", "SFEBLOCK", "SFBLOCK", "SFL",
        "CE", "CERIG", "CEINTF", "CP", "CPCYC", "CPINTF",
        "TBMODIF", "TBPT",
    }
    zero_commands = {
        "ACEL", "OMEGA", "DOMEGA", "CGOMEGA", "CGOMGA", "DCGOMG",
        "ALPHAD", "BETAD", "DMPRAT", "DMPSTR", "IRLF",
    }
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("!") or stripped.startswith("/"):
            continue
        fields = [field.strip() for field in stripped.split(",")]
        name = fields[0].upper()
        if name in forbidden:
            return True
        if name in zero_commands:
            values = []
            for token in fields[1:]:
                if not token:
                    continue
                try:
                    values.append(float(token.replace("D", "E").replace("d", "e")))
                except Exception:
                    return True
            if not values or any(abs(value) > 1.0e-12 for value in values):
                return True
        if name == "BFUNIF" and (
            len(fields) < 3 or fields[1].upper() != "TEMP" or any(token and token.upper() != "_TINY" for token in fields[2:])
        ):
            return True
    return False


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


def tb_isotropic_elastic_matches(tables):
    if len(tables) != 1:
        return False
    table = tables[0]
    if table["label"] not in ("ELASTIC", "ELAS") or table["option"] not in ("", "ISOT"):
        return False
    try:
        if table["ntemp"] and int(float(table["ntemp"])) != 1:
            return False
        if table["npts"] and int(float(table["npts"])) != 2:
            return False
    except Exception:
        return False
    temperatures = table["temperatures"]
    if len(temperatures) > 1 or any(abs(value) > 1.0e-12 for value in temperatures):
        return False
    if len(table["data"]) != 1:
        return False
    start, values = table["data"][0]
    return (
        start == 1
        and len(values) == 2
        and close_enough(values[0], 210000.0, rel=1.0e-6, abs_tol=1.0e-6)
        and close_enough(values[1], 0.3, rel=1.0e-6, abs_tol=1.0e-8)
    )


def ansys_element_formulation_is_allowed(elements, attributes, type_keyopts):
    allowed_values = {
        185: {2: {0, 1, 2, 3}, 3: {0}, 6: {0, 1}, 15: {0}, 16: {0}, 17: {0, 4}},
        186: {2: {0, 1}, 3: {0}, 6: {0, 1}, 15: {0}, 16: {0}, 17: {0, 4}},
        187: {6: {0, 1, 2}, 15: {0}, 16: {0}, 17: {0, 4}},
    }
    checked = set()
    for label, (code, _connectivity) in elements.items():
        type_id, _real_id, _section_id = attributes[label]
        if type_id in checked:
            continue
        checked.add(type_id)
        keyopts = type_keyopts.get(type_id, ())
        if len(keyopts) != 18 or code not in allowed_values:
            log("ANSYS element type has incomplete or unsupported KEYOPT metadata: type=%s code=%s" % (type_id, code))
            return False
        for number, value in enumerate(keyopts, 1):
            accepted = allowed_values[code].get(number, {0})
            if value not in accepted:
                log(
                    "ANSYS SOLID%s uses prohibited KEYOPT(%s)=%s on referenced type %s"
                    % (code, number, value, type_id)
                )
                return False
    return True


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


def audit_ansys_cdb(cdb_path, live_status_path):
    text = cdb_path.read_text(encoding="utf-8", errors="ignore")
    if cdb_has_forbidden_state(text):
        log("ANSYS DB contains a non-linear material, inertia, initial state, or extra load command")
        return None
    (
        coords, elements, element_attributes, type_keyopts, materials,
        properties, tb_tables, constraints, forces,
    ) = parse_ansys_cdb(text)
    if parse_ansys_live_status(live_status_path, elements) is None:
        return None
    if not ansys_element_formulation_is_allowed(elements, element_attributes, type_keyopts):
        return None
    mesh_info = audit_ansys_mesh(coords, elements)
    if mesh_info is None:
        return None
    structural_elastic_keys = {
        "EX", "EY", "EZ", "PRXY", "PRYZ", "PRXZ", "NUXY", "NUYZ", "NUXZ",
        "GXY", "GYZ", "GXZ",
    }
    for material_id in set(materials.values()):
        labels = set(label for mid, label in properties if mid == material_id)
        poisson_labels = labels & {"PRXY", "NUXY"}
        allowed_structural = {"EX"} | poisson_labels
        mp_structural = labels & structural_elastic_keys
        tb_defined = material_id in tb_tables
        if tb_defined and mp_structural:
            log("ANSYS assigned material mixes MP and TB structural elasticity")
            return None
        if tb_defined:
            if not tb_isotropic_elastic_matches(tb_tables[material_id]):
                log("ANSYS assigned TB material is not one temperature-independent ELASTIC/ISOT table with E=210000 MPa, nu=0.3")
                return None
            continue
        if not poisson_labels or mp_structural != allowed_structural:
            log("ANSYS assigned material contains extra or ambiguous structural elastic coefficients: %r" % sorted(labels))
            return None
        if (
            not close_enough(properties.get((material_id, "EX")), 210000.0, rel=1.0e-6, abs_tol=1.0e-6)
            or any(
                not close_enough(properties.get((material_id, poisson_label)), 0.3, rel=1.0e-6, abs_tol=1.0e-8)
                for poisson_label in poisson_labels
            )
        ):
            log("ANSYS assigned material is not E=210000 MPa, nu=0.3")
            return None
    expected_constraints = set(
        (node, dof, 0.0)
        for node in mesh_info["fixed"] for dof in ("UX", "UY", "UZ")
    )
    if set(constraints) != expected_constraints:
        log("ANSYS constraints are not exactly UX/UY/UZ=0 on the complete Z=0 face")
        return None
    if forces != [(mesh_info["load"], "FY", -100.0)]:
        log("ANSYS nodal load is not exactly FY=-100 at (5,10,100)")
        return None
    return {
        "coords": coords,
        "elements": elements,
        "materials": materials,
        "mesh_info": mesh_info,
    }


def write_ansys_export_input(path, model_path, export_stem, nonce):
    path.write_text("\n".join((
        "/BATCH",
        "/COM,TASK11_EXPORT_BEGIN_%s" % nonce,
        "RESUME,'%s','db'" % apdl_path(model_path.with_suffix("")),
        *ansys_resume_hardening_commands(),
        "FINISH",
        "/PREP7",
        "ALLSEL,ALL",
        "CSYS,0",
        "DSYS,0",
        "*GET,T11ECNT,ELEM,0,COUNT",
        "T11EID=0",
        "*CFOPEN,%s_live,txt" % export_stem,
        "*DO,T11I,1,T11ECNT",
        "T11EID=ELNEXT(T11EID)",
        "*GET,T11LIVE,ELEM,T11EID,ATTR,LIVE",
        "*VWRITE,T11EID,T11LIVE",
        "(F20.0,1X,E24.16)",
        "*ENDDO",
        "*CFCLOS",
        "CDWRITE,DB,%s,cdb" % export_stem,
        "FINISH",
        "/COM,TASK11_EXPORT_END_%s" % nonce,
        "/EXIT,NOSAVE",
        "",
    )), encoding="ascii")


def write_ansys_post_input(path, model_path, result_path, prefix, nonce, load_node):
    path.write_text("\n".join((
        "/BATCH",
        "/COM,TASK11_POST_BEGIN_%s" % nonce,
        "RESUME,'%s','db'" % apdl_path(model_path.with_suffix("")),
        *ansys_resume_hardening_commands(),
        "FINISH",
        "/POST1",
        "FILE,'%s','rst'" % apdl_path(result_path.with_suffix("")),
        "SET,LAST",
        "*GET,T11ANTY,ACTIVE,0,ANTY",
        "RSYS,0",
        "/GRAPHICS,FULL",
        "AVPRIN,0",
        "ALLSEL,ALL",
        "*GET,T11TIME,ACTIVE,0,SET,TIME",
        "*GET,T11NSET,ACTIVE,0,SET,NSET",
        "*GET,T11TIP,NODE,%d,U,Y" % int(load_node),
        "ESEL,ALL",
        "NSLE,S",
        "NSORT,S,EQV,0,1,ALL",
        "*GET,T11MISES,SORT,0,MAX",
        "ALLSEL,ALL",
        "NSEL,S,LOC,Z,0",
        "FSUM",
        "*GET,T11FX,FSUM,0,ITEM,FX",
        "*GET,T11FY,FSUM,0,ITEM,FY",
        "*GET,T11FZ,FSUM,0,ITEM,FZ",
        "*GET,T11MX,FSUM,0,ITEM,MX",
        "*GET,T11MY,FSUM,0,ITEM,MY",
        "*GET,T11MZ,FSUM,0,ITEM,MZ",
        "ALLSEL,ALL",
        "/OUTPUT,%s_u,txt" % prefix,
        "PRNSOL,U,COMP",
        "/OUTPUT",
        "/OUTPUT,%s_s,txt" % prefix,
        "PRNSOL,S,PRIN",
        "/OUTPUT",
        "*CFOPEN,%s_metrics,json" % prefix,
        "*VWRITE",
        "('{')",
        "*VWRITE,T11TIME,T11NSET,T11ANTY,T11TIP,T11MISES",
        "('  \"time\": ',E24.16,', \"result_sets\": ',E24.16,', \"analysis_type\": ',E24.16,', \"tip_displacement\": ',E24.16,', \"max_mises\": ',E24.16,',')",
        "*VWRITE,T11FX,T11FY,T11FZ",
        "('  \"force\": [',E24.16,',',E24.16,',',E24.16,'],')",
        "*VWRITE,T11MX,T11MY,T11MZ",
        "('  \"moment\": [',E24.16,',',E24.16,',',E24.16,']')",
        "*VWRITE",
        "('}')",
        "*CFCLOS",
        "FINISH",
        "/COM,TASK11_POST_END_%s" % nonce,
        "/EXIT,NOSAVE",
        "",
    )), encoding="ascii")


def write_ansys_resolve_input(path, model_path, nonce):
    path.write_text("\n".join((
        "/BATCH",
        "/COM,TASK11_RESOLVE_BEGIN_%s" % nonce,
        "RESUME,'%s','db'" % apdl_path(model_path.with_suffix("")),
        *ansys_resume_hardening_commands(),
        "FINISH",
        "/SOLU",
        "ANTYPE,STATIC,NEW",
        "NLGEOM,OFF",
        "EQSLV,SPARSE",
        "NSUBST,1,1,1",
        "OUTRES,ALL,ALL",
        "ALLSEL,ALL",
        "SOLVE",
        "FINISH",
        "/COM,TASK11_RESOLVE_END_%s" % nonce,
        "/EXIT,NOSAVE",
        "",
    )), encoding="ascii")


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
    scalar = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[DE][+-]?\d+)?"
    row_pattern = re.compile(
        r"^\s*(\d+)\s+" + r"\s*".join("(%s)" % scalar for _ in range(columns)) + r"\s*$",
        re.IGNORECASE,
    )
    for raw in text.splitlines():
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
            "parsed=%d expected=%d missing=%r unexpected=%r samples=%r" % (
                path.name, len(rows), len(expected_nodes), missing[:20],
                unexpected[:20], numeric_samples,
            )
        )
    return rows


def read_ansys_post_payload(root, prefix, expected_nodes):
    metrics_path = root / (prefix + "_metrics.json")
    if not is_nonempty(metrics_path):
        raise RuntimeError("ANSYS post metrics were not written")
    payload = json.loads(metrics_path.read_text(encoding="utf-8-sig"))
    if set(payload) != {"time", "result_sets", "analysis_type", "tip_displacement", "max_mises", "force", "moment"}:
        raise RuntimeError("ANSYS post metrics have unexpected keys")
    if any(not finite_number(payload[name]) for name in ("time", "result_sets", "analysis_type", "tip_displacement", "max_mises")):
        raise RuntimeError("ANSYS post scalar is non-finite")
    for name in ("force", "moment"):
        if not isinstance(payload[name], list) or len(payload[name]) != 3 or any(not finite_number(value) for value in payload[name]):
            raise RuntimeError("ANSYS post %s vector is invalid" % name)
        payload[name] = tuple(float(value) for value in payload[name])
    payload["tip_displacement"] = float(payload["tip_displacement"])
    payload["max_mises"] = float(payload["max_mises"])
    payload["analysis_type"] = float(payload["analysis_type"])
    payload["u"] = parse_ansys_numeric_listing(root / (prefix + "_u.txt"), 4, expected_nodes)
    payload["s"] = parse_ansys_numeric_listing(root / (prefix + "_s.txt"), 5, expected_nodes)
    return payload


def ansys_post_is_task11(payload):
    if not close_enough(payload["analysis_type"], 0.0, rel=0.0, abs_tol=1.0e-12):
        log("ANSYS submitted result set is not a static structural analysis")
        return False
    if not (-0.35 <= payload["tip_displacement"] <= -0.08):
        log("ANSYS native signed tip UY is outside the Task-11 physical range")
        return False
    if not (10.0 <= payload["max_mises"] <= 1000.0):
        log("ANSYS native maximum nodally averaged SEQV is outside the Task-11 range")
        return False
    force = payload["force"]
    moment = payload["moment"]
    if not close_enough(force[1], -100.0, rel=3.0e-3, abs_tol=0.05) or abs(force[0]) > 0.05 or abs(force[2]) > 0.05:
        log("ANSYS fixed-face force resultant does not balance the point load")
        return False
    if not close_enough(moment[0], 10000.0, rel=3.0e-3, abs_tol=2.0) or abs(moment[1]) > 2.0 or not close_enough(moment[2], -500.0, rel=3.0e-3, abs_tol=1.0):
        log("ANSYS fixed-face moment resultant does not match r cross F")
        return False
    return True


def ansys_post_payloads_match(left, right):
    for name in ("tip_displacement", "max_mises"):
        tolerance = 2.0e-7 if name == "tip_displacement" else 5.0e-4
        if not close_enough(left[name], right[name], rel=5.0e-4, abs_tol=tolerance):
            return False
    for name, tolerance in (("force", 0.05), ("moment", 1.0)):
        if any(not close_enough(left[name][index], right[name][index], rel=5.0e-4, abs_tol=tolerance) for index in range(3)):
            return False
    for name in ("u", "s"):
        if set(left[name]) != set(right[name]):
            return False
        for label in left[name]:
            if len(left[name][label]) != len(right[name][label]):
                return False
            if any(not close_enough(a, b, rel=5.0e-4, abs_tol=2.0e-7) for a, b in zip(left[name][label], right[name][label])):
                return False
    return True


def run_ansys_checker(model_path, result_path, metrics):
    token = uuid.uuid4().hex
    audit_root = None
    solve_root = None
    post_root = None
    audit_job = "e11audit_" + token[:12]
    solve_job = "e11solve_" + token[:12]
    post_job = "e11post_" + token[:12]
    markers = (token, audit_job, solve_job, post_job)
    baseline = None
    owned_history = {}
    tracker_stop = None
    tracker = None
    ansys_temp_before = None
    semantic_ok = False
    process_ok = False
    tracker_ok = False
    temp_ok = False
    ansys_temp_ok = False
    try:
        original_hashes = (sha256(model_path), sha256(result_path))
        audit_root = Path(tempfile.mkdtemp(prefix="eval_cli_task11_ansys_audit_%s_" % token))
        solve_root = Path(tempfile.mkdtemp(prefix="eval_cli_task11_ansys_solve_%s_" % token))
        post_root = Path(tempfile.mkdtemp(prefix="eval_cli_task11_ansys_post_%s_" % token))
        staged_model = audit_root / "source.db"
        staged_result = audit_root / "submitted.rst"
        solve_model = solve_root / "source.db"
        post_model = post_root / "source.db"
        post_result = post_root / "submitted.rst"
        markers = markers + (str(audit_root), str(solve_root), str(post_root))
        baseline = windows_processes(ANSYS_PROCESS_PATTERN)
        ansys_temp_before = ansys_temp_inventory()
        tracker_stop = threading.Event()
        tracker = threading.Thread(
            target=track_owned_processes,
            args=(tracker_stop, owned_history, baseline, ANSYS_PROCESS_PATTERN, markers),
        )
        tracker.daemon = True
        tracker.start()
        shutil.copy2(str(model_path), str(staged_model))
        shutil.copy2(str(result_path), str(staged_result))
        shutil.copy2(str(model_path), str(solve_model))
        if (sha256(staged_model), sha256(staged_result), sha256(solve_model)) != (original_hashes[0], original_hashes[1], original_hashes[0]):
            raise RuntimeError("ANSYS staging hashes do not match submitted artifacts")

        nonce = uuid.uuid4().hex
        export_input = audit_root / "task11_export.inp"
        export_output = audit_root / "task11_export.out"
        export_stem = "task11_eval_export"
        write_ansys_export_input(export_input, staged_model, export_stem, nonce)
        export_text = run_ansys_batch(audit_root, export_input, export_output, audit_job, nonce, baseline, owned_history)
        if "TASK11_EXPORT_BEGIN_%s" % nonce not in export_text or "TASK11_EXPORT_END_%s" % nonce not in export_text:
            raise RuntimeError("ANSYS CDB export markers are incomplete")
        model = audit_ansys_cdb(
            audit_root / (export_stem + ".cdb"),
            audit_root / (export_stem + "_live.txt"),
        )
        if model is None:
            raise RuntimeError("ANSYS DB semantic audit failed")
        expected_nodes = set(model["coords"])
        load_node = model["mesh_info"]["load"]

        submitted_nonce = uuid.uuid4().hex
        submitted_input = audit_root / "task11_submitted_post.inp"
        submitted_output = audit_root / "task11_submitted_post.out"
        write_ansys_post_input(submitted_input, staged_model, staged_result, "submitted", submitted_nonce, load_node)
        submitted_text = run_ansys_batch(audit_root, submitted_input, submitted_output, audit_job, submitted_nonce, baseline, owned_history)
        if "TASK11_POST_BEGIN_%s" % submitted_nonce not in submitted_text or "TASK11_POST_END_%s" % submitted_nonce not in submitted_text:
            raise RuntimeError("ANSYS submitted RST post markers are incomplete")
        submitted = read_ansys_post_payload(audit_root, "submitted", expected_nodes)
        if not ansys_post_is_task11(submitted):
            raise RuntimeError("ANSYS submitted RST physical/result audit failed")
        for name in METRIC_FIELDS:
            tolerance = 2.0e-7 if name == "tip_displacement" else 2.0e-5
            if not close_enough(submitted[name], metrics[name], rel=2.0e-5, abs_tol=tolerance):
                raise RuntimeError("metrics.json %s does not match native RST" % name)

        resolve_nonce = uuid.uuid4().hex
        resolve_input = solve_root / "task11_resolve.inp"
        resolve_output = solve_root / "task11_resolve.out"
        fresh_result = solve_root / (solve_job + ".rst")
        write_ansys_resolve_input(resolve_input, solve_model, resolve_nonce)
        resolve_text = run_ansys_batch(solve_root, resolve_input, resolve_output, solve_job, resolve_nonce, baseline, owned_history)
        if (
            "TASK11_RESOLVE_BEGIN_%s" % resolve_nonce not in resolve_text
            or "TASK11_RESOLVE_END_%s" % resolve_nonce not in resolve_text
            or "RUN COMPLETED" not in resolve_text
            or re.search(r"\*\*\* LOAD STEP\s+1\s+SUBSTEP\s+1\s+COMPLETED", resolve_text) is None
            or "NUMBER OF ERROR   MESSAGES ENCOUNTERED=          0" not in resolve_text
            or not is_nonempty(fresh_result)
        ):
            raise RuntimeError("isolated ANSYS batch re-solve failed")
        shutil.copy2(str(solve_model), str(post_model))
        shutil.copy2(str(fresh_result), str(post_result))
        if sha256(post_model) != original_hashes[0] or sha256(post_result) != sha256(fresh_result):
            raise RuntimeError("ANSYS re-solve post staging hashes do not match")

        recheck_nonce = uuid.uuid4().hex
        recheck_input = post_root / "task11_rechecked_post.inp"
        recheck_output = post_root / "task11_rechecked_post.out"
        write_ansys_post_input(recheck_input, post_model, post_result, "rechecked", recheck_nonce, load_node)
        recheck_text = run_ansys_batch(post_root, recheck_input, recheck_output, post_job, recheck_nonce, baseline, owned_history)
        if "TASK11_POST_BEGIN_%s" % recheck_nonce not in recheck_text or "TASK11_POST_END_%s" % recheck_nonce not in recheck_text:
            raise RuntimeError("ANSYS rechecked RST post markers are incomplete")
        rechecked = read_ansys_post_payload(post_root, "rechecked", expected_nodes)
        if not ansys_post_is_task11(rechecked) or not ansys_post_payloads_match(submitted, rechecked):
            raise RuntimeError("submitted RST U/S fields do not match isolated DB re-solve")
        if (sha256(model_path), sha256(result_path)) != original_hashes:
            raise RuntimeError("submitted ANSYS artifacts changed during evaluation")
        semantic_ok = True
    except Exception as exc:
        log("ANSYS evaluator failed: %s" % exc)
        semantic_ok = False
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
                process_ok = restore_process_baseline(
                    baseline, ANSYS_PROCESS_PATTERN, markers, owned_history.values()
                )
            except Exception as exc:
                log("ANSYS process cleanup failed: %s" % exc)
        else:
            log("ANSYS process cleanup skipped because no baseline was captured")
        roots = tuple(path for path in (audit_root, solve_root, post_root) if path is not None)
        temp_results = [remove_tree(path) for path in roots]
        temp_ok = len(roots) == 3 and all(temp_results)
        if not temp_ok:
            log("ANSYS temporary directory cleanup was incomplete")
        if ansys_temp_before is not None:
            ansys_temp_ok = restore_ansys_temp_inventory(
                ansys_temp_before,
                markers + tuple(path.name for path in roots),
                tuple(row.get("pid", 0) for row in owned_history.values()),
            )
        else:
            log("ANSYS .ansys cleanup skipped because no baseline was captured")
    return semantic_ok and process_ok and tracker_ok and temp_ok and ansys_temp_ok


def evaluate():
    root = desktop_dir()
    metrics = read_metrics(root)
    if metrics is None:
        return False, root
    branch = discover_branch(root)
    if branch is None:
        return False, root
    if branch[0] == "abaqus":
        log("evaluating Abaqus 2025 native Task-11 branch")
        return run_abaqus_checker(branch[1], branch[2], metrics), root
    log("evaluating ANSYS MAPDL 2026 R1 native Task-11 branch")
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
