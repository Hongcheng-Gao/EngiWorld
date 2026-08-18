import os
import sys


if os.environ.get("CONDA_DEFAULT_ENV") != "fenics-legacy":
    os.execv(
        "/bin/bash",
        [
            "/bin/bash",
            "-lc",
            'source /home/user/miniconda3/etc/profile.d/conda.sh && '
            'conda activate fenics-legacy && exec python3 "$@"',
            "fenics-legacy",
            *sys.argv,
        ],
    )

from dolfin import *


mesh = BoxMesh(Point(0, 0, 0), Point(100, 10, 10), 20, 2, 2)
V = VectorFunctionSpace(mesh, "P", 1)


def left_end(point, on_boundary):
    return on_boundary and near(point[0], 0.0)


class RightEnd(SubDomain):
    def inside(self, point, on_boundary):
        return on_boundary and near(point[0], 100.0)


fixed = DirichletBC(V, Constant((0.0, 0.0, 0.0)), left_end)
facets = MeshFunction("size_t", mesh, mesh.topology().dim() - 1, 0)
RightEnd().mark(facets, 1)
surface_measure = Measure("ds", domain=mesh, subdomain_data=facets)
traction = Constant((0.0, -10.0, 0.0))

E = 210000.0
nu = 0.3


def epsilon(displacement):
    return 0.5 * (grad(displacement) + grad(displacement).T)


def sigma(displacement):
    strain = epsilon(displacement)
    return E / (1.0 + nu) * (
        strain + nu / (1.0 - 2.0 * nu) * tr(strain) * Identity(3)
    )


u = TrialFunction(V)
v = TestFunction(V)
a = inner(sigma(u), epsilon(v)) * dx
L = dot(traction, v) * surface_measure(1)

u_sol = Function(V)
solve(a == L, u_sol, fixed)

tip_uy = float(u_sol(Point(100.0, 10.0, 5.0))[1])
stress = sigma(u_sol)
deviatoric = stress - tr(stress) / 3.0 * Identity(3)
von_mises = project(sqrt(3.0 / 2.0 * inner(deviatoric, deviatoric)), FunctionSpace(mesh, "DG", 0))
max_mises = float(von_mises.vector().max())

with open("/home/user/Desktop/summary.txt", "w", encoding="utf-8") as handle:
    handle.write(f"{tip_uy:.16g},{max_mises:.16g}\n")

print(f"tip_uy={tip_uy:.16g}")
print(f"max_mises={max_mises:.16g}")
