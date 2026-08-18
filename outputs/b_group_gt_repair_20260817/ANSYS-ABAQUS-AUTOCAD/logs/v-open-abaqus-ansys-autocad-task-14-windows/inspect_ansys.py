import json
from pathlib import Path

import numpy as np
from ansys.mapdl import reader
from ansys.mapdl.core import launch_mapdl


desktop = Path(r"C:\Users\user\Desktop")
stem = "apdl_transient_thermal"
mapdl = launch_mapdl(
    exec_file=r"C:\Program Files\ANSYS Inc\v261\ansys\bin\winx64\ANSYS261.exe",
    jobname="inspect_v14", run_location=str(desktop), nproc=1, override=True,
    cleanup_on_exit=True, license_type="meba", start_timeout=180,
)
try:
    mapdl.resume(str(desktop / stem), "db")
    evidence = {
        "node_count": int(mapdl.mesh.n_node), "element_count": int(mapdl.mesh.n_elem),
        "element_types": mapdl.run("ETLIST,ALL"), "materials": mapdl.run("MPLIST,ALL"),
        "temperature_constraints": mapdl.run("DLIST,ALL"),
    }
    result = reader.read_binary(str(desktop / (stem + ".rth")))
    last = int(result.nsets) - 1
    nodes = np.asarray(result.mesh.nodes, dtype=float)
    _, temperature = result.nodal_temperature(last)
    temperature = np.asarray(temperature, dtype=float)
    evidence["bbox"] = {axis: [float(nodes[:, i].min()), float(nodes[:, i].max())]
                        for i, axis in enumerate("xyz")}
    evidence["result_set_count"] = int(result.nsets)
    evidence["final_time"] = float(result.time_values[-1])
    evidence["temperature_range"] = [float(temperature.min()), float(temperature.max())]
    evidence["probe_sections"] = {}
    for x in (0.0, 4.0, 6.0, 50.0):
        values = temperature[np.isclose(nodes[:, 0], x, atol=0.1)]
        evidence["probe_sections"][str(x)] = {
            "count": int(len(values)), "min": float(values.min()),
            "mean": float(values.mean()), "max": float(values.max())}
    (desktop / "v14_inspect.json").write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"element_count": evidence["element_count"],
                      "final_time": evidence["final_time"],
                      "probe_sections": evidence["probe_sections"]}))
finally:
    try:
        mapdl.exit()
    except Exception:
        pass
