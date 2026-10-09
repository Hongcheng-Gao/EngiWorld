#!/usr/bin/env python3
from __future__ import annotations

import csv
import math
import re
import subprocess
from pathlib import Path


ROOT = Path("/home/user/Desktop")
CASE = ROOT / "dam_break"
TARGET_X = 0.25


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


def latest_time() -> Path:
    times = [
        path
        for path in CASE.iterdir()
        if path.is_dir() and re.fullmatch(r"\d+(?:\.\d+)?", path.name) and float(path.name) > 0
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


def vector_entry(text: str, key: str) -> tuple[float, float, float]:
    match = re.search(rf"(?<!\w){re.escape(key)}\s+\(([^()]+)\)\s*;", text)
    if not match:
        raise ValueError(f"missing vector entry {key}")
    values = tuple(float(value) for value in match.group(1).split())
    if len(values) != 3:
        raise ValueError(f"invalid vector entry {key}")
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
    cell_shapes = [
        tuple(int(value) for value in item.split())
        for item in re.findall(r"hex\s*\([^)]*\)\s*\(([^()]*)\)", paren_section(mesh, "blocks"))
    ]
    if (
        scale_match is None
        or len(vertices) != 24
        or any(len(point) != 3 for point in vertices)
        or len(cell_shapes) != 5
        or any(len(shape) != 3 for shape in cell_shapes)
    ):
        return False
    scale = float(scale_match.group(1))
    xs, ys, zs = zip(*(tuple(scale * value for value in point) for point in vertices))
    cells = sum(nx * ny * nz for nx, ny, nz in cell_shapes)
    return (
        abs(min(xs)) <= 1e-12
        and abs(max(xs) - 0.584) <= 1e-12
        and abs(min(ys)) <= 1e-12
        and abs(max(ys) - 0.584) <= 1e-12
        and abs(min(zs)) <= 1e-12
        and abs(max(zs) - 0.0146) <= 1e-12
        and cells == 2268
    )


def log_finished(path: Path) -> bool:
    text = read(path)
    return "FOAM FATAL" not in text and text.rstrip().endswith("End")


def interface_profile(final: Path) -> tuple[float, list[tuple[float, float]]]:
    centres = field(final / "C", "vector")
    alpha = field(final / "alpha.water", "scalar")
    if not (len(centres) == len(alpha) == 2268):
        raise ValueError("unexpected cell count")
    if any(not math.isfinite(value) or value < -1e-6 or value > 1.000001 for value in alpha):
        raise ValueError("unbounded phase fraction")
    selected_x = min((point[0] for point in centres), key=lambda value: abs(value - TARGET_X))
    profile = sorted(
        ((point[1], value) for point, value in zip(centres, alpha) if abs(point[0] - selected_x) < 1e-9),
        key=lambda row: row[0],
    )
    if len(profile) != 50 or profile[0][1] < 0.5:
        raise ValueError("invalid sample column")
    for lower, upper in zip(profile, profile[1:]):
        if lower[1] >= 0.5 and upper[1] < 0.5:
            fraction = (0.5 - lower[1]) / (upper[1] - lower[1])
            return lower[0] + fraction * (upper[0] - lower[0]), profile
    raise ValueError("missing bottom-connected interface crossing")


def check_case() -> bool:
    mesh = read(CASE / "system/blockMeshDict")
    control = read(CASE / "system/controlDict")
    initial = read(CASE / "system/setFieldsDict")
    gravity = read(CASE / "constant/g")
    water = read(CASE / "constant/physicalProperties.water")
    air = read(CASE / "constant/physicalProperties.air")
    phases = read(CASE / "constant/phaseProperties")
    momentum = read(CASE / "constant/momentumTransport")
    velocity = read(CASE / "0/U")
    alpha = read(CASE / "0/alpha.water.orig") if (CASE / "0/alpha.water.orig").is_file() else read(CASE / "0/alpha.water")
    pressure = read(CASE / "0/p_rgh")
    return all(
        (
            mesh_geometry_is_valid(mesh),
            "application interFoam;" in control,
            abs(numeric_entry(control, "endTime") - 0.5) <= 1e-12,
            abs(numeric_entry(control, "maxCo") - 0.5) <= 1e-12,
            abs(numeric_entry(control, "maxAlphaCo") - 0.5) <= 1e-12,
            re.search(r"\bwriteFormat\s+ascii\s*;", control) is not None,
            box_entry(initial) == ((0.0, 0.0, -1.0), (0.1461, 0.292, 1.0)),
            vector_entry(gravity, "value") == (0.0, -9.81, 0.0),
            abs(numeric_entry(water, "nu") - 1e-6) <= 1e-15,
            abs(numeric_entry(water, "rho") - 1000.0) <= 1e-12,
            abs(numeric_entry(air, "nu") - 1.48e-5) <= 1e-15,
            abs(numeric_entry(air, "rho") - 1.0) <= 1e-12,
            abs(numeric_entry(phases, "sigma") - 0.07) <= 1e-12,
            "simulationType  laminar;" in momentum or "simulationType laminar;" in momentum,
            all(has_entry(patch(velocity, name), "type", r"noSlip") for name in ("leftWall", "rightWall", "lowerWall")),
            has_entry(patch(velocity, "atmosphere"), "type", r"pressureInletOutletVelocity"),
            has_entry(patch(velocity, "defaultFaces"), "type", r"empty"),
            all(has_entry(patch(alpha, name), "type", r"zeroGradient") for name in ("leftWall", "rightWall", "lowerWall")),
            has_entry(patch(alpha, "atmosphere"), "type", r"inletOutlet"),
            has_entry(patch(alpha, "defaultFaces"), "type", r"empty"),
            has_entry(patch(pressure, "atmosphere"), "type", r"prghTotalPressure"),
            has_entry(patch(pressure, "atmosphere"), "p0", r"uniform\s+0(?:\.0+)?"),
        )
    )


def check() -> bool:
    final = latest_time()
    required = (
        ROOT / "build_case.py",
        ROOT / "postprocess.py",
        ROOT / "summary.txt",
        ROOT / "interface_profile.csv",
        CASE / "log.blockMesh",
        CASE / "log.checkMesh",
        CASE / "log.setFields",
        CASE / "log.interFoam",
        CASE / "log.writeCellCentres",
        final / "alpha.water",
        final / "U",
        final / "p_rgh",
        final / "C",
    )
    if any(not path.is_file() or path.stat().st_size == 0 for path in required):
        return False
    if abs(float(final.name) - 0.5) > 1e-12:
        return False
    mesh_log = read(CASE / "log.checkMesh")
    solve_log = read(CASE / "log.interFoam")
    if not (
        log_finished(CASE / "log.blockMesh")
        and log_finished(CASE / "log.setFields")
        and log_finished(CASE / "log.writeCellCentres")
        and "Mesh OK." in mesh_log
        and log_finished(CASE / "log.checkMesh")
        and "Time = 0.5" in solve_log
        and log_finished(CASE / "log.interFoam")
    ):
        return False
    mesh_check = subprocess.run(
        [
            "bash",
            "--noprofile",
            "--norc",
            "-c",
            "trap - CHLD; . /opt/openfoam11/etc/bashrc && checkMesh -case /home/user/Desktop/dam_break",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=120,
    )
    if mesh_check.returncode != 0 or "Mesh OK." not in mesh_check.stdout or not check_case():
        return False

    velocity = field(final / "U", "vector")
    pressure = field(final / "p_rgh", "scalar")
    if not (len(velocity) == len(pressure) == 2268):
        return False
    height, profile = interface_profile(final)
    if not (0.0 < height < 0.584):
        return False
    with (ROOT / "interface_profile.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != len(profile) or set(rows[0]) != {"y_m", "alpha_water"}:
        return False
    for row, expected in zip(rows, profile):
        actual = (float(row["y_m"]), float(row["alpha_water"]))
        if any(not close(left, right, 5e-7) for left, right in zip(actual, expected)):
            return False

    lines = [line.strip() for line in read(ROOT / "summary.txt").splitlines() if line.strip()]
    if len(lines) != 1:
        return False
    reported = float(lines[0])
    return math.isfinite(reported) and abs(reported - height) <= 5e-7


def main() -> int:
    try:
        result = check()
    except Exception:
        result = False
    print("True" if result else "False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
