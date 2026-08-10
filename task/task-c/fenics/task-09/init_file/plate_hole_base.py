from dolfin import *
# from mshr import *

# TODO: 生成含圆孔的几何
# 外矩形 100x200，中心圆孔直径 10
# 或使用 RectangleMesh + 手动标记

E = 210000.0
nu = 0.3

# TODO: 创建上面给定的 100x200 带孔网格后，使用 VectorFunctionSpace(mesh, 'P', 1)

# TODO: 定义边界：左右边施加等效 10 MPa 远场拉伸，并约束刚体运动
# 求解并提取孔边应力
