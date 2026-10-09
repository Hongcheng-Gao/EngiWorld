#!/usr/bin/env python3
from __future__ import annotations

import csv
import math
import re
import subprocess
from pathlib import Path


ROOT = Path("/home/user/Desktop")
CASE = ROOT / "shock_tube"
PLATEAU_MIN = 0.64
PLATEAU_MAX = 0.72


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


def initial_states(path: Path, left: float, right: float) -> bool:
    try:
        values = field(path, "scalar")
    except ValueError:
        return False
    return len(values) == 1000 and all(abs(value - left) <= 1.0e-6 for value in values[:500]) and all(abs(value - right) <= 1.0e-6 for value in values[500:])


def latest_time() -> Path:
    times = [
        path
        for path in CASE.iterdir()
        if path.is_dir()
        and re.fullmatch(r"(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?", path.name)
        and float(path.name) > 0
    ]
    if not times:
        raise FileNotFoundError("no computed time directory")
    return max(times, key=lambda path: float(path.name))


def field(path: Path, kind: str) -> list:
    text = read(path)
    header = named_block(text, "FoamFile")
    if not (
        has_entry(header, "format", r"ascii")
        and has_entry(header, "class", rf"vol{kind.capitalize()}Field")
        and has_entry(header, "object", re.escape(path.name))
    ):
        raise ValueError(f"field is not ASCII: {path}")
    match = re.search(
        rf"internalField\s+nonuniform\s+List<{kind}>\s+(\d+)\s*\((.*?)\)\s*;",
        text,
        re.S,
    )
    if not match:
        raise ValueError(f"missing nonuniform {kind} field")
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
    if len(values) != int(match.group(1)) or not valid:
        raise ValueError("field count mismatch")
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
    match = re.search(rf"(?<!\w){re.escape(key)}\s+([^;]+);", text)
    if not match:
        raise ValueError(f"missing entry {key}")
    return float(match.group(1))


def uniform_vector(text: str) -> tuple[float, float, float]:
    match = re.search(r"\binternalField\s+uniform\s+\(([^()]+)\)\s*;", text)
    if not match:
        raise ValueError("missing uniform vector field")
    values = tuple(float(value) for value in match.group(1).split())
    if len(values) != 3:
        raise ValueError("invalid uniform vector field")
    return values


def box_entry(text: str) -> tuple[tuple[float, ...], tuple[float, ...]]:
    match = re.search(r"\bbox\s+\(([^()]+)\)\s+\(([^()]+)\)\s*;", text)
    if not match:
        raise ValueError("missing box entry")
    return tuple(float(value) for value in match.group(1).split()), tuple(
        float(value) for value in match.group(2).split()
    )


def mesh_geometry_is_valid(mesh: str) -> bool:
    scale_match = re.search(r"\bconvertToMeters\s+([^;]+);", mesh)
    vertices = [
        tuple(float(value) for value in item.split())
        for item in re.findall(r"\(([^()]+)\)", paren_section(mesh, "vertices"))
    ]
    shapes = [
        tuple(int(value) for value in item.split())
        for item in re.findall(r"hex\s*\([^)]*\)\s*\(([^()]*)\)", paren_section(mesh, "blocks"))
    ]
    if (
        scale_match is None
        or len(vertices) != 8
        or any(len(point) != 3 for point in vertices)
        or shapes != [(1000, 1, 1)]
    ):
        return False
    scale = float(scale_match.group(1))
    xs, ys, zs = zip(*(tuple(scale * value for value in point) for point in vertices))
    return (
        abs(min(xs)) <= 1e-12
        and abs(max(xs) - 1.0) <= 1e-12
        and abs(min(ys)) <= 1e-12
        and abs(max(ys) - 0.01) <= 1e-12
        and abs(min(zs)) <= 1e-12
        and abs(max(zs) - 0.01) <= 1e-12
    )


def log_finished(path: Path) -> bool:
    text = read(path)
    return "FOAM FATAL" not in text and text.rstrip().endswith("End")


def pressure_profile(final: Path) -> tuple[float, list[tuple[float, float]]]:
    centres = field(final / "C", "vector")
    pressure = field(final / "p", "scalar")
    if not (len(centres) == len(pressure) == 1000):
        raise ValueError("unexpected cell count")
    profile = sorted(((point[0], value) for point, value in zip(centres, pressure)), key=lambda row: row[0])
    plateau = [value for x, value in profile if PLATEAU_MIN <= x <= PLATEAU_MAX]
    if len(plateau) != 80 or any(not math.isfinite(value) or value <= 0 for value in pressure):
        raise ValueError("invalid pressure field")
    average = sum(plateau) / len(plateau)
    relative_std = math.sqrt(sum((value - average) ** 2 for value in plateau) / len(plateau)) / average
    if not (20000 < average < 50000 and relative_std < 0.05):
        raise ValueError("fixed interval is not the expected post-shock plateau")
    return average, profile


