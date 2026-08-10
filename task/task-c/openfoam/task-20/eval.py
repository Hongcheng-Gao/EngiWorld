#!/usr/bin/env python3
from __future__ import annotations

import csv
import math
import re
import subprocess
from pathlib import Path


ROOT = Path("/home/user/Desktop")
CASE = ROOT / "dynamic"
FORCES = CASE / "postProcessing/bodyForces/0/forces.dat"
NUMBER = re.compile(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def named_block(text: str, name: str) -> str:
    text = re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.S)
    match = re.search(rf"(?m)^\s*{re.escape(name)}\s*\{{", text)
    if not match:
        raise ValueError(f"missing block {name}")
    start = text.find("{", match.start())
    depth = 0
    for index in range(start, len(text)):
        depth += text[index] == "{"
        depth -= text[index] == "}"
        if depth == 0:
            return text[start + 1 : index]
    raise ValueError(f"unterminated block {name}")


def paren_section(text: str, name: str) -> str:
    match = re.search(rf"(?m)^\s*{re.escape(name)}\s*\(", text)
    if not match:
        raise ValueError(f"missing section {name}")
    start = text.find("(", match.start())
    depth = 0
    for index in range(start, len(text)):
        depth += text[index] == "("
        depth -= text[index] == ")"
        if depth == 0:
            return text[start + 1 : index]
    raise ValueError(f"unterminated section {name}")


def has_entry(block: str, key: str, value: str) -> bool:
    return re.search(rf"(?<!\w){re.escape(key)}\s+{value}\s*;", block) is not None


def patch(text: str, name: str) -> str:
    return named_block(named_block(text, "boundaryField"), name)


def zone_labels(text: str, name: str) -> set[int]:
    block = named_block(text, name)
    match = re.search(r"\bcellLabels\s+List<label>\s+(\d+)\s*\((.*?)\)\s*;", block, re.S)
    if not match:
        raise ValueError(f"missing labels for zone {name}")
    labels = [int(value) for value in match.group(2).split()]
    if len(labels) != int(match.group(1)) or len(labels) != len(set(labels)):
        raise ValueError("invalid cell-zone labels")
    return set(labels)


def vector_field(path: Path) -> list[tuple[float, float, float]]:
    match = re.search(r"internalField\s+nonuniform\s+List<vector>\s+(\d+)\s*\((.*?)\)\s*;", read(path), re.S)
    if not match:
        raise ValueError("missing vector field")
    values = [tuple(float(value) for value in item.split()) for item in re.findall(r"\(([^()]+)\)", match.group(2))]
    if len(values) != int(match.group(1)):
        raise ValueError("vector field count mismatch")
    return values


def mesh_geometry_is_valid(mesh: str) -> bool:
    vertices = [
        tuple(float(value) for value in item.split())
        for item in re.findall(r"\(([^()]+)\)", paren_section(mesh, "vertices"))
    ]
    if len(vertices) != 64:
        return False
    xs, ys, zs = zip(*vertices)
    inner = [point for point in vertices if abs(math.hypot(point[0], point[1]) - 1.0) <= 1.0e-5]
    return (
        abs(min(xs) + 5.0) <= 1.0e-12
        and abs(max(xs) - 5.0) <= 1.0e-12
        and abs(min(ys) + 1.5) <= 1.0e-12
        and abs(max(ys) - 2.5) <= 1.0e-12
        and abs(min(zs) + 1.0) <= 1.0e-12
        and abs(max(zs) - 1.0) <= 1.0e-12
        and len(inner) == 16
    )


def internal_count(path: Path, kind: str) -> int:
    match = re.search(rf"internalField\s+nonuniform\s+List<{kind}>\s+(\d+)", read(path))
    if not match:
        raise ValueError(f"missing nonuniform {kind} field")
    return int(match.group(1))


def force_history() -> list[tuple[float, float, float, float, float]]:
    history = []
    for line in read(FORCES).splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        values = [float(value) for value in NUMBER.findall(stripped)]
        if len(values) < 10:
            raise ValueError("invalid forces.dat row")
        pressure_fx = values[1]
        viscous_fx = values[4]
        porous_fx = values[7]
        history.append((values[0], pressure_fx, viscous_fx, porous_fx, pressure_fx + viscous_fx + porous_fx))
    return history


