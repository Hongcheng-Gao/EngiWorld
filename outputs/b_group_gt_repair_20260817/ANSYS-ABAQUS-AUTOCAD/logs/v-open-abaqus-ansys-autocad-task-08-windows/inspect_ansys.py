import json
import re
from pathlib import Path

from ansys.mapdl.core import launch_mapdl


desktop = Path(r"C:\Users\user\Desktop")
stem = "gt_task_08_ansys"
mapdl = launch_mapdl(
    exec_file=r"C:\Program Files\ANSYS Inc\v261\ansys\bin\winx64\ANSYS261.exe",
    jobname="inspect_v08",
    run_location=str(desktop),
    nproc=1,
    override=True,
    cleanup_on_exit=True,
    license_type="meba",
    start_timeout=180,
)
try:
    mapdl.resume(str(desktop / stem), "db")
    node_numbers = [int(value) for value in mapdl.mesh.nnum]
    nodes = [[float(value) for value in row[:3]] for row in mapdl.mesh.nodes]
    coordinates = dict(zip(node_numbers, nodes))
    constraints = mapdl.run("DLIST,ALL")
    constrained = sorted(
        {
            int(match.group(1))
            for line in constraints.splitlines()
            if (match := re.match(r"\s*(\d+)\s+(UX|UY|UZ)\s+", line))
        }
    )
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
        "constraints": constraints,
        "constrained_node_coordinates": {
            str(number): coordinates[number] for number in constrained
        },
    }
    mapdl.post1()
    mapdl.file(str(desktop / stem), "rst")
    result = mapdl.result
    evidence["result_set_count"] = int(result.nsets)
    evidence["frequencies_hz"] = [float(value) for value in result.time_values]
    (desktop / "v08_inspect.json").write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"frequencies_hz": evidence["frequencies_hz"]}))
finally:
    try:
        mapdl.exit()
    except Exception:
        pass
