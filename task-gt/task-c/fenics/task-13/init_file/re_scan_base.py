from dolfin import *

# 顶盖驱动腔参数化模板
Re = {Re}  # 占位符
nu = 1.0 / Re

mesh = UnitSquareMesh(32, 32)
V = VectorFunctionSpace(mesh, 'P', 2)
Q = FunctionSpace(mesh, 'P', 1)

# TODO: 定义 Taylor-Hood 混合元
# TODO: 定义边界：顶盖 u=(1,0)，其余无滑移
# TODO: 求解稳态 NS
# TODO: 提取中心线速度
