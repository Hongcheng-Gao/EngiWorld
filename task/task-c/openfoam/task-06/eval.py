#!/usr/bin/env python3
from __future__ import annotations

import csv
import math
import re
import subprocess
from pathlib import Path


ROOT = Path("/home/user/Desktop")
CASE = ROOT / "plate"
U_REF = 10.0
NU = 1.5e-5
STATION = 0.5


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


def internal_field(path: Path, kind: str) -> list:
    match = re.search(
        rf"internalField\s+nonuniform\s+List<{kind}>\s+\d+\s*\((.*?)\)\s*;",
        read(path),
        re.S,
    )
    if not match:
        raise ValueError(f"missing {kind} field")
    if kind == "vector":
        return [
            tuple(float(value) for value in item.split())
            for item in re.findall(r"\(([^()]+)\)", match.group(1))
        ]
    return [float(value) for value in match.group(1).split()]


def patch_vectors(path: Path, patch: str) -> list[tuple[float, float, float]]:
    match = re.search(
        rf"\b{re.escape(patch)}\s*\{{.*?value\s+nonuniform\s+List<vector>\s+(\d+)\s*\((.*?)\)\s*;",
        read(path),
        re.S,
    )
    if not match:
        raise ValueError(f"missing {patch} vectors")
    values = [
        tuple(float(value) for value in item.split())
        for item in re.findall(r"\(([^()]+)\)", match.group(2))
    ]
    if len(values) != int(match.group(1)):
        raise ValueError(f"{patch} vector count mismatch")
    return values


def check_case() -> bool:
    mesh = read(CASE / "system/blockMeshDict")
    velocity = read(CASE / "0/U")
    pressure = read(CASE / "0/p")
    physical = read(CASE / "constant/physicalProperties")
    momentum = read(CASE / "constant/momentumTransport")
    control = read(CASE / "system/controlDict")
    schemes = read(CASE / "system/fvSchemes")
    return all(
        (
            "(-0.2 0 0)" in mesh,
            "(1 0.2 0)" in mesh,
            "(40 60 1)" in mesh,
            "(200 60 1)" in mesh,
            mesh.count("simpleGrading (1 50 1)") == 2,
            has_entry(named_block(mesh, "upstreamBottom"), "type", r"symmetryPlane"),
            has_entry(named_block(mesh, "plate"), "type", r"wall"),
            has_entry(named_block(mesh, "frontAndBack"), "type", r"empty"),
            all(has_entry(patch(velocity, name), "value", r"uniform\s+\(10(?:\.0+)?\s+0(?:\.0+)?\s+0(?:\.0+)?\)") for name in ("inlet", "freeStream")),
            has_entry(patch(velocity, "outlet"), "type", r"zeroGradient"),
            has_entry(patch(velocity, "upstreamBottom"), "type", r"symmetryPlane"),
            has_entry(patch(velocity, "plate"), "type", r"noSlip"),
            has_entry(patch(velocity, "frontAndBack"), "type", r"empty"),
            has_entry(patch(pressure, "outlet"), "type", r"fixedValue"),
            has_entry(patch(pressure, "outlet"), "value", r"uniform\s+0(?:\.0+)?"),
            has_entry(patch(pressure, "upstreamBottom"), "type", r"symmetryPlane"),
            has_entry(patch(pressure, "frontAndBack"), "type", r"empty"),
            re.search(r"\bnu\s+\[0 2 -1 0 0 0 0\]\s+1\.5e-?5\s*;", physical, re.I)
            is not None,
            "simulationType laminar;" in momentum,
            re.search(r"\bendTime\s+2000\s*;", control) is not None,
            re.search(r"\bwriteInterval\s+2000\s*;", control) is not None,
            "div(phi,U) bounded Gauss linearUpwind grad(U);" in schemes,
        )
    )


def check() -> bool:
    required = (
        ROOT / "build_case.py",
        ROOT / "postprocess.py",
        ROOT / "summary.txt",
        ROOT / "plate_shear.csv",
        CASE / "log.blockMesh",
        CASE / "log.simpleFoam",
        CASE / "log.cellCentres",
        CASE / "log.wallShearStress",
        CASE / "2000/C",
        CASE / "2000/U",
        CASE / "2000/p",
        CASE / "2000/wallShearStress",
    )
    if any(not path.is_file() or path.stat().st_size == 0 for path in required):
        return False
    solve_log = read(CASE / "log.simpleFoam")
    if any("End" not in read(path) for path in (CASE / "log.blockMesh", CASE / "log.cellCentres", CASE / "log.wallShearStress")):
        return False
    if "End" not in solve_log or "Time = 2000" not in solve_log:
        return False
    mesh_check = subprocess.run(
        ["bash", "-lc", ". /opt/openfoam11/etc/bashrc && checkMesh -case /home/user/Desktop/plate"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=120,
    )
    if mesh_check.returncode != 0 or "Mesh OK." not in mesh_check.stdout or not check_case():
        return False

    centres_internal = internal_field(CASE / "2000/C", "vector")
    velocity = internal_field(CASE / "2000/U", "vector")
    pressure = internal_field(CASE / "2000/p", "scalar")
    if not (len(centres_internal) == len(velocity) == len(pressure) == 14400):
        return False

    centres = patch_vectors(CASE / "2000/C", "plate")
    shear = patch_vectors(CASE / "2000/wallShearStress", "plate")
    if len(centres) != 200 or len(shear) != 200:
        return False
    calculated = []
    for centre, stress in sorted(zip(centres, shear), key=lambda item: item[0][0]):
        x = centre[0]
        tau_x = stress[0]
        cf = 2.0 * abs(tau_x) / U_REF**2
        theory = 0.664 / math.sqrt(U_REF * x / NU)
        error_percent = abs(cf - theory) / theory * 100.0
        calculated.append((x, tau_x, cf, theory, error_percent))
    sample = min(calculated, key=lambda row: abs(row[0] - STATION))
    if abs(sample[0] - STATION) > 0.003 or not (8e-4 < sample[2] < 1.5e-3 and sample[4] <= 15.0):
        return False

    keys = ("x_m", "wall_shear_kinematic_m2ps2", "cf", "blasius_cf", "error_percent")
    with (ROOT / "plate_shear.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != 200 or set(rows[0]) != set(keys):
        return False
    for row, expected in zip(rows, calculated):
        actual = tuple(float(row[key]) for key in keys)
        if any(abs(a - b) > 5.0e-7 for a, b in zip(actual, expected)):
            return False

    values = [item.strip() for item in read(ROOT / "summary.txt").strip().split(",")]
    if len(values) != 2:
        return False
    reported = tuple(float(value) for value in values)
    return all(math.isfinite(value) for value in reported) and all(
        abs(actual - expected) <= 5.0e-7
        for actual, expected in zip(reported, (sample[2], sample[4]))
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
