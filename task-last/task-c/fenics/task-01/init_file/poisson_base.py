from dolfin import *

# 创建单位正方形网格
mesh = UnitSquareMesh(32, 32)

# 定义函数空间
V = FunctionSpace(mesh, 'P', 1)

# 定义边界条件
u_D = Expression('1 + x[0]*x[0] + 2*x[1]*x[1]', degree=2)

def boundary(x, on_boundary):
    return on_boundary

bc = DirichletBC(V, u_D, boundary)

# 定义变分问题
u = TrialFunction(V)
v = TestFunction(V)

# TODO: 补充双线性型 a 和线性型 L


# 求解
u = Function(V)
# solve(a == L, u, bc)

# 输出到文件
# vtkfile = File('outputs/solution.pvd')
# vtkfile << u
