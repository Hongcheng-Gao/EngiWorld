from dolfin import *
import numpy as np

mesh = UnitSquareMesh(10, 10)
V = FunctionSpace(mesh, 'P', 1)

# TODO: 创建边界子网格（co-dimension 1）
# TODO: 在子网格上定义函数空间 Q
# TODO: 组装混合维变分形式：inner(u, q) * ds

u = TrialFunction(V)
# q = TestFunction(Q)  # 子网格测试函数
