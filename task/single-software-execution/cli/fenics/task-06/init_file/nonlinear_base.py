from dolfin import *

mesh = UnitSquareMesh(32, 32)
V = FunctionSpace(mesh, 'P', 1)

bc = DirichletBC(V, Constant(0.0), lambda x, on_b: on_b)

u = Function(V)  # Use Function rather than TrialFunction for a nonlinear problem.
v = TestFunction(V)

# TODO: Define the nonlinear residual form.
# Equation: -div((1+u^2)*grad(u)) = f, with f=1.

# TODO: Use NonlinearVariationalProblem and NonlinearVariationalSolver.

# Solve the problem and extract the center-point value.
