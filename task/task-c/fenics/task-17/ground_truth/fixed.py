from pathlib import Path

from dolfin import *


mesh = UnitSquareMesh(16, 16)
V = FunctionSpace(mesh, "P", 1)

u = TrialFunction(V)
v = TestFunction(V)
f = Constant(1.0)

a = inner(grad(u), grad(v)) * dx
L = f * v * dx
bc = DirichletBC(V, Constant(0.0), lambda x, on_b: on_b)

u_sol = Function(V)
solve(a == L, u_sol, bc)

vtkfile = File(str(Path(__file__).with_name("result.pvd")))
vtkfile << u_sol

center_value = float(u_sol(Point(0.5, 0.5)))
max_value = float(u_sol.vector().get_local().max())
Path(__file__).with_name("fixed_summary.txt").write_text(
    f"{center_value:.12g},{max_value:.12g}\n",
    encoding="utf-8",
)
