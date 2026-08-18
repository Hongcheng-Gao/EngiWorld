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
from slepc4py import SLEPc
from petsc4py import PETSc
from math import pi, sqrt

mesh = RectangleMesh(Point(0, 0), Point(500, 10), 50, 1)
V = VectorFunctionSpace(mesh, "P", 2)
E = 210000.0
nu = 0.3
rho = 7.85e-9
mu = E/(2.0*(1.0 + nu))
lam = E*nu/(1.0 - nu**2)


def epsilon(w):
    return sym(grad(w))


def sigma(w):
    return 2.0*mu*epsilon(w) + lam*tr(epsilon(w))*Identity(2)


bc = DirichletBC(V, Constant((0.0, 0.0)), lambda x, on_boundary: on_boundary and near(x[0], 0.0))
u = TrialFunction(V)
v = TestFunction(V)
a = inner(sigma(u), epsilon(v))*dx
m = rho*inner(u, v)*dx
A = as_backend_type(assemble(a)).mat()
M = as_backend_type(assemble(m)).mat()

fixed = set(bc.get_boundary_values())
free = [i for i in range(V.dim()) if i not in fixed]
index_set = PETSc.IS().createGeneral(free)
A_free = A.createSubMatrix(index_set, index_set)
M_free = M.createSubMatrix(index_set, index_set)

solver = SLEPc.EPS().create()
solver.setOperators(A_free, M_free)
solver.setProblemType(SLEPc.EPS.ProblemType.GHEP)
solver.setType(SLEPc.EPS.Type.LAPACK)
solver.setWhichEigenpairs(SLEPc.EPS.Which.SMALLEST_REAL)
solver.setDimensions(nev=6)
solver.setTolerances(tol=1.0e-10, max_it=1000)
solver.solve()

values = []
for i in range(solver.getConverged()):
    eigenvalue = solver.getEigenvalue(i).real
    if eigenvalue > 0.0:
        values.append(sqrt(eigenvalue)/(2.0*pi))
frequencies = sorted(values)[:3]
if len(frequencies) != 3:
    raise RuntimeError("fewer than three positive eigenvalues converged")

with open("summary.txt", "w", encoding="utf-8") as handle:
    handle.write(", ".join(f"{value:.12g}" for value in frequencies) + "\n")
