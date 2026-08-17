from dolfin import *
from mshr import Rectangle, Circle, generate_mesh
from math import sqrt

domain = Rectangle(Point(0, 0), Point(100, 200)) - Circle(Point(50, 100), 5)
mesh = generate_mesh(domain, 30)
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
mises = project(mises_expr, FunctionSpace(mesh, "P", 1))
hole_mises = mises(Point(50.0, 105.5))
far_mises = mises(Point(50.0, 25.0))
with open("summary.txt", "w", encoding="utf-8") as handle:
    handle.write(f"{hole_mises:.12g}, {far_mises:.12g}\n")
