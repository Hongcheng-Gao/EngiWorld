#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import os
from pathlib import Path

import dolfin as df


ROOT = Path(os.environ.get("FENICS_TASK_ROOT", "/home/user/Desktop"))


def read_density(path: Path, rows: int, cols: int) -> list[list[float]]:
    with path.open("r", encoding="utf-8") as handle:
        grid = [[float(value) for value in row] for row in csv.reader(handle) if row]
    if len(grid) != rows or any(len(row) != cols for row in grid):
        raise ValueError(f"density field must be {rows} by {cols}")
    return grid


def main() -> int:
    spec = json.loads((ROOT / "problem_spec.json").read_text(encoding="utf-8"))
    rows = int(spec["design_grid"]["rows"])
    cols = int(spec["design_grid"]["cols"])
    density = read_density(ROOT / "density_field.csv", rows, cols)
    budget = float(spec["design_budget"]["max_mean_density"])
    values = [value for row in density for value in row]
    if any(value < 0.0 or value > 1.0 for value in values):
        raise ValueError("density values must be in [0, 1]")
    if sum(values) / len(values) > budget + 1.0e-12:
        raise ValueError("density budget exceeded")

    length = float(spec["domain"]["length"])
    height = float(spec["domain"]["height"])
    nx = int(spec["solver_mesh"]["nx"])
    ny = int(spec["solver_mesh"]["ny"])
    mesh = df.RectangleMesh(df.Point(0.0, 0.0), df.Point(length, height), nx, ny, "right")
    vector_space = df.VectorFunctionSpace(mesh, "Lagrange", 1)
    density_space = df.FunctionSpace(mesh, "DG", 0)

    rho = df.Function(density_space)
    rho_values = rho.vector().get_local()
    dofmap = density_space.dofmap()
    for cell in df.cells(mesh):
        midpoint = cell.midpoint()
        col = min(cols - 1, max(0, int(midpoint.x() / length * cols)))
        row = min(rows - 1, max(0, int(midpoint.y() / height * rows)))
        rho_values[dofmap.cell_dofs(cell.index())[0]] = density[row][col]
    rho.vector().set_local(rho_values)
    rho.vector().apply("insert")

    material = spec["material"]
    young = float(material["minimum_young_modulus"]) + rho ** float(material["simp_penalty"]) * (
        float(material["young_modulus"]) - float(material["minimum_young_modulus"])
    )
    nu = float(material["poisson_ratio"])
    mu = young / (2.0 * (1.0 + nu))
    lmbda = young * nu / ((1.0 + nu) * (1.0 - 2.0 * nu))

    def epsilon(field):
        return df.sym(df.grad(field))

    def sigma(field):
        return lmbda * df.tr(epsilon(field)) * df.Identity(2) + 2.0 * mu * epsilon(field)

    class FixedLeft(df.SubDomain):
        def inside(self, point, on_boundary):
            return on_boundary and df.near(point[0], 0.0)

    load = spec["load"]
    center_y = float(load["patch_center_y"])
    patch_height = float(load["patch_height"])

    class LoadPatch(df.SubDomain):
        def inside(self, point, on_boundary):
            return (
                on_boundary
                and df.near(point[0], length)
                and center_y - patch_height / 2.0 - df.DOLFIN_EPS
                <= point[1]
                <= center_y + patch_height / 2.0 + df.DOLFIN_EPS
            )

    markers = df.MeshFunction("size_t", mesh, mesh.topology().dim() - 1, 0)
    LoadPatch().mark(markers, 1)
    boundary_measure = df.Measure("ds", domain=mesh, subdomain_data=markers)
    traction = df.Constant(
        (
            float(load["total_force_x"]) / patch_height,
            float(load["total_force_y"]) / patch_height,
        )
    )

    trial = df.TrialFunction(vector_space)
    test = df.TestFunction(vector_space)
    displacement = df.Function(vector_space)
    fixed = df.DirichletBC(vector_space, df.Constant((0.0, 0.0)), FixedLeft())
    stiffness = df.inner(sigma(trial), epsilon(test)) * df.dx
    force = df.dot(traction, test) * boundary_measure(1)
    df.solve(stiffness == force, displacement, fixed)

    compliance = abs(float(df.assemble(df.dot(traction, displacement) * boundary_measure(1))))
    displacement.rename("displacement", "2D cantilever displacement")
    output = ROOT / "displacement.xdmf"
    with df.XDMFFile(mesh.mpi_comm(), str(output)) as xdmf:
        xdmf.parameters["flush_output"] = True
        xdmf.parameters["functions_share_mesh"] = True
        xdmf.write_checkpoint(
            displacement,
            "displacement",
            0.0,
            df.XDMFFile.Encoding.HDF5,
            False,
        )
    print(f"dolfin={df.__version__}")
    print(f"compliance={compliance:.16g}")
    print(f"wrote={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
