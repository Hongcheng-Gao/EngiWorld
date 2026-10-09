from dolfin import *

# Self-contained setup: 2.2 x 0.41 channel, cylinder centered at (0.2, 0.2), diameter 0.1.
# Use RectangleMesh and SubMesh to create a mesh with a cylindrical hole, then solve steady Stokes flow.

# TODO: Define cylinder-surface boundary markers.
# TODO: Calculate lift and drag coefficients.
# F_D = assemble(-force[0]*ds_circle)
# F_L = assemble(-force[1]*ds_circle)
