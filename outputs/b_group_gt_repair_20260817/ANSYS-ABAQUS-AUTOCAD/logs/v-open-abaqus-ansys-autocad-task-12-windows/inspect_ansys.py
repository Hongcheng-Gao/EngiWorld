import json
import re
from pathlib import Path

import numpy as np
from ansys.mapdl import reader
from ansys.mapdl.core import launch_mapdl


desktop = Path(r"C:\Users\user\Desktop")
stem = "apdl_plate"
mapdl = launch_mapdl(
    exec_file=r"C:\Program Files\ANSYS Inc\v261\ansys\bin\winx64\ANSYS261.exe",
    jobname="inspect_v12", run_location=str(desktop), nproc=1, override=True,
    cleanup_on_exit=True, license_type="meba", start_timeout=180,
)
try:
    mapdl.resume(str(desktop / stem), "db")
    node_numbers = [int(value) for value in mapdl.mesh.nnum]
    nodes = [[float(value) for value in row[:3]] for row in mapdl.mesh.nodes]
    coordinates = dict(zip(node_numbers, nodes))
    constraints = mapdl.run("DLIST,ALL")
    surface_loads = mapdl.run("SFLIST,ALL")
    constrained = sorted({int(m.group(1)) for line in constraints.splitlines()
                          if (m := re.match(r"\s*(\d+)\s+(UX|UY)\s+", line))})
    pressure_nodes = set()
    for line in surface_loads.splitlines():
        if "-0.100" not in line:
            continue
        labels = re.findall(r"\d+", line.split("-0.100", 1)[0])
        if labels:
            pressure_nodes.add(int(labels[-1]))
    evidence = {
        "bbox": {axis: [min(row[i] for row in nodes), max(row[i] for row in nodes)]
                 for i, axis in enumerate("xyz")},
        "node_count": len(nodes),
        "element_count": int(mapdl.mesh.n_elem),
        "element_types": mapdl.run("ETLIST,ALL"),
        "materials": mapdl.run("MPLIST,ALL"),
        "constraints": constraints,
        "constrained_node_coordinates": {str(n): coordinates[n] for n in constrained},
        "surface_loads": surface_loads,
        "pressure_node_coordinates": {str(n): coordinates[n] for n in sorted(pressure_nodes)},
        "element_surface_loads": mapdl.run("SFELIST,ALL"),
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
    (desktop / "v12_inspect.json").write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({"bbox": evidence["bbox"], "element_count": evidence["element_count"],
                      "max_displacement": evidence["max_displacement"],
                      "max_mises": evidence["max_mises"]}))
finally:
    try:
        mapdl.exit()
    except Exception:
        pass
