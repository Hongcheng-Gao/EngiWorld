from dolfin import *

mesh = BoxMesh(Point(0, 0, 0), Point(100, 10, 10), 20, 2, 2)
V = VectorFunctionSpace(mesh, 'P', 1)

# TODO: Define the fixed left boundary.
# TODO: Define the point force or traction at the right end.

u = TrialFunction(V)
v = TestFunction(V)

# TODO: Define strain epsilon(u) and stress sigma(u).
# E=210000, nu=0.3

a = inner(sigma(u), epsilon(v)) * dx
L = dot(f, v) * dx

u_sol = Function(V)
# solve(a == L, u_sol, bcs)
