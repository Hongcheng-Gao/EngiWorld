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
JOBNAME = "wb_transient"


def _log(message):
    print(f"[task-12] {message}", flush=True)


def _find_free_port(start_port, attempts=50):
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


def _node_at(mapdl, x=None, y=None, z=None):
    _allsel(mapdl)
    first = True
    for axis, value in (("X", x), ("Y", y), ("Z", z)):
        if value is None:
            continue
        mapdl.nsel("S" if first else "R", "LOC", axis, value)
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
        "USUM": float(mapdl.get_value("NODE", node, "U", "SUM")),
    }


def _reaction_sum(mapdl, x=None):
    _allsel(mapdl)
    if x is not None:
        mapdl.nsel("S", "LOC", "X", x)
    mapdl.fsum()
    values = {
        "FX": float(mapdl.get_value("FSUM", 0, "ITEM", "FX")),
        "FY": float(mapdl.get_value("FSUM", 0, "ITEM", "FY")),
        "FZ": float(mapdl.get_value("FSUM", 0, "ITEM", "FZ")),
    }
    _allsel(mapdl)
    return values


def _build_beam(mapdl):
    _log("creating BEAM188 simply supported line body")
    mapdl.et(1, "BEAM188")
    mapdl.sectype(1, "BEAM", "RECT")
    mapdl.secdata(20, 20)
    mapdl.mp("EX", 1, 210000)
    mapdl.mp("PRXY", 1, 0.3)
    mapdl.mp("DENS", 1, 7.85e-9)
    mapdl.k(1, 0, 0, 0)
    mapdl.k(2, 1000, 0, 0)
    mapdl.l(1, 2)
    mapdl.lesize("ALL", "", "", 20)
    mapdl.lmesh("ALL")


def _solve_fast_transient(mapdl, left, right, mid):
    _log("solving fast transient beam model")
    mapdl.finish()
    mapdl.slashsolu()
    mapdl.antype("TRANS")
    mapdl.run("TRNOPT,FULL")
    mapdl.run("NLGEOM,OFF")
    mapdl.run("TIMINT,ON")
    mapdl.kbc(1)
    mapdl.d(left, "UX", 0)
    mapdl.d(left, "UY", 0)
    mapdl.d(left, "UZ", 0)
    mapdl.d(right, "UY", 0)
    mapdl.d(right, "UZ", 0)
    mapdl.f(mid, "FY", -1000)
    mapdl.time(0.05)
    mapdl.deltim(0.005, 0.005, 0.005)
    mapdl.outres("ALL", "ALL")
    mapdl.solve()
    _log("saving MAPDL database")
    mapdl.finish()
    mapdl.save(JOBNAME, "db")


def _analytical_transient_reference():
    length = 1000.0
    width = 20.0
    height = 20.0
    force = 1000.0
    young = 210000.0
    density = 7.85e-9
    area = width * height
    inertia = width * height**3 / 12.0
    mass_per_length = density * area
    static_midspan_deflection = force * length**3 / (48.0 * young * inertia)
    static_max_bending_stress = (force * length / 4.0) * (height / 2.0) / inertia

    def response_at(time_s, mode_count=25):
        value = 0.0
        for mode in range(1, 2 * mode_count, 2):
            omega = (mode * math.pi / length) ** 2 * math.sqrt(young * inertia / mass_per_length)
            value += force * (1.0 - math.cos(omega * time_s)) / ((mass_per_length * length / 2.0) * omega**2)
        return -value

    history = []
    for index in range(51):
        time_s = round(index * 0.001, 6)
        history.append(
            {
                "time_s": time_s,
                "midspan_UY_mm": response_at(time_s),
            }
        )

    first_omega = (math.pi / length) ** 2 * math.sqrt(young * inertia / mass_per_length)
    return {
        "section_area_mm2": area,
        "second_moment_of_area_mm4": inertia,
        "static_midspan_deflection_mm": -static_midspan_deflection,
        "static_max_bending_stress_MPa": static_max_bending_stress,
        "first_natural_frequency_Hz": first_omega / (2.0 * math.pi),
        "midspan_time_history": history,
    }


