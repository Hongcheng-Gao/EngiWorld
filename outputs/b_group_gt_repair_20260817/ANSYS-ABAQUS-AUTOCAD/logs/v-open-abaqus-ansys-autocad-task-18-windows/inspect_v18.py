import hashlib
import json
import math
from pathlib import Path

import numpy as np
from ansys.mapdl import reader
from ansys.mapdl.core import launch_mapdl


desktop = Path(r"C:\Users\user\Desktop")
db_path = desktop / "wb_hertz.db"
rst_path = desktop / "wb_hertz.rst"


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def records(result, method_name, set_index):
    nnum, dof, values = getattr(result, method_name)(set_index)
    node_index = {int(node): index for index, node in enumerate(result.mesh.nnum)}
    output = []
    for node, code, value in zip(nnum, dof, values):
        index = node_index.get(int(node))
        xyz = None if index is None else tuple(float(v) for v in result.mesh.nodes[index][:3])
        output.append((int(code), float(value), xyz))
    return output


def contact_pressure_max(result, set_index, element_type_by_number):
    enum, element_data, _ = result.element_solution_data(set_index, "ECT")
    observed = []
    for element_number, values in zip(enum, element_data):
        if element_type_by_number.get(int(element_number)) not in (171, 172, 173, 174, 175, 176, 177):
            continue
        if values is None:
            continue
        flat = np.asarray(values, dtype=float).ravel()
        pressures = flat[2:-1:10]
        pressures = pressures[np.isfinite(pressures)]
        if pressures.size:
            observed.append(float(np.max(pressures)))
    return max(observed) if observed else None


result = reader.read_binary(str(rst_path))
last = int(result.nsets) - 1
nodes = np.asarray(result.mesh.nodes, dtype=float)
element_types = sorted(set(int(value) for value in result.mesh.etype))
element_type_by_number = {
    int(number): int(etype)
    for number, etype in zip(result.mesh.enum, result.mesh.etype)
}
forces = records(result, "nodal_input_force", last)
bcs = records(result, "nodal_boundary_conditions", last)
_, displacement = result.nodal_solution(last)
displacement = np.asarray(displacement, dtype=float)
sphere_radius = np.sqrt(
    nodes[:, 0] ** 2 + (nodes[:, 1] - 10.0) ** 2 + nodes[:, 2] ** 2
)

bottom_bc_counts = {
    str(code): sum(
        1
        for observed_code, value, xyz in bcs
        if observed_code == code
        and xyz is not None
        and abs(xyz[1] + 10.0) <= 0.1
        and abs(value) <= 1.0e-10
    )
    for code in (1, 2, 3)
}
top_bc_counts = {
    str(code): sum(
        1
        for observed_code, value, xyz in bcs
        if observed_code == code
        and xyz is not None
        and xyz[1] >= 19.4
        and abs(value) <= 1.0e-10
    )
    for code in (1, 2, 3)
}

evidence = {
    "db": {"size": db_path.stat().st_size, "sha256": sha256(db_path)},
    "rst": {"size": rst_path.stat().st_size, "sha256": sha256(rst_path)},
    "result_sets": int(result.nsets),
    "time_values": [float(value) for value in result.time_values],
    "bbox": {
        axis: [float(nodes[:, index].min()), float(nodes[:, index].max())]
        for index, axis in enumerate(("x", "y", "z"))
    },
    "node_count": int(result.mesh.nnum.size),
    "element_count": int(result.mesh.enum.size),
    "element_types": element_types,
    "sphere_surface_node_count_tolerance_0_08": int(
        np.count_nonzero(
            (nodes[:, 1] >= -0.1) & np.isclose(sphere_radius, 10.0, atol=0.08)
        )
    ),
    "total_fy": sum(value for code, value, _ in forces if code == 2),
    "nonzero_fy_record_count": sum(
        1 for code, value, _ in forces if code == 2 and abs(value) > 1.0e-12
    ),
    "bottom_bc_counts_by_dof_code": bottom_bc_counts,
    "sphere_top_bc_counts_by_dof_code": top_bc_counts,
    "contact_pressure_max": contact_pressure_max(result, last, element_type_by_number),
    "uy_range": [
        float(np.nanmin(displacement[:, 1])),
        float(np.nanmax(displacement[:, 1])),
    ],
}

mapdl = launch_mapdl(
    exec_file=r"C:\Program Files\ANSYS Inc\v261\ansys\bin\winx64\ANSYS261.exe",
    jobname="inspect_v18",
    run_location=str(desktop),
    nproc=1,
    override=True,
    cleanup_on_exit=True,
    license_type="meba",
    start_timeout=180,
)
try:
    mapdl.resume(str(db_path.with_suffix("")), "db")
    mapdl_nodes = [[float(value) for value in row[:3]] for row in mapdl.mesh.nodes]
    evidence["mapdl_native_model"] = {
        "node_count": len(mapdl_nodes),
        "element_count": int(mapdl.mesh.n_elem),
        "bbox": {
            axis: [
                min(row[index] for row in mapdl_nodes),
                max(row[index] for row in mapdl_nodes),
            ]
            for index, axis in enumerate(("x", "y", "z"))
        },
        "element_type_listing": mapdl.run("ETLIST,ALL"),
        "material_listing": mapdl.run("MPLIST,ALL"),
        "analysis_status": mapdl.run("STAT,SOLU"),
    }
finally:
    try:
        mapdl.exit()
    except Exception:
        pass

(desktop / "v18_inspect.json").write_text(
    json.dumps(evidence, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
print(json.dumps({
    "bbox": evidence["bbox"],
    "node_count": evidence["node_count"],
    "element_count": evidence["element_count"],
    "element_types": evidence["element_types"],
    "sphere_surface_nodes": evidence["sphere_surface_node_count_tolerance_0_08"],
    "total_fy": evidence["total_fy"],
    "contact_pressure_max": evidence["contact_pressure_max"],
    "uy_range": evidence["uy_range"],
}, sort_keys=True))