def check_case() -> bool:
    mesh = read(CASE / "system/blockMeshDict")
    motion = read(CASE / "constant/dynamicMeshDict")
    topology = read(CASE / "system/topoSetDict")
    velocity = read(CASE / "0/U")
    physical = read(CASE / "constant/physicalProperties")
    momentum = read(CASE / "constant/momentumTransport")
    pressure = read(CASE / "0/p")
    control = read(CASE / "system/controlDict")
    forces = named_block(named_block(control, "functions"), "bodyForces")
    return all(
        (
            mesh.count("hex (") == 20,
            mesh_geometry_is_valid(mesh),
            mesh.count("(10 10 1)") == 16,
            mesh.count("(10 5 1)") == 4,
            "type motionSolver;" in motion,
            "motionSolver solidBody;" in motion,
            "cellZone movingZone;" in motion,
            "solidBodyMotionFunction oscillatingRotatingMotion;" in motion,
            "origin (0 0 0);" in motion,
            "amplitude (0 0 5);" in motion,
            "omega 6.283185307179586;" in motion,
            "radius 1.41;" in topology,
            has_entry(patch(velocity, "left"), "value", r"uniform\s+\(0\.5\s+0(?:\.0+)?\s+0(?:\.0+)?\)"),
            has_entry(patch(velocity, "right"), "type", r"zeroGradient"),
            all(has_entry(patch(velocity, name), "type", r"slip") for name in ("down", "up")),
            has_entry(patch(velocity, "cylinder"), "type", r"movingWallVelocity"),
            has_entry(patch(pressure, "right"), "type", r"fixedValue"),
            has_entry(patch(pressure, "right"), "value", r"uniform\s+0(?:\.0+)?"),
            re.search(r"\bnu\s+\[0 2 -1 0 0 0 0\]\s+0\.01\s*;", physical) is not None,
            "simulationType laminar;" in momentum,
            re.search(r"\bendTime\s+2\s*;", control) is not None,
            re.search(r"\bdeltaT\s+0\.001\s*;", control) is not None,
            re.search(r"\bwriteInterval\s+0\.25\s*;", control) is not None,
            has_entry(forces, "type", r"forces"),
            has_entry(forces, "patches", r"\(\s*cylinder\s*\)"),
            has_entry(forces, "rhoInf", r"1(?:\.0+)?"),
            has_entry(forces, "CofR", r"\(0(?:\.0+)?\s+0(?:\.0+)?\s+0(?:\.0+)?\)"),
        )
    )


def check() -> bool:
    required = (
        ROOT / "build_case.py",
        ROOT / "postprocess.py",
        ROOT / "summary.txt",
        ROOT / "force_history.csv",
        CASE / "log.blockMesh",
        CASE / "log.checkMesh",
        CASE / "log.topoSet",
        CASE / "log.pimpleFoam",
        CASE / "log.checkMeshFinal",
        CASE / "constant/polyMesh/cellZones",
        CASE / "0.25/polyMesh/points",
        CASE / "2/U",
        CASE / "2/p",
        FORCES,
    )
    if any(not path.is_file() or path.stat().st_size == 0 for path in required):
        return False
    initial_mesh_log = read(CASE / "log.checkMesh")
    final_mesh_log = read(CASE / "log.checkMeshFinal")
    solve_log = read(CASE / "log.pimpleFoam")
    if not (
        "End" in read(CASE / "log.blockMesh")
        and "End" in read(CASE / "log.topoSet")
        and "Mesh OK." in initial_mesh_log
        and "End" in initial_mesh_log
        and "Mesh OK." in final_mesh_log
        and "End" in final_mesh_log
        and "Time = 2" in solve_log
        and "End" in solve_log
        and "movingZone" in read(CASE / "constant/polyMesh/cellZones")
        and internal_count(CASE / "2/U", "vector") == 1800
        and internal_count(CASE / "2/p", "scalar") == 1800
        and (CASE / "0.25/polyMesh/points").read_bytes() != (CASE / "constant/polyMesh/points").read_bytes()
    ):
        return False
    mesh_check = subprocess.run(
        [
            "bash",
            "--noprofile",
            "--norc",
            "-c",
            "trap - CHLD; . /opt/openfoam11/etc/bashrc && checkMesh -latestTime -case /home/user/Desktop/dynamic",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=120,
    )
    if mesh_check.returncode != 0 or "Mesh OK." not in mesh_check.stdout or not check_case():
        return False

    centres_result = subprocess.run(
        [
            "bash",
            "--noprofile",
            "--norc",
            "-c",
            "trap - CHLD; . /opt/openfoam11/etc/bashrc && postProcess -case /home/user/Desktop/dynamic -latestTime -func writeCellCentres",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=120,
    )
    if centres_result.returncode != 0 or "End" not in centres_result.stdout:
        return False
    centres = vector_field(CASE / "2/C")
    actual_zone = zone_labels(read(CASE / "constant/polyMesh/cellZones"), "movingZone")
    expected_zone = {
        index
        for index, point in enumerate(centres)
        if math.hypot(point[0], point[1]) <= 1.41 + 1.0e-9 and -2.0 <= point[2] <= 2.0
    }
    if actual_zone != expected_zone or not actual_zone or len(actual_zone) >= 1800:
        return False

    history = force_history()
    if not history or abs(history[-1][0] - 2.0) > 1e-9:
        return False
    if not all(all(math.isfinite(value) for value in row) for row in history) or any(
        right[0] <= left[0] for left, right in zip(history, history[1:])
    ):
        return False
    keys = ("time_s", "pressure_fx_n", "viscous_fx_n", "porous_fx_n", "total_fx_n")
    with (ROOT / "force_history.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != len(history) or set(rows[0]) != set(keys):
        return False
    for row, expected in zip(rows, history):
        actual = tuple(float(row[key]) for key in keys)
        if any(abs(left - right) > 5e-7 for left, right in zip(actual, expected)):
            return False

    lines = [line.strip() for line in read(ROOT / "summary.txt").splitlines() if line.strip()]
    if len(lines) != 1:
        return False
    reported = float(lines[0])
    return math.isfinite(reported) and abs(reported - history[-1][4]) <= 5e-7


def main() -> int:
    try:
        result = check()
    except Exception:
        result = False
    print("True" if result else "False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
