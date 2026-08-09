#!/usr/bin/env python3
from __future__ import annotations

import ast
import csv
import json
import math
import os
import re
from collections import deque
from pathlib import Path

ROOT = Path(os.environ.get("EVAL_ROOT", "/home/user/Desktop"))
TASK = {'id': 'opt-fenics-05', 'title': 'FEniCS PDE parameter-inversion observation-error optimization', 'kind': 'parameters', 'interface': 'cli', 'primary_software': 'fenics', 'objective': 'Minimize RMSE between fixed observations and the forward model prediction.', 'objective_direction': 'minimize', 'metric_name': 'observation_rmse', 'metric_units': 'normalized_observation_units', 'design_file': 'parameters.json', 'result_file': 'predictions.json', 'required_outputs': ['parameters.json', 'solve_submission.py', 'predictions.json'], 'parameter_bounds': {'E': [50000.0, 250000.0], 'k': [1.0, 20.0], 'alpha': [0.01, 0.25]}, 'physics': {'mechanical_load': 0.8, 'thermal_load': 1.2}, 'observations': [{'x': 0.15, 'value': 0.12100390762744567}, {'x': 0.3, 'value': 0.20992902378535888}, {'x': 0.45, 'value': 0.25869975091084596}, {'x': 0.6, 'value': 0.26325194756686726}, {'x': 0.75, 'value': 0.22441885824506286}, {'x': 0.9, 'value': 0.1477494769390637}], 'design_variable': {'file': 'parameters.json', 'required_keys': ['E', 'k', 'alpha']}, 'calibration_status': 'pending_vm_calibration', 'baseline': {'file': 'baseline_parameters.json', 'artifact': 'init_file/baseline_parameters.json', 'metric_value': None, 'metric_units': 'normalized_observation_units', 'metric_source': 'computed_dynamically_by_eval_on_fenics_vm'}, 'invalid_sample': {'artifact': 'ground_truth/invalid/parameters.json'}}
LEGACY_FENICS_MODULES = {"dolfin", "fenics"}


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


def assert_baseline_is_unchanged(params: dict[str, float]) -> None:
    expected = {"E": 90000.0, "k": 4.0, "alpha": 0.18}
    if set(params) != set(expected):
        raise ValueError("baseline parameter file was modified")
    for key, value in expected.items():
        if abs(params[key] - value) > 1.0e-12:
            raise ValueError("baseline parameter file was modified")


def dotted_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = dotted_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    return ""


def check_solve_script() -> None:
    path = ROOT / "solve_submission.py"
    if not path.exists() or not path.is_file() or path.stat().st_size <= 0:
        raise ValueError("missing solve_submission.py")
    source = path.read_text(encoding="utf-8", errors="strict")
    try:
        tree = ast.parse(source, filename=path.name)
    except SyntaxError as exc:
        raise ValueError("solve_submission.py is not valid Python") from exc

    imports: set[str] = set()
    calls: set[str] = set()
    literals: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0].lower() for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0].lower())
        elif isinstance(node, ast.Call):
            calls.add(dotted_name(node.func).lower().split(".")[-1])
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            literals.add(node.value.lower())

    if not imports.intersection(LEGACY_FENICS_MODULES):
        raise ValueError("solve_submission.py must import legacy FEniCS/DOLFIN")
    required_groups = (
        {"mesh", "rectanglemesh", "intervalmesh", "unitsquaremesh", "unitintervalmesh"},
        {"functionspace", "vectorfunctionspace"},
        {"trialfunction", "trialfunctions"},
        {"testfunction", "testfunctions"},
        {"solve", "linearvariationalsolver", "nonlinearvariationalsolver"},
    )
    if any(not calls.intersection(group) for group in required_groups):
        raise ValueError("solve_submission.py lacks a complete DOLFIN PDE workflow")
    for filename in ("problem_spec.json", "parameters.json", "predictions.json"):
        if not any(filename in literal for literal in literals):
            raise ValueError(f"solve_submission.py does not reference {filename}")


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
    params = read_params(ROOT / TASK["design_file"])
    parameter_copy = data.get("parameters") if isinstance(data, dict) else None
    if parameter_copy is not None:
        if not isinstance(parameter_copy, dict):
            raise ValueError("predictions parameters must be an object")
        for key in TASK["parameter_bounds"]:
            try:
                copied = float(parameter_copy[key])
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError("predictions parameters do not match parameters.json") from exc
            if not math.isclose(copied, params[key], rel_tol=1.0e-10, abs_tol=1.0e-12):
                raise ValueError("predictions parameters do not match parameters.json")

    payload = data.get("predictions") if isinstance(data, dict) and "predictions" in data else data
    observed: dict[float, float] = {}
    reported_observations: dict[float, float] = {}
    if isinstance(payload, list):
        if len(payload) != len(TASK["observations"]):
            raise ValueError("predictions.json has the wrong number of predictions")
        for index, item in enumerate(payload):
            if isinstance(item, dict):
                x = float(item.get("x", TASK["observations"][index]["x"]))
                raw_prediction = item.get("prediction", item.get("value"))
                if raw_prediction is None:
                    raise ValueError("prediction row is missing a value")
                prediction = float(raw_prediction)
                if "observation" in item:
                    reported_observations[x] = float(item["observation"])
            else:
                x = float(TASK["observations"][index]["x"])
                prediction = float(item)
            observed[x] = prediction
    elif isinstance(payload, dict):
        for key, value in payload.items():
            if key == "parameters":
                continue
            observed[float(key)] = float(value)
    else:
        raise ValueError("predictions.json has an unsupported prediction layout")

    if len(observed) != len(TASK["observations"]):
        raise ValueError("predictions.json has duplicate or missing observation points")
    for observation in TASK["observations"]:
        x = float(observation["x"])
        matches = [value for point, value in observed.items() if math.isclose(point, x, rel_tol=0.0, abs_tol=1.0e-12)]
        if len(matches) != 1 or not math.isfinite(matches[0]):
            raise ValueError("predictions.json does not cover the fixed observation points")
        reported = [value for point, value in reported_observations.items() if math.isclose(point, x, rel_tol=0.0, abs_tol=1.0e-12)]
        if reported and not math.isclose(reported[0], float(observation["value"]), rel_tol=1.0e-10, abs_tol=1.0e-12):
            raise ValueError("predictions.json changes an observation")
        expected = forward_parameter_model(x, params)
        if not math.isclose(matches[0], expected, rel_tol=1.0e-8, abs_tol=1.0e-10):
            raise ValueError("predictions.json is inconsistent with parameters.json")


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
        params = read_params(path)
        if path.name == TASK["baseline"]["file"]:
            assert_baseline_is_unchanged(params)
        return parameter_rmse(params)
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
