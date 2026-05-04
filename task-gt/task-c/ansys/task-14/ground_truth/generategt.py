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
JOBNAME = "apdl_harmonic"


def _log(message):
    print(f"[task-14] {message}", flush=True)


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


def _sort_max(mapdl, item, comp=""):
    if comp:
        mapdl.run(f"NSORT,{item},{comp},0,1,ALL")
    else:
        mapdl.run(f"NSORT,{item},,0,1,ALL")
    return float(mapdl.get_value("SORT", 0, "MAX"))


def _build_beam(mapdl):
    _log("creating BEAM188 cantilever line body")
    mapdl.et(1, "BEAM188")
    mapdl.sectype(1, "BEAM", "RECT")
    mapdl.secdata(10, 10)
    mapdl.mp("EX", 1, 210000)
    mapdl.mp("PRXY", 1, 0.3)
    mapdl.mp("DENS", 1, 7.85e-9)
    mapdl.k(1, 0, 0, 0)
    mapdl.k(2, 500, 0, 0)
    mapdl.l(1, 2)
    mapdl.lesize("ALL", "", "", 20)
    mapdl.lmesh("ALL")


def _solve_harmonic(mapdl, fixed, free):
    _log("solving single-point full harmonic response at 5 Hz")
    mapdl.finish()
    mapdl.slashsolu()
    mapdl.antype("HARMIC")
    mapdl.run("HROPT,FULL")
    mapdl.harfrq(5, 5)
    mapdl.nsubst(1)
    mapdl.run("KBC,1")
    mapdl.d(fixed, "ALL", 0)
    mapdl.f(free, "FY", -10)
    mapdl.outres("ALL", "ALL")
    mapdl.solve()
    _log("saving MAPDL database")
    mapdl.finish()
    mapdl.save(JOBNAME, "db")


def _analytical_reference():
    length = 500.0
    width = 10.0
    height = 10.0
    force = 10.0
    frequency = 5.0
    young = 210000.0
    density = 7.85e-9
    area = width * height
    inertia = width * height**3 / 12.0
    static_tip_deflection = force * length**3 / (3.0 * young * inertia)
    beta1 = 1.875104068711961
    omega1 = beta1**2 * math.sqrt(young * inertia / (density * area * length**4))
    first_frequency = omega1 / (2.0 * math.pi)
    dynamic_factor = 1.0 / (1.0 - (frequency / first_frequency) ** 2)
    return {
        "section_area_mm2": area,
        "second_moment_of_area_mm4": inertia,
        "static_tip_deflection_mm": -static_tip_deflection,
        "first_natural_frequency_Hz": first_frequency,
        "single_mode_dynamic_amplification_at_5Hz": dynamic_factor,
        "estimated_harmonic_tip_UY_real_mm": -static_tip_deflection * dynamic_factor,
    }


def _assert_result_files():
    missing = []
    for path in (RUN_LOCATION / f"{JOBNAME}.db", RUN_LOCATION / f"{JOBNAME}.rst"):
        if not path.exists():
            missing.append(str(path))
    if missing:
        raise RuntimeError("Expected output files are missing: " + ", ".join(missing))


def _task_14():
    _log(f"output directory: {RUN_LOCATION}")
    _log("launching MAPDL")
    mapdl = _launch_mapdl(JOBNAME, 14)
    data = None
    try:
        _log("preparing MAPDL model")
        _prep(mapdl)
        _build_beam(mapdl)
        _log("saving pre-solve database")
        mapdl.save(JOBNAME, "db")
        fixed = _node_at(mapdl, x=0, y=0, z=0)
        free = _node_at(mapdl, x=500, y=0, z=0)
        _solve_harmonic(mapdl, fixed, free)

        _log("reading solved harmonic result")
        mapdl.post1()
        mapdl.run("SET,1,1")
        data = {
            "metadata": {
                "description": "MAPDL BEAM188 cantilever harmonic response ground-truth generator",
                "software": "ANSYS Mechanical APDL Student v261",
                "units": "N-mm-s-tonne",
                "database_file": str(RUN_LOCATION / f"{JOBNAME}.db"),
                "result_file": str(RUN_LOCATION / f"{JOBNAME}.rst"),
            },
            "input_parameters": {
                "geometry": {"length_x_mm": 500.0, "section_width_mm": 10.0, "section_height_mm": 10.0},
                "material": {"EX_MPa": 210000.0, "PRXY": 0.3, "density_tonne_per_mm3": 7.85e-9},
                "mesh": {"beam188_divisions": 20},
                "boundary_conditions": {"fixed_node": fixed, "fixed_dofs": ["UX", "UY", "UZ", "ROTX", "ROTY", "ROTZ"]},
                "load": {"free_node": free, "harmonic_force_FY_N": -10.0, "frequency_Hz": 5.0},
                "analysis": {"type": "full harmonic response", "frequency_points": [5.0], "damping_ratio": 0.0},
            },
            "results": {
                "analytical_reference": _analytical_reference(),
                "mapdl_free_end_response_real_part_mm": _disp(mapdl, free),
                "mapdl_maximum_response_real_part_mm": {
                    "UY": _sort_max(mapdl, "U", "Y"),
                    "USUM": _sort_max(mapdl, "U", "SUM"),
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
    paths = _write_groundtruth(_task_14())
    print("Ground truth written:")
    for path in paths:
        print(f"  {path}")
    print(f"MAPDL database written: {RUN_LOCATION / (JOBNAME + '.db')}")
    print(f"MAPDL result written: {RUN_LOCATION / (JOBNAME + '.rst')}")
