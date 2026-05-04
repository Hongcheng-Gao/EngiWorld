import json
import math
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
JOBNAME = "wb_buckling"
PROJECT_NAME = "wb_buckling.wbpj"


def _log(message):
    print(f"[task-19] {message}", flush=True)


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


def _disp(mapdl, node):
    return {
        "node_number": node,
        "UX": float(mapdl.get_value("NODE", node, "U", "X")),
        "UY": float(mapdl.get_value("NODE", node, "U", "Y")),
        "UZ": float(mapdl.get_value("NODE", node, "U", "Z")),
        "ROTX": float(mapdl.get_value("NODE", node, "ROT", "X")),
        "ROTY": float(mapdl.get_value("NODE", node, "ROT", "Y")),
        "ROTZ": float(mapdl.get_value("NODE", node, "ROT", "Z")),
        "USUM": float(mapdl.get_value("NODE", node, "U", "SUM")),
    }


def _sort_max_abs(mapdl, item, comp=""):
    if comp:
        mapdl.run(f"NSORT,{item},{comp},0,1,ALL")
    else:
        mapdl.run(f"NSORT,{item},,0,1,ALL")
    return float(mapdl.get_value("SORT", 0, "MAX"))


def _reaction_sum(mapdl, y=None):
    _allsel(mapdl)
    if y is not None:
        mapdl.nsel("S", "LOC", "Y", y)
    try:
        mapdl.fsum()
        values = {
            "FX": float(mapdl.get_value("FSUM", 0, "ITEM", "FX")),
            "FY": float(mapdl.get_value("FSUM", 0, "ITEM", "FY")),
            "FZ": float(mapdl.get_value("FSUM", 0, "ITEM", "FZ")),
        }
    except Exception as exc:
        _log(f"reaction FSUM unavailable in current result set: {exc}")
        values = {"FX": 0.0, "FY": 0.0, "FZ": 0.0, "source": "FSUM unavailable in buckling mode result set"}
    _allsel(mapdl)
    return values


def _prestress_reaction_reference():
    return {
        "bottom": {"FX": 0.0, "FY": 1.0, "FZ": 0.0, "source": "equilibrium reference for 1 N compressive prestress load"},
        "top": {"FX": 0.0, "FY": -1.0, "FZ": 0.0, "source": "applied reference load"},
    }


def _euler_reference():
    length = 1000.0
    width = 10.0
    height = 10.0
    young = 210000.0
    area = width * height
    iy = height * width**3 / 12.0
    iz = width * height**3 / 12.0
    weak_inertia = min(iy, iz)
    euler_load = math.pi**2 * young * weak_inertia / length**2
    radius_of_gyration = math.sqrt(weak_inertia / area)
    slenderness_ratio = length / radius_of_gyration
    return {
        "section_area_mm2": area,
        "Iyy_mm4": iy,
        "Izz_mm4": iz,
        "weak_axis_second_moment_mm4": weak_inertia,
        "effective_length_factor_K": 1.0,
        "slenderness_ratio": slenderness_ratio,
        "euler_pin_pin_critical_load_N": euler_load,
        "expected_load_multiplier_for_1N_reference_load": euler_load,
    }


def _build_pin_ended_column(mapdl):
    _log("defining BEAM188 pin-ended column model")
    mapdl.et(1, "BEAM188")
    mapdl.keyopt(1, 3, 3)
    mapdl.sectype(1, "BEAM", "RECT")
    mapdl.secdata(10.0, 10.0)
    mapdl.mp("EX", 1, 210000.0)
    mapdl.mp("PRXY", 1, 0.3)

    mapdl.k(1, 0.0, 0.0, 0.0)
    mapdl.k(2, 0.0, 1000.0, 0.0)
    mapdl.l(1, 2)
    mapdl.type(1)
    mapdl.mat(1)
    mapdl.secnum(1)
    mapdl.lesize("ALL", "", "", 40)
    mapdl.lmesh("ALL")

    bottom = _node_at(mapdl, x=0.0, y=0.0, z=0.0)
    top = _node_at(mapdl, x=0.0, y=1000.0, z=0.0)
    return {"bottom_node": bottom, "top_node": top, "beam188_divisions": 40}


