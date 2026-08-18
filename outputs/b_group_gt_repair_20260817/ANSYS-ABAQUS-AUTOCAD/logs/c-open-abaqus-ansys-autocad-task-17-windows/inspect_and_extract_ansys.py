import json
import math
from pathlib import Path

from ansys.mapdl.core import launch_mapdl


desktop = Path(r"C:\Users\user\Desktop")
stem = "apdl_thermal_stress"
mapdl = launch_mapdl(
    exec_file=r"C:\Program Files\ANSYS Inc\v261\ansys\bin\winx64\ANSYS261.exe",
    jobname="inspect_task17",
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
    evidence = {
        "bbox": {
            "x": [min(row[0] for row in nodes), max(row[0] for row in nodes)],
            "y": [min(row[1] for row in nodes), max(row[1] for row in nodes)],
            "z": [min(row[2] for row in nodes), max(row[2] for row in nodes)],
        },
        "element_types": mapdl.run("ETLIST,ALL"),
        "materials": mapdl.run("MPLIST,ALL"),
        "constraints": mapdl.run("DLIST,ALL"),
        "body_loads": mapdl.run("BFLIST,ALL"),
        "element_body_loads": mapdl.run("BFELIST,ALL"),
    }
    mapdl.post1()
    mapdl.file(str(desktop / stem), "rst")
    mapdl.set("LAST")
    mapdl.run("NSORT,S,EQV,0,1,ALL")
    thermal_stress = abs(float(mapdl.get_value("SORT", 0, "MAX")))
    result = mapdl.result
    last_set = int(result.nsets) - 1
    reactions, _, components = result.nodal_reaction_forces(last_set)
    axial_absolute_total = sum(
        abs(float(value))
        for value, component in zip(reactions, components)
        if int(component) == 1
    )
    reaction_force = axial_absolute_total / 2.0
    metrics = {
        "reaction_force_optional": reaction_force,
        "thermal_stress": thermal_stress,
    }
    if not all(math.isfinite(value) for value in metrics.values()):
        raise RuntimeError("invalid metrics: %r" % metrics)
    (desktop / "metrics.json").write_text(
        json.dumps(metrics, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    evidence["axial_absolute_reaction_total"] = axial_absolute_total
    evidence["metrics"] = metrics
    (desktop / "task17_inspect.json").write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(metrics, sort_keys=True))
finally:
    try:
        mapdl.exit()
    except Exception:
        pass
