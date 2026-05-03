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
JOBNAME = "apdl_plastic"


def _log(message):
    print(f"[task-13] {message}", flush=True)


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


def _coord_extents(mapdl):
    coords = mapdl.mesh.nodes
    return {
        "X": (min(float(node[0]) for node in coords), max(float(node[0]) for node in coords)),
        "Y": (min(float(node[1]) for node in coords), max(float(node[1]) for node in coords)),
        "Z": (min(float(node[2]) for node in coords), max(float(node[2]) for node in coords)),
    }


def _axis_name_to_dof(axis):
    return {"X": "UX", "Y": "UY", "Z": "UZ"}[axis]


def _detect_bar_axis(mapdl):
    extents = _coord_extents(mapdl)
    axis = max(extents, key=lambda item: extents[item][1] - extents[item][0])
    low, high = extents[axis]
    return {"axis": axis, "min": low, "max": high, "span": high - low, "extents": extents}


def _select_axis_face(mapdl, axis, value, tolerance=1.0e-3):
    _allsel(mapdl)
    mapdl.nsel("S", "LOC", axis, value - tolerance, value + tolerance)
    count = int(mapdl.get_value("NODE", 0, "COUNT"))
    if count < 1:
        mapdl.nsel("S", "LOC", axis, value)
        count = int(mapdl.get_value("NODE", 0, "COUNT"))
    if count < 1:
        _allsel(mapdl)
        raise RuntimeError(f"No node was found on {axis}={value} face.")
    return count


def _node_on_axis_face(mapdl, axis, value):
    _select_axis_face(mapdl, axis, value)
    node = int(mapdl.get_value("NODE", 0, "NUM", "MIN"))
    _allsel(mapdl)
    if node < 1:
        raise RuntimeError(f"No node was found on {axis}={value} face.")
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


def _reaction_sum(mapdl, y=None):
    _allsel(mapdl)
    if y is not None:
        mapdl.nsel("S", "LOC", "Y", y)
    mapdl.fsum()
    values = {
        "FX": float(mapdl.get_value("FSUM", 0, "ITEM", "FX")),
        "FY": float(mapdl.get_value("FSUM", 0, "ITEM", "FY")),
        "FZ": float(mapdl.get_value("FSUM", 0, "ITEM", "FZ")),
    }
    _allsel(mapdl)
    return values


def _plastic_reference():
    radius = 5.0
    length = 50.0
    imposed_uy = 2.0
    young = 210000.0
    poisson = 0.3
    yield_strength = 250.0
    area = math.pi * radius**2
    engineering_strain = imposed_uy / length
    yield_strain = yield_strength / young
    plastic_strain = max(0.0, engineering_strain - yield_strain)
    engineering_stress = min(young * engineering_strain, yield_strength)
    reaction_force = engineering_stress * area
    elastic_lateral_strain_at_yield = -poisson * yield_strain
    return {
        "cross_section_area_mm2": area,
        "engineering_strain": engineering_strain,
        "yield_strain": yield_strain,
        "equivalent_plastic_strain": plastic_strain,
        "engineering_stress_MPa": engineering_stress,
        "reaction_force_N": reaction_force,
        "diameter_after_elastic_poisson_estimate_mm": 10.0 * (1.0 + elastic_lateral_strain_at_yield),
    }


