from dolfin import *

mesh = BoxMesh(Point(0, 0, 0), Point(100, 10, 10), 20, 2, 2)
V = VectorFunctionSpace(mesh, 'P', 1)

# TODO: 定义左端固定边界
# TODO: 定义右端集中力或面力

u = TrialFunction(V)
v = TestFunction(V)

# TODO: 定义应变 epsilon(u) 和应力 sigma(u)
# E=210000, nu=0.3

a = inner(sigma(u), epsilon(v)) * dx
L = dot(f, v) * dx

u_sol = Function(V)
# solve(a == L, u_sol, bcs)
