#!/usr/bin/env python3
from __future__ import annotations

import ast
import csv
import math
import os
import re
import shlex
import subprocess
from pathlib import Path


ROOT = Path(os.environ.get("ENGIWORLD_EVAL_ROOT", "/home/user/Desktop"))
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


def scalar_entry(text: str, key: str) -> float:
    match = re.search(rf"(?<!\w){re.escape(key)}\s+({NUMBER.pattern})\s*;", text)
    if not match:
        raise ValueError(f"missing scalar entry {key}")
    return float(match.group(1))


def dimensioned_scalar(text: str, key: str) -> float:
    match = re.search(
        rf"(?<!\w){re.escape(key)}\s+(?:\[[^\]]+\]\s+)?({NUMBER.pattern})\s*;",
        text,
    )
    if not match:
        raise ValueError(f"missing dimensioned scalar entry {key}")
    return float(match.group(1))


def vector_entry(text: str, key: str) -> tuple[float, float, float]:
    match = re.search(
        rf"(?<!\w){re.escape(key)}\s+\(\s*({NUMBER.pattern})\s+({NUMBER.pattern})\s+({NUMBER.pattern})\s*\)\s*;",
        text,
    )
    if not match:
        raise ValueError(f"missing vector entry {key}")
    return tuple(float(match.group(index)) for index in range(1, 4))


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


def field_count(path: Path, kind: str, class_name: str) -> int:
    text = read(path)
    if not (
        re.search(r"(?m)^\s*format\s+ascii\s*;", text)
        and re.search(rf"(?m)^\s*class\s+{re.escape(class_name)}\s*;", text)
    ):
        raise ValueError(f"invalid field header: {path}")
    match = re.search(
        rf"internalField\s+nonuniform\s+List<{kind}>\s+(\d+)\s*\((.*?)\)\s*;",
        text,
        re.S,
    )
    if not match:
        raise ValueError(f"missing nonuniform {kind} field")
    declared = int(match.group(1))
    if kind == "vector":
        values = [
            tuple(float(value) for value in item.split())
            for item in re.findall(r"\(([^()]+)\)", match.group(2))
        ]
        if any(len(value) != 3 for value in values):
            raise ValueError("invalid vector width")
        flattened = [value for vector in values for value in vector]
        actual = len(values)
    else:
        flattened = [float(value) for value in NUMBER.findall(match.group(2))]
        actual = len(flattened)
    if declared != actual or not all(math.isfinite(value) for value in flattened):
        raise ValueError("field declaration/value mismatch")
    return declared


def force_history() -> list[tuple[float, float, float, float]]:
    header = None
    history = []
    for line in read(FORCES).splitlines():
        stripped = line.strip()
        if stripped.startswith("# Time"):
            header = " ".join(stripped.split())
            continue
        if not stripped or stripped.startswith("#"):
            continue
        time_match = re.match(rf"^\s*({NUMBER.pattern})\s+", stripped)
        vectors = re.findall(
            rf"\(\s*({NUMBER.pattern})\s+({NUMBER.pattern})\s+({NUMBER.pattern})\s*\)",
            stripped,
        )
        if time_match is None or len(vectors) != 4:
            raise ValueError("forces.dat row does not contain four pressure/viscous vectors")
        pressure_fx = float(vectors[0][0])
        viscous_fx = float(vectors[1][0])
        history.append((float(time_match.group(1)), pressure_fx, viscous_fx, pressure_fx + viscous_fx))
    if header is None:
        raise ValueError("missing forces.dat component header")
    if "forces(pressure viscous)" not in header or "moments(pressure viscous)" not in header:
        raise ValueError("unexpected forces.dat component header")
    if "porous" in header.lower():
        raise ValueError("unexpected porous component in non-porous case")
    return history


def log_completed(path: Path, required: tuple[str, ...] = ()) -> bool:
    text = read(path)
    low = text.lower()
    return (
        "foam fatal" not in low
        and text.rstrip().endswith("End")
        and all(token in text for token in required)
    )