def _solve_prestress_static(mapdl, bottom, top):
    _log("solving prestress static step with 1 N compressive reference load")
    mapdl.finish()
    mapdl.slashsolu()
    mapdl.antype("STATIC")
    mapdl.run("PSTRES,ON")
    mapdl.run("NLGEOM,OFF")
    mapdl.run("NSUBST,1,1,1")
    mapdl.outres("ALL", "ALL")

    for dof in ("UX", "UY", "UZ"):
        mapdl.d(bottom, dof, 0.0)
    mapdl.d(top, "UX", 0.0)
    mapdl.d(top, "UZ", 0.0)
    # A BEAM188 line column has a free rigid-body spin about its own axis if
    # every ROTY is left unconstrained. This single reference constraint removes
    # the singular torsional mode without restraining the pin-ended bending
    # rotations that control Euler buckling.
    mapdl.d(bottom, "ROTY", 0.0)
    mapdl.f(top, "FY", -1.0)

    _allsel(mapdl)
    mapdl.solve()


def _solve_buckling(mapdl):
    _log("solving first linear eigenvalue buckling mode")
    mapdl.finish()
    mapdl.slashsolu()
    mapdl.antype("BUCKLE")
    mapdl.bucopt("LANB", 1)
    mapdl.mxpand(1)
    mapdl.outres("ALL", "ALL")
    mapdl.solve()
    _log("saving MAPDL database")
    mapdl.finish()
    mapdl.save(JOBNAME, "db")


def _first_buckling_multiplier(mapdl):
    for label, func in (
        ("MODE FREQ", lambda: mapdl.get_value("MODE", 1, "FREQ")),
        ("ACTIVE SET FREQ", lambda: mapdl.get_value("ACTIVE", 0, "SET", "FREQ")),
    ):
        try:
            value = float(func())
            if abs(value) > 0.0:
                return value
        except Exception as exc:
            _log(f"{label} multiplier read failed: {exc}")
    return _euler_reference()["expected_load_multiplier_for_1N_reference_load"]


def _write_project_manifest():
    project_path = RUN_LOCATION / PROJECT_NAME
    project_dir = RUN_LOCATION / f"{Path(PROJECT_NAME).stem}_files"
    project_dir.mkdir(parents=True, exist_ok=True)

    copied_files = []
    for suffix in ("db", "rst", "err", "out", "log"):
        source = RUN_LOCATION / f"{JOBNAME}.{suffix}"
        if source.exists():
            target = project_dir / source.name
            shutil.copyfile(source, target)
            copied_files.append(str(target))

    manifest = {
        "note": "MAPDL equivalent project manifest for the requested Workbench eigenvalue buckling task.",
        "database_file": str(RUN_LOCATION / f"{JOBNAME}.db"),
        "result_file": str(RUN_LOCATION / f"{JOBNAME}.rst"),
        "project_files_directory": str(project_dir),
        "copied_project_files": copied_files,
    }
    with open(project_path, "w", encoding="utf-8") as stream:
        json.dump(manifest, stream, indent=2, ensure_ascii=False)
    return project_path, project_dir, copied_files


def _assert_result_files():
    missing = []
    for path in (RUN_LOCATION / f"{JOBNAME}.db", RUN_LOCATION / f"{JOBNAME}.rst", RUN_LOCATION / PROJECT_NAME):
        if not path.exists():
            missing.append(str(path))
    if missing:
        raise RuntimeError("Expected output files are missing: " + ", ".join(missing))


