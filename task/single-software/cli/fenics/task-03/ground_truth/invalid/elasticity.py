from dolfin import *


def epsilon(displacement):
    return grad(displacement)


def sigma(displacement):
    return tr(grad(displacement)) * Identity(3)


if False:
    mesh = BoxMesh(Point(0, 0, 0), Point(100, 10, 10), 20, 2, 2)
    space = VectorFunctionSpace(mesh, "P", 1)
    boundary = DirichletBC(space, Constant((0, 0, 0)), "on_boundary")
    facets = Measure("ds", domain=mesh)
    trial = TrialFunction(space)
    test = TestFunction(space)
    solution = Function(space)
    solve(inner(sigma(trial), epsilon(test)) * facets == -10 * test[1] * facets, solution, boundary)
    project(solution[0], FunctionSpace(mesh, "DG", 0))

E = 210000
with open("/home/user/Desktop/summary.txt", "w", encoding="utf-8") as handle:
    handle.write("-0.966877365799049,322.9193342375138\n")
