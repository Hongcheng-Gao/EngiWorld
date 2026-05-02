from dolfin import *

mesh = UnitSquareMesh(32, 32)
V = FunctionSpace(mesh, 'P', 1)

bc = DirichletBC(V, Constant(0.0), lambda x, on_b: on_b)

u = Function(V)  # 非线性问题需使用 Function 而非 TrialFunction
v = TestFunction(V)

# TODO: 定义非线性残差形式
# 方程: -div((1+u^2)*grad(u)) = f，f=1

# TODO: 使用 NonlinearVariationalProblem 和 NonlinearVariationalSolver

# 求解并提取中心点值
