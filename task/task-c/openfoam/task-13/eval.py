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


def patch(text: str, name: str) -> str:
    return named_block(named_block(text, "boundaryField"), name)


def field(path: Path, kind: str) -> list:
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
            mesh.count("hex (") == 8,
            mesh.count("(40 12 1)") == 8,
            mesh.count("arc ") == 32,
            has_entry(named_block(mesh, "cylinder"), "type", r"wall"),
            has_entry(named_block(mesh, "frontAndBack"), "type", r"empty"),
            has_entry(patch(velocity, "inlet"), "value", r"uniform\s+\(1(?:\.0+)?\s+0(?:\.0+)?\s+0(?:\.0+)?\)"),
            has_entry(patch(velocity, "outlet"), "type", r"zeroGradient"),
            has_entry(patch(velocity, "cylinder"), "type", r"noSlip"),
            has_entry(patch(velocity, "frontAndBack"), "type", r"empty"),
            has_entry(patch(pressure, "outlet"), "type", r"fixedValue"),
            has_entry(patch(pressure, "outlet"), "value", r"uniform\s+0(?:\.0+)?"),
            re.search(r"\bnu\s+\[0 2 -1 0 0 0 0\]\s+1e-?3\s*;", physical, re.I)
            is not None,
            "simulationType laminar;" in momentum,
            re.search(r"\bendTime\s+20\s*;", control) is not None,
            re.search(r"\bdeltaT\s+0\.0025\s*;", control) is not None,
            has_entry(forces, "type", r"forceCoeffs"),
            has_entry(forces, "patches", r"\(\s*cylinder\s*\)"),
            has_entry(forces, "rhoInf", r"1(?:\.0+)?"),
            has_entry(forces, "magUInf", r"1(?:\.0+)?"),
            has_entry(forces, "lRef", r"0\.1"),
            has_entry(forces, "Aref", r"0\.001"),
            has_entry(forces, "dragDir", r"\(1(?:\.0+)?\s+0(?:\.0+)?\s+0(?:\.0+)?\)"),
            has_entry(forces, "liftDir", r"\(0(?:\.0+)?\s+1(?:\.0+)?\s+0(?:\.0+)?\)"),
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
        "End" not in read(CASE / "log.blockMesh")
        or "Mesh OK." not in check_log
        or "End" not in check_log
        or "End" not in solve_log
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
    if not history or any(
        not all(math.isfinite(value) for value in row)
        or row[0] < 0.0
        or row[0] > 20.0 + 1.0e-9
        for row in history
    ) or any(right[0] <= left[0] for left, right in zip(history, history[1:])):
        return False
    window = [row for row in history if 10.0 <= row[0] <= 20.0]
    if not window:
        return False
    cl_mean = sum(row[2] for row in window) / len(window)
    cd_mean = sum(row[1] for row in window) / len(window)

    keys = ("time_s", "cd", "cl")
    with (ROOT / "force_history.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != len(history) or set(rows[0]) != set(keys):
        return False
    for row, expected in zip(rows, history):
        actual = tuple(float(row[key]) for key in keys)
        if any(abs(a - b) > 5.0e-7 for a, b in zip(actual, expected)):
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