def postprocess_script_is_valid(path: Path) -> bool:
    source = read(path)
    ast.parse(source)
    original = FORCES.read_bytes()
    original_history = force_history()
    delta = 0.123456789
    restored = False
    mutation_ok = False
    try:
        text = original.decode("utf-8")
        lines = text.splitlines()
        data_indexes = [
            index
            for index, line in enumerate(lines)
            if line.strip() and not line.lstrip().startswith("#")
        ]
        if not data_indexes:
            return False
        last_index = data_indexes[-1]
        first_vector = re.search(
            rf"(\(\s*)({NUMBER.pattern})(\s+{NUMBER.pattern}\s+{NUMBER.pattern}\s*\))",
            lines[last_index],
        )
        if first_vector is None:
            return False
        mutated_pressure = float(first_vector.group(2)) + delta
        lines[last_index] = (
            lines[last_index][: first_vector.start()]
            + first_vector.group(1)
            + f"{mutated_pressure:.12g}"
            + first_vector.group(3)
            + lines[last_index][first_vector.end() :]
        )
        FORCES.write_text("\n".join(lines) + ("\n" if text.endswith("\n") else ""), encoding="utf-8")
        environment = os.environ.copy()
        environment["ENGIWORLD_TASK_ROOT"] = str(ROOT)
        result = subprocess.run(
            ["python3", str(path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=30,
            env=environment,
        )
        if result.returncode == 0:
            reported = float(read(ROOT / "summary.txt").strip())
            with (ROOT / "force_history.csv").open(encoding="utf-8", newline="") as stream:
                rows = list(csv.DictReader(stream))
            expected = original_history[-1][3] + delta
            mutation_ok = (
                len(rows) == 2001
                and tuple(rows[0]) == ("time_s", "pressure_fx_n", "viscous_fx_n", "total_fx_n")
                and abs(float(rows[-1]["total_fx_n"]) - expected) <= 5.0e-7
                and abs(reported - expected) <= 5.0e-7
            )
    finally:
        FORCES.write_bytes(original)
        environment = os.environ.copy()
        environment["ENGIWORLD_TASK_ROOT"] = str(ROOT)
        restored = subprocess.run(
            ["python3", str(path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=30,
            env=environment,
        ).returncode == 0
    return mutation_ok and restored


def check_case() -> bool:
    mesh = read(CASE / "system/blockMeshDict")
    motion = read(CASE / "constant/dynamicMeshDict")
    mover = named_block(motion, "mover")
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
            has_entry(mover, "type", r"motionSolver"),
            has_entry(mover, "motionSolver", r"solidBody"),
            has_entry(mover, "cellZone", r"movingZone"),
            has_entry(mover, "solidBodyMotionFunction", r"oscillatingRotatingMotion"),
            all(abs(value) <= 1.0e-12 for value in vector_entry(mover, "origin")),
            all(
                abs(left - right) <= 1.0e-12
                for left, right in zip(vector_entry(mover, "amplitude"), (0.0, 0.0, 5.0))
            ),
            abs(scalar_entry(mover, "omega") - 2.0 * math.pi) <= 1.0e-12,
            abs(scalar_entry(topology, "radius") - 1.41) <= 1.0e-12,
            has_entry(patch(velocity, "left"), "value", r"uniform\s+\(0\.5\s+0(?:\.0+)?\s+0(?:\.0+)?\)"),
            has_entry(patch(velocity, "right"), "type", r"zeroGradient"),
            all(has_entry(patch(velocity, name), "type", r"slip") for name in ("down", "up")),
            has_entry(patch(velocity, "cylinder"), "type", r"movingWallVelocity"),
            has_entry(patch(pressure, "right"), "type", r"fixedValue"),
            has_entry(patch(pressure, "right"), "value", r"uniform\s+0(?:\.0+)?"),
            abs(dimensioned_scalar(physical, "nu") - 0.01) <= 1.0e-12,
            has_entry(momentum, "simulationType", r"laminar"),
            abs(scalar_entry(control, "endTime") - 2.0) <= 1.0e-12,
            abs(scalar_entry(control, "deltaT") - 0.001) <= 1.0e-12,
            abs(scalar_entry(control, "writeInterval") - 0.25) <= 1.0e-12,
            has_entry(forces, "type", r"forces"),
            has_entry(forces, "patches", r"\(\s*cylinder\s*\)"),
            abs(scalar_entry(forces, "rhoInf") - 1.0) <= 1.0e-12,
            all(abs(value) <= 1.0e-12 for value in vector_entry(forces, "CofR")),
        )
    )


def check() -> bool:
    required = (
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
    if not postprocess_script_is_valid(ROOT / "postprocess.py"):
        return False
    if not (
        log_completed(CASE / "log.blockMesh", ("nCells: 1800",))
        and log_completed(CASE / "log.topoSet", ("movingZone now size 804",))
        and log_completed(CASE / "log.checkMesh", ("Mesh OK.",))
        and log_completed(CASE / "log.checkMeshFinal", ("Mesh OK.",))
        and log_completed(CASE / "log.pimpleFoam", ("Time = 2s",))
        and "movingZone" in read(CASE / "constant/polyMesh/cellZones")
        and field_count(CASE / "2/U", "vector", "volVectorField") == 1800
        and field_count(CASE / "2/p", "scalar", "volScalarField") == 1800
        and (CASE / "0.25/polyMesh/points").read_bytes() != (CASE / "constant/polyMesh/points").read_bytes()
    ):
        return False
    times = set()
    for path in CASE.iterdir():
        if not path.is_dir():
            continue
        try:
            times.add(round(float(path.name), 9))
        except ValueError:
            continue
    expected_times = {round(index * 0.25, 9) for index in range(9)}
    if not expected_times.issubset(times) or not times or max(times) != 2.0:
        return False
    mesh_check = subprocess.run(
        [
            "bash",
            "--noprofile",
            "--norc",
            "-c",
            f"trap - CHLD; . /opt/openfoam11/etc/bashrc && checkMesh -latestTime -case {shlex.quote(str(CASE))}",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=120,
    )
    if (
        mesh_check.returncode != 0
        or "Mesh OK." not in mesh_check.stdout
        or "Failed " in mesh_check.stdout
        or not mesh_check.stdout.rstrip().endswith("End")
        or not check_case()
    ):
        return False

    centres_result = subprocess.run(
        [
            "bash",
            "--noprofile",
            "--norc",
            "-c",
            f"trap - CHLD; . /opt/openfoam11/etc/bashrc && postProcess -case {shlex.quote(str(CASE))} -latestTime -func writeCellCentres",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=120,
    )
    centres_output = centres_result.stdout
    if (
        centres_result.returncode != 0
        or "foam fatal" in centres_output.lower()
        or not centres_output.rstrip().endswith("End")
    ):
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
    if len(history) != 2001:
        return False
    if not all(all(math.isfinite(value) for value in row) for row in history):
        return False
    if any(abs(row[0] - index * 0.001) > 1.0e-9 for index, row in enumerate(history)):
        return False
    totals = [row[3] for row in history]
    if (
        max(abs(row[1]) for row in history) <= 0.1
        or max(abs(row[2]) for row in history) <= 0.01
        or max(totals) - min(totals) <= 0.1
        or abs(totals[-1]) <= 1.0e-6
    ):
        return False
    keys = ("time_s", "pressure_fx_n", "viscous_fx_n", "total_fx_n")
    with (ROOT / "force_history.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != len(history) or tuple(rows[0]) != keys:
        return False
    for row, expected in zip(rows, history):
        actual = tuple(float(row[key]) for key in keys)
        if any(abs(left - right) > 5e-7 for left, right in zip(actual, expected)):
            return False

    lines = [line.strip() for line in read(ROOT / "summary.txt").splitlines() if line.strip()]
    if len(lines) != 1:
        return False
    reported = float(lines[0])
    return math.isfinite(reported) and abs(reported - history[-1][3]) <= 5e-7


def main() -> int:
    try:
        result = check()
    except Exception:
        result = False
    print("True" if result else "False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
