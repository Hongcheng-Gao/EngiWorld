# -*- coding: utf-8 -*-
"""Fail-closed evaluator for EngiWorld Task-17.

The evaluator audits one native solver pair, performs an isolated native
re-solve, binds the submitted result fields to that re-solve, and removes every
evaluator-owned process and temporary file before returning a result.
"""
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
import traceback
import uuid
from pathlib import Path


TASK_ID = "c-open-abaqus-ansys-autocad-task-17-windows"
ABAQUS_COMMAND = r"C:\SIMULIA\CAE\2025LE\win_b64\code\bin\SMALauncherLE.exe"
ANSYS_EXEC = r"C:\Program Files\ANSYS Inc\v261\ansys\bin\winx64\ANSYS261.exe"
EXPECTED_STRESS = 252.0
EXPECTED_REACTION = 25200.0
GEOMETRY_TOL = 1.0e-5
DETAILS: list[str] = []
_ANSYS_READER = None
_OWNED_PROCESS_IDENTITIES: set[tuple[int, str, str]] = set()
OWNED_PROCESS_NAMES = {
    "python.exe",
    "cmd.exe",
    "conhost.exe",
    "powershell.exe",
    "package.exe",
    "ansys.exe",
    "ansys261.exe",
    "ansyscl.exe",
    "smalauncherle.exe",
    "abqlauncher.exe",
    "abq2025le.exe",
    "abqcaek.exe",
    "smapython.exe",
    "smasimutility.exe",
    "smaeqsdirsolversymmetric.exe",
    "pre.exe",
    "standard.exe",
    "mpiexec.exe",
    "hydra_service.exe",
    "hydra_bstrap_proxy.exe",
    "hydra_pmi_proxy.exe",
}


class EvaluationError(RuntimeError):
    pass


def windows_processes() -> list[dict[str, object]]:
    if os.name != "nt":
        return []
    query = (
        "Get-CimInstance Win32_Process | "
        "Select-Object ProcessId,ParentProcessId,Name,CreationDate,ExecutablePath,CommandLine | "
        "ConvertTo-Json -Compress"
    )
    completed = subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command", query],
        capture_output=True,
        text=True,
        timeout=60,
        shell=False,
    )
    if completed.returncode != 0:
        raise EvaluationError("cannot inventory evaluator-owned processes")
    value = [] if not completed.stdout.strip() else json.loads(completed.stdout)
    rows = [value] if isinstance(value, dict) else value
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise EvaluationError("invalid Windows process inventory")
    return rows


def process_identity(row: dict[str, object]) -> tuple[int, str, str]:
    return (
        int(row.get("ProcessId") or 0),
        str(row.get("CreationDate") or ""),
        str(row.get("ExecutablePath") or "").casefold(),
    )


def process_creation_stamp(row: dict[str, object]) -> int:
    match = re.search(r"\d+", str(row.get("CreationDate") or ""))
    return int(match.group(0)) if match else -1


def remember_evaluator_processes(work: Path, root_pid: int) -> None:
    if os.name != "nt":
        return
    rows = windows_processes()
    marker = str(work).casefold()
    by_pid = {int(row.get("ProcessId") or 0): row for row in rows}
    if not any(identity[0] == root_pid for identity in _OWNED_PROCESS_IDENTITIES):
        root = by_pid.get(root_pid)
        if root is not None:
            _OWNED_PROCESS_IDENTITIES.add(process_identity(root))
    owned_ids = set()
    for row in rows:
        pid = int(row.get("ProcessId") or 0)
        command = str(row.get("CommandLine") or "")
        if (
            pid > 0
            and pid != os.getpid()
            and (
                marker in command.casefold()
                or process_identity(row) in _OWNED_PROCESS_IDENTITIES
            )
        ):
            owned_ids.add(pid)
    changed = True
    while changed:
        changed = False
        for row in rows:
            pid = int(row.get("ProcessId") or 0)
            parent = int(row.get("ParentProcessId") or 0)
            parent_row = by_pid.get(parent)
            child_stamp = process_creation_stamp(row)
            parent_stamp = process_creation_stamp(parent_row or {})
            if (
                pid > 0
                and pid != os.getpid()
                and parent in owned_ids
                and parent_row is not None
                and child_stamp >= 0
                and parent_stamp >= 0
                and child_stamp >= parent_stamp
                and pid not in owned_ids
            ):
                owned_ids.add(pid)
                changed = True
    for row in rows:
        if int(row.get("ProcessId") or 0) in owned_ids and int(row.get("ProcessId") or 0) != os.getpid():
            _OWNED_PROCESS_IDENTITIES.add(process_identity(row))


def evaluator_owned_processes(work: Path) -> list[dict[str, object]]:
    if os.name != "nt":
        return []
    rows = windows_processes()
    marker = str(work).casefold()
    owned: dict[int, dict[str, object]] = {}
    for row in rows:
        pid = int(row.get("ProcessId") or 0)
        command = str(row.get("CommandLine") or "")
        identity = process_identity(row)
        if pid > 0 and pid != os.getpid() and marker in command.casefold():
            owned[pid] = row
        if identity in _OWNED_PROCESS_IDENTITIES and pid != os.getpid():
            owned[pid] = row
    changed = True
    while changed:
        changed = False
        for row in rows:
            pid = int(row.get("ProcessId") or 0)
            parent = int(row.get("ParentProcessId") or 0)
            parent_row = owned.get(parent)
            child_stamp = process_creation_stamp(row)
            parent_stamp = process_creation_stamp(parent_row or {})
            if (
                pid > 0
                and pid != os.getpid()
                and parent_row is not None
                and child_stamp >= 0
                and parent_stamp >= 0
                and child_stamp >= parent_stamp
                and pid not in owned
            ):
                owned[pid] = row
                changed = True
    return sorted(
        owned.values(),
        key=lambda row: (
            process_creation_stamp(row),
            int(row.get("ProcessId") or 0),
        ),
        reverse=True,
    )


def cleanup_evaluator_work(work: Path) -> bool:
    try:
        owned = evaluator_owned_processes(work)
        for row in owned:
            name = (
                Path(str(row.get("ExecutablePath") or "")).name
                or str(row.get("Name") or "")
            ).casefold()
            if name not in OWNED_PROCESS_NAMES:
                log("refusing unsafe evaluator process cleanup: %r" % row)
                return False
        for row in owned:
            pid = int(row.get("ProcessId") or 0)
            current = {
                int(item.get("ProcessId") or 0): item for item in windows_processes()
            }.get(pid)
            if current is None:
                continue
            if process_identity(current) != process_identity(row):
                log("refusing cleanup after process identity changed: %r" % row)
                return False
            completed = subprocess.run(
                ["taskkill", "/PID", str(pid), "/F"],
                capture_output=True,
                text=True,
                timeout=60,
                shell=False,
            )
            if completed.returncode not in (0, 128):
                remaining = {
                    int(item.get("ProcessId") or 0) for item in windows_processes()
                }
                if pid in remaining:
                    log("cannot stop evaluator-owned process %s" % pid)
                    return False
        for _ in range(50):
            if not evaluator_owned_processes(work):
                break
            time.sleep(0.1)
        if evaluator_owned_processes(work):
            log("evaluator-owned processes remain after cleanup")
            return False
        for _ in range(50):
            try:
                if work.exists():
                    shutil.rmtree(work)
                if not work.exists():
                    _OWNED_PROCESS_IDENTITIES.clear()
                    return True
            except (PermissionError, OSError):
                pass
            time.sleep(0.1)
        log("evaluator isolation directory remains after cleanup: %s" % work)
        return False
    except Exception as exc:
        log("evaluator cleanup failed: %s" % exc)
        return False


def ansys_reader_runtime():
    global _ANSYS_READER
    if _ANSYS_READER is not None:
        return _ANSYS_READER
    candidates = []
    appdata = os.environ.get("APPDATA")
    if appdata:
        candidates.append(str(Path(appdata) / "Python" / "Python311" / "site-packages"))
    try:
        candidates.append(site.getusersitepackages())
    except Exception:
        pass
    for candidate in candidates:
        if isinstance(candidate, str) and Path(candidate).is_dir() and candidate not in sys.path:
            sys.path.insert(0, candidate)
    saved_userprofile = os.environ.get("USERPROFILE")
    try:
        if appdata:
            os.environ["USERPROFILE"] = str(Path(appdata).parent.parent)
        from ansys.mapdl import reader as pymapdl_reader
    finally:
        if saved_userprofile is None:
            os.environ.pop("USERPROFILE", None)
        else:
            os.environ["USERPROFILE"] = saved_userprofile
    _ANSYS_READER = pymapdl_reader
    return _ANSYS_READER


def log(message: object) -> None:
    DETAILS.append(str(message))


def run_owned_process(command: list[str], work: Path, timeout: int) -> subprocess.CompletedProcess:
    creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    process = subprocess.Popen(
        command,
        cwd=str(work),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
        creationflags=creationflags,
    )
    deadline = time.monotonic() + timeout
    timed_out = None
    while True:
        if os.name == "nt":
            remember_evaluator_processes(work, int(process.pid))
        remaining = deadline - time.monotonic()
        if remaining <= 0.0:
            timed_out = subprocess.TimeoutExpired(command, timeout)
            break
        try:
            stdout, stderr = process.communicate(timeout=min(0.2, remaining))
            if os.name == "nt":
                remember_evaluator_processes(work, int(process.pid))
            return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)
        except subprocess.TimeoutExpired:
            continue
    if timed_out is not None:
        known_root = next(
            (
                identity
                for identity in _OWNED_PROCESS_IDENTITIES
                if identity[0] == int(process.pid)
            ),
            None,
        )
        current_root = {
            int(row.get("ProcessId") or 0): row for row in windows_processes()
        }.get(int(process.pid))
        if current_root is not None and (
            known_root is None or process_identity(current_root) != known_root
        ):
            raise EvaluationError("solver root identity changed before timeout cleanup")
        killed = []
        for row in evaluator_owned_processes(work):
            name = (
                Path(str(row.get("ExecutablePath") or "")).name
                or str(row.get("Name") or "")
            ).casefold()
            if name not in OWNED_PROCESS_NAMES:
                raise EvaluationError(
                    "refusing unsafe timed-out process cleanup: %r" % row
                )
            pid = int(row.get("ProcessId") or 0)
            current = {
                int(item.get("ProcessId") or 0): item
                for item in windows_processes()
            }.get(pid)
            if current is None:
                continue
            if process_identity(current) != process_identity(row):
                raise EvaluationError(
                    "timed-out process identity changed before cleanup: %r" % row
                )
            killed.append(
                subprocess.run(
                    ["taskkill", "/PID", str(pid), "/F"],
                    text=True,
                    capture_output=True,
                    timeout=60,
                    shell=False,
                )
            )
        try:
            process.communicate(timeout=60)
        except subprocess.TimeoutExpired as cleanup_exc:
            raise EvaluationError("solver process tree survived timeout cleanup") from cleanup_exc
        for _ in range(60):
            if not evaluator_owned_processes(work):
                break
            time.sleep(0.25)
        remaining = evaluator_owned_processes(work)
        if remaining:
            raise EvaluationError(
                "solver process tree survived timeout cleanup: %r" % remaining
            ) from timed_out
        failed_kills = [item for item in killed if item.returncode not in (0, 128)]
        if failed_kills:
            raise EvaluationError(
                "solver timed out and process-tree cleanup failed: %s"
                % (failed_kills[0].stderr or failed_kills[0].stdout)
            ) from timed_out
        raise EvaluationError("solver timed out after %s seconds" % timeout) from timed_out


def desktop_dir() -> Path:
    isolated = os.environ.get("ENGIWORLD_EVAL_DESKTOP")
    if isolated:
        candidate = Path(isolated)
        if candidate.is_dir():
            return candidate
    candidates = [
        Path(os.environ.get("USERPROFILE", r"C:\Users\user")) / "Desktop",
        Path(r"C:\Users\user\Desktop"),
        Path(r"C:\Users\User\Desktop"),
    ]
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    return candidates[1]


def finite_number(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def close(actual: float, expected: float, rel: float, absolute: float) -> bool:
    return math.isfinite(float(actual)) and math.isclose(
        float(actual), float(expected), rel_tol=rel, abs_tol=absolute
    )


def strict_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    folded: set[str] = set()
    for key, value in pairs:
        if not isinstance(key, str):
            raise EvaluationError("JSON object key is not text")
        normalized = key.casefold()
        if normalized in folded:
            raise EvaluationError("duplicate or case-colliding JSON key: %s" % key)
        folded.add(normalized)
        result[key] = value
    return result


def read_json_strict(path: Path) -> object:
    if not path.is_file() or path.stat().st_size <= 0:
        raise EvaluationError("missing or empty JSON: %s" % path.name)
    try:
        return json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=strict_object,
            parse_constant=lambda token: (_ for _ in ()).throw(
                EvaluationError("non-finite JSON token: %s" % token)
            ),
        )
    except EvaluationError:
        raise
    except Exception as exc:
        raise EvaluationError("invalid JSON %s: %s" % (path.name, exc)) from exc


