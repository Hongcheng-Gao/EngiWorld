from dolfin import *

mesh = UnitSquareMesh(8, 8)
V = FunctionSpace(mesh, 'P', 1)

u_D = Expression('exp(-100*(pow(x[0]-0.5, 2) + pow(x[1]-0.5, 2)))', degree=2)
bc = DirichletBC(V, u_D, lambda x, on_b: on_b)

u = TrialFunction(V)
v = TestFunction(V)
f = Constant(0.0)

a = inner(grad(u), grad(v)) * dx
L = f * v * dx

u_sol = Function(V)
solve(a == L, u_sol, bc)

# TODO: 使用 adaptive 进行自适应求解
# 目标：在中心峰值区域自动加密
