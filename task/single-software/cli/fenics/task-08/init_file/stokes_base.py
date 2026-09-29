from dolfin import *

mesh = RectangleMesh(Point(0, 0), Point(2.2, 0.41), 60, 20)

# TODO: Define Taylor-Hood mixed elements.
# P2 velocity + P1 pressure.

# TODO: Define boundary conditions.
# Parabolic inlet velocity, no-slip walls, and natural outlet boundary.

# TODO: Define the variational form.
# a = nu*inner(grad(u), grad(v))*dx - p*div(v)*dx - q*div(u)*dx
# L = inner(f, v)*dx

# Solve the problem and extract the mean outlet pressure.
