import os
import subprocess
import sys

import numpy as np


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

geo_source = """
SetFactory("OpenCASCADE");
Rectangle(1) = {0, 0, 0, 100, 200};
Disk(2) = {50, 100, 0, 5, 5};
BooleanDifference{ Surface{1}; Delete; }{ Surface{2}; Delete; }
Mesh.CharacteristicLengthMin = 0.25;
Mesh.CharacteristicLengthMax = 2.0;
"""
with open("plate_hole.geo", "w", encoding="utf-8") as handle:
    handle.write(geo_source)
subprocess.run(
    ["gmsh", "-2", "plate_hole.geo", "-format", "msh2", "-o", "plate_hole.msh"],
    check=True,
)
subprocess.run(["dolfin-convert", "plate_hole.msh", "plate_hole.xml"], check=True)
mesh = Mesh("plate_hole.xml")
V = VectorFunctionSpace(mesh, "P", 2)
E = 210000.0
nu = 0.3
mu = E/(2.0*(1.0 + nu))
lam = E*nu/(1.0 - nu**2)


def epsilon(w):
    return sym(grad(w))


def sigma(w):
    return 2.0*mu*epsilon(w) + lam*tr(epsilon(w))*Identity(2)


left = DirichletBC(V.sub(0), Constant(0.0), lambda x, on_boundary: on_boundary and near(x[0], 0.0))
right = DirichletBC(
    V.sub(0),
    Constant(100.0*10.0/E),
    lambda x, on_boundary: on_boundary and near(x[0], 100.0),
)
anchor = DirichletBC(
    V.sub(1),
    Constant(0.0),
    lambda x, on_boundary: near(x[0], 0.0) and near(x[1], 0.0),
    method="pointwise",
)

u = TrialFunction(V)
v = TestFunction(V)
a = inner(sigma(u), epsilon(v))*dx
L = dot(Constant((0.0, 0.0)), v)*dx
u_sol = Function(V)
solve(a == L, u_sol, [left, right, anchor])

stress = sigma(u_sol)
mises_expr = sqrt(
    stress[0, 0]**2
    - stress[0, 0]*stress[1, 1]
    + stress[1, 1]**2
    + 3.0*stress[0, 1]**2
)
mises_space = FunctionSpace(mesh, "P", 1)
mises = project(mises_expr, mises_space)
coordinates = mises_space.tabulate_dof_coordinates().reshape((-1, 2))
values = mises.vector().get_local()
radius = np.sqrt((coordinates[:, 0] - 50.0)**2 + (coordinates[:, 1] - 100.0)**2)
top_region = (
    (radius <= 8.0)
    & (coordinates[:, 1] >= 100.0)
    & (np.abs(coordinates[:, 0] - 50.0) <= 3.0)
)
hole_mises = float(values[top_region].max())
far_mises = mises(Point(50.0, 25.0))
with open("summary.txt", "w", encoding="utf-8") as handle:
    handle.write(f"{hole_mises:.12g}, {far_mises:.12g}\n")
