#!/usr/bin/env python3
from __future__ import annotations

import csv
import math
import re
import subprocess
from pathlib import Path


ROOT = Path("/home/user/Desktop")
CASE = ROOT / "cylinder_fo"
COEFFICIENTS = CASE / "postProcessing/forces/0/forceCoeffs.dat"


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


def has_entry(block: str, key: str, value: str) -> bool:
    return re.search(rf"(?<!\w){re.escape(key)}\s+{value}\s*;", block) is not None


def close(actual: float, expected: float, tolerance: float) -> bool:
    return math.isfinite(actual) and abs(actual - expected) <= tolerance


def patch(text: str, name: str) -> str:
    return named_block(named_block(text, "boundaryField"), name)


def field(path: Path, kind: str) -> list:
    text = read(path)
    header = named_block(text, "FoamFile")
    match = re.search(
        rf"internalField\s+nonuniform\s+List<{kind}>\s+(\d+)\s*\((.*?)\)\s*;",
        text,
        re.S,
    )
    if not match:
        raise ValueError(f"missing {kind} field")
    if kind == "vector":
        values = [
            tuple(float(value) for value in item.split())
            for item in re.findall(r"\(([^()]+)\)", match.group(2))
        ]
        valid = all(
            len(value) == 3 and all(math.isfinite(component) for component in value)
            for value in values
        )
    else:
        values = [float(value) for value in match.group(2).split()]
        valid = all(math.isfinite(value) for value in values)
    if (
        len(values) != int(match.group(1))
        or not valid
        or not has_entry(header, "format", r"ascii")
        or not has_entry(header, "class", rf"vol{kind.capitalize()}Field")
        or not has_entry(header, "object", re.escape(path.name))
    ):
        raise ValueError(f"invalid {kind} field")
    return values


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


def numeric_entry(text: str, key: str) -> float:
    match = re.search(rf"(?m)^\s*{re.escape(key)}\s+([^;]+);", text)
    if not match:
        raise ValueError(f"missing entry {key}")
    return float(match.group(1))


def dimensioned_value(text: str, key: str) -> float:
    match = re.search(rf"(?m)^\s*{re.escape(key)}\s+\[[^]]+\]\s+([^;]+);", text)
    if not match:
        raise ValueError(f"missing dimensioned entry {key}")
    return float(match.group(1))


def vector_entry(text: str, key: str, uniform: bool = False) -> tuple[float, float, float]:
    prefix = r"uniform\s+" if uniform else ""
    match = re.search(rf"(?m)^\s*{re.escape(key)}\s+{prefix}\(([^()]+)\)\s*;", text)
    if not match:
        raise ValueError(f"missing vector entry {key}")
    values = tuple(float(value) for value in match.group(1).split())
    if len(values) != 3:
        raise ValueError(f"invalid vector entry {key}")
    return values


def patch_faces(mesh: str, name: str) -> list[tuple[int, ...]]:
    section = paren_section(named_block(mesh, name), "faces")
    return [tuple(int(value) for value in item.split()) for item in re.findall(r"\(([^()]+)\)", section)]


def mesh_geometry_is_valid(mesh: str) -> bool:
    scale_match = re.search(r"\bconvertToMeters\s+([^;]+);", mesh)
    vertices = [
        tuple(float(value) for value in item.split())
        for item in re.findall(r"\(([^()]+)\)", paren_section(mesh, "vertices"))
    ]
    if scale_match is None or len(vertices) != 32 or any(len(point) != 3 for point in vertices):
        return False
    scale = float(scale_match.group(1))
    points = [tuple(scale * value for value in point) for point in vertices]
    radii = [math.hypot(point[0], point[1]) for point in points]
    zs = [point[2] for point in points]
    inlet = patch_faces(mesh, "inlet")
    outlet = patch_faces(mesh, "outlet")
    cylinder = patch_faces(mesh, "cylinder")

    def outer_half(faces: list[tuple[int, ...]], sign: int) -> bool:
        return len(faces) == 4 and all(
            len(face) == 4
            and all(abs(radii[index] - 1.0) <= 1e-9 for index in face)
            and sign * sum(points[index][0] for index in face) / 4.0 > 1e-6
            for face in faces
        )

    return (
        abs(min(zs)) <= 1e-12
        and abs(max(zs) - 0.01) <= 1e-12
        and sum(abs(radius - 0.05) <= 1e-9 for radius in radii) == 16
        and sum(abs(radius - 1.0) <= 1e-9 for radius in radii) == 16
        and len(re.findall(r"(?m)^\s*hex\b", mesh)) == 8
        and len(re.findall(r"hex\s*\([^)]*\)\s*\(\s*40\s+12\s+1\s*\)", mesh)) == 8
        and len(re.findall(r"(?m)^\s*arc\b", mesh)) == 32
        and outer_half(inlet, -1)
        and outer_half(outlet, 1)
        and len(cylinder) == 8
        and all(all(abs(radii[index] - 0.05) <= 1e-9 for index in face) for face in cylinder)
    )


def log_finished(path: Path) -> bool:
    text = read(path)
    return "FOAM FATAL" not in text and text.rstrip().endswith("End")


