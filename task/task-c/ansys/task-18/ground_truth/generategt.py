import json
import math
import os
import socket
from pathlib import Path


RUN_LOCATION = Path(os.environ.get("ANSYS_RUN_LOCATION", r"C:\Users\Administrator\Desktop"))
EXEC_FILE = os.environ.get(
    "ANSYS_MAPDL_EXEC",
    r"C:\Program Files\ANSYS Inc\ANSYS Student\v261\ansys\bin\winx64\ANSYS261.exe",
)
NPROC = int(os.environ.get("PYMAPDL_NPROC", "1"))
BASE_PORT = int(os.environ.get("PYMAPDL_PORT", "50100"))
JOBNAME = "wb_plate"
PROJECT_NAME = "wb_plate.wbpj"


def _log(message):
    print(f"[task-18] {message}", flush=True)


def _find_free_port(start_port, attempts=80):
    for port in range(start_port, start_port + attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.2)
            if sock.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise RuntimeError(f"No free MAPDL gRPC port found from {start_port} to {start_port + attempts - 1}.")


def _launch_mapdl(jobname, port_offset):
    from ansys.mapdl.core import launch_mapdl

    RUN_LOCATION.mkdir(parents=True, exist_ok=True)
    port = _find_free_port(BASE_PORT + port_offset)
    _log(f"using MAPDL gRPC port {port}")
    return launch_mapdl(
        exec_file=EXEC_FILE,
        jobname=jobname,
        run_location=str(RUN_LOCATION),
        nproc=NPROC,
        port=port,
        override=True,
    )


def _write_groundtruth(data):
    target = RUN_LOCATION / "groundtruth.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "w", encoding="utf-8") as stream:
        json.dump(data, stream, indent=2, ensure_ascii=False)
    return [target]


def _write_project_manifest():
    project_path = RUN_LOCATION / PROJECT_NAME
    project_dir = RUN_LOCATION / f"{Path(PROJECT_NAME).stem}_files"
    project_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "note": "MAPDL equivalent project manifest for the requested Workbench Static Structural plate task.",
        "database_file": str(RUN_LOCATION / f"{JOBNAME}.db"),
        "result_file": str(RUN_LOCATION / f"{JOBNAME}.rst"),
        "project_files_directory": str(project_dir),
    }
    with open(project_path, "w", encoding="utf-8") as stream:
        json.dump(manifest, stream, indent=2, ensure_ascii=False)
    return project_path, project_dir


def _allsel(mapdl):
    mapdl.run("ALLSEL,ALL")


def _prep(mapdl):
    mapdl.finish()
    mapdl.clear()
    mapdl.prep7()


def _node_at(mapdl, x=None, y=None, z=None, tolerance=1.0e-5):
    _allsel(mapdl)
    first = True
    for axis, value in (("X", x), ("Y", y), ("Z", z)):
        if value is None:
            continue
        if tolerance:
            mapdl.nsel("S" if first else "R", "LOC", axis, value - tolerance, value + tolerance)
        else:
            mapdl.nsel("S" if first else "R", "LOC", axis, value)
        first = False
    node = int(mapdl.get_value("NODE", 0, "NUM", "MIN"))
    _allsel(mapdl)
    if node < 1:
        raise RuntimeError(f"No node was found at x={x}, y={y}, z={z}.")
    return node


def _select_edge_nodes(mapdl, axis, value, tolerance=1.0e-5):
    _allsel(mapdl)
    mapdl.nsel("S", "LOC", axis, value - tolerance, value + tolerance)
    count = int(mapdl.get_value("NODE", 0, "COUNT"))
    if count < 1:
        _allsel(mapdl)
        raise RuntimeError(f"No edge nodes were found on {axis}={value}.")
    return count


def _count_selected_nodes(mapdl):
    return int(mapdl.get_value("NODE", 0, "COUNT"))


def _disp(mapdl, node):
    return {
        "node_number": node,
        "UX": float(mapdl.get_value("NODE", node, "U", "X")),
        "UY": float(mapdl.get_value("NODE", node, "U", "Y")),
        "UZ": float(mapdl.get_value("NODE", node, "U", "Z")),
        "USUM": float(mapdl.get_value("NODE", node, "U", "SUM")),
    }


def _sort_max_abs(mapdl, item, comp=""):
    if comp:
        mapdl.run(f"NSORT,{item},{comp},0,1,ALL")
    else:
        mapdl.run(f"NSORT,{item},,0,1,ALL")
    return float(mapdl.get_value("SORT", 0, "MAX"))


