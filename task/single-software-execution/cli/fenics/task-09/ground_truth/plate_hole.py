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
from math import hypot
from pathlib import Path
import subprocess

workdir = Path(__file__).resolve().parent
geo_path = workdir / "plate_hole.geo"
msh_path = workdir / "plate_hole.msh"
xml_path = workdir / "plate_hole.xml"
geo_path.write_text(
    """SetFactory("OpenCASCADE");
Rectangle(1) = {0, 0, 0, 100, 200};
Disk(2) = {50, 100, 0, 5, 5};
BooleanDifference{ Surface{1}; Delete; }{ Surface{2}; Delete; }
Mesh.CharacteristicLengthMin = 0.75;
Mesh.CharacteristicLengthMax = 4.0;
Mesh.MeshSizeFromCurvature = 32;
""",
    encoding="utf-8",
)
subprocess.run(
    ["gmsh", "-2", str(geo_path), "-format", "msh2", "-o", str(msh_path)],
    check=True,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
)
subprocess.run(
    ["dolfin-convert", str(msh_path), str(xml_path)],
    check=True,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
)
mesh = Mesh(str(xml_path))
V = VectorFunctionSpace(mesh, "P", 1)
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
mises = project(mises_expr, FunctionSpace(mesh, "DG", 0))
stress_values = mises.vector().get_local()
hole_values = []
far_values = []
for cell in cells(mesh):
    midpoint = cell.midpoint()
    x = midpoint.x()
    y = midpoint.y()
    radius = hypot(x - 50.0, y - 100.0)
    value = stress_values[cell.index()]
    if 5.0 <= radius <= 8.0 and y >= 100.0 and abs(x - 50.0) <= 4.0:
        hole_values.append(value)
    if 20.0 <= x <= 80.0 and (y <= 50.0 or y >= 150.0):
        far_values.append(value)

if not hole_values or not far_values:
    raise RuntimeError("stress sampling regions contain no mesh cells")
hole_mises = max(hole_values)
far_mises = sum(far_values)/len(far_values)
with open("summary.txt", "w", encoding="utf-8") as handle:
    handle.write(f"{hole_mises:.12g}, {far_mises:.12g}\n")
