#!/usr/bin/env python3
from __future__ import annotations

import math
import re
import subprocess
from pathlib import Path


ROOT = Path("/home/user/Desktop")
CASE = ROOT / "channel"
HEIGHT = 0.1
MEAN_SPEED = 0.1
THEORY_MAX = 0.15


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def close(actual: float, expected: float, tolerance: float) -> bool:
    return math.isfinite(actual) and abs(actual - expected) <= tolerance


def summary(path: Path) -> tuple[float, float, float]:
    rows = [line.strip() for line in read(path).splitlines() if line.strip()]
    if len(rows) != 1:
        raise ValueError("summary must contain one row")
    values = tuple(float(field.strip()) for field in rows[0].split(","))
    if len(values) != 3 or not all(math.isfinite(value) for value in values):
        raise ValueError("summary must contain three finite values")
    return values


def latest_time() -> float:
    times = [
        float(path.name)
        for path in CASE.iterdir()
        if path.is_dir() and re.fullmatch(r"\d+(?:\.\d+)?", path.name)
    ]
    if not times:
        raise ValueError("no OpenFOAM time directory")
    return max(times)


def resample() -> Path:
    command = (
        ". /opt/openfoam11/etc/bashrc && "
        "postProcess -case /home/user/Desktop/channel -latestTime -func sampleDict "
        "> /tmp/engiworld-openfoam-01-sample.log 2>&1"
    )
    result = subprocess.run(
        ["bash", "-lc", command],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError("postProcess sampling failed")
    candidates = list((CASE / "postProcessing/sampleDict").glob("*/outletLine.xy"))
    if not candidates:
        raise FileNotFoundError("missing sampled outlet profile")
    return max(candidates, key=lambda path: float(path.parent.name))


def mesh_is_valid() -> bool:
    command = ". /opt/openfoam11/etc/bashrc && checkMesh -case /home/user/Desktop/channel"
    result = subprocess.run(
        ["bash", "-lc", command],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=120,
    )
    return result.returncode == 0 and "Mesh OK." in result.stdout


def profile_metrics(path: Path) -> tuple[float, float]:
    rows: list[tuple[float, float]] = []
    for line in read(path).splitlines():
        fields = line.split()
        if len(fields) < 4 or fields[0].startswith("#"):
            continue
        y, ux, uy, uz = (float(value) for value in fields[:4])
        if not 0.0 < y < HEIGHT or abs(uy) > 1.0e-5 or abs(uz) > 1.0e-5:
            raise ValueError("invalid outlet sample")
        rows.append((y, ux))
    if len(rows) != 80:
        raise ValueError("outlet profile must contain 80 samples")
    errors = []
    for y, ux in rows:
        theory = 6.0 * MEAN_SPEED * y * (HEIGHT - y) / HEIGHT**2
        errors.append(abs(ux - theory))
    return max(ux for _, ux in rows), max(errors) / THEORY_MAX * 100.0


def check_case_definition() -> bool:
    mesh = read(CASE / "system/blockMeshDict")
    velocity = read(CASE / "0/U")
    pressure = read(CASE / "0/p")
    physical = read(CASE / "constant/physicalProperties")
    control = read(CASE / "system/controlDict")
    sampling = read(CASE / "system/sampleDict")

    return all(
        (
            "(1.0 0 0)" in mesh,
            "(1.0 0.1 0)" in mesh,
            "(100 80 1)" in mesh,
            "type empty;" in mesh,
            "value           nonuniform List<vector>" in velocity,
            re.search(r"\b80\s*\(", velocity) is not None,
            "type            zeroGradient;" in pressure,
            re.search(r"\bnu\s+\[0 2 -1 0 0 0 0\]\s+1(?:\.0)?e-0?5\s*;", physical, re.I)
            is not None,
            re.search(r"\bendTime\s+30(?:\.0)?\s*;", control) is not None,
            re.search(r"\bdeltaT\s+0\.02\s*;", control) is not None,
            "nPoints     80;" in sampling,
            "start       (0.99 0.00062500 0.00500000);" in sampling,
            "end         (0.99 0.09937500 0.00500000);" in sampling,
        )
    )


def check() -> bool:
    required = (
        ROOT / "build_case.py",
        ROOT / "postprocess.py",
        ROOT / "summary.txt",
        ROOT / "outlet_profile.csv",
        CASE / "log.blockMesh",
        CASE / "log.icoFoam",
        CASE / "log.sample",
        CASE / "system/blockMeshDict",
        CASE / "system/controlDict",
        CASE / "system/fvSchemes",
        CASE / "system/fvSolution",
        CASE / "system/sampleDict",
        CASE / "constant/transportProperties",
        CASE / "constant/physicalProperties",
        CASE / "0/U",
        CASE / "0/p",
    )
    if any(not path.is_file() or path.stat().st_size == 0 for path in required):
        return False
    if latest_time() < 30.0 or "End" not in read(CASE / "log.icoFoam"):
        return False
    if "End" not in read(CASE / "log.blockMesh") or not mesh_is_valid() or not check_case_definition():
        return False

    calculated_max, calculated_error = profile_metrics(resample())
    reported_max, reported_theory, reported_error = summary(ROOT / "summary.txt")
    if calculated_error > 2.0:
        return False
    return (
        close(calculated_max, THEORY_MAX, 0.003)
        and close(reported_max, calculated_max, 2.0e-5)
        and close(reported_theory, THEORY_MAX, 1.0e-8)
        and close(reported_error, calculated_error, 2.0e-3)
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
