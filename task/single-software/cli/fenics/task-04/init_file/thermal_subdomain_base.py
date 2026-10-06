from dolfin import *

mesh = RectangleMesh(Point(0, 0), Point(100, 50), 20, 10)
V = FunctionSpace(mesh, 'P', 1)

# TODO: Define two subdomains.
# Left half (0<=x<=50): k=50.
# Right half (50<x<=100): k=10.

# TODO: Define boundary conditions.
# Left boundary: 100 degrees C; right boundary: 20 degrees C.

u = TrialFunction(V)
v = TestFunction(V)

# TODO: a = k * inner(grad(u), grad(v)) * dx, with k varying by subdomain.

u_sol = Function(V)
# solve(...)
