import json
import math
from pathlib import Path

from ansys.mapdl.core import launch_mapdl


desktop = Path(r"C:\Users\user\Desktop")
stem = "apdl_hole_plate"
mapdl = launch_mapdl(
    exec_file=r"C:\Program Files\ANSYS Inc\v261\ansys\bin\winx64\ANSYS261.exe",
    jobname="inspect_task13",
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
    radii = [math.hypot(row[0] - 50.0, row[1] - 100.0) for row in nodes]
    evidence = {
        "bbox": {
            "x": [min(row[0] for row in nodes), max(row[0] for row in nodes)],
            "y": [min(row[1] for row in nodes), max(row[1] for row in nodes)],
            "z": [min(row[2] for row in nodes), max(row[2] for row in nodes)],
        },
        "minimum_radius_from_hole_center": min(radii),
        "hole_boundary_node_count": sum(abs(radius - 5.0) <= 0.25 for radius in radii),
        "element_types": mapdl.run("ETLIST,ALL"),
        "real_constants": mapdl.run("RLIST,ALL"),
        "materials": mapdl.run("MPLIST,ALL"),
        "constraints": mapdl.run("DLIST,ALL"),
        "surface_loads": mapdl.run("SFLIST,ALL"),
        "nodal_forces": mapdl.run("FLIST,ALL"),
    }
    mapdl.post1()
    mapdl.file(str(desktop / stem), "rst")
    mapdl.set("LAST")
    mapdl.run("NSORT,S,EQV,0,1,ALL")
    max_stress = abs(float(mapdl.get_value("SORT", 0, "MAX")))
    metrics = {
        "max_stress": max_stress,
        "stress_concentration_proxy": max_stress / 10.0,
    }
    if not all(math.isfinite(value) and value > 0.0 for value in metrics.values()):
        raise RuntimeError("invalid metrics: %r" % metrics)
    (desktop / "metrics.json").write_text(
        json.dumps(metrics, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    evidence["metrics"] = metrics
    (desktop / "task13_inspect.json").write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(metrics, sort_keys=True))
finally:
    try:
        mapdl.exit()
    except Exception:
        pass
