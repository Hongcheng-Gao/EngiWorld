from dolfin import *

# 自包含设置：2.2 x 0.41 通道，圆柱中心 (0.2, 0.2)，直径 0.1
# 用 RectangleMesh + SubMesh 创建带圆柱孔的网格，并求解稳态 Stokes 流。

# TODO: 定义圆柱表面边界标记
# TODO: 计算升力/阻力系数
# F_D = assemble(-force[0]*ds_circle)
# F_L = assemble(-force[1]*ds_circle)
