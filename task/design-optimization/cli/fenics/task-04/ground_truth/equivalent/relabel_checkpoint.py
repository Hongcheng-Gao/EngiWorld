from pathlib import Path

import dolfin as df


root = Path("/home/user/Desktop")
mesh = df.RectangleMesh(df.Point(0.0, 0.0), df.Point(1.6, 0.8), 32, 16, "right")
space = df.FunctionSpace(mesh, "Lagrange", 1)
field = df.Function(space)
with df.XDMFFile(mesh.mpi_comm(), str(root / "pressure.xdmf")) as source:
    source.read_checkpoint(field, "pressure", 0)
with df.XDMFFile(mesh.mpi_comm(), str(root / "equivalent_pressure.xdmf")) as target:
    target.write_checkpoint(field, "darcy_head", 0.0, df.XDMFFile.Encoding.HDF5, False)
