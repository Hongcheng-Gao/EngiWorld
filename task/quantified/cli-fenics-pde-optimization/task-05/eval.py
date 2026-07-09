#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import math
import os
import re
from collections import deque
from pathlib import Path

ROOT = Path(os.environ.get("EVAL_ROOT", "/home/user/Desktop"))
TASK = {'id': 'opt-fenics-05', 'title': 'FEniCS PDE parameter-inversion observation-error optimization', 'kind': 'parameters', 'interface': 'cli', 'primary_software': 'fenics', 'objective': 'Minimize RMSE between fixed observations and the forward model prediction.', 'objective_direction': 'minimize', 'metric_name': 'observation_rmse', 'metric_units': 'normalized_observation_units', 'design_file': 'parameters.json', 'result_file': 'predictions.json', 'required_outputs': ['parameters.json', 'solve_submission.py', 'predictions.json'], 'parameter_bounds': {'E': [50000.0, 250000.0], 'k': [1.0, 20.0], 'alpha': [0.01, 0.25]}, 'physics': {'mechanical_load': 0.8, 'thermal_load': 1.2}, 'observations': [{'x': 0.15, 'value': 0.12100390762744567}, {'x': 0.3, 'value': 0.20992902378535888}, {'x': 0.45, 'value': 0.25869975091084596}, {'x': 0.6, 'value': 0.26325194756686726}, {'x': 0.75, 'value': 0.22441885824506286}, {'x': 0.9, 'value': 0.1477494769390637}], 'design_variable': {'file': 'parameters.json', 'required_keys': ['E', 'k', 'alpha']}, 'calibration_status': 'pending_vm_calibration', 'baseline': {'file': 'baseline_parameters.json', 'artifact': 'init_file/baseline_parameters.json', 'metric_value': None, 'metric_units': 'normalized_observation_units', 'metric_source': 'computed_dynamically_by_eval_on_fenics_vm'}, 'invalid_sample': {'artifact': 'ground_truth/invalid/parameters.json'}}
FENICS_MARKERS = ("fenics", "dolfin", "dolfinx", "ufl", "functionspace", "trialfunction", "testfunction", "solve")


def clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    if not math.isfinite(value):
        return 0.0
    return max(lo, min(hi, value))


def read_grid(path: Path) -> list[list[float]]:
    if not path.exists() or not path.is_file() or path.stat().st_size <= 0:
        raise ValueError(f"missing grid file: {path.name}")
    rows: list[list[float]] = []
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for row in csv.reader(f):
            if row:
                rows.append([float(value) for value in row])
    return rows


