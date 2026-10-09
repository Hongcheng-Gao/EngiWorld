from dolfin import *

mesh = UnitIntervalMesh(40)
V = FunctionSpace(mesh, 'DG', 1)  # Discontinuous Galerkin.

# TODO: Define the convection-diffusion variational form, including numerical fluxes.
# Equation: -eps*u'' + beta*u' = 0, eps=0.01, beta=1.
# Left endpoint: u=0; right endpoint: u=1.

u = TrialFunction(V)
v = TestFunction(V)

# TODO: Define interior-face fluxes using averages and jumps.
# TODO: Impose boundary conditions weakly.
