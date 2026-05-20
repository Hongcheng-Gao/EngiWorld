from dolfin import *
# from mshr import *

# TODO: 生成含圆孔的几何
# 外矩形 100x200，中心圆孔直径 10
# 或使用 RectangleMesh + 手动标记

mesh = UnitSquareMesh(20, 40)
V = FunctionSpace(mesh, 'P', 1)

# TODO: 定义边界：左右拉伸，上下对称
# 求解并提取孔边应力
