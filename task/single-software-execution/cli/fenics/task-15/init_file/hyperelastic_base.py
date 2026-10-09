from dolfin import *

mesh = BoxMesh(Point(0, 0, 0), Point(100, 10, 10), 10, 2, 2)
V = VectorFunctionSpace(mesh, 'P', 1)

# TODO: Define a Neo-Hookean hyperelastic material.
# I1 = tr(C), J = det(F), C = F.T*F
# psi = mu/2*(I1-3) - mu*ln(J) + lambd/2*(ln(J))^2

# TODO: Define first Piola-Kirchhoff stress P = diff(psi, F).
# Alternatively, use the variational form Pi = inner(P, grad(v))*dx.

u = Function(V)
v = TestFunction(V)

# Boundary conditions: fixed left end, 50% extension at the right end.
