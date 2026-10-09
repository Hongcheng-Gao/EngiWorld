#!/usr/bin/env python3
"""Starter workflow for FEniCS PDE parameter-inversion observation-error optimization.

Read problem_spec.json and baseline_parameters.json from the Desktop.
Create parameters.json, solve_submission.py, and predictions.json.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path("/home/user/Desktop")
PROBLEM_SPEC_PATH = ROOT / "problem_spec.json"
BASELINE_PATH = ROOT / "baseline_parameters.json"
DESIGN_OUTPUT = ROOT / "parameters.json"
SOLVE_SCRIPT_OUTPUT = ROOT / "solve_submission.py"
RESULT_OUTPUT = ROOT / "predictions.json"


def write_solver_template(path: Path) -> None:
    path.write_text(
        '''#!/usr/bin/env python3
from __future__ import annotations

# Build your FEniCS/dolfin or dolfinx solve here:
# 1. Read problem_spec.json and the submitted design variable file.
# 2. Map the design variable to the PDE coefficient or parameter set.
# 3. Solve the fixed problem described in problem_spec.json.
# 4. Write the requested result artifact.

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
    design_text = BASELINE_PATH.read_text(encoding="utf-8")
    DESIGN_OUTPUT.write_text(design_text, encoding="utf-8")
    write_solver_template(SOLVE_SCRIPT_OUTPUT)
    print(f"Wrote {DESIGN_OUTPUT}")
    print(f"Wrote {SOLVE_SCRIPT_OUTPUT}")
    print(f"Use FEniCS to write {RESULT_OUTPUT}")
    _ = spec
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
