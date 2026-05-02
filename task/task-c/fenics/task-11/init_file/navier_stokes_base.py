from dolfin import *

mesh = RectangleMesh(Point(0, 0), Point(2.2, 0.41), 60, 20)
V = VectorFunctionSpace(mesh, 'P', 2)
Q = FunctionSpace(mesh, 'P', 1)

# 边界条件定义...

# TODO: 实现 IPCS 三步格式
# Step 1:  tentative velocity
# Step 2:  pressure correction (Poisson)
# Step 3:  velocity correction

# 时间步进 50 步，dt=0.001
