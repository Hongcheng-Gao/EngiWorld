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

mesh = UnitIntervalMesh(40)
V = FunctionSpace(mesh, 'DG', 1)
u = TrialFunction(V)
v = TestFunction(V)
eps = Constant(0.01)
beta = Constant((1.0,))
n = FacetNormal(mesh)
h = CellDiameter(mesh)
penalty = Constant(40.0)


class Left(SubDomain):
    def inside(self, x, on_boundary):
        return on_boundary and near(x[0], 0.0)


class Right(SubDomain):
    def inside(self, x, on_boundary):
        return on_boundary and near(x[0], 1.0)


boundaries = MeshFunction("size_t", mesh, mesh.topology().dim() - 1, 0)
Left().mark(boundaries, 1)
Right().mark(boundaries, 2)
ds = Measure("ds", domain=mesh, subdomain_data=boundaries)

a = eps*inner(grad(u), grad(v))*dx
a += -eps*inner(avg(grad(u)), jump(v, n))*dS
a += -eps*inner(jump(u, n), avg(grad(v)))*dS
a += eps*penalty/avg(h)*inner(jump(u, n), jump(v, n))*dS

bn = dot(beta, n)
upwind = conditional(gt(dot(beta, n("+")), 0.0), u("+"), u("-"))
a += -u*dot(beta, grad(v))*dx + dot(beta, n("+"))*upwind*jump(v)*dS

a += -eps*dot(grad(u), n)*v*ds - eps*dot(grad(v), n)*u*ds + eps*penalty/h*u*v*ds
L = -eps*dot(grad(v), n)*Constant(1.0)*ds(2) + eps*penalty/h*Constant(1.0)*v*ds(2)
a += bn*u*v*ds(2)

u_sol = Function(V)
solve(a == L, u_sol)
mid_value = 0.5*(u_sol(Point(0.5 - 1.0e-8)) + u_sol(Point(0.5 + 1.0e-8)))
max_value = u_sol.vector().get_local().max()
with open("summary.txt", "w", encoding="utf-8") as handle:
    handle.write(f"{mid_value:.12g}, {max_value:.12g}\n")
