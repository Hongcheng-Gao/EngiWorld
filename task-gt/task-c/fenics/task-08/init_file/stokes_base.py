from dolfin import *

mesh = RectangleMesh(Point(0, 0), Point(2.2, 0.41), 60, 20)

# TODO: 定义 Taylor-Hood 混合元
# P2 速度 + P1 压力

# TODO: 定义边界条件
# 入口抛物线速度，壁面无滑移，出口自然边界

# TODO: 定义变分形式
# a = nu*inner(grad(u), grad(v))*dx - p*div(v)*dx - q*div(u)*dx
# L = inner(f, v)*dx

# 求解并提取出口平均压力
