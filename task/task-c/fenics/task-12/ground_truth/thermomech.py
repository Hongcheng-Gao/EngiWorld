from dolfin import *


mesh = RectangleMesh(Point(0, 0), Point(100, 10), 20, 2)
VT = FunctionSpace(mesh, "P", 1)
bc_left = DirichletBC(VT, Constant(100.0), lambda x, on_b: near(x[0], 0) and on_b)
bc_right = DirichletBC(VT, Constant(20.0), lambda x, on_b: near(x[0], 100) and on_b)
u_T = TrialFunction(VT)
v_T = TestFunction(VT)
a_T = inner(grad(u_T), grad(v_T)) * dx
L_T = Constant(0.0) * v_T * dx
T_sol = Function(VT)
solve(a_T == L_T, T_sol, [bc_left, bc_right])

V = VectorFunctionSpace(mesh, "P", 1)


def fixed_ends(point, on_boundary):
    return on_boundary and (near(point[0], 0.0) or near(point[0], 100.0))


bc_u = DirichletBC(V, Constant((0.0, 0.0)), fixed_ends)
E = 210000.0
nu = 0.3
alpha = 1.2e-5
T0 = 20.0
mu = E / (2.0 * (1.0 + nu))
lmbda = E * nu / ((1.0 + nu) * (1.0 - 2.0 * nu))


def epsilon(displacement):
    return sym(grad(displacement))


def constitutive(strain):
    return lmbda * tr(strain) * Identity(2) + 2.0 * mu * strain


u = TrialFunction(V)
v = TestFunction(V)
epsilon_th = alpha * (T_sol - T0) * Identity(2)
a = inner(constitutive(epsilon(u)), epsilon(v)) * dx
L = -inner(constitutive(epsilon_th), epsilon(v)) * dx
u_sol = Function(V)
solve(a == L, u_sol, bc_u)

total_strain = epsilon(u_sol) + epsilon_th
stress = constitutive(total_strain)
stress_zz = lmbda * tr(total_strain)
von_mises_expression = sqrt(
    stress[0, 0] ** 2
    + stress[1, 1] ** 2
    + stress_zz**2
    - stress[0, 0] * stress[1, 1]
    - stress[1, 1] * stress_zz
    - stress_zz * stress[0, 0]
    + 3.0 * stress[0, 1] ** 2
)
von_mises = project(von_mises_expression, FunctionSpace(mesh, "DG", 0))
max_mises = float(von_mises.vector().max())
ux = u_sol.split(deepcopy=True)[0]
max_ux = max(abs(float(value)) for value in ux.vector().get_local())

with open("/home/user/Desktop/summary.txt", "w", encoding="utf-8") as handle:
    handle.write(f"{max_mises:.16g},{max_ux:.16g}\n")

print(f"max_mises={max_mises:.16g}")
print(f"max_ux={max_ux:.16g}")
