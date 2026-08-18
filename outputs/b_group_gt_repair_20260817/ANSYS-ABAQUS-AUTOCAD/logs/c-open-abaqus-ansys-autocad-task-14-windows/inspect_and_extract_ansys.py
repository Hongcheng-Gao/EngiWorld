import json
import math
from pathlib import Path

from ansys.mapdl.core import launch_mapdl


desktop = Path(r"C:\Users\user\Desktop")
stem = "apdl_transient_thermal"
mapdl = launch_mapdl(
    exec_file=r"C:\Program Files\ANSYS Inc\v261\ansys\bin\winx64\ANSYS261.exe",
    jobname="inspect_task14",
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
        "loads": mapdl.run("BFLIST,ALL"),
    }
    mapdl.post1()
    mapdl.file(str(desktop / stem), "rth")
    mapdl.set("LAST")
    final_time = float(mapdl.get_value("ACTIVE", 0, "SET", "TIME"))

    def temperature_at_x(x_value):
        mapdl.allsel("ALL")
        mapdl.nsel("S", "LOC", "X", x_value)
        mapdl.nsel("R", "LOC", "Y", 10.0)
        mapdl.nsel("R", "LOC", "Z", 10.0)
        node_id = int(mapdl.get_value("NODE", 0, "NUM", "MIN"))
        if node_id < 1:
            raise RuntimeError("probe node missing at x=%s" % x_value)
        value = float(mapdl.get_value("NODE", node_id, "TEMP"))
        return node_id, value

    node4, temp4 = temperature_at_x(4.0)
    node6, temp6 = temperature_at_x(6.0)
    mapdl.allsel("ALL")
    metrics = {
        "probe_temperature": temp4,
        "time_value": final_time,
    }
    if not all(math.isfinite(value) for value in metrics.values()):
        raise RuntimeError("invalid metrics: %r" % metrics)
    (desktop / "metrics.json").write_text(
        json.dumps(metrics, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    evidence["probes"] = {
        "x4": {"node": node4, "temperature": temp4},
        "x6": {"node": node6, "temperature": temp6},
    }
    evidence["metrics"] = metrics
    (desktop / "task14_inspect.json").write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(metrics, sort_keys=True))
finally:
    try:
        mapdl.exit()
    except Exception:
        pass
