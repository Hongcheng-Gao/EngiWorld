from dolfin import *

# === Thermal analysis ===
mesh = RectangleMesh(Point(0, 0), Point(100, 10), 20, 2)
VT = FunctionSpace(mesh, 'P', 1)

# Left boundary: 100 degrees C; right boundary: 20 degrees C.
bc_left = DirichletBC(VT, Constant(100.0), lambda x, on_b: near(x[0], 0) and on_b)
bc_right = DirichletBC(VT, Constant(20.0), lambda x, on_b: near(x[0], 100) and on_b)

u_T = TrialFunction(VT)
v_T = TestFunction(VT)
a_T = inner(grad(u_T), grad(v_T)) * dx
L_T = Constant(0.0) * v_T * dx

T_sol = Function(VT)
solve(a_T == L_T, T_sol, [bc_left, bc_right])

# TODO: Pass T_sol to the structural analysis.
# Structural analysis: VectorFunctionSpace, fixed at both ends, thermal expansion.
