from dolfin import *

mesh = UnitSquareMesh(32, 32)
V = FunctionSpace(mesh, "P", 1)
V_exact = FunctionSpace(mesh, "P", 2)
u_D_expression = Expression("1 + x[0]*x[0] + 2*x[1]*x[1]", degree=2)
u_D = interpolate(u_D_expression, V_exact)
bc = DirichletBC(V, u_D, lambda x, on_boundary: on_boundary)

u = TrialFunction(V)
v = TestFunction(V)
f = Constant(-6.0)
a = inner(grad(u), grad(v))*dx
L = f*v*dx

u = Function(V)
solve(a == L, u, bc)
error_L2 = sqrt(assemble((u - u_D)**2 * dx))
error_H1 = sqrt(assemble(inner(grad(u - u_D), grad(u - u_D)) * dx))

with open("summary.txt", "w", encoding="utf-8") as handle:
    handle.write(f"{error_L2:.12g}, {error_H1:.12g}\n")
