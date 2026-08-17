from dolfin import *

mesh = RectangleMesh(Point(0, 0), Point(20, 50), 10, 25)
V = FunctionSpace(mesh, "P", 1)
u_n = interpolate(Constant(20.0), V)
bc = DirichletBC(V, Constant(100.0), lambda x, on_boundary: on_boundary and near(x[0], 0.0))

u_trial = TrialFunction(V)
v = TestFunction(V)
dt = 0.1
alpha = 50.0
a = u_trial*v*dx + dt*alpha*inner(grad(u_trial), grad(v))*dx
L = u_n*v*dx
u = Function(V)

for n in range(100):
    solve(a == L, u, bc)
    u_n.assign(u)

surface_temp = u(Point(0.0, 25.0))
temp_at_5mm = u(Point(5.0, 25.0))
with open("summary.txt", "w", encoding="utf-8") as handle:
    handle.write(f"{surface_temp:.12g}, {temp_at_5mm:.12g}\n")
