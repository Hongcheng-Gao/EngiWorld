#!/usr/bin/env python3
from __future__ import annotations

import csv
import math
import os
import re
from pathlib import Path


ROOT = Path(os.environ.get("EVAL_ROOT", "/home/user/Desktop"))

TASK = {
    "grid_shape": [10, 20],
    "max_volume_fraction": 0.4,
    "domain": {"length": 2.0, "height": 1.0},
    "solver_mesh": {"nx": 40, "ny": 20},
    "material": {
        "young_modulus": 1.0,
        "minimum_young_modulus": 0.001,
        "poisson_ratio": 0.3,
        "simp_penalty": 3.0,
    },
    "load": {
        "patch_center_y": 0.5,
        "patch_height": 0.2,
        "total_force_x": 0.0,
        "total_force_y": -1.0,
    },
}

EXPECTED_BASELINE_GRID = [[0.35 for _ in range(20)] for _ in range(10)]
FENICS_MARKERS = (
    "fenics",
    "dolfin",
    "dolfinx",
    "ufl",
    "functionspace",
    "vectorfunctionspace",
    "linearvariationalproblem",
)


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
    expected_rows, expected_cols = TASK["grid_shape"]
    if len(rows) != expected_rows or any(len(row) != expected_cols for row in rows):
        raise ValueError("wrong density grid shape")
    return rows


def flatten(grid: list[list[float]]) -> list[float]:
    return [value for row in grid for value in row]


def validate_density(grid: list[list[float]]) -> None:
    values = flatten(grid)
    if any((not math.isfinite(value)) or value < 0.0 or value > 1.0 for value in values):
        raise ValueError("density outside [0, 1]")
    if sum(values) / len(values) > TASK["max_volume_fraction"]:
        raise ValueError("density design budget exceeded")


def assert_baseline_is_unchanged(grid: list[list[float]]) -> None:
    for actual_row, expected_row in zip(grid, EXPECTED_BASELINE_GRID):
        for actual, expected in zip(actual_row, expected_row):
            if abs(actual - expected) > 1.0e-9:
                raise ValueError("baseline density file was modified")


def check_submission_artifacts() -> None:
    solve_script = ROOT / "solve_submission.py"
    xdmf_path = ROOT / "displacement.xdmf"
    if not solve_script.exists() or not solve_script.is_file() or solve_script.stat().st_size <= 0:
        raise ValueError("missing solve_submission.py")
    script_text = solve_script.read_text(encoding="utf-8", errors="ignore").lower()
    if not any(marker in script_text for marker in FENICS_MARKERS):
        raise ValueError("solve_submission.py does not show a FEniCS workflow")
    if not xdmf_path.exists() or not xdmf_path.is_file() or xdmf_path.stat().st_size <= 0:
        raise ValueError("missing displacement.xdmf")
    xdmf_text = xdmf_path.read_text(encoding="utf-8", errors="ignore")
    for raw_ref in re.findall(r"[^\"'<>\s]+\.h5", xdmf_text):
        ref_path = Path(raw_ref)
        candidates = [xdmf_path.parent / ref_path, xdmf_path.parent / ref_path.name]
        if not any(candidate.exists() and candidate.stat().st_size > 0 for candidate in candidates):
            raise ValueError(f"missing XDMF companion file: {ref_path.name}")


def cell_density(grid: list[list[float]], x: float, y: float) -> float:
    rows, cols = TASK["grid_shape"]
    length = TASK["domain"]["length"]
    height = TASK["domain"]["height"]
    col = min(cols - 1, max(0, int((x / length) * cols)))
    row = min(rows - 1, max(0, int((y / height) * rows)))
    return grid[row][col]


