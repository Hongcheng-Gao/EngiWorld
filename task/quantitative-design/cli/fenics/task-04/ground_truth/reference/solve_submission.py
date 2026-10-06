#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import os
from pathlib import Path

import dolfin as df


ROOT = Path(os.environ.get("FENICS_TASK_ROOT", "/home/user/Desktop"))


def read_field(path: Path, rows: int, cols: int) -> list[list[float]]:
    with path.open("r", encoding="utf-8") as handle:
        field = [[float(value) for value in row] for row in csv.reader(handle) if row]
    if len(field) != rows or any(len(row) != cols for row in field):
        raise ValueError(f"permeability field must be {rows} by {cols}")
    return field


def main() -> int:
    spec = json.loads((ROOT / "problem_spec.json").read_text(encoding="utf-8"))
    rows = int(spec["design_grid"]["rows"])
    cols = int(spec["design_grid"]["cols"])
    field = read_field(ROOT / "permeability_field.csv", rows, cols)
    values = [value for row in field for value in row]
    constraints = spec["constraints"]
    if any(
        value < float(constraints["permeability_min"])
        or value > float(constraints["permeability_max"])
        for value in values
    ):
        raise ValueError("permeability outside allowed range")
    budget = spec["design_budget"]
    fraction = sum(value >= float(budget["threshold"]) for value in values) / len(values)
    if fraction > float(budget["max_fraction"]) + 1.0e-12:
        raise ValueError("high-permeability budget exceeded")

    length = float(spec["domain"]["length"])
    height = float(spec["domain"]["height"])
    mesh = df.RectangleMesh(
        df.Point(0.0, 0.0),
        df.Point(length, height),
        int(spec["solver_mesh"]["nx"]),
        int(spec["solver_mesh"]["ny"]),
    )
    coefficient_space = df.FunctionSpace(mesh, "DG", 0)
    permeability = df.Function(coefficient_space)
    coefficient_values = permeability.vector().get_local()
    dofmap = coefficient_space.dofmap()
    for cell in df.cells(mesh):
        midpoint = cell.midpoint()
        col = min(cols - 1, max(0, int(midpoint.x() / length * cols)))
        row = min(rows - 1, max(0, int(midpoint.y() / height * rows)))
        coefficient_values[dofmap.cell_dofs(cell.index())[0]] = field[row][col]
    permeability.vector().set_local(coefficient_values)
    permeability.vector().apply("insert")

    pressure_space = df.FunctionSpace(mesh, "CG", 1)
    trial = df.TrialFunction(pressure_space)
    test = df.TestFunction(pressure_space)
    pressure = df.Function(pressure_space)
    flow = spec["flow"]

    def inlet(point, on_boundary):
        return on_boundary and df.near(point[0], 0.0)

    def outlet(point, on_boundary):
        return on_boundary and df.near(point[0], length)

    inlet_condition = df.DirichletBC(
        pressure_space, df.Constant(float(flow["inlet_pressure"])), inlet
    )
    outlet_condition = df.DirichletBC(
        pressure_space, df.Constant(float(flow["outlet_pressure"])), outlet
    )
    stiffness = permeability * df.inner(df.grad(trial), df.grad(test)) * df.dx(domain=mesh)
    source = df.Constant(0.0) * test * df.dx(domain=mesh)
    df.solve(stiffness == source, pressure, [inlet_condition, outlet_condition])

    pressure_drop = abs(float(flow["inlet_pressure"]) - float(flow["outlet_pressure"]))
    conductance = float(
        df.assemble(permeability * df.inner(df.grad(pressure), df.grad(pressure)) * df.dx(domain=mesh))
    ) / (pressure_drop * pressure_drop)
    hydraulic_resistance = 1.0 / conductance
    pressure.rename("pressure", "porous pressure")
    output = ROOT / "pressure.xdmf"
    with df.XDMFFile(mesh.mpi_comm(), str(output)) as xdmf:
        xdmf.parameters["flush_output"] = True
        xdmf.parameters["functions_share_mesh"] = True
        xdmf.write_checkpoint(pressure, "pressure", 0.0, df.XDMFFile.Encoding.HDF5, False)
    print(f"dolfin={df.__version__}")
    print(f"hydraulic_resistance={hydraulic_resistance:.16g}")
    print(f"wrote={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
