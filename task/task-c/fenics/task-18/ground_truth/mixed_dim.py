from dolfin import *
from petsc4py import PETSc


mesh = UnitSquareMesh(10, 10)
V = FunctionSpace(mesh, "P", 1)
boundary_mesh = BoundaryMesh(mesh, "exterior")
Q = FunctionSpace(boundary_mesh, "DG", 0)

boundary_to_parent_vertex = boundary_mesh.entity_map(0).array()
parent_vertex_to_dof = vertex_to_dof_map(V)
matrix = PETSc.Mat().createAIJ(size=(Q.dim(), V.dim()), nnz=2)
matrix.setUp()

for boundary_cell in cells(boundary_mesh):
    row = int(Q.dofmap().cell_dofs(boundary_cell.index())[0])
    edge_length = float(boundary_cell.volume())
    for boundary_vertex in boundary_cell.entities(0):
        parent_vertex = int(boundary_to_parent_vertex[int(boundary_vertex)])
        column = int(parent_vertex_to_dof[parent_vertex])
        matrix.setValue(row, column, edge_length / 2.0, addv=PETSc.InsertMode.ADD_VALUES)

matrix.assemblyBegin()
matrix.assemblyEnd()
nnz = int(matrix.getInfo()["nz_used"])
submesh_cells = int(boundary_mesh.num_cells())

with open("/home/user/Desktop/summary.txt", "w", encoding="utf-8") as handle:
    handle.write(f"{nnz},{submesh_cells}\n")

print(f"nnz={nnz}")
print(f"submesh_cells={submesh_cells}")
