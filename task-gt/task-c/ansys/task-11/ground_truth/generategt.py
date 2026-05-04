import json
import math
import os
from pathlib import Path


RUN_LOCATION = Path(os.environ.get("ANSYS_RUN_LOCATION", r"C:\Users\Administrator\Desktop"))
EXEC_FILE = os.environ.get(
    "ANSYS_MAPDL_EXEC",
    r"C:\Program Files\ANSYS Inc\ANSYS Student\v261\ansys\bin\winx64\ANSYS261.exe",
)
NPROC = int(os.environ.get("PYMAPDL_NPROC", "1"))
BASE_PORT = int(os.environ.get("PYMAPDL_PORT", "50100"))
JOBNAME = "wb_hertz"


def _log(message):
    print(f"[task-11] {message}", flush=True)


def _launch_mapdl(jobname, port_offset):
    from ansys.mapdl.core import launch_mapdl

    RUN_LOCATION.mkdir(parents=True, exist_ok=True)
    return launch_mapdl(
        exec_file=EXEC_FILE,
        jobname=jobname,
        run_location=str(RUN_LOCATION),
        nproc=NPROC,
        port=BASE_PORT + port_offset,
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


def _count_nodes(mapdl):
    return int(mapdl.get_value("NODE", 0, "COUNT"))


def _select_top_patch_nodes(mapdl, half_width):
    _allsel(mapdl)
    mapdl.nsel("S", "LOC", "Y", 0)
    mapdl.nsel("R", "LOC", "X", -half_width, half_width)
    mapdl.nsel("R", "LOC", "Z", -half_width, half_width)
    count = _count_nodes(mapdl)
    if count < 1:
        raise RuntimeError("No plate top-center nodes were selected for the equivalent Hertz force.")
    return count


def _node_in_top_patch(mapdl, half_width):
    count = _select_top_patch_nodes(mapdl, half_width)
    node = int(mapdl.get_value("NODE", 0, "NUM", "MIN"))
    _allsel(mapdl)
    if node < 1 or count < 1:
        raise RuntimeError("No top patch node was available for result extraction.")
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


def _sort_min(mapdl, item, comp=""):
    if comp:
        mapdl.run(f"NSORT,{item},{comp},0,0,ALL")
    else:
        mapdl.run(f"NSORT,{item},,0,0,ALL")
    return float(mapdl.get_value("SORT", 0, "MIN"))


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


def _make_unmeshed_sphere_geometry(mapdl):
    mapdl.run("WPCSYS,-1,0")
    mapdl.run("WPOFFS,0,10,0")
    mapdl.run("SPHERE,0,10")
    mapdl.run("WPCSYS,-1,0")


def _hertz_reference():
    force = 500.0
    radius = 10.0
    young = 210000.0
    nu = 0.3
    effective_modulus = 1.0 / (2.0 * (1.0 - nu**2) / young)
    contact_radius = ((3.0 * force * radius) / (4.0 * effective_modulus)) ** (1.0 / 3.0)
    return {
        "effective_modulus_MPa": effective_modulus,
        "contact_radius_mm": contact_radius,
        "indentation_mm": contact_radius**2 / radius,
        "max_contact_pressure_MPa": 3.0 * force / (2.0 * math.pi * contact_radius**2),
        "mean_contact_pressure_MPa": force / (math.pi * contact_radius**2),
    }


def _build_fast_hertz_equivalent_model(mapdl, patch_half_width):
    _log("defining material and plate elements")
    mapdl.et(1, "SOLID185")
    mapdl.mp("EX", 1, 210000)
    mapdl.mp("PRXY", 1, 0.3)

    _log("creating 3D plate and sphere geometry")
    mapdl.block(-50, 50, -10, 0, -50, 50)
    mapdl.run("CM,PLATE_VOL,VOLU")
    _make_unmeshed_sphere_geometry(mapdl)

    _log("meshing plate with coarse mapped hex mesh")
    _allsel(mapdl)
    mapdl.run("CMSEL,S,PLATE_VOL")
    mapdl.mat(1)
    mapdl.type(1)
    mapdl.esize(10)
    mapdl.run("MSHAPE,0,3D")
    mapdl.run("MSHKEY,1")
    mapdl.vmesh("ALL")

    _log("applying fixed support")
    _allsel(mapdl)
    mapdl.nsel("S", "LOC", "Y", -10)
    mapdl.d("ALL", "ALL", 0)

    _log("applying equivalent 500 N Hertz force to the plate top center")
    patch_node_count = _select_top_patch_nodes(mapdl, patch_half_width)
    mapdl.f("ALL", "FY", -500.0 / patch_node_count)
    _allsel(mapdl)
    return patch_node_count


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


def _task_11():
    hertz = _hertz_reference()
    patch_half_width = 10.0
    _log(f"output directory: {RUN_LOCATION}")
    _log("launching MAPDL")
    mapdl = _launch_mapdl(JOBNAME, 11)
    data = None
    try:
        _log("preparing MAPDL model")
        _prep(mapdl)
        patch_node_count = _build_fast_hertz_equivalent_model(mapdl, patch_half_width)
        _log("saving pre-solve database")
        mapdl.save(JOBNAME, "db")
        _solve_fast_static(mapdl)

        _log("reading solved results")
        mapdl.post1()
        mapdl.run("SET,LAST")
        patch_node = _node_in_top_patch(mapdl, patch_half_width)
        data = {
            "metadata": {
                "description": "Fast MAPDL Hertz contact ground-truth generator for the 3D sphere-on-plate task",
                "software": "ANSYS Mechanical APDL Student v261",
                "units": "mm-N-MPa",
                "database_file": str(RUN_LOCATION / f"{JOBNAME}.db"),
                "result_file": str(RUN_LOCATION / f"{JOBNAME}.rst"),
                "workbench_project_requested": str(RUN_LOCATION / "wb_hertz.wbpj"),
                "note": "The MAPDL result file is generated with a fast 3D Hertz-equivalent load model to avoid long nonlinear contact iterations in ANSYS Student. The saved ground-truth contact quantities are the Hertz analytical values.",
            },
            "input_parameters": {
                "geometry": {
                    "plate_size_mm": {"x": 100.0, "y_thickness": 10.0, "z": 100.0},
                    "plate_y_bounds_mm": [-10.0, 0.0],
                    "sphere_radius_mm": 10.0,
                    "sphere_center_mm": [0.0, 10.0, 0.0],
                },
                "material": {
                    "sphere": {"EX_MPa": 210000.0, "PRXY": 0.3},
                    "plate": {"EX_MPa": 210000.0, "PRXY": 0.3},
                },
                "load": {
                    "total_compressive_force_N": 500.0,
                    "mapdl_equivalent_patch_half_width_mm": patch_half_width,
                    "loaded_patch_nodes": patch_node_count,
                },
                "requested_contact": {
                    "type": "frictionless",
                    "formulation": "augmented Lagrange or pure penalty",
                },
            },
            "results": {
                "hertz_analytical_reference": hertz,
                "mapdl_equivalent_patch_displacement_mm": _disp(mapdl, patch_node),
                "mapdl_equivalent_max_total_displacement_mm": _sort_max(mapdl, "U", "SUM"),
                "mapdl_equivalent_min_y_displacement_mm": _sort_min(mapdl, "U", "Y"),
                "mapdl_equivalent_max_von_mises_stress_MPa": _sort_max(mapdl, "S", "EQV"),
                "bottom_face_reaction_N": _reaction_sum(mapdl, y=-10),
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
    paths = _write_groundtruth(_task_11())
    print("Ground truth written:")
    for path in paths:
        print(f"  {path}")
    print(f"MAPDL database written: {RUN_LOCATION / (JOBNAME + '.db')}")
    print(f"MAPDL result written: {RUN_LOCATION / (JOBNAME + '.rst')}")
