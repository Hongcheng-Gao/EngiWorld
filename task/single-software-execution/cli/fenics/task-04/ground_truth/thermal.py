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

mesh = RectangleMesh(Point(0, 0), Point(100, 50), 20, 10)
V = FunctionSpace(mesh, "P", 1)
subdomains = MeshFunction("size_t", mesh, 2)
subdomains.set_all(1)


class LeftHalf(SubDomain):
    def inside(self, x, on_boundary):
        return x[0] <= 50.0 + DOLFIN_EPS


LeftHalf().mark(subdomains, 0)
dx_sub = Measure("dx", domain=mesh, subdomain_data=subdomains)

left = DirichletBC(V, Constant(100.0), lambda x, on_boundary: on_boundary and near(x[0], 0.0))
right = DirichletBC(V, Constant(20.0), lambda x, on_boundary: on_boundary and near(x[0], 100.0))

u = TrialFunction(V)
v = TestFunction(V)
a = 50.0*inner(grad(u), grad(v))*dx_sub(0) + 10.0*inner(grad(u), grad(v))*dx_sub(1)
L = Constant(0.0)*v*dx
u_sol = Function(V)
solve(a == L, u_sol, [left, right])

interface_temp = u_sol(Point(50.0, 25.0))
center_temp = u_sol(Point(25.0, 25.0))
with open("summary.txt", "w", encoding="utf-8") as handle:
    handle.write(f"{interface_temp:.12g}, {center_temp:.12g}\n")
