#!/usr/bin/env python3
from __future__ import annotations

import csv
import math
import re
import subprocess
from pathlib import Path


ROOT = Path("/home/user/Desktop")
CASE = ROOT / "porous"
RHO = 1000.0


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


def patch(text: str, name: str) -> str:
    return named_block(named_block(text, "boundaryField"), name)


def zone_labels(text: str, name: str) -> list[int]:
    block = named_block(text, name)
    match = re.search(r"\bcellLabels\s+List<label>\s+(\d+)\s*\((.*?)\)\s*;", block, re.S)
    if not match:
        raise ValueError(f"missing labels for zone {name}")
    labels = [int(value) for value in match.group(2).split()]
    if len(labels) != int(match.group(1)) or len(labels) != len(set(labels)):
        raise ValueError("invalid cell-zone labels")
    return labels


def field(path: Path, kind: str) -> list:
    match = re.search(
        rf"internalField\s+nonuniform\s+List<{kind}>\s+(\d+)\s*\((.*?)\)\s*;",
        read(path),
        re.S,
    )
    if not match:
        raise ValueError(f"missing nonuniform {kind} field")
    if kind == "vector":
        values = [
            tuple(float(value) for value in item.split())
            for item in re.findall(r"\(([^()]+)\)", match.group(2))
        ]
    else:
        values = [float(value) for value in match.group(2).split()]
    if len(values) != int(match.group(1)):
        raise ValueError("field count mismatch")
    return values


def axial_profile() -> list[tuple[float, float]]:
    centres = field(CASE / "500/C", "vector")
    pressure = field(CASE / "500/p", "scalar")
    velocity = field(CASE / "500/U", "vector")
    if not (len(centres) == len(pressure) == len(velocity) == 1000):
        raise ValueError("unexpected field count")
    stations: dict[float, list[float]] = {}
    for point, value in zip(centres, pressure):
        stations.setdefault(point[0], []).append(value)
    if len(stations) != 100 or any(len(values) != 10 for values in stations.values()):
        raise ValueError("unexpected station layout")
    if not 0.095 < sum(item[0] for item in velocity) / len(velocity) < 0.105:
        raise ValueError("unexpected bulk velocity")
    return [(x, sum(values) / len(values)) for x, values in sorted(stations.items())]


def check_case() -> bool:
    mesh = read(CASE / "system/blockMeshDict")
    velocity = read(CASE / "0/U")
    pressure = read(CASE / "0/p")
    physical = read(CASE / "constant/physicalProperties")
    reference = read(CASE / "constant/referenceProperties")
    porosity = read(CASE / "constant/porosityProperties")
    topology = read(CASE / "system/topoSetDict")
    control = read(CASE / "system/controlDict")
    porous_bed = named_block(porosity, "porousBed")
    coordinates = named_block(porous_bed, "coordinateSystem")
    rotation = named_block(coordinates, "coordinateRotation")
    return all(
        (
            "(1 0.1 0.01)" in mesh,
            "(100 10 1)" in mesh,
            has_entry(patch(velocity, "inlet"), "value", r"uniform\s+\(0\.1\s+0(?:\.0+)?\s+0(?:\.0+)?\)"),
            has_entry(patch(velocity, "outlet"), "type", r"zeroGradient"),
            has_entry(patch(velocity, "topBottom"), "type", r"symmetry"),
            has_entry(patch(velocity, "frontAndBack"), "type", r"empty"),
            has_entry(patch(pressure, "outlet"), "type", r"fixedValue"),
            has_entry(patch(pressure, "outlet"), "value", r"uniform\s+0(?:\.0+)?"),
            has_entry(patch(pressure, "topBottom"), "type", r"symmetry"),
            has_entry(patch(pressure, "frontAndBack"), "type", r"empty"),
            re.search(r"\bnu\s+\[0 2 -1 0 0 0 0\]\s+1e-?6\s*;", physical, re.I) is not None,
            re.search(r"\brho\s+1000\s*;", reference) is not None,
            has_entry(porous_bed, "type", r"DarcyForchheimer"),
            has_entry(porous_bed, "cellZone", r"porosity"),
            has_entry(porous_bed, "d", r"\(1e8\s+1e8\s+1e8\)"),
            has_entry(porous_bed, "f", r"\(1000\s+1000\s+1000\)"),
            has_entry(coordinates, "type", r"cartesian"),
            has_entry(coordinates, "origin", r"\(0(?:\.0+)?\s+0(?:\.0+)?\s+0(?:\.0+)?\)"),
            has_entry(rotation, "e1", r"\(1(?:\.0+)?\s+0(?:\.0+)?\s+0(?:\.0+)?\)"),
            has_entry(rotation, "e2", r"\(0(?:\.0+)?\s+1(?:\.0+)?\s+0(?:\.0+)?\)"),
            "box (-1 -1 -1) (2 2 2);" in topology,
            "application porousSimpleFoam;" in control,
            re.search(r"\bendTime\s+500\s*;", control) is not None,
        )
    )


def check() -> bool:
    required = (
        ROOT / "build_case.py",
        ROOT / "postprocess.py",
        ROOT / "summary.txt",
        ROOT / "axial_pressure.csv",
        CASE / "log.blockMesh",
        CASE / "log.checkMesh",
        CASE / "log.topoSet",
        CASE / "log.porousSimpleFoam",
        CASE / "log.writeCellCentres",
        CASE / "constant/polyMesh/cellZones",
        CASE / "500/C",
        CASE / "500/U",
        CASE / "500/p",
    )
    if any(not path.is_file() or path.stat().st_size == 0 for path in required):
        return False
    mesh_log = read(CASE / "log.checkMesh")
    solve_log = read(CASE / "log.porousSimpleFoam")
    zones = read(CASE / "constant/polyMesh/cellZones")
    if not (
        "End" in read(CASE / "log.blockMesh")
        and "End" in read(CASE / "log.topoSet")
        and "End" in read(CASE / "log.writeCellCentres")
        and "Mesh OK." in mesh_log
        and "End" in mesh_log
        and "Time = 500" in solve_log
        and "End" in solve_log
        and zone_labels(zones, "porosity") == list(range(1000))
    ):
        return False
    mesh_check = subprocess.run(
        [
            "bash",
            "--noprofile",
            "--norc",
            "-c",
            "trap - CHLD; . /opt/openfoam11/etc/bashrc && checkMesh -case /home/user/Desktop/porous",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=120,
    )
    if mesh_check.returncode != 0 or "Mesh OK." not in mesh_check.stdout or not check_case():
        return False

    profile = axial_profile()
    delta_p = RHO * (profile[0][1] - profile[-1][1])
    if not math.isfinite(delta_p):
        return False
    with (ROOT / "axial_pressure.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    keys = ("x_m", "p_kinematic_m2ps2", "p_pa")
    if len(rows) != len(profile) or set(rows[0]) != set(keys):
        return False
    for row, (x, value) in zip(rows, profile):
        actual = tuple(float(row[key]) for key in keys)
        expected = (x, value, RHO * value)
        if any(abs(left - right) > 5e-7 for left, right in zip(actual, expected)):
            return False

    lines = [line.strip() for line in read(ROOT / "summary.txt").splitlines() if line.strip()]
    if len(lines) != 1:
        return False
    reported = float(lines[0])
    return math.isfinite(reported) and abs(reported - delta_p) <= 5e-7


def main() -> int:
    try:
        result = check()
    except Exception:
        result = False
    print("True" if result else "False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
