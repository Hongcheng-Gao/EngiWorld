#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import os
from pathlib import Path

import dolfin as df


ROOT = Path(os.environ.get("FENICS_TASK_ROOT", "/home/user/Desktop"))


def read_mask(path: Path, rows: int, cols: int) -> list[list[float]]:
    with path.open("r", encoding="utf-8") as handle:
        mask = [[float(value) for value in row] for row in csv.reader(handle) if row]
    if len(mask) != rows or any(len(row) != cols for row in mask):
        raise ValueError(f"conductivity mask must be {rows} by {cols}")
    return mask


def main() -> int:
    spec = json.loads((ROOT / "problem_spec.json").read_text(encoding="utf-8"))
    rows = int(spec["design_grid"]["rows"])
    cols = int(spec["design_grid"]["cols"])
    mask = read_mask(ROOT / "conductivity_mask.csv", rows, cols)
    values = [value for row in mask for value in row]
    if any(value < 0.0 or value > 1.0 for value in values):
        raise ValueError("mask values must be in [0, 1]")
    budget = spec["design_budget"]
    fraction = sum(value >= float(budget["threshold"]) for value in values) / len(values)
    if fraction > float(budget["max_fraction"]) + 1.0e-12:
        raise ValueError("high-conductivity material budget exceeded")

    width = float(spec["domain"]["width"])
    height = float(spec["domain"]["height"])
    mesh = df.RectangleMesh(
        df.Point(0.0, 0.0),
        df.Point(width, height),
        int(spec["solver_mesh"]["nx"]),
        int(spec["solver_mesh"]["ny"]),
    )

    def grid_index(x: float, y: float) -> tuple[int, int]:
        col = min(cols - 1, max(0, int(x / width * cols)))
        row = min(rows - 1, max(0, int(y / height * rows)))
        return row, col

    coefficient_space = df.FunctionSpace(mesh, "DG", 0)
    conductivity = df.Function(coefficient_space)
    coefficient_values = conductivity.vector().get_local()
    dofmap = coefficient_space.dofmap()
    base = float(spec["material"]["base_conductivity"])
    high = float(spec["material"]["high_conductivity"])
    for cell in df.cells(mesh):
        midpoint = cell.midpoint()
        row, col = grid_index(midpoint.x(), midpoint.y())
        coefficient_values[dofmap.cell_dofs(cell.index())[0]] = base + mask[row][col] * (high - base)
    conductivity.vector().set_local(coefficient_values)
    conductivity.vector().apply("insert")

    thermal = spec["thermal"]
    source_row, source_col = map(int, thermal["heat_source_cell"])
    heat_power = float(thermal["heat_power"])
    source_area = width / cols * height / rows
    source_density = heat_power / source_area

    class HeatSource(df.UserExpression):
        def eval(self, result, point):
            row, col = grid_index(float(point[0]), float(point[1]))
            result[0] = source_density if (row, col) == (source_row, source_col) else 0.0

        def value_shape(self):
            return ()

    temperature_space = df.FunctionSpace(mesh, "CG", 1)
    trial = df.TrialFunction(temperature_space)
    test = df.TestFunction(temperature_space)
    temperature = df.Function(temperature_space)

    def cold_boundary(point, on_boundary):
        return on_boundary and df.near(point[0], 0.0)

    cold_value = float(thermal["cold_boundary_temperature"])
    cold = df.DirichletBC(temperature_space, df.Constant(cold_value), cold_boundary)
    stiffness = conductivity * df.inner(df.grad(trial), df.grad(test)) * df.dx(domain=mesh)
    source = HeatSource(degree=0) * test * df.dx(domain=mesh)
    df.solve(stiffness == source, temperature, cold)

    thermal_resistance = (max(temperature.vector().get_local()) - cold_value) / heat_power
    temperature.rename("temperature", "steady temperature")
    output = ROOT / "temperature.xdmf"
    with df.XDMFFile(mesh.mpi_comm(), str(output)) as xdmf:
        xdmf.parameters["flush_output"] = True
        xdmf.parameters["functions_share_mesh"] = True
        xdmf.write_checkpoint(
            temperature,
            "temperature",
            0.0,
            df.XDMFFile.Encoding.HDF5,
            False,
        )
    print(f"dolfin={df.__version__}")
    print(f"thermal_resistance={thermal_resistance:.16g}")
    print(f"wrote={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
