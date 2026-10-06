from dolfin import *

# Create a unit-square mesh.
mesh = UnitSquareMesh(32, 32)

# Define the function space.
V = FunctionSpace(mesh, 'P', 1)

# Define boundary conditions.
u_D = Expression('1 + x[0]*x[0] + 2*x[1]*x[1]', degree=2)

def boundary(x, on_boundary):
    return on_boundary

bc = DirichletBC(V, u_D, boundary)

# Define the variational problem.
u = TrialFunction(V)
v = TestFunction(V)

# TODO: Complete the bilinear form a and linear form L.


# Solve the problem.
u = Function(V)
# solve(a == L, u, bc)

# Write the output file.
# vtkfile = File('outputs/solution.pvd')
# vtkfile << u
