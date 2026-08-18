import json
from pathlib import Path

import numpy as np
from ansys.mapdl import reader


desktop = Path(r"C:\Users\user\Desktop")
result = reader.read_binary(str(desktop / "gt_task_07_ansys.rst"))
last = int(result.nsets) - 1

node_numbers, displacement = result.nodal_solution(last)
mesh_node_numbers = np.asarray(result.mesh.nnum, dtype=int)
mesh_coordinates = np.asarray(result.mesh.nodes, dtype=float)
coordinate_by_label = {
    int(label): mesh_coordinates[index]
    for index, label in enumerate(mesh_node_numbers)
}

thetas = []
ymax = float(mesh_coordinates[:, 1].max())
for label, vector in zip(node_numbers, displacement):
    xyz = coordinate_by_label[int(label)]
    if abs(float(xyz[1]) - ymax) > 1.0e-4:
        continue
    x = float(xyz[0])
    z = float(xyz[2])
    radius2 = x * x + z * z
    if radius2 <= 1.0e-8:
        continue
    ux = float(vector[0])
    uz = float(vector[2])
    thetas.append((z * ux - x * uz) / radius2)

_, principal = result.principal_nodal_stress(last)
max_stress = float(np.nanmax(np.abs(np.asarray(principal)[:, -1])))
metrics = {
    "twist_angle": abs(float(np.mean(thetas))),
    "max_stress": max_stress,
}
(desktop / "metrics.json").write_text(
    json.dumps(metrics, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
print(json.dumps(metrics, sort_keys=True))
