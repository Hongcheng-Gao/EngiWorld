#!/usr/bin/env python3
"""Starter workflow for the FEniCS cantilever density optimization task.

Read problem_spec.json and baseline_density_field.csv from the Desktop.
Create density_field.csv, solve_submission.py, and displacement.xdmf.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path("/home/user/Desktop")
PROBLEM_SPEC_PATH = ROOT / "problem_spec.json"
BASELINE_PATH = ROOT / "baseline_density_field.csv"
DENSITY_OUTPUT = ROOT / "density_field.csv"
SOLVE_SCRIPT_OUTPUT = ROOT / "solve_submission.py"
DISPLACEMENT_OUTPUT = ROOT / "displacement.xdmf"


def read_grid(path: Path) -> list[list[float]]:
    rows: list[list[float]] = []
    with path.open("r", encoding="utf-8") as f:
        for row in csv.reader(f):
            if row:
                rows.append([float(value) for value in row])
    return rows


def write_grid(path: Path, rows: list[list[float]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        for row in rows:
            writer.writerow([f"{value:.6f}" for value in row])


def make_initial_design(baseline: list[list[float]]) -> list[list[float]]:
    """Return a feasible starting design.

    Replace this with your own optimization logic. Keep the mean density within
    the limit in problem_spec.json and preserve the fixed physical inputs.
    """
    return [row[:] for row in baseline]


def write_solver_template(path: Path) -> None:
    path.write_text(
        '''#!/usr/bin/env python3
from __future__ import annotations

# Build your FEniCS/dolfin or dolfinx solve here:
# 1. Read problem_spec.json and density_field.csv.
# 2. Map the density grid to a cell-wise material coefficient.
# 3. Solve the fixed 2D linear-elastic cantilever problem.
# 4. Write the displacement field to displacement.xdmf.

try:
    import dolfin  # FEniCS classic
except Exception:
    import dolfinx  # FEniCSx/dolfinx

# Implement the final solve workflow in this file.
''',
        encoding="utf-8",
    )


def main() -> int:
    spec = json.loads(PROBLEM_SPEC_PATH.read_text(encoding="utf-8"))
    baseline = read_grid(BASELINE_PATH)
    design = make_initial_design(baseline)
    write_grid(DENSITY_OUTPUT, design)
    write_solver_template(SOLVE_SCRIPT_OUTPUT)
    print(f"Wrote {DENSITY_OUTPUT}")
    print(f"Wrote {SOLVE_SCRIPT_OUTPUT}")
    print(f"Use FEniCS to write {DISPLACEMENT_OUTPUT}")
    _ = spec
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