def read_metrics(root: Path) -> dict[str, float]:
    value = read_json_strict(root / "metrics.json")
    if not isinstance(value, dict):
        raise EvaluationError("metrics.json must contain one object")
    if set(value) != {"thermal_stress", "reaction_force"}:
        raise EvaluationError(
            "metrics.json must contain exactly thermal_stress and reaction_force"
        )
    metrics: dict[str, float] = {}
    for key in ("thermal_stress", "reaction_force"):
        if not finite_number(value[key]):
            raise EvaluationError("metrics field is not a finite JSON number: %s" % key)
        metrics[key] = float(value[key])
    require_physical_metrics(metrics, "metrics.json", analytical_rel=0.03)
    return metrics


def require_physical_metrics(
    metrics: dict[str, float], label: str, analytical_rel: float = 0.03
) -> None:
    if metrics["thermal_stress"] < 0.0 or metrics["reaction_force"] < 0.0:
        raise EvaluationError("%s metrics must be nonnegative: %r" % (label, metrics))
    if not close(metrics["thermal_stress"], EXPECTED_STRESS, analytical_rel, 0.5):
        raise EvaluationError("%s thermal stress is not 252 MPa: %r" % (label, metrics))
    if not close(metrics["reaction_force"], EXPECTED_REACTION, analytical_rel, 20.0):
        raise EvaluationError("%s reaction is not 25200 N: %r" % (label, metrics))


def compare_metrics(
    left: dict[str, float], right: dict[str, float], label: str
) -> None:
    limits = {"thermal_stress": 0.2, "reaction_force": 10.0}
    for key in ("thermal_stress", "reaction_force"):
        if left[key] < 0.0 or right[key] < 0.0 or not close(left[key], right[key], 0.01, limits[key]):
            raise EvaluationError(
                "%s mismatch for %s: %r versus %r" % (label, key, left[key], right[key])
            )


def nonempty_files(root: Path, suffix: str) -> list[Path]:
    return sorted(
        [
            path
            for path in root.iterdir()
            if path.is_file() and path.suffix.casefold() == suffix and path.stat().st_size > 0
        ],
        key=lambda path: path.name.casefold(),
    )


def select_backend(root: Path) -> tuple[str, Path, Path]:
    suffixes = (".cae", ".odb", ".db", ".rst", ".rth", ".wbpj")
    inventory = {suffix: nonempty_files(root, suffix) for suffix in suffixes}
    any_abaqus = bool(inventory[".cae"] or inventory[".odb"])
    any_ansys = bool(
        inventory[".db"]
        or inventory[".rst"]
        or inventory[".rth"]
        or inventory[".wbpj"]
    )
    if any_abaqus and any_ansys:
        raise EvaluationError("mixed Abaqus and ANSYS native artifacts are not allowed")
    if any_abaqus:
        if len(inventory[".cae"]) != 1 or len(inventory[".odb"]) != 1:
            raise EvaluationError("Abaqus submission must contain exactly one CAE and one ODB")
        cae, odb = inventory[".cae"][0], inventory[".odb"][0]
        if cae.stem.casefold() != odb.stem.casefold():
            raise EvaluationError("Abaqus CAE and ODB stems differ")
        return "abaqus", cae, odb
    if any_ansys:
        if inventory[".rth"] or inventory[".wbpj"]:
            raise EvaluationError("Task-17 requires a native MAPDL DB/RST pair")
        if len(inventory[".db"]) != 1 or len(inventory[".rst"]) != 1:
            raise EvaluationError("ANSYS submission must contain exactly one DB and one RST")
        db, rst = inventory[".db"][0], inventory[".rst"][0]
        if db.stem.casefold() != rst.stem.casefold():
            raise EvaluationError("ANSYS DB and RST stems differ")
        return "ansys", db, rst
    raise EvaluationError("no supported native model/result pair found")


