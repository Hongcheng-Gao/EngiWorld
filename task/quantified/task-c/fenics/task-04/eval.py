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
TASK = {'id': 'opt-fenics-04', 'title': 'FEniCS porous-flow hydraulic-resistance optimization', 'kind': 'permeability', 'interface': 'cli', 'primary_software': 'fenics', 'objective': 'Minimize hydraulic resistance through a fixed porous channel.', 'objective_direction': 'minimize', 'metric_name': 'hydraulic_resistance', 'metric_units': 'normalized_Pa_s_per_m3', 'design_file': 'permeability_field.csv', 'result_file': 'pressure.xdmf', 'required_outputs': ['permeability_field.csv', 'solve_submission.py', 'pressure.xdmf'], 'domain': {'length': 1.6, 'height': 0.8, 'unit': 'm'}, 'design_grid': {'rows': 8, 'cols': 16, 'row_axis': 'y', 'col_axis': 'x', 'row_0_location': 'bottom wall', 'col_0_location': 'inlet'}, 'solver_mesh': {'nx': 32, 'ny': 16, 'cell_type': 'triangle'}, 'flow': {'inlet_boundary': 'x = 0', 'outlet_boundary': 'x = length', 'inlet_pressure': 1.0, 'outlet_pressure': 0.0, 'impermeable_walls': ['y = 0', 'y = height']}, 'constraints': {'permeability_min': 0.1, 'permeability_max': 5.0}, 'design_budget': {'type': 'high_permeability_cell_fraction', 'threshold': 3.0, 'max_fraction': 0.4}, 'calibration_status': 'pending_vm_calibration', 'baseline': {'file': 'baseline_permeability_field.csv', 'artifact': 'init_file/baseline_permeability_field.csv', 'metric_value': None, 'metric_units': 'normalized_Pa_s_per_m3', 'metric_source': 'computed_dynamically_by_eval_on_fenics_vm'}, 'invalid_sample': {'artifact': 'ground_truth/invalid/permeability_field.csv'}}
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

    rows, cols = len(grid), len(grid[0])
    domain = TASK["domain"]
    width = float(domain.get("width", domain.get("length", 1.0)))
    height = float(domain["height"])
    mesh_spec = TASK["solver_mesh"]
    mesh = df.RectangleMesh(
        df.Point(0.0, 0.0),
        df.Point(width, height),
        int(mesh_spec["nx"]),
        int(mesh_spec["ny"]),
    )
    dg0 = df.FunctionSpace(mesh, "DG", 0)
    coeff = df.Function(dg0)
    coeff_values = coeff.vector().get_local()
    dofmap = dg0.dofmap()

    def grid_index(x: float, y: float) -> tuple[int, int]:
        col = min(cols - 1, max(0, int((x / width) * cols)))
        row = min(rows - 1, max(0, int((y / height) * rows)))
        return row, col

    for cell in df.cells(mesh):
        midpoint = cell.midpoint()
        row, col = grid_index(float(midpoint.x()), float(midpoint.y()))
        raw = float(grid[row][col])
        if TASK["kind"] == "heat":
            material = TASK["material"]
            value = float(material["base_conductivity"]) + raw * (
                float(material["high_conductivity"]) - float(material["base_conductivity"])
            )
        elif TASK["kind"] == "conductance":
            material = TASK["material"]
            value = float(material["void_conductivity"]) + raw * (
                float(material["conductor_conductivity"]) - float(material["void_conductivity"])
            )
        elif TASK["kind"] == "permeability":
            value = raw
        else:
            raise ValueError("unsupported scalar metric")
        coeff_values[dofmap.cell_dofs(cell.index())[0]] = value
    coeff.vector().set_local(coeff_values)
    coeff.vector().apply("insert")

    V = df.FunctionSpace(mesh, "CG", 1)
    trial = df.TrialFunction(V)
    test = df.TestFunction(V)
    solution = df.Function(V)
    dx = df.dx(domain=mesh)
    tol = 1.0e-10

    def left_boundary(x, on_boundary):
        return on_boundary and abs(x[0]) <= tol

    def right_boundary(x, on_boundary):
        return on_boundary and abs(x[0] - width) <= tol

    if TASK["kind"] == "heat":
        thermal = TASK["thermal"]
        source_row, source_col = thermal["heat_source_cell"]
        heat_power = float(thermal["heat_power"])
        source_area = (width / cols) * (height / rows)
        source_density = heat_power / source_area

        class HeatSource(df.UserExpression):
            def eval(self, values, x):
                row, col = grid_index(float(x[0]), float(x[1]))
                values[0] = source_density if row == source_row and col == source_col else 0.0

            def value_shape(self):
                return ()

        source = HeatSource(degree=0)
        a_form = coeff * df.inner(df.grad(trial), df.grad(test)) * dx
        l_form = source * test * dx
        cold_temp = float(thermal["cold_boundary_temperature"])
        bc = df.DirichletBC(V, df.Constant(cold_temp), left_boundary)
        df.solve(a_form == l_form, solution, bc)
        values = solution.vector().get_local()
        tmax = float(max(values))
        return max(0.0, (tmax - cold_temp) / heat_power)
    if TASK["kind"] == "conductance":
        electrical = TASK["electrical"]
        left_voltage = float(electrical["left_electrode_voltage"])
        right_voltage = float(electrical["right_electrode_voltage"])
        bcs = [
            df.DirichletBC(V, df.Constant(left_voltage), left_boundary),
            df.DirichletBC(V, df.Constant(right_voltage), right_boundary),
        ]
        a_form = coeff * df.inner(df.grad(trial), df.grad(test)) * dx
        l_form = df.Constant(0.0) * test * dx
        df.solve(a_form == l_form, solution, bcs)
        dv = abs(left_voltage - right_voltage)
        energy = float(df.assemble(coeff * df.inner(df.grad(solution), df.grad(solution)) * dx))
        return max(1.0e-12, energy / max(1.0e-12, dv * dv))
    if TASK["kind"] == "permeability":
        flow = TASK["flow"]
        inlet_pressure = float(flow["inlet_pressure"])
        outlet_pressure = float(flow["outlet_pressure"])
        bcs = [
            df.DirichletBC(V, df.Constant(inlet_pressure), left_boundary),
            df.DirichletBC(V, df.Constant(outlet_pressure), right_boundary),
        ]
        a_form = coeff * df.inner(df.grad(trial), df.grad(test)) * dx
        l_form = df.Constant(0.0) * test * dx
        df.solve(a_form == l_form, solution, bcs)
        dp = abs(inlet_pressure - outlet_pressure)
        conductance = float(df.assemble(coeff * df.inner(df.grad(solution), df.grad(solution)) * dx)) / max(1.0e-12, dp * dp)
        return 1.0 / max(1.0e-12, conductance)
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
