from dolfin import *

mesh = RectangleMesh(Point(0, 0), Point(20, 50), 10, 25)
V = FunctionSpace(mesh, 'P', 1)

# 初始条件 u=20
u_n = interpolate(Constant(20.0), V)

# 边界：左端 100°C
bc = DirichletBC(V, Constant(100.0), lambda x, on_b: near(x[0], 0) and on_b)

u = TrialFunction(V)
v = TestFunction(V)

dt = 0.1
alpha = 50.0  # 热扩散系数

# TODO: 定义时间离散变分形式（向后欧拉）
# (u - u_n)/dt * v * dx + alpha * inner(grad(u), grad(v)) * dx = 0

# TODO: 编写时间循环，计算 100 步（dt=0.1 s，总时间 10 s）
