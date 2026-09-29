from dolfin import *

mesh = RectangleMesh(Point(0, 0), Point(20, 50), 10, 25)
V = FunctionSpace(mesh, 'P', 1)

# Initial condition: u=20.
u_n = interpolate(Constant(20.0), V)

# Left boundary: 100 degrees Celsius.
bc = DirichletBC(V, Constant(100.0), lambda x, on_b: near(x[0], 0) and on_b)

u = TrialFunction(V)
v = TestFunction(V)

dt = 0.1
alpha = 50.0  # Thermal diffusivity.

# TODO: Define the time-discrete variational form using backward Euler.
# (u - u_n)/dt * v * dx + alpha * inner(grad(u), grad(v)) * dx = 0

# TODO: Implement 100 time steps (dt=0.1 s, total duration 10 s).
