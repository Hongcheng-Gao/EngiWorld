from dolfin import *

mesh = RectangleMesh(Point(0, 0), Point(2.2, 0.41), 60, 20)
V = VectorFunctionSpace(mesh, 'P', 2)
Q = FunctionSpace(mesh, 'P', 1)

# Boundary-condition definitions...

# TODO: Implement the three-step IPCS scheme.
# Step 1:  tentative velocity
# Step 2:  pressure correction (Poisson)
# Step 3:  velocity correction

# Advance 50 time steps with dt=0.001.