def coefficient_history() -> list[tuple[float, float, float]]:
    values = []
    for line in read(COEFFICIENTS).splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        row = [float(value) for value in stripped.split()]
        if len(row) >= 4:
            values.append((row[0], row[2], row[3]))
    return values


def check_case() -> bool:
    mesh = read(CASE / "system/blockMeshDict")
    velocity = read(CASE / "0/U")
    pressure = read(CASE / "0/p")
    physical = read(CASE / "constant/physicalProperties")
    momentum = read(CASE / "constant/momentumTransport")
    control = read(CASE / "system/controlDict")
    forces = named_block(named_block(control, "functions"), "forces")
    return all(
        (
            mesh_geometry_is_valid(mesh),
            has_entry(named_block(mesh, "cylinder"), "type", r"wall"),
            has_entry(named_block(mesh, "frontAndBack"), "type", r"empty"),
            has_entry(patch(velocity, "inlet"), "value", r"uniform\s+\(1(?:\.0+)?\s+0(?:\.0+)?\s+0(?:\.0+)?\)"),
            has_entry(patch(velocity, "outlet"), "type", r"zeroGradient"),
            has_entry(patch(velocity, "cylinder"), "type", r"noSlip"),
            has_entry(patch(velocity, "frontAndBack"), "type", r"empty"),
            has_entry(patch(pressure, "outlet"), "type", r"fixedValue"),
            has_entry(patch(pressure, "outlet"), "value", r"uniform\s+0(?:\.0+)?"),
            abs(dimensioned_value(physical, "nu") - 1e-3) <= 1e-12,
            "simulationType laminar;" in momentum,
            abs(numeric_entry(control, "endTime") - 20.0) <= 1e-12,
            abs(numeric_entry(control, "deltaT") - 0.0025) <= 1e-12,
            has_entry(forces, "type", r"forceCoeffs"),
            has_entry(forces, "patches", r"\(\s*cylinder\s*\)"),
            abs(numeric_entry(forces, "rhoInf") - 1.0) <= 1e-12,
            abs(numeric_entry(forces, "magUInf") - 1.0) <= 1e-12,
            abs(numeric_entry(forces, "lRef") - 0.1) <= 1e-12,
            abs(numeric_entry(forces, "Aref") - 0.001) <= 1e-12,
            vector_entry(forces, "dragDir") == (1.0, 0.0, 0.0),
            vector_entry(forces, "liftDir") == (0.0, 1.0, 0.0),
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
        CASE / "log.pimpleFoam",
        CASE / "20/U",
        CASE / "20/p",
        COEFFICIENTS,
    )
    if any(not path.is_file() or path.stat().st_size == 0 for path in required):
        return False
    solve_log = read(CASE / "log.pimpleFoam")
    check_log = read(CASE / "log.checkMesh")
    if (
        not log_finished(CASE / "log.blockMesh")
        or "Mesh OK." not in check_log
        or not log_finished(CASE / "log.checkMesh")
        or not log_finished(CASE / "log.pimpleFoam")
        or "Time = 20" not in solve_log
    ):
        return False
    mesh_check = subprocess.run(
        [
            "bash",
            "--noprofile",
            "--norc",
            "-c",
            "trap - CHLD; . /opt/openfoam11/etc/bashrc && checkMesh -case /home/user/Desktop/cylinder_fo",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=120,
    )
    if mesh_check.returncode != 0 or "Mesh OK." not in mesh_check.stdout or not check_case():
        return False
    velocity = field(CASE / "20/U", "vector")
    pressure = field(CASE / "20/p", "scalar")
    if not (len(velocity) == len(pressure) == 3840):
        return False

    history = coefficient_history()
    if not history or abs(history[0][0]) > 1e-9 or abs(history[-1][0] - 20.0) > 1e-9 or any(
        not all(math.isfinite(value) for value in row)
        or row[0] < 0.0
        or row[0] > 20.0 + 1.0e-9
        for row in history
    ) or any(right[0] <= left[0] for left, right in zip(history, history[1:])):
        return False
    window = [row for row in history if 10.0 <= row[0] <= 20.0]
    if len(window) < 100:
        return False
    cl_mean = sum(row[2] for row in window) / len(window)
    cd_mean = sum(row[1] for row in window) / len(window)
    cl_range = max(row[2] for row in window) - min(row[2] for row in window)
    if not (1.0 < cd_mean < 2.0 and abs(cl_mean) < 0.1 and cl_range > 0.2):
        return False

    keys = ("time_s", "cd", "cl")
    with (ROOT / "force_history.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != len(history) or set(rows[0]) != set(keys):
        return False
    for row, expected in zip(rows, history):
        actual = tuple(float(row[key]) for key in keys)
        if any(not close(a, b, 5.0e-7) for a, b in zip(actual, expected)):
            return False

    values = [line.strip() for line in read(ROOT / "summary.txt").splitlines() if line.strip()]
    if len(values) != 1:
        return False
    parts = [item.strip() for item in values[0].split(",")]
    if len(parts) != 2:
        return False
    reported = tuple(float(value) for value in parts)
    expected = (cl_mean, cd_mean)
    return all(math.isfinite(value) for value in reported) and all(
        abs(actual - target) <= 5.0e-7 for actual, target in zip(reported, expected)
    )


def main() -> int:
    try:
        result = check()
    except Exception:
        result = False
    print("True" if result else "False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