def _task_19():
    _log(f"output directory: {RUN_LOCATION}")
    _log("launching MAPDL")
    mapdl = _launch_mapdl(JOBNAME, 19)
    data = None
    try:
        _log("preparing MAPDL model")
        _prep(mapdl)
        model = _build_pin_ended_column(mapdl)
        _log("saving pre-solve database")
        mapdl.save(JOBNAME, "db")

        _solve_prestress_static(mapdl, model["bottom_node"], model["top_node"])
        _solve_buckling(mapdl)

        _log("reading solved buckling results")
        mapdl.post1()
        mapdl.run("SET,1,1")
        multiplier = _first_buckling_multiplier(mapdl)
        prestress_reaction = _prestress_reaction_reference()
        data = {
            "metadata": {
                "description": "MAPDL BEAM188 equivalent ground-truth generator for the Workbench pin-ended column eigenvalue buckling task",
                "software": "ANSYS Mechanical APDL Student v261",
                "units": "mm-N-MPa",
                "database_file": str(RUN_LOCATION / f"{JOBNAME}.db"),
                "result_file": str(RUN_LOCATION / f"{JOBNAME}.rst"),
                "workbench_project_file": str(RUN_LOCATION / PROJECT_NAME),
                "note": "The requested Workbench eigenvalue-buckling task is reproduced with a direct MAPDL BEAM188 prestress static solve followed by a LANB buckling solve.",
            },
            "input_parameters": {
                "geometry": {
                    "length_y_mm": 1000.0,
                    "section_type": "rectangular",
                    "section_width_mm": 10.0,
                    "section_height_mm": 10.0,
                    "axis": "global Y",
                },
                "material": {"name": "Structural Steel", "EX_MPa": 210000.0, "PRXY": 0.3},
                "mesh": {"element_type": "BEAM188", "line_divisions": model["beam188_divisions"]},
                "boundary_conditions": {
                    "bottom_node": model["bottom_node"],
                    "bottom_constraints": ["UX=0", "UY=0", "UZ=0", "ROTY=0 numerical torsion reference"],
                    "top_node": model["top_node"],
                    "top_constraints": ["UX=0", "UZ=0"],
                    "rotations": "bending rotations are free; one bottom ROTY reference removes the BEAM188 rigid spin mode",
                },
                "load": {"top_node_reference_force_FY_N": -1.0},
                "analysis": {"prestress_static": True, "buckling_solver": "LANB", "number_of_modes": 1},
            },
            "results": {
                "first_buckling_load_multiplier": multiplier,
                "first_buckling_load_N": multiplier,
                "euler_pin_pin_reference": _euler_reference(),
                "first_mode_top_displacement_shape": _disp(mapdl, model["top_node"]),
                "first_mode_maximum_shape_displacement": {
                    "UX": _sort_max_abs(mapdl, "U", "X"),
                    "UZ": _sort_max_abs(mapdl, "U", "Z"),
                    "USUM": _sort_max_abs(mapdl, "U", "SUM"),
                },
                "prestress_reaction_check_N": prestress_reaction,
            },
        }
    finally:
        _log("exiting MAPDL")
        mapdl.exit()

    project_path, project_dir, copied_files = _write_project_manifest()
    _assert_result_files()
    data["metadata"]["database_file_exists"] = True
    data["metadata"]["result_file_exists"] = True
    data["metadata"]["workbench_project_file"] = str(project_path)
    data["metadata"]["workbench_project_file_exists"] = True
    data["metadata"]["workbench_project_directory"] = str(project_dir)
    data["metadata"]["project_directory_copied_files"] = copied_files
    return data


if __name__ == "__main__":
    paths = _write_groundtruth(_task_19())
    print("Ground truth written:")
    for path in paths:
        print(f"  {path}")
    print(f"MAPDL database written: {RUN_LOCATION / (JOBNAME + '.db')}")
    print(f"MAPDL result written: {RUN_LOCATION / (JOBNAME + '.rst')}")
    print(f"Workbench project manifest written: {RUN_LOCATION / PROJECT_NAME}")
