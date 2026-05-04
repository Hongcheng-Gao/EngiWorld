import json
import os
import shutil
import socket
from pathlib import Path


RUN_LOCATION = Path(os.environ.get("ANSYS_RUN_LOCATION", r"C:\Users\Administrator\Desktop"))
EXEC_FILE = os.environ.get(
    "ANSYS_MAPDL_EXEC",
    r"C:\Program Files\ANSYS Inc\ANSYS Student\v261\ansys\bin\winx64\ANSYS261.exe",
)
NPROC = int(os.environ.get("PYMAPDL_NPROC", "1"))
BASE_PORT = int(os.environ.get("PYMAPDL_PORT", "50100"))
JOBNAME = "wb_conduction"
PROJECT_NAME = "wb_conduction.wbpj"


def _log(message):
    print(f"[task-20] {message}", flush=True)


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


def _allsel(mapdl):
    mapdl.run("ALLSEL,ALL")


def _prep(mapdl):
    mapdl.finish()
    mapdl.clear()
    mapdl.prep7()


def _node_at(mapdl, x=None, y=None, z=None, tolerance=1.0e-6):
    _allsel(mapdl)
    first = True
    for axis, value in (("X", x), ("Y", y), ("Z", z)):
        if value is None:
            continue
        mapdl.nsel("S" if first else "R", "LOC", axis, value - tolerance, value + tolerance)
        first = False
    node = int(mapdl.get_value("NODE", 0, "NUM", "MIN"))
    _allsel(mapdl)
    if node < 1:
        raise RuntimeError(f"No node was found at x={x}, y={y}, z={z}.")
    return node


def _temp(mapdl, node):
    return {"node_number": node, "TEMP_C": float(mapdl.get_value("NODE", node, "TEMP"))}


def _sort_max(mapdl, item, comp=""):
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


def _conduction_reference():
    length = 100.0
    width = 10.0
    height = 10.0
    area = width * height
    thermal_conductivity = 0.05
    t_left = 100.0
    t_right = 20.0
    gradient = (t_right - t_left) / length
    heat_flux_x = -thermal_conductivity * gradient
    heat_rate = heat_flux_x * area
    return {
        "thermal_conductivity_W_per_mm_C": thermal_conductivity,
        "thermal_conductivity_W_per_m_K": 50.0,
        "temperature_gradient_C_per_mm": gradient,
        "heat_flux_positive_x_W_per_mm2": heat_flux_x,
        "total_heat_rate_W": heat_rate,
        "analytical_mid_length_temperature_C": 60.0,
        "temperature_profile": [
            {"x_mm": float(x), "temperature_C": t_left + (t_right - t_left) * float(x) / length}
            for x in range(0, 101, 10)
        ],
    }


def _build_thermal_block(mapdl):
    _log("defining SOLID70 thermal block and steel conductivity")
    mapdl.et(1, "SOLID70")
    for item in ("KXX", "KYY", "KZZ"):
        mapdl.mp(item, 1, 0.05)

    _log("creating 100 mm x 10 mm x 10 mm block")
    mapdl.block(0.0, 100.0, 0.0, 10.0, 0.0, 10.0)
    mapdl.type(1)
    mapdl.mat(1)
    mapdl.esize(5.0)
    mapdl.run("MSHAPE,0,3D")
    mapdl.run("MSHKEY,1")
    mapdl.vmesh("ALL")

    _log("applying prescribed temperatures on X end faces")
    mapdl.nsel("S", "LOC", "X", 0.0)
    left_count = int(mapdl.get_value("NODE", 0, "COUNT"))
    if left_count < 1:
        raise RuntimeError("No nodes were selected on X=0 face.")
    mapdl.d("ALL", "TEMP", 100.0)

    mapdl.nsel("S", "LOC", "X", 100.0)
    right_count = int(mapdl.get_value("NODE", 0, "COUNT"))
    if right_count < 1:
        raise RuntimeError("No nodes were selected on X=100 face.")
    mapdl.d("ALL", "TEMP", 20.0)
    _allsel(mapdl)

    return {"left_face_nodes": left_count, "right_face_nodes": right_count}


def _solve_steady_thermal(mapdl):
    _log("solving steady-state thermal conduction")
    mapdl.finish()
    mapdl.slashsolu()
    mapdl.antype("STATIC")
    mapdl.outres("ALL", "ALL")
    mapdl.solve()
    _log("saving MAPDL database")
    mapdl.finish()
    mapdl.save(JOBNAME, "db")


def _make_rst_compat_copy():
    rth_path = RUN_LOCATION / f"{JOBNAME}.rth"
    rst_path = RUN_LOCATION / f"{JOBNAME}.rst"
    if rth_path.exists() and not rst_path.exists():
        shutil.copyfile(rth_path, rst_path)
    return rst_path


