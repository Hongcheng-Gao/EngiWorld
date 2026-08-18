import json
import math
import re
from pathlib import Path

from ansys.mapdl.core import launch_mapdl


desktop = Path(r"C:\Users\user\Desktop")
stem = "wb_hertz"
mapdl = launch_mapdl(
    exec_file=r"C:\Program Files\ANSYS Inc\v261\ansys\bin\winx64\ANSYS261.exe",
    jobname="inspect_task18",
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
        "node_count": len(nodes),
        "element_count": int(mapdl.mesh.n_elem),
        "element_types": mapdl.run("ETLIST,ALL"),
        "materials": mapdl.run("MPLIST,ALL"),
        "constraints": mapdl.run("DLIST,ALL"),
        "nodal_loads": mapdl.run("FLIST,ALL"),
        "surface_loads": mapdl.run("SFLIST,ALL"),
        "element_surface_loads": mapdl.run("SFELIST,ALL"),
    }
    center = [0.0, 10.0, 0.0]
    distances = [
        math.sqrt(sum((row[index] - center[index]) ** 2 for index in range(3)))
        for row in nodes
    ]
    evidence["sphere_surface_node_count_tolerance_0_8"] = sum(
        abs(value - 10.0) <= 0.8 for value in distances
    )

    mapdl.post1()
    mapdl.file(str(desktop / stem), "rst")
    mapdl.set("LAST")
    uy_values = [float(value) for value in mapdl.post_processing.nodal_displacement("Y")]
    mapdl.ignore_errors = True
    contact_text = mapdl.run("PRNSOL,CONT,PRES")
    mapdl.ignore_errors = False
    contact_values = []
    for line in contact_text.splitlines():
        if not re.match(r"^\s*\d+\s", line):
            continue
        tokens = re.findall(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[EeDd][-+]?\d+)?", line)
        if len(tokens) >= 2:
            try:
                int(float(tokens[0]))
                contact_values.append(float(tokens[-1].replace("D", "E").replace("d", "e")))
            except Exception:
                pass
    eqv_values = [float(value) for value in mapdl.post_processing.nodal_eqv_stress()]
    metrics = {
        "max_contact_pressure": (
            max(abs(value) for value in contact_values) if contact_values else None
        ),
        "vertical_displacement": max(abs(value) for value in uy_values),
    }
    evidence["uy_range"] = [min(uy_values), max(uy_values)]
    evidence["contact_pressure_range"] = (
        [min(contact_values), max(contact_values)] if contact_values else None
    )
    evidence["contact_pressure_listing"] = contact_text
    evidence["equivalent_stress_range"] = [min(eqv_values), max(eqv_values)]
    evidence["metrics"] = metrics
    if all(value is not None and math.isfinite(value) for value in metrics.values()):
        (desktop / "metrics.json").write_text(
            json.dumps(metrics, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    (desktop / "task18_inspect.json").write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(metrics, sort_keys=True))
finally:
    try:
        mapdl.exit()
    except Exception:
        pass
