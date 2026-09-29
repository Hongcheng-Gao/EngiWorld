#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import math
import re
import subprocess
from pathlib import Path


ROOT = Path("/home/user/Desktop")
CASE = ROOT / "cylinder_snappy"
STL_SHA256 = "e5901f31b9024d86c25ca7c508193dfefeb300b24c008cb15d3010412ad3d54e"


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
    match = re.search(rf"(?<!\w){re.escape(key)}\s+([^;]+);", text)
    if not match:
        raise ValueError(f"missing entry {key}")
    return float(match.group(1))


def dimensioned_value(text: str, key: str) -> float:
    match = re.search(rf"(?m)^\s*{re.escape(key)}\s+\[[^]]+\]\s+([^;]+);", text)
    if not match:
        raise ValueError(f"missing dimensioned entry {key}")
    return float(match.group(1))


def tuple_entry(text: str, key: str, uniform: bool = False) -> tuple[float, ...]:
    prefix = r"uniform\s+" if uniform else ""
    match = re.search(rf"(?m)^\s*{re.escape(key)}\s+{prefix}\(([^()]+)\)\s*;", text)
    if not match:
        raise ValueError(f"missing tuple entry {key}")
    return tuple(float(value) for value in match.group(1).split())


def vector_entry(text: str, key: str, uniform: bool = False) -> tuple[float, float, float]:
    values = tuple_entry(text, key, uniform)
    if len(values) != 3:
        raise ValueError(f"invalid vector entry {key}")
    return values


def uniform_scalar(text: str) -> float:
    match = re.search(r"\binternalField\s+uniform\s+([^;]+);", text)
    if not match:
        raise ValueError("missing uniform scalar field")
    return float(match.group(1))


def uniform_vector(text: str) -> tuple[float, float, float]:
    match = re.search(r"\binternalField\s+uniform\s+\(([^()]+)\)\s*;", text)
    if not match:
        raise ValueError("missing uniform vector field")
    values = tuple(float(value) for value in match.group(1).split())
    if len(values) != 3:
        raise ValueError("invalid uniform vector field")
    return values


def mesh_geometry_is_valid(mesh: str) -> bool:
    scale_match = re.search(r"\bconvertToMeters\s+([^;]+);", mesh)
    vertices = [
        tuple(float(value) for value in item.split())
        for item in re.findall(r"\(([^()]+)\)", paren_section(mesh, "vertices"))
    ]
    if scale_match is None or len(vertices) != 8 or any(len(point) != 3 for point in vertices):
        return False
    scale = float(scale_match.group(1))
    xs, ys, zs = zip(*(tuple(scale * value for value in point) for point in vertices))
    return (
        abs(min(xs)) <= 1e-12
        and abs(max(xs) - 2.0) <= 1e-12
        and abs(min(ys)) <= 1e-12
        and abs(max(ys) - 1.0) <= 1e-12
        and abs(min(zs) + 0.005) <= 1e-12
        and abs(max(zs) - 0.005) <= 1e-12
        and re.search(r"hex\s*\([^)]*\)\s*\(\s*160\s+80\s+1\s*\)", mesh) is not None
    )


def log_finished(path: Path) -> bool:
    text = read(path)
    return "FOAM FATAL" not in text and text.rstrip().endswith("End")


def patch_values(path: Path, patch: str) -> list[float]:
    text = read(path)
    header = named_block(text, "FoamFile")
    block = re.search(rf"\b{re.escape(patch)}\s*\{{(.*?)\n\s*\}}", text, re.S)
    if not block:
        raise ValueError(f"missing {patch} boundary field")
    values = re.search(
        r"value\s+nonuniform\s+List<scalar>\s+(\d+)\s*\((.*?)\)\s*;",
        block.group(1),
        re.S,
    )
    if not values:
        raise ValueError(f"missing nonuniform values on {patch}")
    result = [float(value) for value in values.group(2).split()]
    if (
        len(result) != int(values.group(1))
        or not has_entry(header, "format", r"ascii")
        or not has_entry(header, "class", r"volScalarField")
        or not has_entry(header, "object", re.escape(path.name))
    ):
        raise ValueError("boundary face-count mismatch")
    return result


def cylinder_faces() -> int:
    boundary = read(CASE / "constant/polyMesh/boundary")
    block = re.search(r"\bcylinder\s*\{(.*?)\n\s*\}", boundary, re.S)
    if not block:
        raise ValueError("missing cylinder mesh patch")
    match = re.search(r"\bnFaces\s+(\d+)\s*;", block.group(1))
    if not match:
        raise ValueError("missing cylinder face count")
    return int(match.group(1))


