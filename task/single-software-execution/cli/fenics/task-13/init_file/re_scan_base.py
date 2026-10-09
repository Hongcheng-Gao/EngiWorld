from dolfin import *

# Parametric template for a lid-driven cavity.
Re = {Re}  # Placeholder.
nu = 1.0 / Re

mesh = UnitSquareMesh(32, 32)
V = VectorFunctionSpace(mesh, 'P', 2)
Q = FunctionSpace(mesh, 'P', 1)

# TODO: Define Taylor-Hood mixed elements.
# TODO: Set lid velocity u=(1,0) and no-slip conditions elsewhere.
# TODO: Solve steady Navier-Stokes flow.
# TODO: Extract centerline velocity.
