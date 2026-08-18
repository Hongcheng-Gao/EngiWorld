import hashlib
import json
from pathlib import Path

import numpy as np
from ansys.mapdl import reader
from ansys.mapdl.core import launch_mapdl


desktop = Path(r"C:\Users\user\Desktop")
db_path = desktop / "wb_conduction.db"
rth_path = desktop / "wb_conduction.rth"


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def boundary_records(result, set_index):
    nnum, dof, values = result.nodal_boundary_conditions(set_index)
    node_index = {int(node): index for index, node in enumerate(result.mesh.nnum)}
    output = []
    for node, code, value in zip(nnum, dof, values):
        index = node_index.get(int(node))
        xyz = None if index is None else tuple(float(v) for v in result.mesh.nodes[index][:3])
        output.append((int(code), float(value), xyz))
    return output


result = reader.read_binary(str(rth_path))
last = int(result.nsets) - 1
nodes = np.asarray(result.mesh.nodes, dtype=float)
nnum, values = result.nodal_temperature(last)
node_index = {int(node): index for index, node in enumerate(result.mesh.nnum)}
temperatures = np.full(len(result.mesh.nnum), np.nan, dtype=float)
for node, value in zip(nnum, values):
    index = node_index.get(int(node))
    if index is not None:
        temperatures[index] = float(value)
bcs = boundary_records(result, last)
reaction_values, reaction_nodes, _ = result.nodal_reaction_forces(last)
reactions = []
for value, node in zip(reaction_values, reaction_nodes):
    index = node_index.get(int(node))
    xyz = None if index is None else tuple(float(v) for v in nodes[index][:3])
    reactions.append((float(value), xyz))

left_node_mask = np.isclose(nodes[:, 0], 0.0, atol=0.1)
right_node_mask = np.isclose(nodes[:, 0], 100.0, atol=0.1)
mid_node_mask = np.isclose(nodes[:, 0], 50.0, atol=0.1)
thermal_bcs = [(value, xyz) for code, value, xyz in bcs if code == 20 and xyz is not None]

evidence = {
    "db": {"size": db_path.stat().st_size, "sha256": sha256(db_path)},
    "rth": {"size": rth_path.stat().st_size, "sha256": sha256(rth_path)},
    "bbox": {
        axis: [float(nodes[:, index].min()), float(nodes[:, index].max())]
        for index, axis in enumerate(("x", "y", "z"))
    },
    "node_count": int(result.mesh.nnum.size),
    "element_count": int(result.mesh.enum.size),
    "element_types": sorted(set(int(value) for value in result.mesh.etype)),
    "result_sets": int(result.nsets),
    "time_values": [float(value) for value in result.time_values],
    "temperature_range": [
        float(np.nanmin(temperatures)),
        float(np.nanmax(temperatures)),
    ],
    "left_face_node_count": int(np.count_nonzero(left_node_mask)),
    "right_face_node_count": int(np.count_nonzero(right_node_mask)),
    "mid_face_node_count": int(np.count_nonzero(mid_node_mask)),
    "left_face_temperature_range": [
        float(np.nanmin(temperatures[left_node_mask])),
        float(np.nanmax(temperatures[left_node_mask])),
    ],
    "right_face_temperature_range": [
        float(np.nanmin(temperatures[right_node_mask])),
        float(np.nanmax(temperatures[right_node_mask])),
    ],
    "mid_face_temperature_range": [
        float(np.nanmin(temperatures[mid_node_mask])),
        float(np.nanmax(temperatures[mid_node_mask])),
    ],
    "left_face_temp_bc_count": sum(
        1 for value, xyz in thermal_bcs if abs(xyz[0]) <= 0.1 and abs(value - 100.0) <= 1.0e-8
    ),
    "right_face_temp_bc_count": sum(
        1 for value, xyz in thermal_bcs if abs(xyz[0] - 100.0) <= 0.1 and abs(value - 20.0) <= 1.0e-8
    ),
    "invalid_temp_bcs": [
        {"value": value, "xyz": xyz}
        for value, xyz in thermal_bcs
        if not (
            (abs(xyz[0]) <= 0.1 and abs(value - 100.0) <= 1.0e-8)
            or (abs(xyz[0] - 100.0) <= 0.1 and abs(value - 20.0) <= 1.0e-8)
        )
    ],
    "left_heat_reaction": sum(
        value for value, xyz in reactions if xyz is not None and abs(xyz[0]) <= 0.1
    ),
    "right_heat_reaction": sum(
        value for value, xyz in reactions if xyz is not None and abs(xyz[0] - 100.0) <= 0.1
    ),
    "theoretical_heat_flow": 0.05 * 10.0 * 10.0 * (100.0 - 20.0) / 100.0,
}

mapdl = launch_mapdl(
    exec_file=r"C:\Program Files\ANSYS Inc\v261\ansys\bin\winx64\ANSYS261.exe",
    jobname="inspect_v20",
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
        "temperature_constraint_listing": mapdl.run("DLIST,ALL"),
        "nodal_load_listing": mapdl.run("FLIST,ALL"),
        "surface_load_listing": mapdl.run("SFLIST,ALL"),
        "body_load_listing": mapdl.run("BFLIST,ALL"),
    }
    mapdl.slashsolu()
    evidence["mapdl_native_model"]["solution_status"] = mapdl.run("STATUS,SOLU")
finally:
    try:
        mapdl.exit()
    except Exception:
        pass

(desktop / "v20_inspect.json").write_text(
    json.dumps(evidence, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
print(json.dumps({
    "bbox": evidence["bbox"],
    "element_types": evidence["element_types"],
    "temperature_range": evidence["temperature_range"],
    "mid_face_temperature_range": evidence["mid_face_temperature_range"],
    "left_temp_bc_count": evidence["left_face_temp_bc_count"],
    "right_temp_bc_count": evidence["right_face_temp_bc_count"],
    "left_heat_reaction": evidence["left_heat_reaction"],
    "right_heat_reaction": evidence["right_heat_reaction"],
}, sort_keys=True))
