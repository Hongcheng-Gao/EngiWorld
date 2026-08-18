import json
import math
from pathlib import Path

from ansys.mapdl.core import launch_mapdl


desktop = Path(r"C:\Users\user\Desktop")
stem = "apdl_plate"
mapdl = launch_mapdl(
    exec_file=r"C:\Program Files\ANSYS Inc\v261\ansys\bin\winx64\ANSYS261.exe",
    jobname="inspect_task12",
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
    model_evidence = {
        "bbox": bbox,
        "element_types": mapdl.run("ETLIST,ALL"),
        "materials": mapdl.run("MPLIST,ALL"),
        "constraints": mapdl.run("DLIST,ALL"),
        "surface_loads": mapdl.run("SFLIST,ALL"),
        "element_surface_loads": mapdl.run("SFELIST,ALL"),
    }
    mapdl.post1()
    mapdl.file(str(desktop / stem), "rst")
    mapdl.set("LAST")
    mapdl.nsel("S", "LOC", "X", 0.0)
    axis_nodes = int(mapdl.get_value("NODE", 0, "COUNT"))
    mapdl.run("NSORT,U,Y,0,1,ALL")
    uy_max = float(mapdl.get_value("SORT", 0, "MAX"))
    uy_min = float(mapdl.get_value("SORT", 0, "MIN"))
    center_deflection = max(abs(uy_max), abs(uy_min))
    mapdl.allsel("ALL")
    mapdl.run("NSORT,S,EQV,0,1,ALL")
    max_stress = abs(float(mapdl.get_value("SORT", 0, "MAX")))
    metrics = {
        "center_deflection": center_deflection,
        "max_stress": max_stress,
    }
    if not all(math.isfinite(value) and value > 0.0 for value in metrics.values()):
        raise RuntimeError("invalid metrics: %r" % metrics)
    (desktop / "metrics.json").write_text(
        json.dumps(metrics, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    model_evidence["axis_node_count"] = axis_nodes
    model_evidence["metrics"] = metrics
    (desktop / "task12_inspect.json").write_text(
        json.dumps(model_evidence, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(metrics, sort_keys=True))
finally:
    try:
        mapdl.exit()
    except Exception:
        pass
