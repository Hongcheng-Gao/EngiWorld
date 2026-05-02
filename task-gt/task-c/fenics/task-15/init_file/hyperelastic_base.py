from dolfin import *

mesh = BoxMesh(Point(0, 0, 0), Point(100, 10, 10), 10, 2, 2)
V = VectorFunctionSpace(mesh, 'P', 1)

# TODO: 定义 Neo-Hookean 超弹性材料
# I1 = tr(C), J = det(F), C = F.T*F
# psi = mu/2*(I1-3) - mu*ln(J) + lambd/2*(ln(J))^2

# TODO: 定义第一 Piola-Kirchhoff 应力 P = diff(psi, F)
# 或使用变分形式 Pi = inner(P, grad(v))*dx

u = Function(V)
v = TestFunction(V)

# 边界：左端固定，右端拉伸 50%
