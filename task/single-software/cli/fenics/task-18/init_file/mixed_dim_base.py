from dolfin import *
import numpy as np

mesh = UnitSquareMesh(10, 10)
V = FunctionSpace(mesh, 'P', 1)

# TODO: Create BoundaryMesh with co-dimension 1.
# TODO: Define a DG(0) space Q on the boundary mesh.
# TODO: Assemble the discrete trace coupling matrix using BoundaryMesh.entity_map(0).

u = TrialFunction(V)
# Legacy DOLFIN cannot directly mix function spaces on different meshes in one UFL form.
