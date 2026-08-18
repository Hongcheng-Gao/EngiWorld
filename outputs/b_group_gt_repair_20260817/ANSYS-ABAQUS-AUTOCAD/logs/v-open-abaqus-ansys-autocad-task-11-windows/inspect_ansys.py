import json
import re
from pathlib import Path

import numpy as np
from ansys.mapdl import reader
from ansys.mapdl.core import launch_mapdl


desktop = Path(r"C:\Users\user\Desktop")
stem = "apdl_solid_beam"
mapdl = launch_mapdl(
    exec_file=r"C:\Program Files\ANSYS Inc\v261\ansys\bin\winx64\ANSYS261.exe",
    jobname="inspect_v11",
    run_location=str(desktop),
    nproc=1,
    override=True,
    cleanup_on_exit=True,
    license_type="meba",
    start_timeout=180,
)
try:
    mapdl.resume(str(desktop / stem), "db")
    numbers = [int(value) for value in mapdl.mesh.nnum]
    nodes = [[float(value) for value in row[:3]] for row in mapdl.mesh.nodes]
    coordinates = dict(zip(numbers, nodes))
    constraints = mapdl.run("DLIST,ALL")
    constrained = sorted({int(m.group(1)) for line in constraints.splitlines()
                          if (m := re.match(r"\s*(\d+)\s+(UX|UY|UZ)\s+", line))})
    evidence = {
        "bbox": {axis: [min(row[i] for row in nodes), max(row[i] for row in nodes)]
                 for i, axis in enumerate("xyz")},
        "node_count": len(nodes),
        "element_count": int(mapdl.mesh.n_elem),
        "element_types": mapdl.run("ETLIST,ALL"),
        "materials": mapdl.run("MPLIST,ALL"),
        "constraints": constraints,
        "constrained_node_coordinates": {str(n): coordinates[n] for n in constrained},
        "loads": mapdl.run("FLIST,ALL"),
    }
    result = reader.read_binary(str(desktop / (stem + ".rst")))
    last = int(result.nsets) - 1
    node_index = {int(n): i for i, n in enumerate(result.mesh.nnum)}
    nnum, dof, values = result.nodal_input_force(last)
    evidence["input_forces"] = [
        {"node": int(n), "dof": int(d), "value": float(v),
         "xyz": [float(x) for x in result.mesh.nodes[node_index[int(n)]][:3]]}
        for n, d, v in zip(nnum, dof, values) if abs(float(v)) > 1.0e-12
    ]
    _, displacement = result.nodal_solution(last)
    evidence["max_displacement"] = float(np.linalg.norm(displacement, axis=1).max())
    _, stress = result.nodal_stress(last)
    sx, sy, sz, sxy, syz, sxz = np.asarray(stress, dtype=float)[:, :6].T
    mises = np.sqrt(0.5 * ((sx - sy) ** 2 + (sy - sz) ** 2 + (sz - sx) ** 2)
                    + 3.0 * (sxy ** 2 + syz ** 2 + sxz ** 2))
    evidence["max_mises"] = float(np.nanmax(mises))
    (desktop / "v11_inspect.json").write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({"input_forces": evidence["input_forces"],
                      "max_displacement": evidence["max_displacement"],
                      "max_mises": evidence["max_mises"]}))
finally:
    try:
        mapdl.exit()
    except Exception:
        pass
