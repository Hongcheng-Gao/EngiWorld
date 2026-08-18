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

mesh = UnitSquareMesh(32, 32)
V = FunctionSpace(mesh, "P", 1)
u_D = Expression("1 + x[0]*x[0] + 2*x[1]*x[1]", degree=2, domain=mesh)
bc = DirichletBC(V, u_D, lambda x, on_boundary: on_boundary)

u = TrialFunction(V)
v = TestFunction(V)
f = Constant(-6.0)
a = inner(grad(u), grad(v))*dx
L = f*v*dx

u = Function(V)
solve(a == L, u, bc)
error_L2 = sqrt(assemble((u - u_D)**2 * dx))
error_H1 = sqrt(assemble(inner(grad(u - u_D), grad(u - u_D)) * dx))

with open("summary.txt", "w", encoding="utf-8") as handle:
    handle.write(f"{error_L2:.12g}, {error_H1:.12g}\n")
