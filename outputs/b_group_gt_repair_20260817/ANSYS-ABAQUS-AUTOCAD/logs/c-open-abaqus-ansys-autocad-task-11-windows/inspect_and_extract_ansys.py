import json
import math
from pathlib import Path

from ansys.mapdl.core import launch_mapdl


desktop = Path(r"C:\Users\user\Desktop")
stem = "apdl_solid_beam"
mapdl = launch_mapdl(
    exec_file=r"C:\Program Files\ANSYS Inc\v261\ansys\bin\winx64\ANSYS261.exe",
    jobname="inspect_task11",
    run_location=str(desktop),
    nproc=1,
    override=True,
    cleanup_on_exit=True,
    license_type="meba",
    start_timeout=180,
)
try:
    mapdl.resume(str(desktop / stem), "db")
    nodes = [[float(value) for value in row[:3]] for row in mapdl.mesh.nodes]
    bbox = {
        "x": [min(row[0] for row in nodes), max(row[0] for row in nodes)],
        "y": [min(row[1] for row in nodes), max(row[1] for row in nodes)],
        "z": [min(row[2] for row in nodes), max(row[2] for row in nodes)],
    }
    element_types = mapdl.run("ETLIST,ALL")
    materials = mapdl.run("MPLIST,ALL")
    constraints = mapdl.run("DLIST,ALL")
    forces = mapdl.run("FLIST,ALL")

    mapdl.post1()
    mapdl.file(str(desktop / stem), "rst")
    mapdl.set("LAST")
    mapdl.nsel("S", "LOC", "X", 5.0)
    mapdl.nsel("R", "LOC", "Y", 10.0)
    mapdl.nsel("R", "LOC", "Z", 100.0)
    node_id = int(mapdl.get_value("NODE", 0, "NUM", "MIN"))
    tip_displacement = abs(float(mapdl.get_value("NODE", node_id, "U", "Y")))
    mapdl.allsel("ALL")
    mapdl.run("NSORT,S,EQV,0,1,ALL")
    max_mises = abs(float(mapdl.get_value("SORT", 0, "MAX")))
    metrics = {
        "max_mises": max_mises,
        "tip_displacement": tip_displacement,
    }
    if not all(math.isfinite(value) and value > 0.0 for value in metrics.values()):
        raise RuntimeError("invalid metrics: %r" % metrics)
    (desktop / "metrics.json").write_text(
        json.dumps(metrics, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    report = {
        "bbox": bbox,
        "element_types": element_types,
        "materials": materials,
        "constraints": constraints,
        "forces": forces,
        "tip_node": node_id,
        "metrics": metrics,
    }
    (desktop / "task11_inspect.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(metrics, sort_keys=True))
finally:
    try:
        mapdl.exit()
    except Exception:
        pass
