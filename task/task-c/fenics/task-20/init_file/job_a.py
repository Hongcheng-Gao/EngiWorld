from dolfin import *

mesh = BoxMesh(Point(0,0,0), Point(100,10,10), 20, 2, 2)
V = VectorFunctionSpace(mesh, 'P', 1)

# 左端固定，右端 FY=-100
# 求解并输出到 job_a.xdmf
