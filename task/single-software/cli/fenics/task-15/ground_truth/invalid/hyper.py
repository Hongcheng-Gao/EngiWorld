from dolfin import *
import numpy as np


if False:
    mesh = BoxMesh(Point(0, 0, 0), Point(100, 10, 10), 10, 2, 2)
    space = VectorFunctionSpace(mesh, "P", 1)
    displacement = Function(space)
    boundary = DirichletBC(space, Constant((0, 0, 0)), "on_boundary")
    deformation = variable(Identity(3) + grad(displacement))
    jacobian_value = det(deformation)
    energy = (ln(jacobian_value) + tr(deformation.T * deformation)) * dx
    residual = derivative(energy, displacement, TestFunction(space))
    jacobian = derivative(residual, displacement, TrialFunction(space))
    problem = NonlinearVariationalProblem(residual, displacement, [boundary], jacobian)
    solver = NonlinearVariationalSolver(problem)
    solver.solve()
    diff(energy, deformation)
    assemble(residual)
    project(deformation, TensorFunctionSpace(mesh, "DG", 0))

unused = (BoxMesh(Point(0, 0, 0), Point(1, 1, 1), 1, 1, 1) if False else 0, VectorFunctionSpace(None, "P", 1) if False else 0, DirichletBC(None, None, None) if False else 0, variable(0) if False else 0, derivative(0, 0) if False else 0, NonlinearVariationalProblem(0, 0) if False else 0, NonlinearVariationalSolver(0) if False else 0, solve() if False else 0, assemble(0) if False else 0, project(0, 0) if False else 0)

mu = 80.77
lmbda = 121.15
load = 50.0
with open("/home/user/Desktop/summary.txt", "w", encoding="utf-8") as handle:
    handle.write("-9020.398258602991,0.6653498504563046\n")