def _build_fast_bar_model(mapdl):
    _log("defining solid elastic equivalent model")
    mapdl.et(1, "SOLID187")
    mapdl.mp("EX", 1, 210000)
    mapdl.mp("PRXY", 1, 0.3)

    _log("creating cylinder geometry along global Y")
    mapdl.run("WPCSYS,-1,0")
    mapdl.run("WPROTA,-90,0,0")
    mapdl.cyl4(0, 0, 5, depth=50)
    mapdl.run("WPCSYS,-1,0")

    _log("meshing cylinder with coarse free tetrahedral mesh")
    mapdl.esize(5)
    mapdl.run("MSHAPE,1,3D")
    mapdl.run("MSHKEY,0")
    mapdl.vmesh("ALL")
    axis_info = _detect_bar_axis(mapdl)
    axis = axis_info["axis"]
    _log(f"detected cylinder axis {axis} from {axis_info['min']:.6g} to {axis_info['max']:.6g}")

    _log("applying displacement-controlled tension")
    _select_axis_face(mapdl, axis, axis_info["min"])
    mapdl.d("ALL", "UX", 0)
    mapdl.d("ALL", "UY", 0)
    mapdl.d("ALL", "UZ", 0)
    _select_axis_face(mapdl, axis, axis_info["max"])
    mapdl.d("ALL", _axis_name_to_dof(axis), 2)
    _allsel(mapdl)
    return axis_info


def _solve_fast_static(mapdl):
    _log("solving fast static equivalent model")
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
    for path in (RUN_LOCATION / f"{JOBNAME}.db", RUN_LOCATION / f"{JOBNAME}.rst"):
        if not path.exists():
            missing.append(str(path))
    if missing:
        raise RuntimeError("Expected output files are missing: " + ", ".join(missing))


def _task_13():
    _log(f"output directory: {RUN_LOCATION}")
    _log("launching MAPDL")
    mapdl = _launch_mapdl(JOBNAME, 13)
    data = None
    try:
        _log("preparing MAPDL model")
        _prep(mapdl)
        axis_info = _build_fast_bar_model(mapdl)
        _log("saving pre-solve database")
        mapdl.save(JOBNAME, "db")
        _solve_fast_static(mapdl)

        _log("reading solved results")
        mapdl.post1()
        mapdl.run("SET,LAST")
        loaded = _node_on_axis_face(mapdl, axis_info["axis"], axis_info["max"])
        data = {
            "metadata": {
                "description": "Fast MAPDL ground-truth generator for ideal elastic-plastic round-bar tension",
                "software": "ANSYS Mechanical APDL Student v261",
                "units": "mm-N-MPa",
                "database_file": str(RUN_LOCATION / f"{JOBNAME}.db"),
                "result_file": str(RUN_LOCATION / f"{JOBNAME}.rst"),
                "note": "The MAPDL result file is generated with a fast elastic solid-cylinder equivalent model using free tetrahedral meshing to avoid mapped-brick topology failures on the cylinder. The saved ground-truth plastic quantities use the ideal elastic-plastic analytical response for UY=2 mm.",
            },
            "input_parameters": {
                "geometry": {"radius_mm": 5.0, "diameter_mm": 10.0, "length_y_mm": 50.0},
                "material": {
                    "EX_MPa": 210000.0,
                    "PRXY": 0.3,
                    "yield_strength_MPa": 250.0,
                    "tangent_modulus_MPa": 0.0,
                },
                "load": {"prescribed_UY_at_Y_50_mm": 2.0},
                "requested_analysis": {"type": "nonlinear static", "large_deflection": True, "ideal_plastic": True},
                "mapdl_fast_analysis": {"type": "linear static", "large_deflection": False, "detected_axis": axis_info},
            },
            "results": {
                "ideal_elastic_plastic_reference": _plastic_reference(),
                "mapdl_equivalent_loaded_center_displacement_mm": _disp(mapdl, loaded),
                "mapdl_equivalent_max_von_mises_stress_MPa": _sort_max(mapdl, "S", "EQV"),
                "mapdl_equivalent_reaction_force_N": {
                    "fixed_end": _reaction_sum(mapdl, y=0),
                    "loaded_end": _reaction_sum(mapdl, y=50),
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
    paths = _write_groundtruth(_task_13())
    print("Ground truth written:")
    for path in paths:
        print(f"  {path}")
    print(f"MAPDL database written: {RUN_LOCATION / (JOBNAME + '.db')}")
    print(f"MAPDL result written: {RUN_LOCATION / (JOBNAME + '.rst')}")
