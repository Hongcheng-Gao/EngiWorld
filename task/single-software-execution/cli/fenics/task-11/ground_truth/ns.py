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


length = 2.2
height = 0.41
mesh = RectangleMesh(Point(0, 0), Point(length, height), 60, 20)
V = VectorFunctionSpace(mesh, "P", 2)
Q = FunctionSpace(mesh, "P", 1)


def inlet(point, on_boundary):
    return on_boundary and near(point[0], 0.0)


def walls(point, on_boundary):
    return on_boundary and (near(point[1], 0.0) or near(point[1], height))


def outlet(point, on_boundary):
    return on_boundary and near(point[0], length)


inlet_profile = Expression(
    ("4.0*U*x[1]*(H-x[1])/(H*H)", "0.0"), degree=2, U=0.3, H=height
)
velocity_bcs = [
    DirichletBC(V, inlet_profile, inlet),
    DirichletBC(V, Constant((0.0, 0.0)), walls),
]
pressure_bcs = [DirichletBC(Q, Constant(0.0), outlet)]

u = TrialFunction(V)
v = TestFunction(V)
p = TrialFunction(Q)
q = TestFunction(Q)
u_n = Function(V)
u_star = Function(V)
u_new = Function(V)
p_n = Function(Q)
p_new = Function(Q)

nu = Constant(0.001)
dt = Constant(0.001)

a1 = (1.0 / dt) * inner(u, v) * dx + nu * inner(grad(u), grad(v)) * dx
L1 = (
    (1.0 / dt) * inner(u_n, v) * dx
    - inner(dot(grad(u_n), u_n), v) * dx
    + p_n * div(v) * dx
)
a2 = inner(grad(p), grad(q)) * dx
L2 = inner(grad(p_n), grad(q)) * dx - (1.0 / dt) * div(u_star) * q * dx
a3 = inner(u, v) * dx
L3 = inner(u_star, v) * dx - dt * inner(grad(p_new - p_n), v) * dx

A2 = assemble(a2)
for condition in pressure_bcs:
    condition.apply(A2)
A3 = assemble(a3)
for condition in velocity_bcs:
    condition.apply(A3)

for _ in range(50):
    A1 = assemble(a1)
    b1 = assemble(L1)
    for condition in velocity_bcs:
        condition.apply(A1, b1)
    solve(A1, u_star.vector(), b1, "bicgstab", "hypre_amg")

    b2 = assemble(L2)
    for condition in pressure_bcs:
        condition.apply(b2)
    solve(A2, p_new.vector(), b2, "bicgstab", "hypre_amg")

    b3 = assemble(L3)
    for condition in velocity_bcs:
        condition.apply(b3)
    solve(A3, u_new.vector(), b3, "cg", "sor")
    u_n.assign(u_new)
    p_n.assign(p_new)

facet_markers = MeshFunction("size_t", mesh, mesh.topology().dim() - 1, 0)


class Outlet(SubDomain):
    def inside(self, point, on_boundary):
        return on_boundary and near(point[0], length)


Outlet().mark(facet_markers, 1)
boundary_measure = Measure("ds", domain=mesh, subdomain_data=facet_markers)
outlet_velocity = float(assemble(u_new[0] * boundary_measure(1)) / height)
speed = project(sqrt(dot(u_new, u_new)), FunctionSpace(mesh, "P", 1))
max_velocity = float(speed.vector().max())

with open("/home/user/Desktop/summary.txt", "w", encoding="utf-8") as handle:
    handle.write(f"{outlet_velocity:.16g},{max_velocity:.16g}\n")

print(f"outlet_velocity={outlet_velocity:.16g}")
print(f"max_velocity={max_velocity:.16g}")
