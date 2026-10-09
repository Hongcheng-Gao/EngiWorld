from pathlib import Path

import dolfin as df


root = Path("/home/user/Desktop")
mesh = df.RectangleMesh(df.Point(0.0, 0.0), df.Point(1.0, 1.0), 40, 40, "right")
space = df.FunctionSpace(mesh, "Lagrange", 1)
field = df.Function(space)
with df.XDMFFile(mesh.mpi_comm(), str(root / "potential.xdmf")) as source:
    source.read_checkpoint(field, "potential", 0)
with df.XDMFFile(mesh.mpi_comm(), str(root / "equivalent_potential.xdmf")) as target:
    target.write_checkpoint(field, "voltage_solution", 0.0, df.XDMFFile.Encoding.HDF5, False)