def _sort_min(mapdl, item, comp=""):
    if comp:
        mapdl.run(f"NSORT,{item},{comp},0,0,ALL")
    else:
        mapdl.run(f"NSORT,{item},,0,0,ALL")
    return float(mapdl.get_value("SORT", 0, "MIN"))


def _reaction_sum_on_edges(mapdl):
    _allsel(mapdl)
    mapdl.nsel("S", "LOC", "X", 0)
    mapdl.nsel("A", "LOC", "X", 100)
    mapdl.nsel("A", "LOC", "Y", 0)
    mapdl.nsel("A", "LOC", "Y", 100)
    mapdl.fsum()
    values = {
        "FX": float(mapdl.get_value("FSUM", 0, "ITEM", "FX")),
        "FY": float(mapdl.get_value("FSUM", 0, "ITEM", "FY")),
        "FZ": float(mapdl.get_value("FSUM", 0, "ITEM", "FZ")),
    }
    _allsel(mapdl)
    return values


def _simply_supported_plate_reference():
    side = 100.0
    thickness = 1.0
    pressure = 0.1
    young = 210000.0
    poisson = 0.3
    flexural_rigidity = young * thickness**3 / (12.0 * (1.0 - poisson**2))
    center_deflection = 0.00406 * pressure * side**4 / flexural_rigidity
    total_force = pressure * side**2
    return {
        "plate_flexural_rigidity_N_mm": flexural_rigidity,
        "total_downward_force_N": total_force,
        "classical_center_deflection_estimate_mm": -center_deflection,
        "reference_formula": "w_center = 0.00406*q*a^4/D for a simply supported square isotropic plate",
    }


def _apply_equivalent_uniform_pressure(mapdl, nx=20, ny=20):
    pressure = 0.1
    dx = 100.0 / nx
    dy = 100.0 / ny
    total_force = 0.0
    node_force_count = 0

    for j in range(ny + 1):
        y = j * dy
        for i in range(nx + 1):
            x = i * dx
            node = _node_at(mapdl, x=x, y=y, z=0.0)
            x_weight = 0.5 if i in (0, nx) else 1.0
            y_weight = 0.5 if j in (0, ny) else 1.0
            tributary_area = dx * dy * x_weight * y_weight
            force = -pressure * tributary_area
            mapdl.f(node, "FZ", force)
            total_force += force
            node_force_count += 1

    return {"loaded_nodes": node_force_count, "total_FZ_N": total_force}


def _build_plate_model(mapdl):
    _log("defining SHELL181 plate section and structural steel material")
    mapdl.et(1, "SHELL181")
    mapdl.keyopt(1, 3, 2)
    mapdl.sectype(1, "SHELL")
    mapdl.secdata(1.0, 1)
    mapdl.mp("EX", 1, 210000)
    mapdl.mp("PRXY", 1, 0.3)

    _log("creating 100 mm x 100 mm mid-surface in global X-Y plane")
    mapdl.rectng(0, 100, 0, 100)
    mapdl.aatt(1, 1, 1, 0, 1)
    mapdl.esize(5)
    mapdl.run("MSHAPE,0,2D")
    mapdl.run("MSHKEY,1")
    mapdl.amesh("ALL")

    _log("applying simply supported UZ constraints on all four edges")
    edge_counts = {}
    for axis, value in (("X", 0.0), ("X", 100.0), ("Y", 0.0), ("Y", 100.0)):
        count = _select_edge_nodes(mapdl, axis, value)
        edge_counts[f"{axis}={value:g}"] = count
        mapdl.d("ALL", "UZ", 0)
    _allsel(mapdl)

    _log("applying minimum in-plane constraints to prevent rigid-body motion")
    anchor = _node_at(mapdl, x=0.0, y=0.0, z=0.0)
    anti_rotation = _node_at(mapdl, x=100.0, y=0.0, z=0.0)
    mapdl.d(anchor, "UX", 0)
    mapdl.d(anchor, "UY", 0)
    mapdl.d(anti_rotation, "UY", 0)

    _log("applying equivalent uniform pressure in negative global Z")
    load_summary = _apply_equivalent_uniform_pressure(mapdl)
    _allsel(mapdl)

    return {"edge_node_counts": edge_counts, "anchor_node": anchor, "anti_rotation_node": anti_rotation, "load_summary": load_summary}