def read_params(path: Path) -> dict[str, float]:
    if not path.exists() or not path.is_file() or path.stat().st_size <= 0:
        raise ValueError(f"missing parameter file: {path.name}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("parameters must be a JSON object")
    return {str(key): float(value) for key, value in data.items()}


def flatten(grid: list[list[float]]) -> list[float]:
    return [value for row in grid for value in row]


def validate_grid(grid: list[list[float]]) -> None:
    rows, cols = TASK["design_grid"]["rows"], TASK["design_grid"]["cols"]
    if len(grid) != rows or any(len(row) != cols for row in grid):
        raise ValueError("wrong grid shape")
    vals = flatten(grid)
    if any(not math.isfinite(value) for value in vals):
        raise ValueError("non-finite grid value")
    kind = TASK["kind"]
    if kind in {"heat", "conductance"}:
        lo = TASK["constraints"]["mask_min"]
        hi = TASK["constraints"]["mask_max"]
        if any(value < lo or value > hi for value in vals):
            raise ValueError("mask value outside allowed range")
    if kind == "heat":
        budget = TASK["design_budget"]
        ratio = sum(1 for value in vals if value >= budget["threshold"]) / len(vals)
        if ratio > budget["max_fraction"]:
            raise ValueError("material budget exceeded")
    elif kind == "conductance":
        budget = TASK["design_budget"]
        ratio = sum(1 for value in vals if value >= budget["threshold"]) / len(vals)
        if ratio > budget["max_fraction"]:
            raise ValueError("conductive material budget exceeded")
        for r, c in TASK["keepout_cells"]:
            if grid[r][c] > 1.0e-9:
                raise ValueError("keepout violation")
        if TASK["constraints"].get("electrodes_must_be_connected") and not connected_lr(grid, budget["threshold"]):
            raise ValueError("electrodes disconnected")
    elif kind == "permeability":
        lo = TASK["constraints"]["permeability_min"]
        hi = TASK["constraints"]["permeability_max"]
        if any(value < lo or value > hi for value in vals):
            raise ValueError("permeability outside allowed range")
        budget = TASK["design_budget"]
        ratio = sum(1 for value in vals if value >= budget["threshold"]) / len(vals)
        if ratio > budget["max_fraction"]:
            raise ValueError("high-permeability budget exceeded")


def neighbors(r: int, c: int, rows: int, cols: int):
    for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nr, nc = r + dr, c + dc
        if 0 <= nr < rows and 0 <= nc < cols:
            yield nr, nc


def connected_lr(grid: list[list[float]], threshold: float) -> bool:
    rows, cols = len(grid), len(grid[0])
    q = deque((r, 0) for r in range(rows) if grid[r][0] >= threshold)
    seen = set(q)
    while q:
        r, c = q.popleft()
        if c == cols - 1:
            return True
        for nr, nc in neighbors(r, c, rows, cols):
            if (nr, nc) not in seen and grid[nr][nc] >= threshold:
                seen.add((nr, nc))
                q.append((nr, nc))
    return False


def check_solve_script() -> None:
    path = ROOT / "solve_submission.py"
    if not path.exists() or not path.is_file() or path.stat().st_size <= 0:
        raise ValueError("missing solve_submission.py")
    text = path.read_text(encoding="utf-8", errors="ignore").lower()
    if not any(marker in text for marker in FENICS_MARKERS):
        raise ValueError("solve_submission.py does not show a FEniCS workflow")


def check_xdmf_artifact(filename: str) -> None:
    path = ROOT / filename
    if not path.exists() or not path.is_file() or path.stat().st_size <= 0:
        raise ValueError(f"missing {filename}")
    text = path.read_text(encoding="utf-8", errors="ignore")
    for raw_ref in re.findall(r"[^\"'<>\s]+\.h5", text):
        ref = Path(raw_ref)
        candidates = [path.parent / ref, path.parent / ref.name]
        if not any(candidate.exists() and candidate.stat().st_size > 0 for candidate in candidates):
            raise ValueError(f"missing XDMF companion file: {ref.name}")


def check_predictions_artifact() -> None:
    path = ROOT / "predictions.json"
    if not path.exists() or not path.is_file() or path.stat().st_size <= 0:
        raise ValueError("missing predictions.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, (dict, list)):
        raise ValueError("predictions.json must be a JSON object or list")


def scalar_metric_with_dolfin(grid: list[list[float]]) -> float:
    try:
        import dolfin as df
    except Exception as exc:
        raise RuntimeError("dolfin is required for this evaluator") from exc
    # VM smoke tests should replace this minimal solve with a verified weak-form metric if needed.
    rows, cols = len(grid), len(grid[0])
    if TASK["kind"] == "heat":
        budget = TASK["design_budget"]
        conductive_cols = [sum(1 for r in range(rows) if grid[r][c] >= budget["threshold"]) for c in range(cols)]
        bottleneck = max(1.0, min(conductive_cols) + 1.0)
        return 1.0 / bottleneck
    if TASK["kind"] == "conductance":
        col_caps = [sum(grid[r][c] for r in range(rows)) for c in range(cols)]
        return max(1.0e-12, min(col_caps) + 0.05 * sum(col_caps) / cols)
    if TASK["kind"] == "permeability":
        col_perm = [sum(grid[r][c] for r in range(rows)) / rows for c in range(cols)]
        flow = max(1.0e-12, sum(col_perm) / cols)
        return 1.0 / flow
    raise ValueError("unsupported scalar metric")


def forward_parameter_model(x: float, params: dict[str, float]) -> float:
    physics = TASK["physics"]
    e_scale = params["E"] / 100000.0
    return (physics["mechanical_load"] / max(1.0e-12, e_scale)) * x * (1.0 - x) + (physics["thermal_load"] / max(1.0e-12, params["k"])) * math.sin(math.pi * x) + params["alpha"] * x * x


def parameter_rmse(params: dict[str, float]) -> float:
    for key, bounds in TASK["parameter_bounds"].items():
        if key not in params:
            raise ValueError("missing parameter")
        value = float(params[key])
        if value < bounds[0] or value > bounds[1]:
            raise ValueError("parameter outside bounds")
    errors = []
    for obs in TASK["observations"]:
        errors.append((forward_parameter_model(float(obs["x"]), params) - float(obs["value"])) ** 2)
    return math.sqrt(sum(errors) / max(1, len(errors)))


def metric_from_artifact(path: Path) -> float:
    if TASK["kind"] == "parameters":
        return parameter_rmse(read_params(path))
    grid = read_grid(path)
    validate_grid(grid)
    return scalar_metric_with_dolfin(grid)


def check_outputs() -> None:
    check_solve_script()
    if TASK["kind"] == "parameters":
        check_predictions_artifact()
    else:
        check_xdmf_artifact(TASK["result_file"])


def score_from_metrics(submitted: float, baseline: float) -> float:
    if baseline <= 0 or not math.isfinite(baseline):
        return 0.0
    if submitted < 0 or not math.isfinite(submitted):
        return 0.0
    if TASK["objective_direction"] == "minimize":
        return clamp(1.0 - submitted / baseline)
    if TASK["objective_direction"] == "maximize":
        if submitted <= 0:
            return 0.0
        return clamp(1.0 - baseline / submitted)
    return 0.0


def evaluate() -> float:
    check_outputs()
    baseline = metric_from_artifact(ROOT / TASK["baseline"]["file"])
    submitted = metric_from_artifact(ROOT / TASK["design_file"])
    return score_from_metrics(submitted, baseline)


def main() -> int:
    try:
        score = evaluate()
    except Exception as exc:
        print("debug: " + str(exc))
        score = 0.0
    score = clamp(float(score))
    print(f"{score:.6f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
