import json
import re
from pathlib import Path

import numpy as np
from ansys.mapdl import reader
from ansys.mapdl.core import launch_mapdl


desktop = Path(r"C:\Users\user\Desktop")
stem = "apdl_cylinder"
mapdl = launch_mapdl(
    exec_file=r"C:\Program Files\ANSYS Inc\v261\ansys\bin\winx64\ANSYS261.exe",
    jobname="inspect_v16", run_location=str(desktop), nproc=1, override=True,
    cleanup_on_exit=True, license_type="meba", start_timeout=180,
)
try:
    mapdl.resume(str(desktop / stem), "db")
    labels = [int(value) for value in mapdl.mesh.nnum]
    nodes = [[float(value) for value in row[:3]] for row in mapdl.mesh.nodes]
    coordinates = dict(zip(labels, nodes))
    pressure_text = mapdl.run("SFELIST,ALL")
    pressure_nodes = set()
    for line in pressure_text.splitlines():
        values = re.findall(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][+-]?\d+)?", line)
        if len(values) >= 3:
            try:
                node = int(float(values[-3])); pressure = float(values[-2])
                if abs(pressure) > 1.0e-12:
                    pressure_nodes.add(node)
            except Exception:
                pass
    evidence = {
        "bbox": {axis: [min(row[i] for row in nodes), max(row[i] for row in nodes)]
                 for i, axis in enumerate("xyz")},
        "node_count": len(nodes), "element_count": int(mapdl.mesh.n_elem),
        "element_types": mapdl.run("ETLIST,ALL"), "materials": mapdl.run("MPLIST,ALL"),
        "constraints": mapdl.run("DLIST,ALL"), "surface_loads": pressure_text,
        "pressure_node_coordinates": {str(n): coordinates[n] for n in sorted(pressure_nodes)},
    }
    result = reader.read_binary(str(desktop / (stem + ".rst")))
    last = int(result.nsets) - 1
    _, displacement = result.nodal_solution(last)
    evidence["max_displacement"] = float(np.linalg.norm(displacement, axis=1).max())
    _, stress = result.nodal_stress(last)
    sx, sy, sz, sxy, syz, sxz = np.asarray(stress, dtype=float)[:, :6].T
    mises = np.sqrt(0.5 * ((sx - sy) ** 2 + (sy - sz) ** 2 + (sz - sx) ** 2)
                    + 3.0 * (sxy ** 2 + syz ** 2 + sxz ** 2))
    evidence["max_mises"] = float(np.nanmax(mises))
    (desktop / "v16_inspect.json").write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"pressure_node_coordinates": evidence["pressure_node_coordinates"],
                      "max_displacement": evidence["max_displacement"],
                      "max_mises": evidence["max_mises"]}))
finally:
    try:
        mapdl.exit()
    except Exception:
        pass