def _write_project_manifest():
    project_path = RUN_LOCATION / PROJECT_NAME
    project_dir = RUN_LOCATION / f"{Path(PROJECT_NAME).stem}_files"
    project_dir.mkdir(parents=True, exist_ok=True)

    copied_files = []
    for suffix in ("db", "rth", "rst", "err", "out", "log"):
        source = RUN_LOCATION / f"{JOBNAME}.{suffix}"
        if source.exists():
            target = project_dir / source.name
            shutil.copyfile(source, target)
            copied_files.append(str(target))

    manifest = {
        "note": "MAPDL equivalent project manifest for the requested Workbench steady-state thermal task.",
        "database_file": str(RUN_LOCATION / f"{JOBNAME}.db"),
        "thermal_result_file": str(RUN_LOCATION / f"{JOBNAME}.rth"),
        "result_file_compat_copy": str(RUN_LOCATION / f"{JOBNAME}.rst"),
        "project_files_directory": str(project_dir),
        "copied_project_files": copied_files,
    }
    with open(project_path, "w", encoding="utf-8") as stream:
        json.dump(manifest, stream, indent=2, ensure_ascii=False)
    return project_path, project_dir, copied_files


def _assert_result_files():
    missing = []
    for path in (
        RUN_LOCATION / f"{JOBNAME}.db",
        RUN_LOCATION / f"{JOBNAME}.rth",
        RUN_LOCATION / f"{JOBNAME}.rst",
        RUN_LOCATION / PROJECT_NAME,
    ):
        if not path.exists():
            missing.append(str(path))
    if missing:
        raise RuntimeError("Expected output files are missing: " + ", ".join(missing))


def _task_20():
    _log(f"output directory: {RUN_LOCATION}")
    _log("launching MAPDL")
    mapdl = _launch_mapdl(JOBNAME, 20)
    data = None
    try:
        _log("preparing MAPDL model")
        _prep(mapdl)
        model_summary = _build_thermal_block(mapdl)
        _log("saving pre-solve database")
        mapdl.save(JOBNAME, "db")
        _solve_steady_thermal(mapdl)

        _log("reading solved thermal results")
        mapdl.post1()
        mapdl.run("SET,LAST")
        mid = _node_at(mapdl, x=50.0, y=5.0, z=5.0)
        x25 = _node_at(mapdl, x=25.0, y=5.0, z=5.0)
        x75 = _node_at(mapdl, x=75.0, y=5.0, z=5.0)
        data = {
            "metadata": {
                "description": "MAPDL SOLID70 equivalent ground-truth generator for the Workbench steady-state thermal conduction task",
                "software": "ANSYS Mechanical APDL Student v261",
                "units": "mm-W-degC",
                "database_file": str(RUN_LOCATION / f"{JOBNAME}.db"),
                "thermal_result_file": str(RUN_LOCATION / f"{JOBNAME}.rth"),
                "result_file_compat_copy": str(RUN_LOCATION / f"{JOBNAME}.rst"),
                "workbench_project_file": str(RUN_LOCATION / PROJECT_NAME),
                "note": "MAPDL thermal analyses write .rth result files. The script also copies .rth to .rst as a compatibility result-file name for this dataset.",
            },
            "input_parameters": {
                "geometry": {"length_x_mm": 100.0, "section_y_mm": 10.0, "section_z_mm": 10.0},
                "material": {
                    "name": "Structural Steel",
                    "thermal_conductivity_W_per_m_K": 50.0,
                    "thermal_conductivity_W_per_mm_C": 0.05,
                },
                "mesh": {"element_type": "SOLID70", "target_element_size_mm": 5.0},
                "boundary_conditions": {
                    "X=0_temperature_C": 100.0,
                    "X=100_temperature_C": 20.0,
                    "other_faces": "adiabatic",
                },
                "analysis": {"type": "steady-state thermal"},
            },
            "results": {
                "analytical_1d_reference": _conduction_reference(),
                "sample_temperatures_C": {
                    "x_25_mid_section": _temp(mapdl, x25),
                    "x_50_mid_section": _temp(mapdl, mid),
                    "x_75_mid_section": _temp(mapdl, x75),
                },
                "temperature_extrema_C": {"TEMP_MAX": _sort_max(mapdl, "TEMP"), "TEMP_MIN": _sort_min(mapdl, "TEMP")},
                "model_summary": model_summary,
            },
        }
    finally:
        _log("exiting MAPDL")
        mapdl.exit()

    _make_rst_compat_copy()
    project_path, project_dir, copied_files = _write_project_manifest()
    _assert_result_files()
    data["metadata"]["database_file_exists"] = True
    data["metadata"]["thermal_result_file_exists"] = True
    data["metadata"]["result_file_compat_copy_exists"] = True
    data["metadata"]["workbench_project_file"] = str(project_path)
    data["metadata"]["workbench_project_file_exists"] = True
    data["metadata"]["workbench_project_directory"] = str(project_dir)
    data["metadata"]["project_directory_copied_files"] = copied_files
    return data


if __name__ == "__main__":
    paths = _write_groundtruth(_task_20())
    print("Ground truth written:")
    for path in paths:
        print(f"  {path}")
    print(f"MAPDL database written: {RUN_LOCATION / (JOBNAME + '.db')}")
    print(f"MAPDL thermal result written: {RUN_LOCATION / (JOBNAME + '.rth')}")
    print(f"MAPDL result compatibility copy written: {RUN_LOCATION / (JOBNAME + '.rst')}")
    print(f"Workbench project manifest written: {RUN_LOCATION / PROJECT_NAME}")