ABAQUS_CHECKER_SOURCE = r'''# -*- coding: utf-8 -*-
from __future__ import print_function

import builtins
import json
import math
import os
import re
import sys
import traceback

from abaqus import openMdb
from abaqusConstants import INTEGRATION_POINT, ON, SIZE
from odbAccess import openOdb


class CheckError(RuntimeError):
    pass


def finite(value):
    try:
        return math.isfinite(float(value))
    except Exception:
        return False


def close(actual, expected, rel=2.0e-3, absolute=1.0e-8):
    return finite(actual) and abs(float(actual) - float(expected)) <= max(
        absolute, rel * max(abs(float(actual)), abs(float(expected)))
    )


def repository_item(repository, name):
    target = str(name).upper()
    for key in repository.keys():
        if str(key).upper() == target:
            return repository[key]
    raise CheckError("repository item not found: %s" % name)


def active_repository_items(repository):
    result = []
    for key in repository.keys():
        item = repository[key]
        if str(getattr(item, "suppressed", "OFF")).upper() not in (
            "ON",
            "TRUE",
            "1",
        ):
            result.append(item)
    return result


def table(owner, attribute):
    try:
        return [[float(value) for value in row] for row in getattr(owner, attribute).table]
    except Exception:
        return []


def node_map(nodes):
    result = {}
    for node in nodes:
        point = list(float(value) for value in node.coordinates)
        while len(point) < 3:
            point.append(0.0)
        result[int(node.label)] = tuple(point[:3])
    return result


def bounds(coordinates):
    rows = list(coordinates.values())
    if not rows:
        raise CheckError("model has no nodes")
    return tuple((min(row[i] for row in rows), max(row[i] for row in rows)) for i in range(3))


def require_bounds(coordinates):
    actual = bounds(coordinates)
    expected = ((0.0, 100.0), (0.0, 10.0), (0.0, 10.0))
    for observed_pair, expected_pair in zip(actual, expected):
        for observed, target in zip(observed_pair, expected_pair):
            if not close(observed, target, rel=0.0, absolute=1.0e-5):
                raise CheckError("Abaqus geometry bounds mismatch: %r" % (actual,))


def require_native_geometry(part, instance):
    try:
        bounding_box = instance.cells.getBoundingBox()
        low = tuple(float(value) for value in bounding_box["low"])
        high = tuple(float(value) for value in bounding_box["high"])
        volume = float(
            part.getVolume(cells=part.cells, relativeAccuracy=1.0e-8)
        )
        cell_volume = builtins.sum(
            float(cell.getSize(printResults=False)) for cell in part.cells
        )
    except Exception as exc:
        raise CheckError("cannot query Abaqus native solid geometry: %s" % exc)
    expected_low = (0.0, 0.0, 0.0)
    expected_high = (100.0, 10.0, 10.0)
    if (
        len(low) != 3
        or len(high) != 3
        or any(
            not close(actual, expected, rel=0.0, absolute=1.0e-5)
            for actual, expected in zip(low + high, expected_low + expected_high)
        )
    ):
        raise CheckError(
            "Abaqus native CAD bounds mismatch: low=%r high=%r" % (low, high)
        )
    if not close(volume, 10000.0, rel=0.0, absolute=0.1):
        raise CheckError("Abaqus native CAD volume is not 10000 mm^3: %r" % volume)
    if not close(cell_volume, 10000.0, rel=0.0, absolute=0.1) or not close(
        cell_volume, volume, rel=0.0, absolute=0.01
    ):
        raise CheckError(
            "Abaqus cell and part volumes disagree: %r versus %r"
            % (cell_volume, volume)
        )

    solid_stat_names = (
        "numHexElems",
        "numWedgeElems",
        "numTetElems",
        "numPyramidElems",
    )
    try:
        unmeshed = part.getUnmeshedRegions()
        unmeshed_cells = tuple(getattr(unmeshed, "cells", ())) if unmeshed is not None else ()
        overall_stats = part.getMeshStats(regions=part.cells)
        overall_solid_count = builtins.sum(
            int(getattr(overall_stats, name)) for name in solid_stat_names
        )
        overall_region_count = int(overall_stats.numMeshedRegions)
        per_cell_solid_count = 0
        for cell in part.cells:
            stats = part.getMeshStats(regions=(cell,))
            solid_count = builtins.sum(
                int(getattr(stats, name)) for name in solid_stat_names
            )
            if (
                solid_count <= 0
                or int(stats.numNodes) <= 0
                or int(stats.numMeshedRegions) != 1
            ):
                raise CheckError("Abaqus active part contains an unmeshed solid cell")
            per_cell_solid_count += solid_count
    except CheckError:
        raise
    except Exception as exc:
        raise CheckError("cannot query Abaqus solid mesh coverage: %s" % exc)
    if unmeshed_cells:
        raise CheckError("Abaqus active part contains an unmeshed solid cell")
    if (
        overall_solid_count != len(part.elements)
        or per_cell_solid_count != len(part.elements)
        or overall_region_count != len(part.cells)
    ):
        raise CheckError("Abaqus solid-cell mesh coverage does not match active elements")
    return {
        "low": low,
        "high": high,
        "volume": volume,
        "cell_volume": cell_volume,
    }


def canonical_mesh(part):
    coordinates = node_map(part.nodes)
    require_bounds(coordinates)
    element_types = sorted(set(str(element.type).upper() for element in part.elements))
    allowed = set((
        "C3D8", "C3D8R", "C3D8I", "C3D8H", "C3D8RH",
        "C3D20", "C3D20R", "C3D20H", "C3D20RH",
        "C3D10", "C3D10M", "C3D10H", "C3D10MH",
    ))
    if not element_types or any(value not in allowed for value in element_types):
        raise CheckError("unsupported active Abaqus element type: %r" % element_types)
    try:
        seed_size = float(part.getPartSeeds(attribute=SIZE))
    except Exception as exc:
        raise CheckError("Abaqus active part has no readable global seed: %s" % exc)
    if not close(seed_size, 5.0, rel=0.0, absolute=0.05):
        raise CheckError("Abaqus global mesh seed is not 5 mm: %r" % seed_size)
    labels = set(coordinates)
    used_labels = set()
    connectivity_rows = []
    corner_edges = {
        "C3D8": ((0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6), (6, 7), (7, 4), (0, 4), (1, 5), (2, 6), (3, 7)),
        "C3D20": ((0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6), (6, 7), (7, 4), (0, 4), (1, 5), (2, 6), (3, 7)),
        "C3D10": ((0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)),
    }
    family_lengths = {"hex": [], "tet": []}
    face_indices = {
        "C3D8": (
            (0, 1, 2, 3),
            (4, 5, 6, 7),
            (0, 1, 5, 4),
            (1, 2, 6, 5),
            (2, 3, 7, 6),
            (3, 0, 4, 7),
        ),
        "C3D20": (
            (0, 1, 2, 3, 8, 9, 10, 11),
            (4, 5, 6, 7, 12, 13, 14, 15),
            (0, 1, 5, 4, 8, 17, 12, 16),
            (1, 2, 6, 5, 9, 18, 13, 17),
            (2, 3, 7, 6, 10, 19, 14, 18),
            (3, 0, 4, 7, 11, 16, 15, 19),
        ),
        "C3D10": (
            (0, 1, 2, 4, 5, 6),
            (0, 1, 3, 4, 8, 7),
            (1, 2, 3, 5, 9, 8),
            (2, 0, 3, 6, 7, 9),
        ),
    }
    face_owners = {}
    for element in part.elements:
        element_type = str(element.type).upper()
        if element_type not in allowed:
            raise CheckError("invalid element in active bar")
        try:
            connectivity = tuple(int(node.label) for node in element.getNodes())
        except Exception as exc:
            raise CheckError("cannot resolve CAE element nodes: %s" % exc)
        if any(label not in labels for label in connectivity):
            raise CheckError("element connectivity references an unknown node")
        base = (
            "C3D20"
            if element_type.startswith("C3D20")
            else "C3D10"
            if element_type.startswith("C3D10")
            else "C3D8"
        )
        required_nodes = 20 if base == "C3D20" else 10 if base == "C3D10" else 8
        if len(connectivity) != required_nodes:
            raise CheckError("Abaqus element connectivity width does not match %s" % element_type)
        used_labels.update(connectivity)
        connectivity_rows.append(set(connectivity))
        for indices in face_indices[base]:
            face = tuple(sorted(connectivity[index] for index in indices))
            if len(set(face)) != len(indices):
                raise CheckError("Abaqus mesh contains a degenerate corner face")
            face_owners.setdefault(face, []).append(int(element.label))
        for first, second in corner_edges[base]:
            point_a = coordinates[connectivity[first]]
            point_b = coordinates[connectivity[second]]
            length = math.sqrt(builtins.sum((point_a[index] - point_b[index]) ** 2 for index in range(3)))
            if not finite(length) or length <= 1.0e-8:
                raise CheckError("Abaqus mesh contains a degenerate corner edge")
            family_lengths["tet" if base == "C3D10" else "hex"].append(length)
    if used_labels != labels or not connectivity_rows:
        raise CheckError("Abaqus mesh has unreferenced nodes or no active elements")
    reached = set(connectivity_rows[0])
    pending = list(connectivity_rows[1:])
    changed = True
    while changed and pending:
        changed = False
        remaining = []
        for row in pending:
            if row & reached:
                reached.update(row)
                changed = True
            else:
                remaining.append(row)
        pending = remaining
    if pending or reached != labels:
        raise CheckError("Abaqus active mesh is not one connected solid mesh")
    element_neighbors = {
        int(element.label): set() for element in part.elements
    }
    boundary_planes = set()
    for face, owners in face_owners.items():
        if len(owners) == 2:
            element_neighbors[owners[0]].add(owners[1])
            element_neighbors[owners[1]].add(owners[0])
            continue
        if len(owners) != 1:
            raise CheckError("Abaqus mesh has a nonmanifold corner face")
        points = [coordinates[label] for label in face]
        matches = []
        for axis, target, name in (
            (0, 0.0, "X0"),
            (0, 100.0, "X100"),
            (1, 0.0, "Y0"),
            (1, 10.0, "Y10"),
            (2, 0.0, "Z0"),
            (2, 10.0, "Z10"),
        ):
            if all(abs(point[axis] - target) <= 1.0e-5 for point in points):
                matches.append(name)
        if len(matches) != 1:
            raise CheckError("Abaqus mesh has a boundary face inside the solid")
        boundary_planes.add(matches[0])
    if boundary_planes != set(("X0", "X100", "Y0", "Y10", "Z0", "Z10")):
        raise CheckError("Abaqus mesh does not cover all six bar boundary planes")
    first_element = next(iter(element_neighbors))
    reached_elements = set((first_element,))
    pending_elements = [first_element]
    while pending_elements:
        current_element = pending_elements.pop()
        for neighbor in element_neighbors[current_element] - reached_elements:
            reached_elements.add(neighbor)
            pending_elements.append(neighbor)
    if reached_elements != set(element_neighbors):
        raise CheckError("Abaqus elements are not connected through complete faces")
    for family, lengths in family_lengths.items():
        if not lengths:
            continue
        ordered = sorted(lengths)
        median = ordered[len(ordered) // 2]
        p90 = ordered[int(0.9 * (len(ordered) - 1))]
        if family == "hex":
            in_band = builtins.sum(1 for value in ordered if 3.5 <= value <= 6.5)
            valid = (
                4.5 <= median <= 5.5
                and p90 <= 6.5
                and in_band >= int(math.ceil(0.7 * len(ordered)))
            )
        else:
            in_band = builtins.sum(1 for value in ordered if 3.0 <= value <= 8.0)
            valid = (
                4.5 <= median <= 6.5
                and p90 <= 8.0
                and builtins.max(ordered) <= 9.6
                and in_band >= int(math.ceil(0.7 * len(ordered)))
            )
        if not valid:
            raise CheckError("Abaqus %s corner-edge distribution is not consistent with 5 mm" % family)
    return coordinates, element_types


def parse_nsets_and_rows(inp_path):
    with open(inp_path, "r", errors="replace") as stream:
        lines = stream.readlines()
    allowed = set((
        "HEADING", "PREPRINT", "PART", "NODE", "ELEMENT", "NSET", "ELSET",
        "SOLID SECTION", "END PART", "ASSEMBLY", "INSTANCE", "END INSTANCE",
        "END ASSEMBLY", "MATERIAL", "ELASTIC", "EXPANSION", "DENSITY",
        "SECTION CONTROLS", "AMPLITUDE", "ORIENTATION", "BOUNDARY",
        "INITIAL CONDITIONS", "STEP", "STATIC", "TEMPERATURE", "RESTART",
        "OUTPUT", "NODE OUTPUT", "ELEMENT OUTPUT", "END STEP"
    ))
    nsets = {}
    boundary_rows = []
    initial_temperature_rows = []
    final_temperature_rows = []
    current = None
    current_header = ""
    current_set = None
    generate = False
    in_step = False
    static_count = 0
    for raw in lines:
        stripped = raw.strip()
        if not stripped or stripped.startswith("**"):
            continue
        if stripped.startswith("*"):
            current_header = stripped.upper()
            current = current_header[1:].split(",", 1)[0].strip()
            if current not in allowed:
                raise CheckError("unknown or forbidden active Abaqus keyword: %s" % current_header)
            if current in ("BOUNDARY", "INITIAL CONDITIONS", "TEMPERATURE") and "AMPLITUDE=" in current_header.replace(" ", ""):
                raise CheckError("time-varying boundary or temperature amplitude is not allowed")
            if current == "STEP":
                in_step = True
            elif current == "END STEP":
                in_step = False
            elif current == "STATIC":
                static_count += 1
            if current == "NSET":
                match = re.search(r"NSET\s*=\s*([^,]+)", current_header)
                if not match:
                    raise CheckError("NSET without a name")
                current_set = match.group(1).strip().upper()
                nsets.setdefault(current_set, set())
                generate = "GENERATE" in current_header
            else:
                current_set = None
                generate = False
            continue
        fields = [value.strip() for value in stripped.split(",") if value.strip()]
        if current == "NSET" and current_set:
            values = [int(value) for value in fields]
            if generate:
                if len(values) != 3 or values[2] <= 0:
                    raise CheckError("invalid generated NSET")
                nsets[current_set].update(range(values[0], values[1] + 1, values[2]))
            else:
                nsets[current_set].update(values)
        elif current == "BOUNDARY":
            if len(fields) < 2:
                raise CheckError("invalid BOUNDARY row")
            first = int(fields[1])
            last = int(fields[2]) if len(fields) >= 3 else first
            value = float(fields[3]) if len(fields) >= 4 else 0.0
            boundary_rows.append((fields[0].upper(), first, last, value))
        elif current == "INITIAL CONDITIONS":
            if "TYPE=TEMPERATURE" not in current_header.replace(" ", ""):
                raise CheckError("only temperature initial conditions are permitted")
            if len(fields) != 2:
                raise CheckError("invalid initial temperature row")
            initial_temperature_rows.append((fields[0].upper(), float(fields[1])))
        elif current == "TEMPERATURE":
            if not in_step or len(fields) != 2:
                raise CheckError("invalid final temperature row")
            final_temperature_rows.append((fields[0].upper(), float(fields[1])))
    if static_count != 1:
        raise CheckError("exactly one STATIC procedure is required")
    return nsets, boundary_rows, initial_temperature_rows, final_temperature_rows


def resolve_set(reference, nsets):
    key = reference.split(".")[-1].upper()
    if key not in nsets or not nsets[key]:
        raise CheckError("unresolved or empty node set: %s" % reference)
    return set(int(value) for value in nsets[key])


def matrix_rank_3(rows):
    matrix = [[float(value) for value in row] for row in rows]
    rank = 0
    column = 0
    while rank < len(matrix) and column < 3:
        pivot = None
        for index in range(rank, len(matrix)):
            if abs(matrix[index][column]) > 1.0e-10:
                pivot = index
                break
        if pivot is None:
            column += 1
            continue
        matrix[rank], matrix[pivot] = matrix[pivot], matrix[rank]
        divisor = matrix[rank][column]
        matrix[rank] = [value / divisor for value in matrix[rank]]
        for index in range(len(matrix)):
            if index == rank:
                continue
            factor = matrix[index][column]
            matrix[index] = [
                matrix[index][j] - factor * matrix[rank][j] for j in range(3)
            ]
        rank += 1
        column += 1
    return rank


def check_boundary_and_temperature(inp_path, coordinates):
    nsets, boundary_rows, initial_rows, final_rows = parse_nsets_and_rows(inp_path)
    scalar = {}
    for reference, first, last, value in boundary_rows:
        if not close(value, 0.0, rel=0.0, absolute=1.0e-12):
            raise CheckError("nonzero prescribed displacement")
        if first < 1 or last > 3 or first > last:
            raise CheckError("unsupported constrained degree of freedom")
        for label in resolve_set(reference, nsets):
            if label not in coordinates:
                raise CheckError("constraint set contains a node outside the bar")
            for dof in range(first, last + 1):
                key = (label, dof)
                if key in scalar:
                    raise CheckError("duplicate scalar constraint")
                scalar[key] = 0.0
    left = set(label for label, point in coordinates.items() if abs(point[0]) <= 1.0e-5)
    right = set(label for label, point in coordinates.items() if abs(point[0] - 100.0) <= 1.0e-5)
    expected_u1 = set((label, 1) for label in left | right)
    actual_u1 = set(key for key in scalar if key[1] == 1)
    if actual_u1 != expected_u1:
        raise CheckError("U1 constraints are not exactly both complete end faces")
    transverse = [key for key in scalar if key[1] in (2, 3)]
    if len(transverse) != 3 or len(scalar) != len(expected_u1) + 3:
        raise CheckError("exactly three additional transverse constraints are required")
    end_sides = set(0 if abs(coordinates[label][0]) <= 1.0e-5 else 100 if abs(coordinates[label][0] - 100.0) <= 1.0e-5 else -1 for label, _ in transverse)
    if len(end_sides) != 1 or -1 in end_sides:
        raise CheckError("transverse constraints must lie on one end face")
    rank_rows = []
    for label, dof in transverse:
        _, y, z = coordinates[label]
        rank_rows.append([1.0, 0.0, -z] if dof == 2 else [0.0, 1.0, y])
    if matrix_rank_3(rank_rows) != 3:
        raise CheckError("transverse constraints do not independently remove rigid modes")

    all_labels = set(coordinates)
    for rows, expected, label in ((initial_rows, 20.0, "initial"), (final_rows, 100.0, "final")):
        assigned = {}
        for reference, value in rows:
            if not close(value, expected, rel=0.0, absolute=1.0e-8):
                raise CheckError("%s temperature is not %s C" % (label, expected))
            for node_label in resolve_set(reference, nsets):
                if node_label in assigned:
                    raise CheckError("overlapping %s temperature definitions" % label)
                assigned[node_label] = value
        if set(assigned) != all_labels:
            raise CheckError("%s temperature does not cover the complete bar" % label)


def model_signature(nodes, elements):
    coordinate_rows = tuple(sorted((int(label), tuple(round(value, 8) for value in point)) for label, point in nodes.items()))
    element_rows = []
    for element in elements:
        try:
            connectivity = tuple(int(node.label) for node in element.getNodes())
        except Exception:
            connectivity = tuple(int(value) for value in element.connectivity)
        element_rows.append((int(element.label), str(element.type).upper(), connectivity))
    element_rows = tuple(sorted(element_rows))
    return coordinate_rows, element_rows


def audit_odb(path, expected_signature, expected_step):
    odb = openOdb(path=path, readOnly=True)
    try:
        status = str(getattr(odb.diagnosticData, "jobStatus", "")).upper()
        if "COMPLETED" not in status or "ABORT" in status or "TERMINAT" in status:
            raise CheckError("ODB is not completed: %s" % status)
        active_instances = [odb.rootAssembly.instances[key] for key in odb.rootAssembly.instances.keys() if len(odb.rootAssembly.instances[key].elements)]
        if len(active_instances) != 1:
            raise CheckError("ODB must contain exactly one active instance")
        instance = active_instances[0]
        nodes = node_map(instance.nodes)
        require_bounds(nodes)
        if model_signature(nodes, instance.elements) != expected_signature:
            raise CheckError("ODB mesh/connectivity does not bind to the CAE model")
        step = repository_item(odb.steps, expected_step)
        if not step.frames:
            raise CheckError("ODB static step has no frames")
        frame = step.frames[-1]
        for field_name in ("S", "U", "RF"):
            if field_name not in frame.fieldOutputs:
                raise CheckError("ODB lacks required field: %s" % field_name)
        instance_name = str(instance.name).upper()
        expected_elements = set(row[0] for row in expected_signature[1])
        stress_signature = {}
        for value in frame.fieldOutputs["S"].getSubset(position=INTEGRATION_POINT).values:
            if str(value.instance.name).upper() != instance_name:
                continue
            section_point = getattr(value, "sectionPoint", None)
            section_number = int(getattr(section_point, "number", 0) or 0)
            key = (
                int(value.elementLabel),
                int(getattr(value, "integrationPoint", 0) or 0),
                section_number,
            )
            data = tuple(float(component) for component in value.data)
            if key in stress_signature or not data or any(not finite(component) for component in data):
                raise CheckError("ODB stress field has duplicate or non-finite values")
            stress_signature[key] = data
        if not stress_signature or set(key[0] for key in stress_signature) != expected_elements:
            raise CheckError("ODB integration-point stress coverage is incomplete")
        s11 = [row[0] for row in stress_signature.values()]
        thermal_stress = builtins.max(abs(value) for value in s11)
        left = set(label for label, point in nodes.items() if abs(point[0]) <= 1.0e-5)
        right = set(label for label, point in nodes.items() if abs(point[0] - 100.0) <= 1.0e-5)
        rf_signature = {}
        for value in frame.fieldOutputs["RF"].values:
            if str(value.instance.name).upper() != instance_name:
                continue
            node_label = int(value.nodeLabel)
            data = tuple(float(component) for component in value.data)
            if node_label in rf_signature or node_label not in nodes or not data or any(not finite(component) for component in data):
                raise CheckError("ODB reaction field has duplicate, unknown, or non-finite values")
            rf_signature[node_label] = data
        if not (left | right).issubset(set(rf_signature)):
            raise CheckError("ODB reaction field does not cover every constrained end node")
        left_sum = builtins.sum(rf_signature[label][0] for label in left)
        right_sum = builtins.sum(rf_signature[label][0] for label in right)
        reaction_force = builtins.max(abs(left_sum), abs(right_sum))
        if abs(left_sum + right_sum) > max(20.0, 0.005 * 25200.0):
            raise CheckError("ODB end reactions are not balanced")
        end_labels = left | right
        displacement_signature = {}
        for value in frame.fieldOutputs["U"].values:
            if str(value.instance.name).upper() != instance_name:
                continue
            node_label = int(value.nodeLabel)
            data = tuple(float(component) for component in value.data)
            if node_label in displacement_signature or not data or any(not finite(component) for component in data):
                raise CheckError("ODB displacement field has duplicate or non-finite values")
            displacement_signature[node_label] = data
        if set(displacement_signature) != set(nodes):
            raise CheckError("ODB displacement field is incomplete")
        if builtins.max(abs(displacement_signature[label][0]) for label in end_labels) > 1.0e-6:
            raise CheckError("ODB end-face U1 is nonzero")
        metrics = {"thermal_stress": thermal_stress, "reaction_force": reaction_force}
        if not close(thermal_stress, 252.0, rel=0.03, absolute=0.5):
            raise CheckError("ODB thermal stress is not physical")
        if not close(reaction_force, 25200.0, rel=0.03, absolute=20.0):
            raise CheckError("ODB reaction force is not physical")
        return {
            "metrics": metrics,
            "fields": {
                "S": stress_signature,
                "U": displacement_signature,
                "RF": rf_signature,
            },
        }
    finally:
        odb.close()


def compare_odb_results(left, right):
    left_metrics, right_metrics = left["metrics"], right["metrics"]
    if not close(abs(left_metrics["thermal_stress"]), abs(right_metrics["thermal_stress"]), rel=0.01, absolute=0.2):
        raise CheckError("submitted and fresh ODB stress differ")
    if not close(abs(left_metrics["reaction_force"]), abs(right_metrics["reaction_force"]), rel=0.01, absolute=10.0):
        raise CheckError("submitted and fresh ODB reaction differ")
    tolerances = {"S": (2.0e-4, 0.02), "U": (2.0e-4, 1.0e-7), "RF": (2.0e-4, 0.1)}
    for field_name in ("S", "U", "RF"):
        submitted = left["fields"][field_name]
        fresh = right["fields"][field_name]
        if set(submitted) != set(fresh):
            raise CheckError("submitted and fresh ODB %s coverage differs" % field_name)
        rel, absolute = tolerances[field_name]
        for key in submitted:
            if len(submitted[key]) != len(fresh[key]) or any(
                not close(actual, expected, rel=rel, absolute=absolute)
                for actual, expected in zip(submitted[key], fresh[key])
            ):
                raise CheckError("submitted ODB %s does not match isolated re-solve" % field_name)


def main():
    work_dir, cae_path, submitted_odb, result_path, nonce = sys.argv[-5:]
    os.chdir(work_dir)
    if os.path.exists(result_path):
        os.remove(result_path)
    database = None
    try:
        database = openMdb(pathName=cae_path)
        plausible = []
        for model_name in database.models.keys():
            model = database.models[model_name]
            meshed_parts = [model.parts[key] for key in model.parts.keys() if len(model.parts[key].elements)]
            active_instances = [model.rootAssembly.instances[key] for key in model.rootAssembly.instances.keys() if len(model.rootAssembly.instances[key].elements)]
            non_initial_steps = [model.steps[key] for key in model.steps.keys() if str(key).upper() != "INITIAL"]
            if len(meshed_parts) == 1 and len(active_instances) == 1 and len(non_initial_steps) == 1:
                plausible.append((model, meshed_parts[0], active_instances[0], non_initial_steps[0]))
        if len(plausible) != 1:
            raise CheckError("CAE must contain exactly one unambiguous active bar model")
        model, part, instance, step = plausible[0]
        if part.__class__.__name__ != "Part" or not len(part.cells):
            raise CheckError("active part has no solid cells")
        if "STATIC" not in step.__class__.__name__.upper():
            raise CheckError("analysis step is not StaticStep")
        if str(getattr(step, "nlgeom", "OFF")).upper() not in ("OFF", "FALSE", "0"):
            raise CheckError("nonlinear geometry is not allowed")
        extra_solid_instances = [
            model.rootAssembly.instances[key]
            for key in model.rootAssembly.instances.keys()
            if str(getattr(model.rootAssembly.instances[key], "name", key)).casefold()
            != str(getattr(instance, "name", "")).casefold()
            and len(getattr(model.rootAssembly.instances[key], "cells", ()))
        ]
        if extra_solid_instances:
            raise CheckError("active model contains an additional solid instance")
        native_geometry = require_native_geometry(part, instance)
        coordinates, _ = canonical_mesh(part)
        if (
            active_repository_items(model.loads)
            or active_repository_items(model.interactions)
            or active_repository_items(getattr(model, "constraints", {}))
        ):
            raise CheckError("an active extra mechanical load/interaction/constraint exists")
        if len(active_repository_items(model.predefinedFields)) != 1:
            raise CheckError("exactly one temperature predefined field is required")

        active_assignments = [
            assignment
            for assignment in part.sectionAssignments
            if str(getattr(assignment, "suppressed", "OFF")).upper()
            not in ("ON", "TRUE", "1")
        ]
        if not active_assignments:
            raise CheckError("bar has no section assignment")
        section_names = set(str(item.sectionName) for item in active_assignments)
        assigned_cells = set()
        for assignment in active_assignments:
            region = assignment.region
            cell_indices = tuple(int(cell.index) for cell in getattr(region, "cells", ()))
            if not cell_indices and isinstance(region, tuple) and region:
                items = tuple(region)
                if len(items) < 5:
                    raise CheckError("section Region tuple is incomplete")
                region_name = str(items[0])
                owners = tuple(str(value) for value in items[1:-3])
                try:
                    flags = tuple(int(value) for value in items[-3:])
                except Exception as exc:
                    raise CheckError("section Region tuple has invalid flags") from exc
                if owners != (str(part.name),) or flags[-1] not in (0, 1):
                    raise CheckError("section Region tuple has the wrong owner or internal flag")
                repository_name = "allInternalSets" if flags[-1] else "allSets"
                repository = getattr(part, repository_name, None)
                if repository is None:
                    raise CheckError("section Region Set repository is unavailable")
                keys = list(repository.keys())
                matches = [key for key in keys if str(key) == region_name]
                if not matches:
                    matches = [
                        key
                        for key in keys
                        if str(key).casefold() == region_name.casefold()
                    ]
                if len(matches) != 1:
                    raise CheckError("section Region Set name is missing or ambiguous")
                resolved = repository[matches[0]]
                cell_indices = tuple(
                    sorted(int(cell.index) for cell in getattr(resolved, "cells", ()))
                )
            if not cell_indices:
                raise CheckError("section assignment does not resolve to solid cells")
            for index in cell_indices:
                if index in assigned_cells:
                    raise CheckError("solid cell has overlapping section assignments")
                assigned_cells.add(index)
        if assigned_cells != set(int(cell.index) for cell in part.cells):
            raise CheckError("section assignments do not cover every solid cell")
        sections = [repository_item(model.sections, name) for name in section_names]
        if any("SOLID" not in section.__class__.__name__.upper() for section in sections):
            raise CheckError("active bar section is not a solid section")
        material_names = set(str(section.material) for section in sections)
        if len(material_names) != 1:
            raise CheckError("partitioned bar sections do not use one common material")
        material = repository_item(model.materials, next(iter(material_names)))
        elastic = table(material, "elastic")
        expansion = table(material, "expansion")
        zero = float(getattr(material.expansion, "zero"))
        if (
            str(getattr(material.elastic, "type", "")).upper() != "ISOTROPIC"
            or bool(getattr(material.elastic, "temperatureDependency", False))
            or int(getattr(material.elastic, "dependencies", 0) or 0) != 0
        ):
            raise CheckError("assigned elastic material must be field-independent isotropic data")
        if (
            str(getattr(material.expansion, "type", "")).upper() != "ISOTROPIC"
            or bool(getattr(material.expansion, "temperatureDependency", False))
            or int(getattr(material.expansion, "dependencies", 0) or 0) != 0
        ):
            raise CheckError("assigned expansion must be field-independent isotropic data")
        if hasattr(material, "userMaterial"):
            raise CheckError("assigned material uses a user subroutine")
        if len(elastic) != 1 or len(elastic[0]) < 2 or not close(elastic[0][0], 210000.0) or not close(elastic[0][1], 0.3):
            raise CheckError("assigned material elastic constants are wrong")
        if len(expansion) != 1 or not expansion[0] or not close(expansion[0][0], 1.5e-5) or not close(zero, 20.0):
            raise CheckError("assigned material thermal expansion/reference is wrong")

        job_name = "eval17_" + nonce[:20]
        job = database.Job(name=job_name, model=model.name, numCpus=1, numDomains=1)
        job.writeInput(consistencyChecking=ON)
        inp_path = os.path.join(work_dir, job_name + ".inp")
        if not os.path.isfile(inp_path) or os.path.getsize(inp_path) <= 0:
            raise CheckError("Abaqus writeInput did not create an INP")
        check_boundary_and_temperature(inp_path, coordinates)

        part_signature = model_signature(coordinates, part.elements)
        submitted_result = audit_odb(submitted_odb, part_signature, step.name)
        job.submit(consistencyChecking=ON)
        job.waitForCompletion()
        fresh_odb = os.path.join(work_dir, job_name + ".odb")
        if not os.path.isfile(fresh_odb) or os.path.getsize(fresh_odb) <= 0:
            raise CheckError("fresh Abaqus solve did not create an ODB")
        fresh_result = audit_odb(fresh_odb, part_signature, step.name)
        compare_odb_results(submitted_result, fresh_result)
        payload = {
            "nonce": nonce,
            "ok": True,
            "backend": "abaqus",
            "geometry": native_geometry,
            "submitted_metrics": submitted_result["metrics"],
            "fresh_metrics": fresh_result["metrics"],
        }
        with open(result_path, "w") as stream:
            json.dump(payload, stream, sort_keys=True)
            stream.write("\n")
    finally:
        if database is not None:
            try:
                database.close()
            except Exception:
                pass


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        detail = traceback.format_exc()
        try:
            with open(sys.argv[-2], "w") as stream:
                json.dump(
                    {
                        "nonce": sys.argv[-1],
                        "ok": False,
                        "backend": "abaqus",
                        "error": str(exc),
                        "traceback": detail,
                    },
                    stream,
                    sort_keys=True,
                )
                stream.write("\n")
        except Exception:
            pass
        print(detail)
        sys.exit(2)
'''


