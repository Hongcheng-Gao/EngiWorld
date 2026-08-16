from dolfin import *


mesh = UnitSquareMesh(8, 8)
V = FunctionSpace(mesh, "P", 1)

u_D = Expression("exp(-100*(pow(x[0]-0.5, 2) + pow(x[1]-0.5, 2)))", degree=4)
bc = DirichletBC(V, u_D, lambda point, on_boundary: on_boundary)

u = TrialFunction(V)
v = TestFunction(V)
f = Expression(
    "400*(1 - 100*(pow(x[0]-0.5, 2) + pow(x[1]-0.5, 2)))"
    "*exp(-100*(pow(x[0]-0.5, 2) + pow(x[1]-0.5, 2)))",
    degree=4,
)
a = inner(grad(u), grad(v)) * dx
L = f * v * dx

u_sol = Function(V)
M = u_sol * dx
problem = LinearVariationalProblem(a, L, u_sol, bc)
solver = AdaptiveLinearVariationalSolver(problem, M)
solver.parameters["error_control"]["dual_variational_solver"]["linear_solver"] = "cg"
solver.solve(1.0e-5)

final_solution = u_sol.leaf_node()
num_cells = final_solution.function_space().mesh().num_cells()
center_value = float(final_solution(Point(0.5, 0.5)))

with open("/home/user/Desktop/summary.txt", "w", encoding="utf-8") as handle:
    handle.write(f"{num_cells},{center_value:.16g}\n")

print(f"num_cells={num_cells}")
print(f"center_value={center_value:.16g}")
