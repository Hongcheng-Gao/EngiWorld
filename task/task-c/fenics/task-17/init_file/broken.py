from dolfin import *

mesh = UnitSquareMesh(16, 16)
V = FunctionSpace(mesh, 'P', 1)

u = TrialFunction(V)
v = TestFunction(V)
f = Constant(1.0)

# 错误1: grad(u)*grad(v) 应为 inner(grad(u), grad(v))
a = grad(u) * grad(v) * dx
L = f * v * dx

bc = DirichletBC(V, Constant(0.0), lambda x, on_b: on_b)

u_sol = Function(V)
solve(a == L, u_sol, bc)

# 缺失要求2: 只写 VTK 文件，没有生成任务要求的 fixed_summary.txt
vtkfile = File('result.pvd')
vtkfile << u_sol

# 错误3: 提取点值使用了错误的调用语法
# val = u_sol(0.5, 0.5)
