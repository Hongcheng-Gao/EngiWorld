#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import os
from collections import deque
from pathlib import Path

import dolfin as df


ROOT = Path(os.environ.get("FENICS_TASK_ROOT", "/home/user/Desktop"))


def read_mask(path: Path, rows: int, cols: int) -> list[list[float]]:
    with path.open("r", encoding="utf-8") as handle:
        mask = [[float(value) for value in row] for row in csv.reader(handle) if row]
    if len(mask) != rows or any(len(row) != cols for row in mask):
        raise ValueError(f"conductive mask must be {rows} by {cols}")
    return mask


def connected_left_to_right(mask: list[list[float]], threshold: float) -> bool:
    rows, cols = len(mask), len(mask[0])
    pending = deque((row, 0) for row in range(rows) if mask[row][0] >= threshold)
    visited = set(pending)
    while pending:
        row, col = pending.popleft()
        if col == cols - 1:
            return True
        for drow, dcol in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            neighbor = (row + drow, col + dcol)
            if (
                0 <= neighbor[0] < rows
                and 0 <= neighbor[1] < cols
                and neighbor not in visited
                and mask[neighbor[0]][neighbor[1]] >= threshold
            ):
                visited.add(neighbor)
                pending.append(neighbor)
    return False


def main() -> int:
    spec = json.loads((ROOT / "problem_spec.json").read_text(encoding="utf-8"))
    rows = int(spec["design_grid"]["rows"])
    cols = int(spec["design_grid"]["cols"])
    mask = read_mask(ROOT / "conductive_mask.csv", rows, cols)
    values = [value for row in mask for value in row]
    if any(value < 0.0 or value > 1.0 for value in values):
        raise ValueError("mask values must be in [0, 1]")
    budget = spec["design_budget"]
    threshold = float(budget["threshold"])
    fraction = sum(value >= threshold for value in values) / len(values)
    if fraction > float(budget["max_fraction"]) + 1.0e-12:
        raise ValueError("conductive material budget exceeded")
    if any(mask[int(row)][int(col)] > 1.0e-9 for row, col in spec["keepout_cells"]):
        raise ValueError("keepout violation")
    if not connected_left_to_right(mask, threshold):
        raise ValueError("electrodes disconnected")

    width = float(spec["domain"]["width"])
    height = float(spec["domain"]["height"])
    mesh = df.RectangleMesh(
        df.Point(0.0, 0.0),
        df.Point(width, height),
        int(spec["solver_mesh"]["nx"]),
        int(spec["solver_mesh"]["ny"]),
    )

    coefficient_space = df.FunctionSpace(mesh, "DG", 0)
    conductivity = df.Function(coefficient_space)
    coefficient_values = conductivity.vector().get_local()
    dofmap = coefficient_space.dofmap()
    material = spec["material"]
    low = float(material["void_conductivity"])
    high = float(material["conductor_conductivity"])
    for cell in df.cells(mesh):
        midpoint = cell.midpoint()
        col = min(cols - 1, max(0, int(midpoint.x() / width * cols)))
        row = min(rows - 1, max(0, int(midpoint.y() / height * rows)))
        coefficient_values[dofmap.cell_dofs(cell.index())[0]] = low + mask[row][col] * (high - low)
    conductivity.vector().set_local(coefficient_values)
    conductivity.vector().apply("insert")

    potential_space = df.FunctionSpace(mesh, "CG", 1)
    trial = df.TrialFunction(potential_space)
    test = df.TestFunction(potential_space)
    potential = df.Function(potential_space)
    electrical = spec["electrical"]

    def left_boundary(point, on_boundary):
        return on_boundary and df.near(point[0], 0.0)

    def right_boundary(point, on_boundary):
        return on_boundary and df.near(point[0], width)

    left = df.DirichletBC(
        potential_space, df.Constant(float(electrical["left_electrode_voltage"])), left_boundary
    )
    right = df.DirichletBC(
        potential_space, df.Constant(float(electrical["right_electrode_voltage"])), right_boundary
    )
    stiffness = conductivity * df.inner(df.grad(trial), df.grad(test)) * df.dx(domain=mesh)
    source = df.Constant(0.0) * test * df.dx(domain=mesh)
    df.solve(stiffness == source, potential, [left, right])

    voltage_difference = abs(
        float(electrical["left_electrode_voltage"]) - float(electrical["right_electrode_voltage"])
    )
    effective_conductance = float(
        df.assemble(conductivity * df.inner(df.grad(potential), df.grad(potential)) * df.dx(domain=mesh))
    ) / (voltage_difference * voltage_difference)
    potential.rename("potential", "electrostatic potential")
    output = ROOT / "potential.xdmf"
    with df.XDMFFile(mesh.mpi_comm(), str(output)) as xdmf:
        xdmf.parameters["flush_output"] = True
        xdmf.parameters["functions_share_mesh"] = True
        xdmf.write_checkpoint(potential, "potential", 0.0, df.XDMFFile.Encoding.HDF5, False)
    print(f"dolfin={df.__version__}")
    print(f"effective_conductance={effective_conductance:.16g}")
    print(f"wrote={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
