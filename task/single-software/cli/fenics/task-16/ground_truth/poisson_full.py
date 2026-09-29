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
import math


mesh = UnitSquareMesh(64, 64)
V = FunctionSpace(mesh, "P", 1)
u = TrialFunction(V)
v = TestFunction(V)
f = Expression("sin(pi*x[0])*sin(pi*x[1])", degree=6, pi=math.pi)
bc = DirichletBC(V, Constant(0.0), lambda point, on_boundary: on_boundary)
a = inner(grad(u), grad(v)) * dx
L = f * v * dx
u_sol = Function(V)
solve(a == L, u_sol, bc)

exact = Expression(
    "sin(pi*x[0])*sin(pi*x[1])/(2*pi*pi)", degree=6, pi=math.pi
)
error_L2 = float(errornorm(exact, u_sol, norm_type="L2", degree_rise=3))
max_nodal_value = float(u_sol.vector().max())

with open("/home/user/Desktop/summary.txt", "w", encoding="utf-8") as handle:
    handle.write(f"{error_L2:.16g},{max_nodal_value:.16g}\n")

print(f"error_L2={error_L2:.16g}")
print(f"max_nodal_value={max_nodal_value:.16g}")
