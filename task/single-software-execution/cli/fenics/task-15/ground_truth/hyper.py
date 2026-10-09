import os
import sys


if os.environ.get("CONDA_DEFAULT_ENV") != "fenics-legacy":
    os.execv(
        "/bin/bash",
        [
            "/bin/bash",
            "-lc",
            'source /home/user/miniconda3/etc/profile.d/conda.sh && '
            'conda activate fenics-legacy && exec python3 "$@"',
            "fenics-legacy",
            *sys.argv,
        ],
    )

from dolfin import *
import numpy as np


mesh = BoxMesh(Point(0, 0, 0), Point(100, 10, 10), 10, 2, 2)
V = VectorFunctionSpace(mesh, "P", 1)
u = Function(V)
v = TestFunction(V)
du = TrialFunction(V)


def left_end(point, on_boundary):
    return on_boundary and near(point[0], 0.0)


def right_end(point, on_boundary):
    return on_boundary and near(point[0], 100.0)


right_displacement = Expression(("load", "0.0", "0.0"), degree=0, load=0.0)
boundary_conditions = [
    DirichletBC(V, Constant((0.0, 0.0, 0.0)), left_end),
    DirichletBC(V, right_displacement, right_end),
]

mu = Constant(80.77)
lmbda = Constant(121.15)
F = variable(Identity(3) + grad(u))
C = F.T * F
J = det(F)
psi = (mu / 2.0) * (tr(C) - 3.0) - mu * ln(J) + (lmbda / 2.0) * ln(J) ** 2
energy = psi * dx
Pi = derivative(energy, u, v)
jacobian = derivative(Pi, u, du)
problem = NonlinearVariationalProblem(Pi, u, boundary_conditions, jacobian)
solver = NonlinearVariationalSolver(problem)
solver.parameters["newton_solver"]["absolute_tolerance"] = 1.0e-9
solver.parameters["newton_solver"]["relative_tolerance"] = 1.0e-8
solver.parameters["newton_solver"]["maximum_iterations"] = 30

for load in (5.0, 10.0, 15.0, 20.0, 25.0, 30.0, 35.0, 40.0, 45.0, 50.0):
    right_displacement.load = load
    solver.solve()

P = diff(psi, F)
facet_markers = MeshFunction("size_t", mesh, mesh.topology().dim() - 1, 0)


class RightFace(SubDomain):
    def inside(self, point, on_boundary):
        return on_boundary and near(point[0], 100.0)


RightFace().mark(facet_markers, 1)
boundary_measure = Measure("ds", domain=mesh, subdomain_data=facet_markers)
reaction_fx = -float(assemble(dot(P, FacetNormal(mesh))[0] * boundary_measure(1)))

green_lagrange = project(
    0.5 * (C - Identity(3)), TensorFunctionSpace(mesh, "DG", 0)
)
max_principal_strain = -float("inf")
for cell in cells(mesh):
    tensor = np.asarray(green_lagrange(cell.midpoint()), dtype=float).reshape((3, 3))
    max_principal_strain = max(max_principal_strain, float(np.linalg.eigvalsh(tensor).max()))

with open("/home/user/Desktop/summary.txt", "w", encoding="utf-8") as handle:
    handle.write(f"{reaction_fx:.16g},{max_principal_strain:.16g}\n")

print(f"reaction_fx={reaction_fx:.16g}")
print(f"max_principal_strain={max_principal_strain:.16g}")
