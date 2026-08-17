from dolfin import *

mesh = UnitSquareMesh(32, 32)
V = FunctionSpace(mesh, "P", 1)

boundaries = MeshFunction("size_t", mesh, mesh.topology().dim() - 1, 0)


class Right(SubDomain):
    def inside(self, x, on_boundary):
        return on_boundary and near(x[0], 1.0)


Right().mark(boundaries, 1)
ds = Measure("ds", domain=mesh, subdomain_data=boundaries)
bc = DirichletBC(V, Constant(0.0), lambda x, on_boundary: on_boundary and near(x[0], 0.0))

u = TrialFunction(V)
v = TestFunction(V)
f = Constant(0.0)
g = Constant(4.0)
a = inner(grad(u), grad(v))*dx
L = f*v*dx + inner(g, v)*ds(1)

u_sol = Function(V)
solve(a == L, u_sol, bc)
point_value = u_sol(Point(1.0, 0.5))
max_value = u_sol.vector().get_local().max()

with open("summary.txt", "w", encoding="utf-8") as handle:
    handle.write(f"{point_value:.12g}, {max_value:.12g}\n")
