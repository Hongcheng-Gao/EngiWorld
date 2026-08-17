from dolfin import *

mesh = UnitIntervalMesh(40)
V = FunctionSpace(mesh, 'DG', 1)
u = TrialFunction(V)
v = TestFunction(V)
eps = Constant(0.01)
beta = Constant((1.0,))
n = FacetNormal(mesh)
h = CellDiameter(mesh)
penalty = Constant(20.0)

a = eps*inner(grad(u), grad(v))*dx
a += -eps*inner(avg(grad(u)), jump(v, n))*dS
a += -eps*inner(jump(u, n), avg(grad(v)))*dS
a += eps*penalty/avg(h)*inner(jump(u, n), jump(v, n))*dS

bn = dot(beta, n)
upwind = conditional(gt(dot(beta, n("+")), 0.0), u("+"), u("-"))
a += -u*dot(beta, grad(v))*dx + dot(beta, n("+"))*upwind*jump(v)*dS

g = Expression("near(x[0], 1.0) ? 1.0 : 0.0", degree=0)
a += -eps*dot(grad(u), n)*v*ds - eps*dot(grad(v), n)*u*ds + eps*penalty/h*u*v*ds
L = -eps*dot(grad(v), n)*g*ds + eps*penalty/h*g*v*ds
a += conditional(gt(bn, 0.0), bn*u*v, Constant(0.0)*u*v)*ds
L += conditional(lt(bn, 0.0), -bn*g*v, Constant(0.0)*v)*ds

u_sol = Function(V)
solve(a == L, u_sol)
mid_value = 0.5*(u_sol(Point(0.5 - 1.0e-8)) + u_sol(Point(0.5 + 1.0e-8)))
max_value = u_sol.vector().get_local().max()
with open("summary.txt", "w", encoding="utf-8") as handle:
    handle.write(f"{mid_value:.12g}, {max_value:.12g}\n")
