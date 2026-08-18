import json
from pathlib import Path

from ansys.mapdl.core import launch_mapdl


desktop = Path(r"C:\Users\user\Desktop")
stem = "apdl_fixed_beam_modal"
mapdl = launch_mapdl(
    exec_file=r"C:\Program Files\ANSYS Inc\v261\ansys\bin\winx64\ANSYS261.exe",
    jobname="inspect_v15", run_location=str(desktop), nproc=1, override=True,
    cleanup_on_exit=True, license_type="meba", start_timeout=180,
)
try:
    mapdl.resume(str(desktop / stem), "db")
    nodes = [[float(value) for value in row[:3]] for row in mapdl.mesh.nodes]
    evidence = {
        "bbox": {axis: [min(row[i] for row in nodes), max(row[i] for row in nodes)]
                 for i, axis in enumerate("xyz")},
        "node_count": len(nodes), "element_count": int(mapdl.mesh.n_elem),
        "element_types": mapdl.run("ETLIST,ALL"), "sections": mapdl.run("SLIST,ALL"),
        "materials": mapdl.run("MPLIST,ALL"), "constraints": mapdl.run("DLIST,ALL"),
    }
    mapdl.post1()
    mapdl.file(str(desktop / stem), "rst")
    result = mapdl.result
    evidence["result_set_count"] = int(result.nsets)
    evidence["frequencies_hz"] = [float(value) for value in result.time_values]
    (desktop / "v15_inspect.json").write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"node_count": evidence["node_count"],
                      "element_count": evidence["element_count"],
                      "frequencies_hz": evidence["frequencies_hz"]}))
finally:
    try:
        mapdl.exit()
    except Exception:
        pass
