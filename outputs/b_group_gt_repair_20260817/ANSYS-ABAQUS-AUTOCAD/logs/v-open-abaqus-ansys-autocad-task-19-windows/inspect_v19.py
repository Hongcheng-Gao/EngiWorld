import hashlib
import json
import math
from pathlib import Path

import numpy as np
from ansys.mapdl import reader
from ansys.mapdl.core import launch_mapdl


desktop = Path(r"C:\Users\user\Desktop")
db_path = desktop / "wb_buckling.db"
rst_path = desktop / "wb_buckling.rst"


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


result = reader.read_binary(str(rst_path))
last = int(result.nsets) - 1
nodes = np.asarray(result.mesh.nodes, dtype=float)
forces = records(result, "nodal_input_force", last)
bcs = records(result, "nodal_boundary_conditions", last)


def end_codes(y_value):
    return sorted(
        set(
            code
            for code, value, xyz in bcs
            if xyz is not None
            and abs(xyz[1] - y_value) <= 0.1
            and abs(value) <= 1.0e-10
        )
    )


first_factor = float(result.time_values[0])
euler_factor = math.pi ** 2 * 210000.0 * (10.0 * 10.0 ** 3 / 12.0) / 1000.0 ** 2
evidence = {
    "db": {"size": db_path.stat().st_size, "sha256": sha256(db_path)},
    "rst": {"size": rst_path.stat().st_size, "sha256": sha256(rst_path)},
    "bbox": {
        axis: [float(nodes[:, index].min()), float(nodes[:, index].max())]
        for index, axis in enumerate(("x", "y", "z"))
    },
    "node_count": int(result.mesh.nnum.size),
    "element_count": int(result.mesh.enum.size),
    "element_types": sorted(set(int(value) for value in result.mesh.etype)),
    "result_sets": int(result.nsets),
    "time_values": [float(value) for value in result.time_values],
    "first_buckling_factor": first_factor,
    "euler_pin_pin_factor": euler_factor,
    "factor_relative_error_to_euler": abs(first_factor - euler_factor) / euler_factor,
    "nonzero_force_records": [
        {"dof_code": code, "value": value, "xyz": xyz}
        for code, value, xyz in forces
        if abs(value) > 1.0e-12
    ],
    "total_fy": sum(value for code, value, _ in forces if code == 2),
    "bottom_constraint_dof_codes": end_codes(0.0),
    "top_constraint_dof_codes": end_codes(1000.0),
}

mapdl = launch_mapdl(
    exec_file=r"C:\Program Files\ANSYS Inc\v261\ansys\bin\winx64\ANSYS261.exe",
    jobname="inspect_v19",
    run_location=str(desktop),
    nproc=1,
    override=True,
    cleanup_on_exit=True,
    license_type="meba",
    start_timeout=180,
)
try:
    mapdl.resume(str(db_path.with_suffix("")), "db")
    mapdl.prep7()
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
        "section_listing": mapdl.run("SLIST,ALL"),
        "material_listing": mapdl.run("MPLIST,ALL"),
        "constraint_listing": mapdl.run("DLIST,ALL"),
        "load_listing": mapdl.run("FLIST,ALL"),
        "analysis_status": mapdl.run("STAT,SOLU"),
    }
    mapdl.post1()
    mapdl.file(str(rst_path.with_suffix("")), "rst")
    mapdl.set(1, 1)
    mode_components = {
        component: [float(value) for value in mapdl.post_processing.nodal_displacement(component)]
        for component in ("X", "Y", "Z")
    }
    evidence["mapdl_native_result"] = {
        "first_buckling_factor": float(mapdl.get_value("MODE", 1, "FREQ")),
        "translation_component_ranges": {
            component: [min(values), max(values)]
            for component, values in mode_components.items()
        },
    }
finally:
    try:
        mapdl.exit()
    except Exception:
        pass

(desktop / "v19_inspect.json").write_text(
    json.dumps(evidence, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
print(json.dumps({
    "bbox": evidence["bbox"],
    "element_types": evidence["element_types"],
    "first_buckling_factor": evidence["first_buckling_factor"],
    "euler_pin_pin_factor": evidence["euler_pin_pin_factor"],
    "total_fy": evidence["total_fy"],
    "bottom_codes": evidence["bottom_constraint_dof_codes"],
    "top_codes": evidence["top_constraint_dof_codes"],
}, sort_keys=True))
