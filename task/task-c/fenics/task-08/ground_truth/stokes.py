from dolfin import *

mesh = RectangleMesh(Point(0, 0), Point(2.2, 0.41), 60, 20)
element = MixedElement([
    VectorElement("P", mesh.ufl_cell(), 2),
    FiniteElement("P", mesh.ufl_cell(), 1),
])
W = FunctionSpace(mesh, element)


class Inlet(SubDomain):
    def inside(self, x, on_boundary):
        return on_boundary and near(x[0], 0.0)


class Outlet(SubDomain):
    def inside(self, x, on_boundary):
        return on_boundary and near(x[0], 2.2)


boundaries = MeshFunction("size_t", mesh, mesh.topology().dim() - 1, 0)
Outlet().mark(boundaries, 2)
ds = Measure("ds", domain=mesh, subdomain_data=boundaries)
inlet_velocity = Expression(("4*0.3*x[1]*(0.41-x[1])/(0.41*0.41)", "0.0"), degree=2)
bc_inlet = DirichletBC(W.sub(0), inlet_velocity, Inlet())
bc_walls = DirichletBC(
    W.sub(0),
    Constant((0.0, 0.0)),
    lambda x, on_boundary: on_boundary and (near(x[1], 0.0) or near(x[1], 0.41)),
)

(u, p) = TrialFunctions(W)
(v, q) = TestFunctions(W)
nu = Constant(0.001)
f = Constant((0.0, 0.0))
a = nu*inner(grad(u), grad(v))*dx - p*div(v)*dx - q*div(u)*dx
L = inner(f, v)*dx
w = Function(W)
solve(a == L, w, [bc_inlet, bc_walls])
u_sol, p_sol = w.split(deepcopy=True)

outlet_length = assemble(Constant(1.0)*ds(2))
outlet_pressure = assemble(p_sol*ds(2))/outlet_length
speed = project(sqrt(dot(u_sol, u_sol)), FunctionSpace(mesh, "P", 1))
max_velocity = speed.vector().get_local().max()
with open("summary.txt", "w", encoding="utf-8") as handle:
    handle.write(f"{outlet_pressure:.12g}, {max_velocity:.12g}\n")
