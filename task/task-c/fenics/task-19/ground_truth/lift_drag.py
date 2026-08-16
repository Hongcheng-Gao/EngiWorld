from dolfin import *


length = 2.2
height = 0.41
cylinder_x = 0.2
cylinder_y = 0.2
diameter = 0.1
radius = diameter / 2.0
background = RectangleMesh(Point(0.0, 0.0), Point(length, height), 110, 21)
fluid_cells = MeshFunction("size_t", background, background.topology().dim(), 0)
for cell in cells(background):
    midpoint = cell.midpoint()
    distance_squared = (midpoint.x() - cylinder_x) ** 2 + (midpoint.y() - cylinder_y) ** 2
    if distance_squared >= radius**2:
        fluid_cells[cell] = 1
mesh = SubMesh(background, fluid_cells, 1)

velocity_element = VectorElement("P", mesh.ufl_cell(), 2)
pressure_element = FiniteElement("P", mesh.ufl_cell(), 1)
mixed_space = FunctionSpace(mesh, MixedElement([velocity_element, pressure_element]))
velocity, pressure = TrialFunctions(mixed_space)
test_velocity, test_pressure = TestFunctions(mixed_space)


def inlet(point, on_boundary):
    return on_boundary and near(point[0], 0.0)


def channel_walls(point, on_boundary):
    return on_boundary and (near(point[1], 0.0) or near(point[1], height))


def cylinder(point, on_boundary):
    radius_from_center = ((point[0] - cylinder_x) ** 2 + (point[1] - cylinder_y) ** 2) ** 0.5
    return on_boundary and radius_from_center < 0.08


def outlet(point, on_boundary):
    return on_boundary and near(point[0], length)


mean_velocity = 0.2
inlet_profile = Expression(
    ("6.0*U*x[1]*(H-x[1])/(H*H)", "0.0"), degree=2, U=mean_velocity, H=height
)
boundary_conditions = [
    DirichletBC(mixed_space.sub(0), inlet_profile, inlet),
    DirichletBC(mixed_space.sub(0), Constant((0.0, 0.0)), channel_walls),
    DirichletBC(mixed_space.sub(0), Constant((0.0, 0.0)), cylinder),
    DirichletBC(mixed_space.sub(1), Constant(0.0), outlet),
]

nu = Constant(0.001)
a = (
    nu * inner(grad(velocity), grad(test_velocity))
    - pressure * div(test_velocity)
    + test_pressure * div(velocity)
) * dx
L = dot(Constant((0.0, 0.0)), test_velocity) * dx
mixed_solution = Function(mixed_space)
solve(a == L, mixed_solution, boundary_conditions)
u, p = mixed_solution.split(deepcopy=True)

facet_markers = MeshFunction("size_t", mesh, mesh.topology().dim() - 1, 0)


class CylinderBoundary(SubDomain):
    def inside(self, point, on_boundary):
        radius_from_center = ((point[0] - cylinder_x) ** 2 + (point[1] - cylinder_y) ** 2) ** 0.5
        return on_boundary and radius_from_center < 0.08


CylinderBoundary().mark(facet_markers, 5)
ds_marked = Measure("ds", domain=mesh, subdomain_data=facet_markers)
n = FacetNormal(mesh)
force = -p * n + nu * dot(grad(u), n)
drag_force = -float(assemble(force[0] * ds_marked(5)))
lift_force = -float(assemble(force[1] * ds_marked(5)))
drag_coefficient = 2.0 * drag_force / (mean_velocity**2 * diameter)
lift_coefficient = 2.0 * lift_force / (mean_velocity**2 * diameter)

with open("/home/user/Desktop/summary.txt", "w", encoding="utf-8") as handle:
    handle.write(f"{drag_coefficient:.16g},{lift_coefficient:.16g}\n")

print(f"drag_coefficient={drag_coefficient:.16g}")
print(f"lift_coefficient={lift_coefficient:.16g}")
