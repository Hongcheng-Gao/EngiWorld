from pathlib import Path

import dolfin as df


root = Path("/home/user/Desktop")
mesh = df.RectangleMesh(df.Point(0.0, 0.0), df.Point(2.0, 1.0), 40, 20, "right")
space = df.VectorFunctionSpace(mesh, "Lagrange", 1)
field = df.Function(space)
with df.XDMFFile(mesh.mpi_comm(), str(root / "displacement.xdmf")) as source:
    source.read_checkpoint(field, "displacement", 0)
with df.XDMFFile(mesh.mpi_comm(), str(root / "equivalent_displacement.xdmf")) as target:
    target.write_checkpoint(field, "u_equivalent", 0.0, df.XDMFFile.Encoding.HDF5, False)