def run_abaqus(
    work: Path, cae_path: Path, odb_path: Path, metrics: dict[str, float], nonce: str
) -> dict[str, float]:
    submitted_cae = work / "submitted.cae"
    submitted_odb = work / "submitted.odb"
    shutil.copy2(cae_path, submitted_cae)
    shutil.copy2(odb_path, submitted_odb)
    checker = work / ("abaqus_checker_%s.py" % nonce)
    result_path = work / ("abaqus_result_%s.json" % nonce)
    checker.write_text(ABAQUS_CHECKER_SOURCE, encoding="utf-8")
    result_path.unlink(missing_ok=True)
    command = [
        ABAQUS_COMMAND,
        "cae",
        "noGUI=" + str(checker),
        "--",
        str(work),
        str(submitted_cae),
        str(submitted_odb),
        str(result_path),
        nonce,
    ]
    completed = run_owned_process(command, work, timeout=1200)
    log("Abaqus command=" + repr(command))
    log("Abaqus checker returncode=%s" % completed.returncode)
    if completed.stdout:
        log("Abaqus stdout tail=" + completed.stdout[-3000:])
    if completed.stderr:
        log("Abaqus stderr tail=" + completed.stderr[-3000:])
    if completed.returncode != 0:
        raise EvaluationError("Abaqus checker/solve returned nonzero")
    if not result_path.is_file() or result_path.stat().st_size <= 0:
        inventory = []
        for path in sorted(work.rglob("*"), key=lambda item: str(item).casefold()):
            inventory.append(
                {
                    "path": str(path.relative_to(work)),
                    "is_file": path.is_file(),
                    "size": path.stat().st_size if path.is_file() else None,
                }
            )
        log("Abaqus work inventory=" + repr(inventory))
    payload = read_json_strict(result_path)
    if isinstance(payload, dict) and payload.get("nonce") == nonce and payload.get("ok") is False:
        raise EvaluationError(
            "Abaqus checker failed: %s\n%s"
            % (payload.get("error"), payload.get("traceback"))
        )
    if not isinstance(payload, dict) or payload.get("nonce") != nonce or payload.get("ok") is not True:
        raise EvaluationError("Abaqus checker returned missing/stale/invalid nonce result")
    if payload.get("backend") != "abaqus":
        raise EvaluationError("Abaqus checker backend mismatch")
    geometry = payload.get("geometry")
    if not isinstance(geometry, dict) or set(geometry) != {
        "low",
        "high",
        "volume",
        "cell_volume",
    }:
        raise EvaluationError("Abaqus checker geometry object is invalid")
    expected_bounds = ((0.0, 0.0, 0.0), (100.0, 10.0, 10.0))
    for key, expected in zip(("low", "high"), expected_bounds):
        observed = geometry.get(key)
        if not isinstance(observed, list) or len(observed) != 3 or any(
            not finite_number(actual)
            or not close(float(actual), target, 0.0, GEOMETRY_TOL)
            for actual, target in zip(observed, expected)
        ):
            raise EvaluationError("Abaqus checker native CAD bounds are invalid")
    for key in ("volume", "cell_volume"):
        if not finite_number(geometry.get(key)) or not close(
            float(geometry[key]), 10000.0, 0.0, 0.1
        ):
            raise EvaluationError("Abaqus checker native CAD volume is invalid")
    submitted_metrics = normalize_checker_metrics(payload.get("submitted_metrics"), "submitted ODB")
    fresh_metrics = normalize_checker_metrics(payload.get("fresh_metrics"), "fresh ODB")
    require_physical_metrics(fresh_metrics, "fresh ODB")
    compare_metrics(submitted_metrics, fresh_metrics, "submitted ODB versus fresh ODB")
    compare_metrics(metrics, fresh_metrics, "metrics.json versus fresh ODB")
    return fresh_metrics


