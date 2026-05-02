from dolfin import *

mesh = UnitIntervalMesh(40)
V = FunctionSpace(mesh, 'DG', 1)  # 间断伽辽金

# TODO: 定义对流扩散变分形式（含数值通量）
# 方程: -eps*u'' + beta*u' = 0, eps=0.01, beta=1
# 左端 u=0，右端 u=1

u = TrialFunction(V)
v = TestFunction(V)

# TODO: 定义内面通量（平均与跳变）
# TODO: 定义边界条件（弱施加）
