import json
from pathlib import Path

import numpy as np
from ansys.mapdl import reader
from ansys.mapdl.core import launch_mapdl


desktop = Path(r"C:\Users\user\Desktop")
stem = "apdl_hole_plate"
mapdl = launch_mapdl(
    exec_file=r"C:\Program Files\ANSYS Inc\v261\ansys\bin\winx64\ANSYS261.exe",
    jobname="inspect_v13", run_location=str(desktop), nproc=1, override=True,
    cleanup_on_exit=True, license_type="meba", start_timeout=180,
)
try:
    mapdl.resume(str(desktop / stem), "db")
    mesh_nodes = np.asarray(mapdl.mesh.nodes, dtype=float)
    evidence = {
        "bbox": {axis: [float(mesh_nodes[:, i].min()), float(mesh_nodes[:, i].max())]
                 for i, axis in enumerate("xyz")},
        "node_count": int(mapdl.mesh.n_node),
        "element_count": int(mapdl.mesh.n_elem),
        "element_types": mapdl.run("ETLIST,ALL"),
        "real_constants": mapdl.run("RLIST,ALL"),
        "materials": mapdl.run("MPLIST,ALL"),
        "constraints": mapdl.run("DLIST,ALL"),
        "surface_loads": mapdl.run("SFELIST,ALL"),
    }
    result = reader.read_binary(str(desktop / (stem + ".rst")))
    last = int(result.nsets) - 1
    nodes = np.asarray(result.mesh.nodes, dtype=float)
    radius = np.sqrt((nodes[:, 0] - 50.0) ** 2 + (nodes[:, 1] - 100.0) ** 2)
    _, stress = result.nodal_stress(last)
    sx, sy, sz, sxy, syz, sxz = np.asarray(stress, dtype=float)[:, :6].T
    mises = np.sqrt(0.5 * ((sx - sy) ** 2 + (sy - sz) ** 2 + (sz - sx) ** 2)
                    + 3.0 * (sxy ** 2 + syz ** 2 + sxz ** 2))
    peak = int(np.nanargmax(mises))
    evidence["hole_min_radius"] = float(radius.min())
    evidence["hole_nodes_within_0p2"] = int(np.sum(np.abs(radius - 5.0) <= 0.2))
    evidence["max_mises"] = float(mises[peak])
    evidence["max_mises_xyz"] = [float(v) for v in nodes[peak, :3]]
    (desktop / "v13_inspect.json").write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({key: evidence[key] for key in
                      ("node_count", "element_count", "hole_min_radius",
                       "hole_nodes_within_0p2", "max_mises", "max_mises_xyz")}))
finally:
    try:
        mapdl.exit()
    except Exception:
        pass