def normalize_checker_metrics(value: object, label: str) -> dict[str, float]:
    if not isinstance(value, dict) or set(value) != {"thermal_stress", "reaction_force"}:
        raise EvaluationError("%s metrics object is invalid" % label)
    if any(not finite_number(value[key]) for key in value):
        raise EvaluationError("%s metrics contain a non-finite number" % label)
    return {key: float(value[key]) for key in ("thermal_stress", "reaction_force")}


def ansys_checker_source(nonce: str) -> str:
    short_nonce = nonce[:16]
    result_name = "ansys_result_%s" % short_nonce
    fresh_name = "fresh_%s" % short_nonce
    return r'''/BATCH
/CLEAR,NOSTART
/FILNAME,eval_%(nonce)s,1
RESUME,submitted,db
/PREP7
ALLSEL,ALL
*GET,NODE_COUNT,NODE,0,COUNT
*GET,ELEMENT_COUNT,ELEM,0,COUNT
*GET,X_MIN,NODE,0,MNLOC,X
*GET,X_MAX,NODE,0,MXLOC,X
*GET,Y_MIN,NODE,0,MNLOC,Y
*GET,Y_MAX,NODE,0,MXLOC,Y
*GET,Z_MIN,NODE,0,MNLOC,Z
*GET,Z_MAX,NODE,0,MXLOC,Z
ELEM_VOLUME_SUM=0
*GET,EID,ELEM,0,NUM,MIN
*DO,II,1,ELEMENT_COUNT
  *GET,ELIVE,ELEM,EID,ATTR,LIVE
  *IF,ELIVE,NE,1,THEN
    /EXIT,NOSAVE
  *ENDIF
  *GET,EVOL,ELEM,EID,VOLU
  *IF,EVOL,LE,0,THEN
    /EXIT,NOSAVE
  *ENDIF
  ELEM_VOLUME_SUM=ELEM_VOLUME_SUM+EVOL
  *GET,EID,ELEM,EID,NXTH
*ENDDO
ALLSEL,ALL
*GET,VOLUME_COUNT,VOLU,0,COUNT
NATIVE_VOLUME=-1
GEOM_ELEM_COUNT=-1
*IF,VOLUME_COUNT,GT,0,THEN
  VSEL,ALL
  VSUM,FINE
  *GET,NATIVE_VOLUME,VOLU,0,VOLU
  ESLV,S
  *GET,GEOM_ELEM_COUNT,ELEM,0,COUNT
  *IF,GEOM_ELEM_COUNT,NE,ELEMENT_COUNT,THEN
    /EXIT,NOSAVE
  *ENDIF
  VSEL,ALL
  *GET,VID,VOLU,0,NUM,MIN
  *DO,VI,1,VOLUME_COUNT
    VSEL,S,VOLU,,VID
    ESLV,S
    *GET,VNE,ELEM,0,COUNT
    *IF,VNE,LE,0,THEN
      /EXIT,NOSAVE
    *ENDIF
    VSEL,ALL
    *GET,VID,VOLU,VID,NXTH
  *ENDDO
*ENDIF
ALLSEL,ALL
*GET,FIRST_ELEM,ELEM,0,NUM,MIN
*GET,ACTIVE_MAT,ELEM,FIRST_ELEM,ATTR,MAT
*GET,E_VALUE,EX,ACTIVE_MAT,TEMP,0
*GET,PRXY_VALUE,PRXY,ACTIVE_MAT,TEMP,0
*GET,NUXY_VALUE,NUXY,ACTIVE_MAT,TEMP,0
NU_VALUE=PRXY_VALUE
*IF,ABS(NUXY_VALUE),GT,ABS(NU_VALUE),THEN
  NU_VALUE=NUXY_VALUE
*ENDIF
*GET,ALPX_VALUE,ALPX,ACTIVE_MAT,TEMP,0
*GET,CTEX_VALUE,CTEX,ACTIVE_MAT,TEMP,0
ALPHA_VALUE=ALPX_VALUE
*IF,ABS(CTEX_VALUE),GT,ABS(ALPHA_VALUE),THEN
  ALPHA_VALUE=CTEX_VALUE
*ENDIF
CDWRITE,DB,model_audit,cdb
/OUTPUT,model_listing,txt
ETLIST,ALL
MPLIST,ALL
NLIST,ALL
ELIST,ALL
/OUTPUT
/OUTPUT,load_listing,txt
DLIST,ALL
BFLIST,ALL,TEMP
BFELIST,ALL,TEMP
FLIST,ALL
SFLIST,ALL
SFELIST,ALL
SFLLIST,ALL
SFALIST,ALL
/OUTPUT
FINISH

/POST1
FILE,submitted,rst
SET,LAST
RSYS,0
ALLSEL,ALL
NSORT,S,X,0,1,ALL
*GET,SUB_MAX_SX,SORT,0,MAX
*GET,SUB_MIN_SX,SORT,0,MIN
SUB_STRESS=ABS(SUB_MAX_SX)
SUB_ABS_MIN=ABS(SUB_MIN_SX)
*IF,SUB_ABS_MIN,GT,SUB_STRESS,THEN
  SUB_STRESS=SUB_ABS_MIN
*ENDIF
NSEL,S,LOC,X,0
FSUM
*GET,SUB_LEFT_RF,FSUM,0,ITEM,FX
NSEL,S,LOC,X,100
FSUM
*GET,SUB_RIGHT_RF,FSUM,0,ITEM,FX
SUB_REACTION=ABS(SUB_LEFT_RF)
*IF,ABS(SUB_RIGHT_RF),GT,SUB_REACTION,THEN
  SUB_REACTION=ABS(SUB_RIGHT_RF)
*ENDIF
FINISH

/FILNAME,%(fresh_name)s,1
/SOLU
ANTYPE,STATIC,NEW
NLGEOM,OFF
EQSLV,SPARSE
NSUBST,1,1,1
OUTRES,ALL,ALL
ALLSEL,ALL
SOLVE
FINISH

/POST1
FILE,%(fresh_name)s,rst
SET,LAST
RSYS,0
ALLSEL,ALL
NSORT,S,X,0,1,ALL
*GET,FRESH_MAX_SX,SORT,0,MAX
*GET,FRESH_MIN_SX,SORT,0,MIN
FRESH_STRESS=ABS(FRESH_MAX_SX)
FRESH_ABS_MIN=ABS(FRESH_MIN_SX)
*IF,FRESH_ABS_MIN,GT,FRESH_STRESS,THEN
  FRESH_STRESS=FRESH_ABS_MIN
*ENDIF
NSEL,S,LOC,X,0
FSUM
*GET,FRESH_LEFT_RF,FSUM,0,ITEM,FX
NSEL,S,LOC,X,100
FSUM
*GET,FRESH_RIGHT_RF,FSUM,0,ITEM,FX
FRESH_REACTION=ABS(FRESH_LEFT_RF)
*IF,ABS(FRESH_RIGHT_RF),GT,FRESH_REACTION,THEN
  FRESH_REACTION=ABS(FRESH_RIGHT_RF)
*ENDIF
ALLSEL,ALL

*CFOPEN,%(result_name)s,json
*VWRITE
('{')
*VWRITE
('  "nonce": "%(nonce)s",')
*VWRITE
('  "ok": true,')
*VWRITE,NODE_COUNT,ELEMENT_COUNT
('  "node_count": ',E24.16,', "element_count": ',E24.16,',')
*VWRITE,X_MIN,X_MAX,Y_MIN,Y_MAX,Z_MIN,Z_MAX
('  "bounds": [',E24.16,',',E24.16,',',E24.16,',',E24.16,',',E24.16,',',E24.16,'],')
*VWRITE,E_VALUE,NU_VALUE,ALPHA_VALUE
('  "material": [',E24.16,',',E24.16,',',E24.16,'],')
*VWRITE,ELEM_VOLUME_SUM,VOLUME_COUNT,NATIVE_VOLUME,GEOM_ELEM_COUNT
('  "geometry": {"element_volume_sum": ',E24.16,', "volume_count": ',E24.16,', "native_volume": ',E24.16,', "geometry_element_count": ',E24.16,'},')
*VWRITE,SUB_STRESS,SUB_REACTION,SUB_LEFT_RF,SUB_RIGHT_RF
('  "submitted": {"thermal_stress": ',E24.16,', "reaction_force": ',E24.16,', "left_rf": ',E24.16,', "right_rf": ',E24.16,'},')
*VWRITE,FRESH_STRESS,FRESH_REACTION,FRESH_LEFT_RF,FRESH_RIGHT_RF
('  "fresh": {"thermal_stress": ',E24.16,', "reaction_force": ',E24.16,', "left_rf": ',E24.16,', "right_rf": ',E24.16,'}')
*VWRITE
('}')
*CFCLOS
FINISH
/EXIT,NOSAVE
''' % {"nonce": nonce, "fresh_name": fresh_name, "result_name": result_name}


def parse_float_token(token: str) -> float:
    return float(token.strip().replace("D", "E").replace("d", "e"))


