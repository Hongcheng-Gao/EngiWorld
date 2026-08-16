from dolfin import *
import numpy as np

mesh = UnitSquareMesh(10, 10)
V = FunctionSpace(mesh, 'P', 1)

# TODO: 创建 BoundaryMesh（co-dimension 1）
# TODO: 在边界网格上定义 DG(0) 空间 Q
# TODO: 用 BoundaryMesh.entity_map(0) 组装离散 trace 耦合矩阵

u = TrialFunction(V)
# legacy DOLFIN 不能直接在一个 UFL form 中混合不同 mesh 的函数空间。
