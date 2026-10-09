from dolfin import *

mesh = UnitSquareMesh(32, 32)
V = FunctionSpace(mesh, 'P', 1)

# TODO: Define subdomain markers.
# Left boundary Dirichlet condition: u=0.
# Right boundary Neumann condition: g=4.
# Retain natural zero-flux conditions on the top and bottom boundaries.

u = TrialFunction(V)
v = TestFunction(V)
f = Constant(0.0)

# TODO: Complete a and L, including the ds boundary integral.

u_sol = Function(V)
# solve(a == L, u_sol, bcs)

# Extract the value at x=(1.0, 0.5).
# point_value = u_sol(Point(1.0, 0.5))