def parse_ansys_cdb(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8", errors="replace")
    upper = text.upper()
    forbidden_patterns = {
        "nonlinear material": r"(?m)^\s*(?:TB|TBDATA|TBTEMP)\s*,",
        "initial state": r"(?m)^\s*INISTATE\s*,",
        "constraint equation": r"(?m)^\s*(?:CE|CEBLOCK|CERIG|CP|CPBLOCK)\s*,",
        "nodal force block": r"(?m)^\s*FBLOCK\s*,",
        "surface load block": r"(?m)^\s*(?:SFBLOCK|SFEBLOCK)\s*,",
        "direct nodal force": r"(?m)^\s*F\s*,",
        "direct surface load": r"(?m)^\s*(?:SF|SFE|SFL|SFA)\s*,",
    }
    for label, pattern in forbidden_patterns.items():
        if re.search(pattern, upper):
            raise EvaluationError("ANSYS CDB contains forbidden %s" % label)

    tref_values = [parse_float_token(value) for value in re.findall(r"(?mi)^\s*TREF\s*,\s*([^,\s]+)", text)]
    if len(tref_values) > 1 or any(not finite_number(value) for value in tref_values):
        raise EvaluationError("ANSYS global TREF definition is ambiguous or non-finite")
    for command in ("ACEL", "OMEGA", "DOMEGA", "CGOMEGA", "DCGOMG"):
        matches = re.findall(r"(?mi)^\s*%s\s*,([^\r\n]*)" % command, text)
        for row in matches:
            numbers = [parse_float_token(value) for value in row.split(",") if value.strip()]
            if any(abs(value) > 1.0e-12 for value in numbers):
                raise EvaluationError("ANSYS CDB contains nonzero %s" % command)

    etypes: dict[int, int] = {}
    et_match = re.search(r"(?ms)^ETBLOCK,[^\r\n]*\r?\n[^\r\n]*\r?\n(.*?)^\s*-1\s*$", text)
    if not et_match:
        raise EvaluationError("ANSYS CDB has no parseable ETBLOCK")
    for line in et_match.group(1).splitlines():
        values = [int(value) for value in re.findall(r"[-+]?\d+", line)]
        if len(values) >= 2:
            etypes[values[0]] = values[1]
    if not etypes:
        raise EvaluationError("ANSYS CDB ETBLOCK is empty")

    node_match = re.search(
        r"(?ms)^NBLOCK,[^\r\n]*\r?\n[^\r\n]*\r?\n(.*?)^\s*N\s*,\s*UNBL\s*,\s*LOC\s*,\s*-1\s*,?\s*$",
        text,
    )
    if not node_match:
        raise EvaluationError("ANSYS CDB has no parseable NBLOCK")
    nodes: dict[int, tuple[float, float, float]] = {}
    for line in node_match.group(1).splitlines():
        if not line.strip():
            continue
        try:
            label = int(line[0:9])
            numeric_fields = []
            for start in (27, 48, 69, 90, 111, 132):
                field = line[start : start + 21].strip()
                numeric_fields.append(parse_float_token(field) if field else 0.0)
            if any(abs(value) > 1.0e-12 for value in numeric_fields[3:]):
                raise EvaluationError("ANSYS node uses a rotated nodal coordinate system")
            nodes[label] = tuple(numeric_fields[:3])  # type: ignore[assignment]
        except Exception as exc:
            raise EvaluationError("cannot parse ANSYS NBLOCK row: %r" % line) from exc
    if len(nodes) < 8 or len(nodes) != len(set(nodes)):
        raise EvaluationError("ANSYS mesh has too few or duplicate nodes")
    expected_bounds = ((0.0, 100.0), (0.0, 10.0), (0.0, 10.0))
    actual_bounds = tuple(
        (min(point[index] for point in nodes.values()), max(point[index] for point in nodes.values()))
        for index in range(3)
    )
    if any(
        not close(actual, expected, 0.0, GEOMETRY_TOL)
        for actual_pair, expected_pair in zip(actual_bounds, expected_bounds)
        for actual, expected in zip(actual_pair, expected_pair)
    ):
        raise EvaluationError("ANSYS mesh bounds do not match the 100 x 10 x 10 mm bar")

    elem_match = re.search(r"(?ms)^EBLOCK,[^\r\n]*\r?\n[^\r\n]*\r?\n(.*?)^\s*-1\s*$", text)
    if not elem_match:
        raise EvaluationError("ANSYS CDB has no parseable EBLOCK")
    elements = []
    material_numbers = set()
    current = None
    for line in elem_match.group(1).splitlines():
        fields = [int(value) for value in re.findall(r"[-+]?\d+", line)]
        if not fields:
            continue
        if current is None:
            if len(fields) < 12:
                raise EvaluationError("cannot parse ANSYS EBLOCK element header")
            material_number, type_number = fields[0], fields[1]
            node_count, element_label = fields[8], fields[10]
            element_code = etypes.get(type_number)
            expected_width = {185: 8, 186: 20, 187: 10}.get(element_code)
            if expected_width is None or node_count != expected_width:
                raise EvaluationError("active ANSYS element is not SOLID185/186/187")
            current = {
                "material": material_number,
                "type": element_code,
                "label": element_label,
                "width": expected_width,
                "connectivity": list(fields[11:]),
            }
        else:
            current["connectivity"].extend(fields)
        if len(current["connectivity"]) >= current["width"]:
            if len(current["connectivity"]) != current["width"]:
                raise EvaluationError("ANSYS EBLOCK connectivity has an invalid width")
            connectivity = tuple(current["connectivity"])
            if any(label not in nodes for label in connectivity):
                raise EvaluationError("ANSYS element references an unknown node")
            elements.append((current["label"], connectivity, current["type"]))
            material_numbers.add(current["material"])
            current = None
    if current is not None or not elements or len(elements) != len(set(row[0] for row in elements)):
        raise EvaluationError("ANSYS EBLOCK has incomplete or duplicate elements")
    if len(material_numbers) != 1:
        raise EvaluationError("ANSYS active bar must use exactly one material")

    used_nodes = set(label for _, connectivity, _ in elements for label in connectivity)
    if used_nodes != set(nodes):
        raise EvaluationError("ANSYS mesh has unreferenced nodes")
    connectivity_sets = [set(connectivity) for _, connectivity, _ in elements]
    reached = set(connectivity_sets[0])
    pending = list(connectivity_sets[1:])
    changed = True
    while changed and pending:
        changed = False
        remaining = []
        for row in pending:
            if row & reached:
                reached.update(row)
                changed = True
            else:
                remaining.append(row)
        pending = remaining
    if pending or reached != set(nodes):
        raise EvaluationError("ANSYS active mesh is not one connected solid mesh")
    face_indices = {
        185: (
            (0, 1, 2, 3),
            (4, 5, 6, 7),
            (0, 1, 5, 4),
            (1, 2, 6, 5),
            (2, 3, 7, 6),
            (3, 0, 4, 7),
        ),
        186: (
            (0, 1, 2, 3, 8, 9, 10, 11),
            (4, 5, 6, 7, 12, 13, 14, 15),
            (0, 1, 5, 4, 8, 17, 12, 16),
            (1, 2, 6, 5, 9, 18, 13, 17),
            (2, 3, 7, 6, 10, 19, 14, 18),
            (3, 0, 4, 7, 11, 16, 15, 19),
        ),
        187: (
            (0, 1, 2, 4, 5, 6),
            (0, 1, 3, 4, 8, 7),
            (1, 2, 3, 5, 9, 8),
            (2, 0, 3, 6, 7, 9),
        ),
    }
    face_owners: dict[tuple[int, ...], list[int]] = {}
    for element_label, connectivity, element_code in elements:
        for indices in face_indices[element_code]:
            face = tuple(sorted(connectivity[index] for index in indices))
            if len(set(face)) != len(indices):
                raise EvaluationError("ANSYS mesh contains a degenerate face")
            face_owners.setdefault(face, []).append(element_label)
    element_neighbors = {element_label: set() for element_label, _, _ in elements}
    boundary_planes = set()
    for face, owners in face_owners.items():
        if len(owners) == 2:
            element_neighbors[owners[0]].add(owners[1])
            element_neighbors[owners[1]].add(owners[0])
            continue
        if len(owners) != 1:
            raise EvaluationError("ANSYS mesh has a nonmanifold face")
        points = [nodes[label] for label in face]
        matches = []
        for axis, target, name in (
            (0, 0.0, "X0"),
            (0, 100.0, "X100"),
            (1, 0.0, "Y0"),
            (1, 10.0, "Y10"),
            (2, 0.0, "Z0"),
            (2, 10.0, "Z10"),
        ):
            if all(abs(point[axis] - target) <= GEOMETRY_TOL for point in points):
                matches.append(name)
        if len(matches) != 1:
            raise EvaluationError("ANSYS mesh has a boundary face inside the solid")
        boundary_planes.add(matches[0])
    if boundary_planes != {"X0", "X100", "Y0", "Y10", "Z0", "Z10"}:
        raise EvaluationError("ANSYS mesh does not cover all six bar boundary planes")
    first_element = next(iter(element_neighbors))
    reached_elements = {first_element}
    pending_elements = [first_element]
    while pending_elements:
        current_element = pending_elements.pop()
        for neighbor in element_neighbors[current_element] - reached_elements:
            reached_elements.add(neighbor)
            pending_elements.append(neighbor)
    if reached_elements != set(element_neighbors):
        raise EvaluationError("ANSYS elements are not connected through complete faces")
    hex_edges = ((0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6), (6, 7), (7, 4), (0, 4), (1, 5), (2, 6), (3, 7))
    tet_edges = ((0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3))
    family_lengths = {"hex": [], "tet": []}
    for _, connectivity, element_code in elements:
        for first, second in (tet_edges if element_code == 187 else hex_edges):
            point_a, point_b = nodes[connectivity[first]], nodes[connectivity[second]]
            family_lengths["tet" if element_code == 187 else "hex"].append(
                math.sqrt(sum((point_a[index] - point_b[index]) ** 2 for index in range(3)))
            )
    for family, lengths in family_lengths.items():
        if not lengths:
            continue
        if any(not finite_number(value) or value <= 1.0e-8 for value in lengths):
            raise EvaluationError("ANSYS actual mesh has degenerate %s edges" % family)
        ordered = sorted(lengths)
        median = ordered[len(ordered) // 2]
        p90 = ordered[int(0.9 * (len(ordered) - 1))]
        if family == "hex":
            in_band = sum(1 for value in ordered if 3.5 <= value <= 6.5)
            valid = (
                4.5 <= median <= 5.5
                and p90 <= 6.5
                and in_band >= math.ceil(0.7 * len(ordered))
            )
        else:
            in_band = sum(1 for value in ordered if 3.0 <= value <= 8.0)
            valid = (
                4.5 <= median <= 6.5
                and p90 <= 8.0
                and max(ordered) <= 9.0
                and in_band >= math.ceil(0.7 * len(ordered))
            )
        if not valid:
            raise EvaluationError("ANSYS %s corner-edge distribution is not consistent with 5 mm" % family)

    material_number = next(iter(material_numbers))
    material_rows: dict[str, list[tuple[int, int, tuple[float, ...]]]] = {}
    allowed_material_names = {
        "EX", "PRXY", "NUXY", "ALPX", "CTEX", "REFT", "DENS"
    }
    for raw_row in re.findall(r"(?mi)^\s*MPDATA\s*,([^\r\n]*)$", text):
        fields = [field.strip() for field in raw_row.split(",")]
        if len(fields) < 6:
            raise EvaluationError("cannot parse ANSYS MPDATA row: %r" % raw_row)
        try:
            row_material = int(fields[1])
        except Exception as exc:
            raise EvaluationError("cannot parse ANSYS MPDATA material number") from exc
        if row_material != material_number:
            continue
        name = fields[2].upper()
        if name not in allowed_material_names:
            raise EvaluationError("unsupported active ANSYS material property: %s" % name)
        try:
            values = tuple(parse_float_token(value) for value in fields[5:] if value)
            start = int(fields[3]) if fields[3] else 1
            count = int(fields[4]) if fields[4] else len(values)
        except Exception as exc:
            raise EvaluationError("cannot parse active ANSYS MPDATA row") from exc
        if not values or any(not finite_number(value) for value in values):
            raise EvaluationError("active ANSYS MPDATA row is empty or non-finite")
        material_rows.setdefault(name, []).append((start, count, values))

    material: dict[str, float] = {}
    expected_material = {
        "EX": (("EX",), 210000.0),
        "PRXY": (("PRXY", "NUXY"), 0.3),
        "ALPX": (("ALPX", "CTEX"), 1.5e-5),
    }
    for canonical_name, (aliases, expected) in expected_material.items():
        matching_names = [name for name in aliases if material_rows.get(name)]
        if not matching_names:
            raise EvaluationError(
                "ANSYS material must define at least one of %s" % "/".join(aliases)
            )
        alias_values = []
        for name in matching_names:
            rows = material_rows[name]
            if len(rows) != 1 or rows[0][0:2] != (1, 1) or len(rows[0][2]) != 1:
                raise EvaluationError(
                    "ANSYS %s must be one temperature-independent value" % name
                )
            alias_values.append(rows[0][2][0])
        if any(
            not close(value, alias_values[0], 1.0e-12, 1.0e-12)
            for value in alias_values[1:]
        ):
            raise EvaluationError("ANSYS material aliases disagree: %s" % "/".join(matching_names))
        material[canonical_name] = alias_values[0]
        if not close(material[canonical_name], expected, 0.002, 1.0e-12):
            raise EvaluationError("ANSYS material property mismatch: %s" % canonical_name)
    reference_rows = material_rows.get("REFT", [])
    if reference_rows:
        if len(reference_rows) != 1 or reference_rows[0][0:2] != (1, 1) or len(reference_rows[0][2]) != 1:
            raise EvaluationError("ANSYS material REFT must be one constant value")
        effective_reference = reference_rows[0][2][0]
    elif len(tref_values) == 1:
        effective_reference = tref_values[0]
    else:
        raise EvaluationError("ANSYS model has no unambiguous thermal reference temperature")
    if not close(effective_reference, 20.0, 0.0, 1.0e-8):
        raise EvaluationError("ANSYS effective TREF/REFT is not exactly 20 C")

    d_match = re.search(r"(?ms)^DBLOCK,[^\r\n]*\r?\n[^\r\n]*\r?\n(.*?)^\s*-1\s*$", text)
    if not d_match:
        raise EvaluationError("ANSYS CDB has no DBLOCK constraints")
    constraints: dict[tuple[int, str], float] = {}
    for line in d_match.group(1).splitlines():
        match = re.match(
            r"^\s*(\d+)\s+(UX|UY|UZ)\s+([-+0-9.EeDd]+)\s+([-+0-9.EeDd]+)", line
        )
        if not match:
            raise EvaluationError("cannot parse ANSYS DBLOCK row: %r" % line)
        node, dof = int(match.group(1)), match.group(2).upper()
        real, imaginary = parse_float_token(match.group(3)), parse_float_token(match.group(4))
        if (node, dof) in constraints or abs(real) > 1.0e-12 or abs(imaginary) > 1.0e-12:
            raise EvaluationError("duplicate or nonzero ANSYS constraint")
        constraints[(node, dof)] = real
    check_constraint_map(nodes, constraints)

    body_headers = re.findall(r"(?mi)^\s*(BFBLOCK|BFEBLOCK)\s*,[^,]*,\s*([^,\s]+)", text)
    if not body_headers or any(label.upper() != "TEMP" for _, label in body_headers):
        raise EvaluationError("ANSYS CDB contains a missing or non-temperature body-load block")
    bf_match = re.search(r"(?ms)^BFBLOCK,[^\r\n]*\r?\n[^\r\n]*\r?\n(.*?)(?:^(?:BF|BFE),end,LOC|^\s*-1\s*$)", text)
    bfe_match = re.search(r"(?ms)^BFEBLOCK,[^\r\n]*\r?\n[^\r\n]*\r?\n(.*?)(?:^(?:BF|BFE),end,LOC|^\s*-1\s*$)", text)
    if (bf_match is None) == (bfe_match is None):
        raise EvaluationError(
            "ANSYS must use exactly one complete nodal or element TEMP field; headers=%r nodal=%s element=%s"
            % (body_headers, bf_match is not None, bfe_match is not None)
        )
    temperatures = {}
    if bf_match is not None:
        temperature_mode = "nodal"
        for line in bf_match.group(1).splitlines():
            match = re.match(
                r"^\s*(\d+)\s+(?:(\d+)\s+)?([-+0-9.EeDd]+)\s*$", line
            )
            if not match:
                if line.strip():
                    raise EvaluationError("cannot parse ANSYS BFBLOCK row: %r" % line)
                continue
            label = int(match.group(1))
            start_location = int(match.group(2)) if match.group(2) is not None else 1
            value = parse_float_token(match.group(3))
            if start_location != 1:
                raise EvaluationError("ANSYS nodal TEMP must start at location 1")
            if label in temperatures or not close(value, 100.0, 0.0, 1.0e-8):
                raise EvaluationError("duplicate or non-100 C ANSYS nodal temperature")
            temperatures[label] = value
        if set(temperatures) != set(nodes):
            raise EvaluationError("ANSYS nodal temperature does not cover the complete bar")
    else:
        temperature_mode = "element"
        element_types_by_label = {label: element_code for label, _, element_code in elements}
        temperature_slots = {}
        for line in bfe_match.group(1).splitlines():
            match = re.match(r"^\s*(\d+)\s+(\d+)\s+(.+?)\s*$", line)
            if not match:
                if line.strip():
                    raise EvaluationError("cannot parse ANSYS BFEBLOCK row: %r" % line)
                continue
            element_label, start_location = int(match.group(1)), int(match.group(2))
            values = tuple(parse_float_token(value) for value in match.group(3).split())
            element_code = element_types_by_label.get(element_label)
            width = {185: 8, 186: 20, 187: 10}.get(element_code)
            if width is None or start_location < 1 or not values or start_location + len(values) - 1 > width:
                raise EvaluationError("unknown, partial, or out-of-range ANSYS element temperature row")
            slots = temperature_slots.setdefault(element_label, {})
            for offset, value in enumerate(values):
                slot = start_location + offset
                if slot in slots or not close(value, 100.0, 0.0, 1.0e-8):
                    raise EvaluationError("duplicate or non-100 C ANSYS element temperature")
                slots[slot] = value
        if set(temperature_slots) != set(row[0] for row in elements):
            raise EvaluationError("ANSYS element temperature does not cover the complete bar")
        for element_label, slots in temperature_slots.items():
            width = {185: 8, 186: 20, 187: 10}[element_types_by_label[element_label]]
            corner_count = {185: 8, 186: 8, 187: 4}[element_types_by_label[element_label]]
            locations = set(slots)
            allowed_locations = (
                {1},
                set(range(1, corner_count + 1)),
                set(range(1, width + 1)),
            )
            if locations not in allowed_locations:
                raise EvaluationError("ANSYS element temperature pattern is not uniformly defined")
            temperatures[element_label] = tuple(slots[index] for index in sorted(slots))
    return {
        "nodes": nodes,
        "elements": elements,
        "material": material,
        "constraints": constraints,
        "temperatures": temperatures,
        "temperature_mode": temperature_mode,
    }


def matrix_rank_3(rows: list[list[float]]) -> int:
    matrix = [list(map(float, row)) for row in rows]
    rank = 0
    column = 0
    while rank < len(matrix) and column < 3:
        pivot = next(
            (index for index in range(rank, len(matrix)) if abs(matrix[index][column]) > 1.0e-10),
            None,
        )
        if pivot is None:
            column += 1
            continue
        matrix[rank], matrix[pivot] = matrix[pivot], matrix[rank]
        divisor = matrix[rank][column]
        matrix[rank] = [value / divisor for value in matrix[rank]]
        for index in range(len(matrix)):
            if index == rank:
                continue
            factor = matrix[index][column]
            matrix[index] = [
                matrix[index][j] - factor * matrix[rank][j] for j in range(3)
            ]
        rank += 1
        column += 1
    return rank


def check_constraint_map(
    nodes: dict[int, tuple[float, float, float]],
    constraints: dict[tuple[int, str], float],
) -> None:
    left = set(label for label, point in nodes.items() if abs(point[0]) <= GEOMETRY_TOL)
    right = set(label for label, point in nodes.items() if abs(point[0] - 100.0) <= GEOMETRY_TOL)
    actual_ux = set((node, dof) for node, dof in constraints if dof == "UX")
    expected_ux = set((node, "UX") for node in left | right)
    if actual_ux != expected_ux:
        raise EvaluationError("ANSYS UX constraints are not exactly both complete end faces")
    transverse = [(node, dof) for node, dof in constraints if dof in ("UY", "UZ")]
    if len(transverse) != 3 or len(constraints) != len(expected_ux) + 3:
        raise EvaluationError("ANSYS must have exactly three transverse scalar constraints")
    sides = set(
        0 if abs(nodes[node][0]) <= GEOMETRY_TOL else 100 if abs(nodes[node][0] - 100.0) <= GEOMETRY_TOL else -1
        for node, _ in transverse
    )
    if len(sides) != 1 or -1 in sides:
        raise EvaluationError("ANSYS transverse constraints are not on one end face")
    rank_rows = []
    for node, dof in transverse:
        _, y, z = nodes[node]
        rank_rows.append([1.0, 0.0, -z] if dof == "UY" else [0.0, 1.0, y])
    if matrix_rank_3(rank_rows) != 3:
        raise EvaluationError("ANSYS transverse constraints have rank below three")


def check_ansys_listings(work: Path, audit: dict[str, object]) -> None:
    load_text = (work / "load_listing.txt").read_text(encoding="utf-8", errors="replace")
    constraint_rows = re.findall(
        r"(?m)^\s*(\d+)\s+(UX|UY|UZ)\s+([-+0-9.EeDd]+)\s+([-+0-9.EeDd]+)\s*$",
        load_text,
    )
    listed_constraints = {}
    for raw_node, dof, raw_real, raw_imaginary in constraint_rows:
        key = (int(raw_node), dof.upper())
        if key in listed_constraints:
            raise EvaluationError("ANSYS DLIST contains a duplicate constraint")
        real, imaginary = parse_float_token(raw_real), parse_float_token(raw_imaginary)
        if abs(real) > 1.0e-12 or abs(imaginary) > 1.0e-12:
            raise EvaluationError("ANSYS DLIST contains a nonzero constraint")
        listed_constraints[key] = real
    if set(listed_constraints) != set(audit["constraints"]):
        raise EvaluationError("ANSYS DLIST does not match the DB constraints")
    if audit["temperature_mode"] == "nodal":
        temperature_rows = re.findall(r"(?m)^\s*(\d+)\s+100\.000000\s*$", load_text)
        listed_temperatures = [int(value) for value in temperature_rows]
        if len(listed_temperatures) != len(set(listed_temperatures)) or set(listed_temperatures) != set(audit["temperatures"]):
            raise EvaluationError("ANSYS BFLIST does not match the complete DB temperature field")
        upper_load_text = load_text.upper()
        no_element_temperature = (
            "NO ELEMENT TEMPERATURES TO LIST" in upper_load_text
            or "NO ELEMENT BODY FORCE LOADS TO LIST" in upper_load_text
        )
        if not no_element_temperature or re.search(
            r"(?m)^\s*ELEMENT=\s*\d+\s+TEMPERATURES", upper_load_text
        ):
            raise EvaluationError("ANSYS nodal TEMP model has unexpected element body loads")
    else:
        if "NO NODAL TEMPERATURES TO LIST" not in load_text.upper():
            raise EvaluationError("ANSYS element TEMP model has unexpected nodal temperatures")
        element_blocks = re.findall(
            r"(?ms)^\s*ELEMENT=\s*(\d+)\s+TEMPERATURES\s*(.*?)(?=^\s*ELEMENT=|^\s*\*\*\* MAPDL|^\s*LIST |^\s*\*\*\* NOTE|\Z)",
            load_text,
        )
        listed = {}
        for raw_label, body in element_blocks:
            label = int(raw_label)
            values = [
                parse_float_token(value)
                for value in re.findall(r"[-+]?\d+\.\d+(?:[EeDd][-+]?\d+)?", body)
            ]
            if (
                label in listed
                or label not in audit["temperatures"]
                or not values
                or any(not close(value, 100.0, 0.0, 1.0e-8) for value in values)
            ):
                raise EvaluationError("ANSYS BFELIST contains duplicate or non-100 C data")
            listed[label] = values
        if set(listed) != set(audit["temperatures"]):
            raise EvaluationError("ANSYS BFELIST does not cover every active element")
    upper = load_text.upper()
    note_prefix = r"(?m)^\s*\*{3}\s+NOTE\s+\*{3}[^\r\n]*\r?\n"
    empty_patterns = (
        note_prefix + r"\s*NO NODAL FORCES TO LIST\.?\s*$",
        note_prefix + r"\s*NO SURFACE LOADS TO LIST\.?\s*$",
        note_prefix + r"\s*NO SURFACE LOADS ON LINES TO LIST\.?\s*$",
    )
    area_loads_empty = re.search(
        note_prefix
        + r"\s*(?:NO SURFACE LOADS ON AREAS TO LIST|NO AREAS DEFINED)\.?\s*$",
        upper,
    )
    if any(re.search(pattern, upper) is None for pattern in empty_patterns) or area_loads_empty is None:
        raise EvaluationError("ANSYS mechanical load listings are not all empty")


def read_ansys_rst(path: Path) -> dict[str, object]:
    reader = ansys_reader_runtime()
    result = reader.read_binary(str(path))
    mesh_labels = [int(value) for value in result.mesh.nnum]
    mesh_rows = [tuple(float(value) for value in row[:3]) for row in result.mesh.nodes]
    if (
        len(mesh_labels) != len(set(mesh_labels))
        or len(mesh_labels) != len(mesh_rows)
        or any(len(row) != 3 or any(not math.isfinite(value) for value in row) for row in mesh_rows)
    ):
        raise EvaluationError("%s contains duplicate or invalid mesh nodes" % path.name)
    nodes = dict(zip(mesh_labels, mesh_rows))
    type_codes = {int(row[0]): int(row[1]) for row in result.mesh.ekey}
    elements = {}
    element_labels = []
    for record in result.mesh.elem:
        type_reference = int(record[1])
        label = int(record[8])
        element_code = type_codes.get(type_reference)
        width = {185: 8, 186: 20, 187: 10}.get(element_code)
        if label <= 0 or width is None:
            raise EvaluationError("%s contains an unsupported solid element" % path.name)
        connectivity = tuple(int(value) for value in record[10 : 10 + width])
        if len(connectivity) != width or any(value not in nodes for value in connectivity):
            raise EvaluationError("%s has incomplete RST element connectivity" % path.name)
        element_labels.append(label)
        elements[label] = (element_code, connectivity)
    result_sets = int(result.nsets)
    if len(element_labels) != len(set(element_labels)) or result_sets < 1:
        raise EvaluationError("%s contains duplicate elements or no result set" % path.name)
    result_index = result_sets - 1
    displacement_labels, displacements = result.nodal_solution(result_index)
    if len(displacement_labels) != len(displacements):
        raise EvaluationError("%s displacement labels and values differ in length" % path.name)
    signature = {"U": {}, "S_ELEMENT": {}, "S_NODAL": {}, "RF": {}}
    for raw_label, raw_row in zip(displacement_labels, displacements):
        label = int(raw_label)
        row = tuple(float(value) for value in raw_row)
        if label in signature["U"] or len(row) != 3 or any(not math.isfinite(value) for value in row):
            raise EvaluationError("%s has duplicate or non-finite U output" % path.name)
        signature["U"][label] = row
    if set(signature["U"]) != set(nodes):
        raise EvaluationError("%s U output does not cover every mesh node" % path.name)

    if "ENS :" not in str(result.available_results).upper():
        raise EvaluationError("%s does not advertise native element stress results" % path.name)
    stress_labels, stress_rows, stress_nodes = result.element_stress(result_index)
    stress_labels = [int(value) for value in stress_labels]
    if (
        len(stress_labels) != len(stress_rows)
        or len(stress_labels) != len(stress_nodes)
        or len(stress_labels) != len(set(stress_labels))
        or set(stress_labels) != set(elements)
    ):
        raise EvaluationError("%s element stress coverage is incomplete" % path.name)
    for index, element_label in enumerate(stress_labels):
        element_code, connectivity = elements[element_label]
        expected_count = {185: 8, 186: 8, 187: 4}[element_code]
        row_nodes = tuple(int(value) for value in stress_nodes[index])
        rows = list(stress_rows[index])
        if (
            len(row_nodes) != expected_count
            or len(rows) != expected_count
            or set(row_nodes) != set(connectivity[:expected_count])
        ):
            raise EvaluationError("%s element stress node coverage is incomplete" % path.name)
        for node_label, raw_row in zip(row_nodes, rows):
            row = tuple(float(value) for value in raw_row)
            key = (element_label, node_label)
            if key in signature["S_ELEMENT"] or len(row) != 6 or any(not math.isfinite(value) for value in row):
                raise EvaluationError("%s has duplicate or non-finite S output" % path.name)
            signature["S_ELEMENT"][key] = row

    nodal_stress_labels, nodal_stress_rows = result.nodal_stress(result_index)
    if len(nodal_stress_labels) != len(nodal_stress_rows):
        raise EvaluationError("%s nodal-stress labels and values differ in length" % path.name)
    for raw_label, raw_row in zip(nodal_stress_labels, nodal_stress_rows):
        label = int(raw_label)
        row = tuple(float(value) for value in raw_row)
        if label in signature["S_NODAL"] or len(row) != 6:
            raise EvaluationError("%s has duplicate or malformed nodal S output" % path.name)
        if all(math.isfinite(value) for value in row):
            signature["S_NODAL"][label] = row
        elif all(math.isnan(value) for value in row):
            signature["S_NODAL"][label] = None
        else:
            raise EvaluationError("%s has invalid non-finite nodal S output" % path.name)
    if set(signature["S_NODAL"]) != set(nodes):
        raise EvaluationError("%s nodal-stress labels do not cover every mesh node" % path.name)
    finite_stress_nodes = {
        node_label for node_label, row in signature["S_NODAL"].items() if row is not None
    }
    element_stress_nodes = {node_label for _, node_label in signature["S_ELEMENT"]}
    if finite_stress_nodes != element_stress_nodes:
        raise EvaluationError("%s nodal and element stress coverage disagree" % path.name)

    reaction_values, reaction_nodes, reaction_dofs = result.nodal_reaction_forces(result_index)
    if not (len(reaction_values) == len(reaction_nodes) == len(reaction_dofs)):
        raise EvaluationError("%s reaction labels and values differ in length" % path.name)
    for raw_value, raw_node, raw_dof in zip(reaction_values, reaction_nodes, reaction_dofs):
        key = (int(raw_node), int(raw_dof))
        value = float(raw_value)
        if key in signature["RF"] or key[0] not in nodes or not math.isfinite(value):
            raise EvaluationError("%s has duplicate, unknown, or non-finite RF output" % path.name)
        signature["RF"][key] = value
    if not signature["RF"]:
        raise EvaluationError("%s has no native reaction-force records" % path.name)
    return {"nodes": nodes, "elements": elements, "signature": signature}


def compare_ansys_rst(
    submitted: dict[str, object],
    fresh: dict[str, object],
    audit: dict[str, object],
) -> None:
    audit_nodes = audit["nodes"]
    audit_elements = {
        int(label): (int(element_code), tuple(int(value) for value in connectivity))
        for label, connectivity, element_code in audit["elements"]
    }
    for label, result in (("submitted", submitted), ("fresh", fresh)):
        nodes = result["nodes"]
        if set(nodes) != set(audit_nodes) or result["elements"] != audit_elements:
            raise EvaluationError("%s RST mesh/type/connectivity does not match the DB" % label)
        for node in nodes:
            if any(
                not close(actual, expected, 0.0, 1.0e-8)
                for actual, expected in zip(nodes[node], audit_nodes[node])
            ):
                raise EvaluationError("%s RST coordinates do not match the DB" % label)
        expected_reactions = {
            (int(node), {"UX": 1, "UY": 2, "UZ": 3}[str(dof)])
            for node, dof in audit["constraints"]
        }
        if set(result["signature"]["RF"]) != expected_reactions:
            raise EvaluationError("%s RST reaction coverage does not match the DB constraints" % label)
    tolerances = {
        "U": (2.0e-4, 1.0e-7),
        "S_ELEMENT": (2.0e-4, 0.02),
        "S_NODAL": (2.0e-4, 0.02),
        "RF": (2.0e-4, 0.1),
    }
    for field in ("U", "S_ELEMENT", "S_NODAL", "RF"):
        left = submitted["signature"][field]
        right = fresh["signature"][field]
        if set(left) != set(right):
            raise EvaluationError("submitted and fresh RST %s coverage differs" % field)
        rel, absolute = tolerances[field]
        for key in left:
            if left[key] is None or right[key] is None:
                if left[key] is not None or right[key] is not None:
                    raise EvaluationError("submitted RST %s finite-value mask differs" % field)
                continue
            left_values = left[key] if isinstance(left[key], tuple) else (left[key],)
            right_values = right[key] if isinstance(right[key], tuple) else (right[key],)
            if len(left_values) != len(right_values) or any(
                not close(actual, expected, rel, absolute)
                for actual, expected in zip(left_values, right_values)
            ):
                raise EvaluationError("submitted RST %s does not match isolated re-solve" % field)


def run_ansys(
    work: Path, db_path: Path, rst_path: Path, metrics: dict[str, float], nonce: str
) -> dict[str, float]:
    shutil.copy2(db_path, work / "submitted.db")
    shutil.copy2(rst_path, work / "submitted.rst")
    checker = work / ("ansys_checker_%s.inp" % nonce)
    output = work / ("ansys_checker_%s.out" % nonce)
    short_nonce = nonce[:16]
    result_path = work / ("ansys_result_%s.json" % short_nonce)
    fresh_rst = work / ("fresh_%s.rst" % short_nonce)
    checker.write_text(ansys_checker_source(nonce), encoding="ascii")
    result_path.unlink(missing_ok=True)
    fresh_rst.unlink(missing_ok=True)
    command = [
        ANSYS_EXEC,
        "-b",
        "-dis",
        "-np",
        "1",
        "-j",
        "eval_%s" % short_nonce,
        "-dir",
        str(work),
        "-i",
        str(checker),
        "-o",
        str(output),
    ]
    completed = run_owned_process(command, work, timeout=1200)
    log("ANSYS checker returncode=%s" % completed.returncode)
    if completed.stdout:
        log("ANSYS stdout tail=" + completed.stdout[-3000:])
    if completed.stderr:
        log("ANSYS stderr tail=" + completed.stderr[-3000:])
    if completed.returncode != 0:
        raise EvaluationError("ANSYS audit/solve returned nonzero")
    if not output.is_file() or output.stat().st_size <= 0:
        raise EvaluationError("ANSYS did not create a run output")
    output_text = output.read_text(encoding="utf-8", errors="replace")
    errors = re.findall(r"NUMBER OF ERROR\s+MESSAGES ENCOUNTERED=\s*(\d+)", output_text)
    if not errors or int(errors[-1]) != 0 or "RUN COMPLETED" not in output_text:
        raise EvaluationError("ANSYS run did not complete with zero errors")
    if not fresh_rst.is_file() or fresh_rst.stat().st_size <= 0:
        raise EvaluationError("ANSYS isolated re-solve did not create a fresh RST")
    audit = parse_ansys_cdb(work / "model_audit.cdb")
    check_ansys_listings(work, audit)
    submitted_rst = read_ansys_rst(work / "submitted.rst")
    fresh_rst_result = read_ansys_rst(fresh_rst)
    compare_ansys_rst(submitted_rst, fresh_rst_result, audit)
    payload = read_json_strict(result_path)
    if not isinstance(payload, dict) or payload.get("nonce") != nonce or payload.get("ok") is not True:
        raise EvaluationError("ANSYS returned missing/stale/invalid nonce result")
    if (
        int(round(float(payload.get("node_count", -1)))) != len(audit["nodes"])
        or int(round(float(payload.get("element_count", -1)))) != len(audit["elements"])
    ):
        raise EvaluationError("ANSYS result-side mesh count mismatch")
    expected_bounds = [0.0, 100.0, 0.0, 10.0, 0.0, 10.0]
    actual_bounds = payload.get("bounds")
    if not isinstance(actual_bounds, list) or len(actual_bounds) != 6 or any(
        not finite_number(actual) or not close(float(actual), expected, 0.0, GEOMETRY_TOL)
        for actual, expected in zip(actual_bounds, expected_bounds)
    ):
        raise EvaluationError("ANSYS result-side geometry bounds mismatch")
    geometry = payload.get("geometry")
    geometry_keys = {
        "element_volume_sum",
        "volume_count",
        "native_volume",
        "geometry_element_count",
    }
    if (
        not isinstance(geometry, dict)
        or set(geometry) != geometry_keys
        or any(not finite_number(geometry[key]) for key in geometry_keys)
    ):
        raise EvaluationError("ANSYS result-side geometry object is invalid")
    if not close(float(geometry["element_volume_sum"]), 10000.0, 0.0, 0.1):
        raise EvaluationError("ANSYS active element volume is not 10000 mm^3")
    volume_count = int(round(float(geometry["volume_count"])))
    if volume_count < 0 or not close(
        float(geometry["volume_count"]), float(volume_count), 0.0, 1.0e-8
    ):
        raise EvaluationError("ANSYS native volume count is invalid")
    if volume_count:
        if not close(float(geometry["native_volume"]), 10000.0, 0.0, 0.1):
            raise EvaluationError("ANSYS native geometry volume is not 10000 mm^3")
        if int(round(float(geometry["geometry_element_count"]))) != len(
            audit["elements"]
        ):
            raise EvaluationError("ANSYS native volumes do not own every active element")
    elif not (
        close(float(geometry["native_volume"]), -1.0, 0.0, 1.0e-8)
        and close(float(geometry["geometry_element_count"]), -1.0, 0.0, 1.0e-8)
    ):
        raise EvaluationError("ANSYS mesh-only geometry sentinel is invalid")
    actual_material = payload.get("material")
    expected_material = [210000.0, 0.3, 1.5e-5]
    if not isinstance(actual_material, list) or len(actual_material) != 3 or any(
        not finite_number(actual) or not close(float(actual), expected, 0.002, 1.0e-12)
        for actual, expected in zip(actual_material, expected_material)
    ):
        raise EvaluationError(
            "ANSYS result-side material mismatch: actual=%r CDB=%r"
            % (actual_material, audit["material"])
        )
    submitted = normalize_ansys_result(payload.get("submitted"), "submitted RST")
    fresh = normalize_ansys_result(payload.get("fresh"), "fresh RST")
    require_physical_metrics(fresh, "fresh RST")
    compare_metrics(submitted, fresh, "submitted RST versus fresh RST")
    compare_metrics(metrics, fresh, "metrics.json versus fresh RST")
    return fresh


def normalize_ansys_result(value: object, label: str) -> dict[str, float]:
    if not isinstance(value, dict):
        raise EvaluationError("%s result object missing" % label)
    required = {"thermal_stress", "reaction_force", "left_rf", "right_rf"}
    if set(value) != required or any(not finite_number(value[key]) for key in required):
        raise EvaluationError("%s result object is invalid" % label)
    left, right = float(value["left_rf"]), float(value["right_rf"])
    if abs(left + right) > max(20.0, 0.005 * EXPECTED_REACTION):
        raise EvaluationError("%s reactions are not balanced" % label)
    return {
        "thermal_stress": float(value["thermal_stress"]),
        "reaction_force": float(value["reaction_force"]),
    }


def write_detail(root: Path, passed: bool) -> None:
    try:
        (root / "eval_detail.txt").write_text("\n".join(DETAILS) + "\n", encoding="utf-8")
        (root / "eval_result.txt").write_text("True\n" if passed else "False\n", encoding="utf-8")
    except Exception:
        pass


def evaluate() -> tuple[bool, Path]:
    desktop = desktop_dir()
    root = desktop / 'result'
    if not root.is_dir():
        log('result directory missing')
        return False, desktop
    work: Path | None = None
    passed = False
    try:
        metrics = read_metrics(root)
        backend, model_path, result_path = select_backend(root)
        nonce = uuid.uuid4().hex
        work = Path(
            tempfile.mkdtemp(
                prefix="engiworld_task17_eval_%s_" % nonce[:12],
                dir=os.environ.get("ENGIWORLD_EVAL_TEMP") or None,
            )
        )
        if backend == "abaqus":
            fresh = run_abaqus(work, model_path, result_path, metrics, nonce)
        else:
            fresh = run_ansys(work, model_path, result_path, metrics, nonce)
        log("Task-17 %s branch passed with fresh metrics %r" % (backend, fresh))
        passed = True
    except Exception as exc:
        log("Task-17 evaluator rejected submission: %s" % exc)
        log(traceback.format_exc())
    finally:
        if work is not None:
            if not cleanup_evaluator_work(work):
                passed = False
            else:
                log("removed evaluator isolation directory: %s" % work)
    return passed, root


def main() -> None:
    passed, root = evaluate()
    write_detail(root, passed)
    sys.stdout.write("True\n" if passed else "False\n")


if __name__ == "__main__":
    main()