def _solve_static(mapdl):
    _log("solving static structural plate model")
    mapdl.finish()
    mapdl.slashsolu()
    mapdl.antype("STATIC")
    mapdl.run("NLGEOM,OFF")
    mapdl.run("NSUBST,1,1,1")
    mapdl.outres("ALL", "ALL")
    mapdl.solve()
    _log("saving MAPDL database")
    mapdl.finish()
    mapdl.save(JOBNAME, "db")


def _assert_result_files():
    missing = []
    for path in (RUN_LOCATION / f"{JOBNAME}.db", RUN_LOCATION / f"{JOBNAME}.rst", RUN_LOCATION / PROJECT_NAME):
        if not path.exists():
            missing.append(str(path))
    if missing:
        raise RuntimeError("Expected output files are missing: " + ", ".join(missing))


def _task_18():
    _log(f"output directory: {RUN_LOCATION}")
    _log("launching MAPDL")
    mapdl = _launch_mapdl(JOBNAME, 18)
    data = None
    try:
        _log("preparing MAPDL model")
        _prep(mapdl)
        model_summary = _build_plate_model(mapdl)
        _log("saving pre-solve database")
        mapdl.save(JOBNAME, "db")
        _solve_static(mapdl)

        _log("reading solved results")
        mapdl.post1()
        mapdl.run("SET,LAST")
        center = _node_at(mapdl, x=50.0, y=50.0, z=0.0)
        project_path, project_dir = _write_project_manifest()
        data = {
            "metadata": {
                "description": "MAPDL SHELL181 equivalent ground-truth generator for the Workbench simply supported square plate task",
                "software": "ANSYS Mechanical APDL Student v261",
                "units": "mm-N-MPa",
                "database_file": str(RUN_LOCATION / f"{JOBNAME}.db"),
                "result_file": str(RUN_LOCATION / f"{JOBNAME}.rst"),
                "workbench_project_file": str(project_path),
                "workbench_project_directory": str(project_dir),
                "note": "The requested Workbench static-structural task is reproduced with a direct MAPDL shell model. The pressure is applied as equivalent nodal FZ forces to avoid shell-face normal sign ambiguity across Fluent/MAPDL releases.",
            },
            "input_parameters": {
                "geometry": {"size_x_mm": 100.0, "size_y_mm": 100.0, "thickness_mm": 1.0},
                "material": {"name": "Structural Steel", "EX_MPa": 210000.0, "PRXY": 0.3},
                "mesh": {"element_type": "SHELL181", "target_element_size_mm": 5.0, "mapped_grid": "20 x 20 shell elements"},
                "boundary_conditions": {
                    "simply_supported_edges": ["X=0 UZ=0", "X=100 UZ=0", "Y=0 UZ=0", "Y=100 UZ=0"],
                    "minimum_in_plane_constraints": {
                        "anchor_node": model_summary["anchor_node"],
                        "anchor_constraints": ["UX=0", "UY=0"],
                        "anti_rotation_node": model_summary["anti_rotation_node"],
                        "anti_rotation_constraints": ["UY=0"],
                    },
                },
                "load": {
                    "uniform_pressure_MPa": 0.1,
                    "direction": "-global Z",
                    "equivalent_nodal_load_summary": model_summary["load_summary"],
                },
            },
            "results": {
                "analytical_plate_reference": _simply_supported_plate_reference(),
                "center_displacement_mm": _disp(mapdl, center),
                "minimum_z_displacement_mm": _sort_min(mapdl, "U", "Z"),
                "maximum_total_displacement_mm": _sort_max_abs(mapdl, "U", "SUM"),
                "maximum_von_mises_stress_MPa": _sort_max_abs(mapdl, "S", "EQV"),
                "edge_reaction_sum_N": _reaction_sum_on_edges(mapdl),
                "model_summary": model_summary,
            },
        }
    finally:
        _log("exiting MAPDL")
        mapdl.exit()

    _assert_result_files()
    data["metadata"]["database_file_exists"] = True
    data["metadata"]["result_file_exists"] = True
    data["metadata"]["workbench_project_file_exists"] = True
    return data


if __name__ == "__main__":
    paths = _write_groundtruth(_task_18())
    print("Ground truth written:")
    for path in paths:
        print(f"  {path}")
    print(f"MAPDL database written: {RUN_LOCATION / (JOBNAME + '.db')}")
    print(f"MAPDL result written: {RUN_LOCATION / (JOBNAME + '.rst')}")
    print(f"Workbench project manifest written: {RUN_LOCATION / PROJECT_NAME}")
