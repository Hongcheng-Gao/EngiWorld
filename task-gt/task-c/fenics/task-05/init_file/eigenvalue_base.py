from dolfin import *
from slepc4py import SLEPc
from petsc4py import PETSc

mesh = RectangleMesh(Point(0, 0), Point(500, 10), 50, 1)
V = VectorFunctionSpace(mesh, 'P', 1)

# TODO: 定义边界条件（固支）
# TODO: 定义双线性型 a（刚度）和 M（质量）

# 求解特征值问题
# A = assemble(a)
# M = assemble(m)
# 设置 SLEPc 求解器，请求 3 阶最小特征值