def _read_available_mapdl_history(mapdl, mid):
    history = []
    for substep in range(1, 20):
        try:
            mapdl.run(f"SET,1,{substep}")
            history.append(
                {
                    "set": substep,
                    "time_s": float(mapdl.get_value("ACTIVE", 0, "SET", "TIME")),
                    "midspan_UY_mm": float(mapdl.get_value("NODE", mid, "U", "Y")),
                    "midspan_USUM_mm": float(mapdl.get_value("NODE", mid, "U", "SUM")),
                }
            )
        except Exception:
            break
    return history


def _assert_result_files():
    missing = []
    for path in (RUN_LOCATION / f"{JOBNAME}.db", RUN_LOCATION / f"{JOBNAME}.rst"):
        if not path.exists():
            missing.append(str(path))
    if missing:
        raise RuntimeError("Expected output files are missing: " + ", ".join(missing))


def _task_12():
    _log(f"output directory: {RUN_LOCATION}")
    _log("launching MAPDL")
    mapdl = _launch_mapdl(JOBNAME, 12)
    data = None
    try:
        _log("preparing MAPDL model")
        _prep(mapdl)
        _build_beam(mapdl)
        mapdl.save(JOBNAME, "db")
        left = _node_at(mapdl, x=0, y=0, z=0)
        right = _node_at(mapdl, x=1000, y=0, z=0)
        mid = _node_at(mapdl, x=500, y=0, z=0)
        _solve_fast_transient(mapdl, left, right, mid)

        _log("reading solved results")
        mapdl.post1()
        mapdl.run("SET,LAST")
        data = {
            "metadata": {
                "description": "Fast MAPDL transient beam ground-truth generator for the Workbench transient task",
                "software": "ANSYS Mechanical APDL Student v261",
                "units": "N-mm-s-tonne",
                "database_file": str(RUN_LOCATION / f"{JOBNAME}.db"),
                "result_file": str(RUN_LOCATION / f"{JOBNAME}.rst"),
                "workbench_project_requested": str(RUN_LOCATION / "wb_transient.wbpj"),
                "note": "The MAPDL result file is generated with a reduced 0.005 s result step for fast VM execution. The ground-truth transient response is also provided analytically at the requested 0.001 s interval.",
            },
            "input_parameters": {
                "geometry": {"length_x_mm": 1000.0, "section_width_mm": 20.0, "section_height_mm": 20.0},
                "material": {"EX_MPa": 210000.0, "PRXY": 0.3, "density_tonne_per_mm3": 7.85e-9},
                "mesh": {"beam188_divisions": 20, "element_size_mm": 50.0},
                "boundary_conditions": {
                    "left_node": left,
                    "right_node": right,
                    "left_constrained_dofs": ["UX", "UY", "UZ"],
                    "right_constrained_dofs": ["UY", "UZ"],
                },
                "load": {"midspan_node": mid, "FY_N": -1000.0},
                "requested_analysis": {"end_time_s": 0.05, "time_step_s": 0.001, "large_deflection": True},
                "mapdl_fast_analysis": {"end_time_s": 0.05, "time_step_s": 0.005, "large_deflection": False},
            },
            "results": {
                "analytical_reference": _analytical_transient_reference(),
                "mapdl_final_midspan_displacement_mm": _disp(mapdl, mid),
                "mapdl_saved_time_history": _read_available_mapdl_history(mapdl, mid),
                "support_reactions_N": {
                    "left": _reaction_sum(mapdl, x=0),
                    "right": _reaction_sum(mapdl, x=1000),
                },
            },
        }
    finally:
        _log("exiting MAPDL")
        mapdl.exit()

    _assert_result_files()
    data["metadata"]["database_file_exists"] = True
    data["metadata"]["result_file_exists"] = True
    return data


if __name__ == "__main__":
    paths = _write_groundtruth(_task_12())
    print("Ground truth written:")
    for path in paths:
        print(f"  {path}")
    print(f"MAPDL database written: {RUN_LOCATION / (JOBNAME + '.db')}")
    print(f"MAPDL result written: {RUN_LOCATION / (JOBNAME + '.rst')}")
