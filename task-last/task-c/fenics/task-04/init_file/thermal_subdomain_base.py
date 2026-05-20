from dolfin import *

mesh = RectangleMesh(Point(0, 0), Point(100, 50), 20, 10)
V = FunctionSpace(mesh, 'P', 1)

# TODO: 定义两个子域
# 左半部分 (0<=x<=50): k=50
# 右半部分 (50<x<=100): k=10

# TODO: 定义边界条件
# 左端 100°C，右端 20°C

u = TrialFunction(V)
v = TestFunction(V)

# TODO: a = k * inner(grad(u), grad(v)) * dx，k 随子域变化

u_sol = Function(V)
# solve(...)
