from dolfin import *
# from mshr import *

# TODO: Generate geometry containing a circular hole.
# Outer rectangle: 100x200; central circular hole diameter: 10.
# Alternatively, use RectangleMesh with manual marking.

E = 210000.0
nu = 0.3

# TODO: Create the specified 100x200 mesh with a hole, then use VectorFunctionSpace(mesh, 'P', 1).

# TODO: Apply equivalent 10 MPa far-field tension on the left and right, and constrain rigid-body motion.
# Solve the problem and extract stress at the hole boundary.
