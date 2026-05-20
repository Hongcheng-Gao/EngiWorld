from dolfin import *

# === 热分析 ===
mesh = RectangleMesh(Point(0, 0), Point(100, 10), 20, 2)
VT = FunctionSpace(mesh, 'P', 1)

# 左端 100°C，右端 20°C
bc_left = DirichletBC(VT, Constant(100.0), lambda x, on_b: near(x[0], 0) and on_b)
bc_right = DirichletBC(VT, Constant(20.0), lambda x, on_b: near(x[0], 100) and on_b)

u_T = TrialFunction(VT)
v_T = TestFunction(VT)
a_T = inner(grad(u_T), grad(v_T)) * dx
L_T = Constant(0.0) * v_T * dx

T_sol = Function(VT)
solve(a_T == L_T, T_sol, [bc_left, bc_right])

# TODO: 将 T_sol 传递给结构分析
# 结构分析：VectorFunctionSpace, 两端固定, 热膨胀
