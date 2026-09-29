from pathlib import Path
import json

from mpi4py import MPI
from petsc4py import PETSc
import numpy as np
import ufl

from dolfinx import fem, io, mesh
from dolfinx.fem.petsc import LinearProblem


JOB = "job_a"
TOTAL_FORCE_Y = -100.0
E = 210000.0
NU = 0.3


def solve():
    domain = mesh.create_box(
        MPI.COMM_WORLD,
        [np.array([0.0, 0.0, 0.0]), np.array([100.0, 10.0, 10.0])],
        [20, 2, 2],
        cell_type=mesh.CellType.hexahedron,
    )
    value_shape = (domain.geometry.dim,)
    space = fem.functionspace(domain, ("Lagrange", 1, value_shape))

    fdim = domain.topology.dim - 1
    fixed_facets = mesh.locate_entities_boundary(domain, fdim, lambda x: np.isclose(x[0], 0.0))
    fixed_dofs = fem.locate_dofs_topological(space, fdim, fixed_facets)
    bc = fem.dirichletbc(np.zeros(3, dtype=PETSc.ScalarType), fixed_dofs, space)

    loaded_facets = mesh.locate_entities_boundary(domain, fdim, lambda x: np.isclose(x[0], 100.0))
    facet_values = np.full(len(loaded_facets), 1, dtype=np.int32)
    facet_tags = mesh.meshtags(domain, fdim, loaded_facets, facet_values)
    ds = ufl.Measure("ds", domain=domain, subdomain_data=facet_tags)

    trial = ufl.TrialFunction(space)
    test = ufl.TestFunction(space)
    mu = E / (2.0 * (1.0 + NU))
    lam = E * NU / ((1.0 + NU) * (1.0 - 2.0 * NU))

    def epsilon(displacement):
        return ufl.sym(ufl.grad(displacement))

    def sigma(displacement):
        return lam * ufl.tr(epsilon(displacement)) * ufl.Identity(3) + 2.0 * mu * epsilon(displacement)

    traction = fem.Constant(domain, PETSc.ScalarType((0.0, TOTAL_FORCE_Y / 100.0, 0.0)))
    bilinear = ufl.inner(sigma(trial), epsilon(test)) * ufl.dx
    linear = ufl.dot(traction, test) * ds(1)
    problem = LinearProblem(
        bilinear,
        linear,
        bcs=[bc],
        petsc_options_prefix=JOB,
        petsc_options={"ksp_type": "preonly", "pc_type": "lu"},
    )
    displacement = problem.solve()
    displacement.name = "displacement"
    displacement.x.scatter_forward()

    scalar_space, scalar_map = space.sub(1).collapse()
    coords = scalar_space.tabulate_dof_coordinates()
    tip = np.isclose(coords[:, 0], 100.0)
    tip_uy_local = float(np.mean(displacement.x.array[scalar_map[tip]]))
    tip_uy = domain.comm.allreduce(tip_uy_local, op=MPI.SUM) / domain.comm.size

    stress = sigma(displacement)
    deviator = stress - ufl.tr(stress) * ufl.Identity(3) / 3.0
    mises_expr = ufl.sqrt(1.5 * ufl.inner(deviator, deviator))
    dg0 = fem.functionspace(domain, ("DG", 0))
    mises = fem.Function(dg0, name="von_mises")
    expression = fem.Expression(mises_expr, dg0.element.interpolation_points)
    mises.interpolate(expression)
    max_local = float(np.max(mises.x.array))
    max_mises = domain.comm.allreduce(max_local, op=MPI.MAX)

    with io.XDMFFile(domain.comm, str(Path(__file__).with_name(JOB + ".xdmf")), "w") as output:
        output.write_mesh(domain)
        output.write_function(displacement)
        output.write_function(mises)

    if domain.comm.rank == 0:
        Path(__file__).with_name(JOB + "_metrics.json").write_text(
            json.dumps({"job": JOB, "total_force_y_n": TOTAL_FORCE_Y, "max_mises_mpa": max_mises, "tip_uy_mm": tip_uy}, indent=2) + "\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    solve()
