from dolfin import *
from slepc4py import SLEPc
from petsc4py import PETSc

mesh = RectangleMesh(Point(0, 0), Point(500, 10), 50, 1)
V = VectorFunctionSpace(mesh, 'P', 1)

E = 210000.0
nu = 0.3
rho = 7.85e-9

# TODO: Define clamped boundary conditions.
# TODO: Define sigma for plane stress, and bilinear stiffness a and mass m forms.

# Solve the eigenvalue problem.
# A = assemble(a)
# M = assemble(m)
# Configure SLEPc to request the three smallest eigenvalues.
