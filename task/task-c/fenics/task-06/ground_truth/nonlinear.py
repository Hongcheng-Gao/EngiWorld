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
bc = DirichletBC(V, Constant(0.0), lambda x, on_boundary: on_boundary)
u = Function(V)
v = TestFunction(V)
f = Constant(1.0)
F = (1 + u**2)*inner(grad(u), grad(v))*dx - f*v*dx
J = derivative(F, u)

problem = NonlinearVariationalProblem(F, u, bc, J)
solver = NonlinearVariationalSolver(problem)
solver.parameters["newton_solver"]["relative_tolerance"] = 1e-6
solver.solve()

center_value = u(Point(0.5, 0.5))
max_value = u.vector().get_local().max()
with open("summary.txt", "w", encoding="utf-8") as handle:
    handle.write(f"{center_value:.12g}, {max_value:.12g}\n")
