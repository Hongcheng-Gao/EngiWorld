from dolfin import *

mesh = UnitSquareMesh(16, 16)
V = FunctionSpace(mesh, 'P', 1)

u = TrialFunction(V)
v = TestFunction(V)
f = Constant(1.0)

# Error 1: grad(u)*grad(v) should be inner(grad(u), grad(v)).
a = grad(u) * grad(v) * dx
L = f * v * dx

bc = DirichletBC(V, Constant(0.0), lambda x, on_b: on_b)

u_sol = Function(V)
solve(a == L, u_sol, bc)

# Missing requirement 2: only VTK is written; the required fixed_summary.txt is not generated.
vtkfile = File('result.pvd')
vtkfile << u_sol

# Error 3: incorrect call syntax is used to evaluate a point value.
# val = u_sol(0.5, 0.5)
