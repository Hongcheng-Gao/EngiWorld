import json
import re
from pathlib import Path

import numpy as np
from ansys.mapdl import reader
from ansys.mapdl.core import launch_mapdl


desktop = Path(r"C:\Users\user\Desktop")
stem = "apdl_thermal_stress"
mapdl = launch_mapdl(
    exec_file=r"C:\Program Files\ANSYS Inc\v261\ansys\bin\winx64\ANSYS261.exe",
    jobname="inspect_v17", run_location=str(desktop), nproc=1, override=True,
    cleanup_on_exit=True, license_type="meba", start_timeout=180,
)
try:
    mapdl.resume(str(desktop / stem), "db")
    labels = [int(value) for value in mapdl.mesh.nnum]
    nodes = [[float(value) for value in row[:3]] for row in mapdl.mesh.nodes]
    coordinates = dict(zip(labels, nodes))
    constraints = mapdl.run("DLIST,ALL")
    constraint_records = []
    for line in constraints.splitlines():
        match = re.match(r"\s*(\d+)\s+(UX|UY|UZ)\s+", line)
        if match:
            constraint_records.append({"node": int(match.group(1)), "dof": match.group(2),
                                       "xyz": coordinates[int(match.group(1))]})
    evidence = {
        "bbox": {axis: [min(row[i] for row in nodes), max(row[i] for row in nodes)]
                 for i, axis in enumerate("xyz")},
        "node_count": len(nodes), "element_count": int(mapdl.mesh.n_elem),
        "element_types": mapdl.run("ETLIST,ALL"), "materials": mapdl.run("MPLIST,ALL"),
        "constraints": constraints, "constraint_records": constraint_records,
        "body_loads": mapdl.run("BFLIST,ALL"),
        "element_body_loads": mapdl.run("BFELIST,ALL"),
    }
    result = reader.read_binary(str(desktop / (stem + ".rst")))
    last = int(result.nsets) - 1
    _, temperature = result.nodal_temperature(last)
    temperature = np.asarray(temperature, dtype=float)
    evidence["temperature_range"] = [float(temperature.min()), float(temperature.max())]
    _, stress = result.nodal_stress(last)
    sx, sy, sz, sxy, syz, sxz = np.asarray(stress, dtype=float)[:, :6].T
    mises = np.sqrt(0.5 * ((sx - sy) ** 2 + (sy - sz) ** 2 + (sz - sx) ** 2)
                    + 3.0 * (sxy ** 2 + syz ** 2 + sxz ** 2))
    evidence["max_mises"] = float(np.nanmax(mises))
    try:
        values, _, _ = result.nodal_reaction_forces(last)
        evidence["reaction_force_sum_abs"] = float(np.sum(np.abs(values)))
    except Exception:
        evidence["reaction_force_sum_abs"] = None
    (desktop / "v17_inspect.json").write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"temperature_range": evidence["temperature_range"],
                      "max_mises": evidence["max_mises"],
                      "reaction_force_sum_abs": evidence["reaction_force_sum_abs"]}))
finally:
    try:
        mapdl.exit()
    except Exception:
        pass