def check_case() -> bool:
    stl = CASE / "constant/triSurface/cylinder.stl"
    if hashlib.sha256(stl.read_bytes()).hexdigest() != STL_SHA256:
        return False
    mesh = read(CASE / "system/blockMeshDict")
    snappy = read(CASE / "system/snappyHexMeshDict")
    velocity = read(CASE / "0/U")
    kinetic = read(CASE / "0/k")
    dissipation = read(CASE / "0/epsilon")
    physical = read(CASE / "constant/physicalProperties")
    momentum = read(CASE / "constant/momentumTransport")
    control = read(CASE / "system/controlDict")
    pressure = read(CASE / "0/p")
    nut = read(CASE / "0/nut")
    geometry = named_block(snappy, "geometry")
    surface = named_block(geometry, "cylinder")
    return all(
        (
            mesh_geometry_is_valid(mesh),
            has_entry(snappy, "castellatedMesh", r"true"),
            has_entry(snappy, "snap", r"true"),
            has_entry(snappy, "addLayers", r"true"),
            has_entry(surface, "type", r"triSurfaceMesh"),
            has_entry(surface, "file", r'"cylinder\.stl"'),
            "transform" not in surface,
            not re.search(r"(?m)^\s*scale\s+", surface) or abs(numeric_entry(surface, "scale") - 1.0) <= 1e-12,
            tuple_entry(snappy, "level") == (2.0, 3.0),
            vector_entry(snappy, "locationInMesh") == (0.1, 0.5, 0.0),
            abs(numeric_entry(snappy, "nSurfaceLayers") - 3.0) <= 1e-12,
            abs(numeric_entry(snappy, "expansionRatio") - 1.2) <= 1e-12,
            abs(numeric_entry(snappy, "finalLayerThickness") - 0.4) <= 1e-12,
            uniform_vector(velocity) == (3.0, 0.0, 0.0),
            abs(uniform_scalar(kinetic) - 0.03375) <= 1e-12,
            abs(uniform_scalar(dissipation) - 0.1458) <= 1e-12,
            has_entry(patch(velocity, "inlet"), "value", r"uniform\s+\(3(?:\.0+)?\s+0(?:\.0+)?\s+0(?:\.0+)?\)"),
            has_entry(patch(velocity, "outlet"), "type", r"zeroGradient"),
            has_entry(patch(velocity, "cylinder"), "type", r"noSlip"),
            all(has_entry(patch(velocity, name), "type", r"symmetry") for name in ("topBottom", "frontAndBack")),
            has_entry(patch(pressure, "outlet"), "type", r"fixedValue"),
            has_entry(patch(pressure, "outlet"), "value", r"uniform\s+0(?:\.0+)?"),
            has_entry(patch(kinetic, "cylinder"), "type", r"kqRWallFunction"),
            has_entry(patch(dissipation, "cylinder"), "type", r"epsilonWallFunction"),
            has_entry(patch(nut, "cylinder"), "type", r"nutkWallFunction"),
            abs(dimensioned_value(physical, "nu") - 1e-6) <= 1e-15,
            "simulationType RAS;" in momentum,
            "model realizableKE;" in momentum,
            abs(numeric_entry(control, "endTime") - 500.0) <= 1e-12,
            "type yPlus;" in control,
        )
    )


def check() -> bool:
    final = latest_time()
    required = (
        ROOT / "build_case.py",
        ROOT / "postprocess.py",
        ROOT / "summary.txt",
        ROOT / "yplus_surface.csv",
        CASE / "log.surfaceFeatures",
        CASE / "log.blockMesh",
        CASE / "log.snappyHexMesh",
        CASE / "log.checkMesh",
        CASE / "log.simpleFoam",
        final / "U",
        final / "p",
        final / "k",
        final / "epsilon",
        final / "nut",
        final / "yPlus",
    )
    if any(not path.is_file() or path.stat().st_size == 0 for path in required):
        return False
    if abs(float(final.name) - 500.0) > 1e-12:
        return False
    mesh_log = read(CASE / "log.checkMesh")
    snappy_log = read(CASE / "log.snappyHexMesh")
    solve_log = read(CASE / "log.simpleFoam")
    if not (
        all(log_finished(path) for path in required[4:9])
        and "Mesh OK." in mesh_log
        and "Layer mesh :" in snappy_log
        and "Time = 500" in solve_log
    ):
        return False
    mesh_check = subprocess.run(
        [
            "bash",
            "--noprofile",
            "--norc",
            "-c",
            "trap - CHLD; . /opt/openfoam11/etc/bashrc && checkMesh -case /home/user/Desktop/cylinder_snappy",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=120,
    )
    if mesh_check.returncode != 0 or "Mesh OK." not in mesh_check.stdout or not check_case():
        return False
    cells = len(field(final / "U", "vector"))
    if cells <= 12800 or any(
        len(field(final / name, "scalar")) != cells
        for name in ("p", "k", "epsilon", "nut")
    ):
        return False

    values = patch_values(final / "yPlus", "cylinder")
    faces = cylinder_faces()
    if faces <= 0 or len(values) != faces:
        return False
    average = sum(values) / len(values)
    if not (all(math.isfinite(value) and value >= 0 for value in values) and 20.0 < average < 80.0):
        return False

    with (ROOT / "yplus_surface.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != len(values) or set(rows[0]) != {"face_index", "yplus"}:
        return False
    for index, (row, expected) in enumerate(zip(rows, values)):
        if int(row["face_index"]) != index or not close(float(row["yplus"]), expected, 5.0e-7):
            return False

    lines = [line.strip() for line in read(ROOT / "summary.txt").splitlines() if line.strip()]
    if len(lines) != 1:
        return False
    reported = float(lines[0])
    return math.isfinite(reported) and abs(reported - average) <= 5.0e-7


def main() -> int:
    try:
        result = check()
    except Exception:
        result = False
    print("True" if result else "False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