def check_case() -> bool:
    mesh = read(CASE / "system/blockMeshDict")
    control = read(CASE / "system/controlDict")
    initial = read(CASE / "system/setFieldsDict")
    thermo = read(CASE / "constant/physicalProperties")
    velocity = read(CASE / "0/U")
    pressure = read(CASE / "0/p")
    temperature = read(CASE / "0/T")
    return all(
        (
            mesh_geometry_is_valid(mesh),
            has_entry(named_block(mesh, "leftRight"), "type", r"patch"),
            has_entry(named_block(mesh, "empty"), "type", r"empty"),
            "application rhoCentralFoam;" in control,
            abs(numeric_entry(control, "endTime") - 0.0005) <= 1e-15,
            abs(numeric_entry(control, "maxCo") - 0.2) <= 1e-12,
            re.search(r"\bwriteFormat\s+ascii\s*;", control) is not None,
            box_entry(initial) == ((0.0, 0.0, 0.0), (0.5, 0.01, 0.01)),
            uniform_vector(velocity) == (0.0, 0.0, 0.0),
            has_entry(patch(velocity, "leftRight"), "type", r"zeroGradient"),
            has_entry(patch(velocity, "empty"), "type", r"empty"),
            has_entry(patch(pressure, "leftRight"), "type", r"zeroGradient"),
            has_entry(patch(pressure, "empty"), "type", r"empty"),
            has_entry(patch(temperature, "leftRight"), "type", r"zeroGradient"),
            has_entry(patch(temperature, "empty"), "type", r"empty"),
            initial_states(CASE / "0/p", 100000.0, 10000.0),
            initial_states(CASE / "0/T", 348.308740203735, 278.646992162988),
            "equationOfState perfectGas;" in thermo,
            abs(numeric_entry(thermo, "molWeight") - 28.96) <= 1e-12,
            abs(numeric_entry(thermo, "Cp") - 1004.5) <= 1e-12,
            abs(numeric_entry(thermo, "mu")) <= 1e-15,
        )
    )


def check() -> bool:
    final = latest_time()
    required = (
        ROOT / "build_case.py",
        ROOT / "postprocess.py",
        ROOT / "summary.txt",
        ROOT / "pressure_profile.csv",
        CASE / "log.blockMesh",
        CASE / "log.checkMesh",
        CASE / "log.setFields",
        CASE / "log.rhoCentralFoam",
        CASE / "log.writeCellCentres",
        final / "C",
        final / "p",
        final / "T",
        final / "U",
    )
    if any(not path.is_file() or path.stat().st_size == 0 for path in required):
        return False
    if abs(float(final.name) - 0.0005) > 1e-15:
        return False
    mesh_log = read(CASE / "log.checkMesh")
    solve_log = read(CASE / "log.rhoCentralFoam")
    if not (
        log_finished(CASE / "log.blockMesh")
        and "Mesh OK." in mesh_log
        and log_finished(CASE / "log.checkMesh")
        and log_finished(CASE / "log.setFields")
        and log_finished(CASE / "log.writeCellCentres")
        and "Time = 0.0005" in solve_log
        and log_finished(CASE / "log.rhoCentralFoam")
    ):
        return False
    mesh_check = subprocess.run(
        [
            "bash",
            "--noprofile",
            "--norc",
            "-c",
            "trap - CHLD; . /opt/openfoam11/etc/bashrc && checkMesh -case /home/user/Desktop/shock_tube",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=120,
    )
    if mesh_check.returncode != 0 or "Mesh OK." not in mesh_check.stdout or not check_case():
        return False

    temperature = field(final / "T", "scalar")
    velocity = field(final / "U", "vector")
    if not (
        len(temperature) == len(velocity) == 1000
        and all(value > 0 for value in temperature)
    ):
        return False
    average, profile = pressure_profile(final)
    with (ROOT / "pressure_profile.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != len(profile) or set(rows[0]) != {"x_m", "p_pa"}:
        return False
    for row, expected in zip(rows, profile):
        actual = (float(row["x_m"]), float(row["p_pa"]))
        if any(not close(left, right, 5e-7) for left, right in zip(actual, expected)):
            return False

    lines = [line.strip() for line in read(ROOT / "summary.txt").splitlines() if line.strip()]
    if len(lines) != 1:
        return False
    reported = float(lines[0])
    return math.isfinite(reported) and abs(reported - average) <= 5e-7


def main() -> int:
    try:
        result = check()
    except Exception:
        result = False
    print("True" if result else "False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
