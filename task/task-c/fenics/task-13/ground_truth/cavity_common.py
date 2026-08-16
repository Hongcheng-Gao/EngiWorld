from dolfin import *


def solve_cavity(reynolds):
    mesh = UnitSquareMesh(32, 32)
    velocity_element = VectorElement("P", mesh.ufl_cell(), 2)
    pressure_element = FiniteElement("P", mesh.ufl_cell(), 1)
    mixed_space = FunctionSpace(mesh, MixedElement([velocity_element, pressure_element]))

    def lid(point, on_boundary):
        return on_boundary and near(point[1], 1.0)

    def fixed_walls(point, on_boundary):
        return on_boundary and (
            near(point[0], 0.0) or near(point[0], 1.0) or near(point[1], 0.0)
        )

    velocity_bcs = [
        DirichletBC(mixed_space.sub(0), Constant((1.0, 0.0)), lid),
        DirichletBC(mixed_space.sub(0), Constant((0.0, 0.0)), fixed_walls),
    ]
    pressure_anchor = DirichletBC(
        mixed_space.sub(1),
        Constant(0.0),
        lambda point, on_boundary: near(point[0], 0.0) and near(point[1], 0.0),
        method="pointwise",
    )
    boundary_conditions = velocity_bcs + [pressure_anchor]

    mixed_solution = Function(mixed_space)
    trial_velocity, trial_pressure = TrialFunctions(mixed_space)
    test_velocity, test_pressure = TestFunctions(mixed_space)
    viscosity = Constant(1.0 / 100.0)
    stokes_form = (
        viscosity * inner(grad(trial_velocity), grad(test_velocity))
        - trial_pressure * div(test_velocity)
        + test_pressure * div(trial_velocity)
    ) * dx
    solve(stokes_form == dot(Constant((0.0, 0.0)), test_velocity) * dx, mixed_solution, boundary_conditions)

    velocity, pressure = split(mixed_solution)
    nonlinear_form = (
        viscosity * inner(grad(velocity), grad(test_velocity))
        + inner(dot(grad(velocity), velocity), test_velocity)
        - pressure * div(test_velocity)
        + test_pressure * div(velocity)
    ) * dx
    continuation_values = [100] if reynolds == 100 else list(range(100, reynolds + 1, 100))
    for continuation_re in continuation_values:
        viscosity.assign(1.0 / continuation_re)
        solve(
            nonlinear_form == 0,
            mixed_solution,
            boundary_conditions,
            solver_parameters={
                "newton_solver": {
                    "absolute_tolerance": 1.0e-9,
                    "relative_tolerance": 1.0e-8,
                    "maximum_iterations": 30,
                    "relaxation_parameter": 1.0,
                }
            },
        )
    velocity_solution, _ = mixed_solution.split(deepcopy=True)
    return float(velocity_solution(Point(0.5, 0.5))[0])
