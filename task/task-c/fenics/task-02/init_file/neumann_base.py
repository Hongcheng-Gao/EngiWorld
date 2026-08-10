from dolfin import *

mesh = UnitSquareMesh(32, 32)
V = FunctionSpace(mesh, 'P', 1)

# TODO: 定义子域标记
# 左边界 Dirichlet: u=0
# 右边界 Neumann: g=4
# 上下边界保持自然零通量条件

u = TrialFunction(V)
v = TestFunction(V)
f = Constant(0.0)

# TODO: 补充 a 和 L（含 ds 边界积分）

u_sol = Function(V)
# solve(a == L, u_sol, bcs)

# 提取 x=(1.0, 0.5) 处的值
# point_value = u_sol(Point(1.0, 0.5))