def solve_compliance_with_dolfin(grid: list[list[float]]) -> float:
    try:
        import dolfin as df
    except Exception as exc:  # pragma: no cover - depends on VM solver image
        raise RuntimeError("dolfin is required for this evaluator") from exc

    length = TASK["domain"]["length"]
    height = TASK["domain"]["height"]
    nx = TASK["solver_mesh"]["nx"]
    ny = TASK["solver_mesh"]["ny"]
    mesh = df.RectangleMesh(df.Point(0.0, 0.0), df.Point(length, height), nx, ny, "right")

    vector_space = df.VectorFunctionSpace(mesh, "Lagrange", 1)
    dg0 = df.FunctionSpace(mesh, "DG", 0)
    rho = df.Function(dg0)
    rho_values = rho.vector().get_local()
    dofmap = dg0.dofmap()
    for cell in df.cells(mesh):
        midpoint = cell.midpoint()
        dof = dofmap.cell_dofs(cell.index())[0]
        rho_values[dof] = cell_density(grid, midpoint.x(), midpoint.y())
    rho.vector().set_local(rho_values)
    rho.vector().apply("insert")

    mat = TASK["material"]
    young = mat["minimum_young_modulus"] + (rho ** mat["simp_penalty"]) * (
        mat["young_modulus"] - mat["minimum_young_modulus"]
    )
    nu = mat["poisson_ratio"]
    mu = young / (2.0 * (1.0 + nu))
    lmbda = young * nu / ((1.0 + nu) * (1.0 - 2.0 * nu))

    def eps(u):
        return df.sym(df.grad(u))

    def sigma(u):
        return lmbda * df.tr(eps(u)) * df.Identity(2) + 2.0 * mu * eps(u)

    class FixedLeft(df.SubDomain):
        def inside(self, x, on_boundary):
            return on_boundary and df.near(x[0], 0.0)

    class LoadPatch(df.SubDomain):
        def inside(self, x, on_boundary):
            center = TASK["load"]["patch_center_y"]
            half_height = TASK["load"]["patch_height"] / 2.0
            return (
                on_boundary
                and df.near(x[0], length)
                and center - half_height - df.DOLFIN_EPS <= x[1] <= center + half_height + df.DOLFIN_EPS
            )

    boundary_markers = df.MeshFunction("size_t", mesh, mesh.topology().dim() - 1, 0)
    LoadPatch().mark(boundary_markers, 1)
    ds = df.Measure("ds", domain=mesh, subdomain_data=boundary_markers)

    u = df.TrialFunction(vector_space)
    v = df.TestFunction(vector_space)
    solution = df.Function(vector_space)
    bc = df.DirichletBC(vector_space, df.Constant((0.0, 0.0)), FixedLeft())

    patch_height = TASK["load"]["patch_height"]
    traction = df.Constant(
        (
            TASK["load"]["total_force_x"] / patch_height,
            TASK["load"]["total_force_y"] / patch_height,
        )
    )
    a = df.inner(sigma(u), eps(v)) * df.dx
    load_form = df.dot(traction, v) * ds(1)
    df.solve(a == load_form, solution, bc)

    compliance = abs(float(df.assemble(df.dot(traction, solution) * ds(1))))
    if not math.isfinite(compliance) or compliance <= 0:
        raise ValueError("invalid compliance")
    return compliance


def solve_compliance(grid: list[list[float]]) -> float:
    return solve_compliance_with_dolfin(grid)


def score_from_metrics(submitted_compliance: float, baseline_compliance: float) -> float:
    if baseline_compliance <= 0 or not math.isfinite(baseline_compliance):
        return 0.0
    if submitted_compliance < 0 or not math.isfinite(submitted_compliance):
        return 0.0
    return clamp(1.0 - submitted_compliance / baseline_compliance)


def evaluate() -> float:
    check_submission_artifacts()

    baseline_grid = read_grid(ROOT / "baseline_density_field.csv")
    assert_baseline_is_unchanged(baseline_grid)
    validate_density(baseline_grid)

    submitted_grid = read_grid(ROOT / "density_field.csv")
    validate_density(submitted_grid)

    baseline_compliance = solve_compliance(baseline_grid)
    submitted_compliance = solve_compliance(submitted_grid)
    return score_from_metrics(submitted_compliance, baseline_compliance)


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
