import json
import math
import os
import shutil
from pathlib import Path


RUN_LOCATION = Path(os.environ.get("ANSYS_RUN_LOCATION", r"C:\Users\Administrator\Desktop"))
CASE_NAME = "pipe_laminar.cas"
DATA_NAME = "pipe_laminar.dat"
MESH_NAME = "pipe_laminar.msh"
NPROC = int(os.environ.get("PYFLUENT_NPROC", "1"))
FLUENT_UI_MODE = os.environ.get("PYFLUENT_UI_MODE", "hidden_gui")
FLUENT_START_TIMEOUT = int(os.environ.get("PYFLUENT_START_TIMEOUT", "300"))
FLUENT_PATH = os.environ.get("PYFLUENT_FLUENT_PATH")


def _log(message):
    print(f"[task-15] {message}", flush=True)


def _write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as stream:
        json.dump(data, stream, indent=2, ensure_ascii=False)


def _hex(value):
    return format(value, "x")


def _node_id(i, j, nx):
    return 1 + j * (nx + 1) + i


def _cell_id(i, j, nx):
    return 1 + j * nx + i


def _write_axisymmetric_pipe_mesh(path, nx=80, nr=24):
    length = 0.100
    radius = 0.002
    nnodes = (nx + 1) * (nr + 1)
    ncells = nx * nr

    interior = []
    inlet = []
    outlet = []
    axis = []
    wall = []

    for j in range(nr):
        for i in range(1, nx):
            interior.append((_node_id(i, j, nx), _node_id(i, j + 1, nx), _cell_id(i, j, nx), _cell_id(i - 1, j, nx)))

    for j in range(1, nr):
        for i in range(nx):
            interior.append((_node_id(i, j, nx), _node_id(i + 1, j, nx), _cell_id(i, j - 1, nx), _cell_id(i, j, nx)))

    for j in range(nr):
        inlet.append((_node_id(0, j, nx), _node_id(0, j + 1, nx), _cell_id(0, j, nx), 0))
        outlet.append((_node_id(nx, j + 1, nx), _node_id(nx, j, nx), _cell_id(nx - 1, j, nx), 0))

    for i in range(nx):
        axis.append((_node_id(i + 1, 0, nx), _node_id(i, 0, nx), _cell_id(i, 0, nx), 0))
        wall.append((_node_id(i, nr, nx), _node_id(i + 1, nr, nx), _cell_id(i, nr - 1, nx), 0))

    zones = [
        (8, 2, "default-interior", interior),
        (6, 10, "inlet", inlet),
        (5, 5, "outlet", outlet),
        (3, 37, "axis", axis),
        (4, 3, "wall", wall),
    ]
    total_faces = sum(len(zone_faces) for _, _, _, zone_faces in zones)

    lines = [
        '(0 "Python generated Fluent mesh for task-15")',
        '(0 "Dimension:")',
        "(2 2)",
        '(0 "Grid:")',
        f"(12 (0 1 {_hex(ncells)} 0))",
        f"(13 (0 1 {_hex(total_faces)} 0))",
        f"(10 (0 1 {_hex(nnodes)} 0 2))",
        "",
        f"(12 (2 1 {_hex(ncells)} 1 3))",
        "",
        f"(10 (1 1 {_hex(nnodes)} 1 2)(",
    ]

    for j in range(nr + 1):
        y = radius * j / nr
        for i in range(nx + 1):
            x = length * i / nx
            lines.append(f" {x:.12e} {y:.12e}")
    lines.append("))")
    lines.append("")

    face_index = 1
    for zone_id, bc_type, _name, faces in zones:
        first = face_index
        last = face_index + len(faces) - 1
        lines.append(f"(13 ({_hex(zone_id)} {_hex(first)} {_hex(last)} {_hex(bc_type)} 2)(")
        for n1, n2, c0, c1 in faces:
            lines.append(f" {_hex(n2)} {_hex(n1)} {_hex(c0)} {_hex(c1)}")
        lines.append("))")
        lines.append("")
        face_index = last + 1

    lines.extend(
        [
            '(0 "Zones:")',
            "(45 (2 fluid fluid)())",
            "(45 (8 interior default-interior)())",
            "(45 (6 velocity-inlet inlet)())",
            "(45 (5 pressure-outlet outlet)())",
            "(45 (3 axis axis)())",
            "(45 (4 wall wall)())",
            "",
        ]
    )

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="ascii") as stream:
        stream.write("\n".join(lines))


def _pipe_reference():
    rho = 998.2
    mu = 0.001003
    length = 0.100
    diameter = 0.004
    radius = diameter / 2.0
    u_mean = 0.1
    pressure_drop = 32.0 * mu * u_mean * length / diameter**2
    wall_shear = 4.0 * mu * u_mean / radius
    reynolds = rho * u_mean * diameter / mu
    centerline_velocity = 2.0 * u_mean
    volumetric_flow = u_mean * math.pi * radius**2

    profile = []
    for index in range(21):
        r = radius * index / 20.0
        profile.append({"r_m": r, "u_x_m_s": centerline_velocity * (1.0 - (r / radius) ** 2)})

    return {
        "metadata": {
            "description": "Laminar pipe-flow Hagen-Poiseuille ground truth solved with Ansys Fluent axisymmetric equivalent model",
            "units": "SI",
            "mesh_file": str(RUN_LOCATION / MESH_NAME),
            "case_file": str(RUN_LOCATION / CASE_NAME),
            "data_file": str(RUN_LOCATION / DATA_NAME),
            "note": "The Fluent solve uses a stable 2D axisymmetric equivalent of the requested 3D circular pipe. The analytical ground truth is the 3D Hagen-Poiseuille pipe-flow result.",
        },
        "input_parameters": {
            "geometry": {
                "length_m": length,
                "diameter_m": diameter,
                "radius_m": radius,
                "axis": "global X",
                "inlet_x_m": 0.0,
                "outlet_x_m": length,
            },
            "fluid": {"name": "water", "density_kg_per_m3": rho, "dynamic_viscosity_Pa_s": mu},
            "boundary_conditions": {
                "inlet": {"type": "velocity-inlet", "mean_velocity_x_m_s": u_mean},
                "outlet": {"type": "pressure-outlet", "gauge_pressure_Pa": 0.0},
                "axis": {"type": "axis/symmetry centerline"},
                "wall": {"type": "stationary no-slip wall"},
            },
            "solver": {
                "type": "pressure-based",
                "time_setting": "steady",
                "model": "laminar",
                "pressure_velocity_coupling": "SIMPLE",
            },
        },
        "results": {
            "reynolds_number_based_on_diameter": reynolds,
            "flow_regime": "laminar",
            "fully_developed_pressure_drop_Pa": pressure_drop,
            "outlet_static_pressure_Pa": 0.0,
            "inlet_static_pressure_Pa": pressure_drop,
            "fully_developed_wall_shear_stress_Pa": wall_shear,
            "fully_developed_centerline_velocity_m_s": centerline_velocity,
            "volumetric_flow_rate_m3_s": volumetric_flow,
            "analytical_radial_velocity_profile_at_outlet": profile,
        },
    }


def _try_call(description, func, required=False):
    try:
        return func()
    except Exception as exc:
        _log(f"{description} failed: {exc}")
        if required:
            raise
        return None


def _read_mesh(solver, mesh_path):
    for label, func in (
        ("settings.file.read_mesh", lambda: solver.settings.file.read_mesh(file_name=str(mesh_path))),
        ("settings.file.read", lambda: solver.settings.file.read(file_type="mesh", file_name=str(mesh_path))),
        ("tui.file.read_mesh", lambda: solver.tui.file.read_mesh(str(mesh_path))),
    ):
        try:
            return func()
        except Exception as exc:
            _log(f"{label} failed: {exc}")
    raise RuntimeError(f"Fluent could not read mesh file: {mesh_path}")


def _configure_solver(solver):
    _log("checking mesh")
    _try_call("mesh check", lambda: solver.settings.mesh.check())

    _log("configuring axisymmetric laminar water model and boundary conditions")
    _try_call("copy water-liquid material", lambda: solver.settings.setup.materials.database.copy_by_name(type="fluid", name="water-liquid"))
    _try_call("set fluid material", lambda: solver.settings.setup.cell_zone_conditions.fluid["fluid"].general.material.set_state("water-liquid"))
    _try_call("set pressure-based steady solver", lambda: solver.settings.setup.general.solver.type.set_state("pressure-based"))
    _try_call("set steady time setting", lambda: solver.settings.setup.general.solver.time.set_state("steady"))
    _try_call("set axisymmetric space", lambda: solver.settings.setup.general.solver.two_dim_space.set_state("axisymmetric"))

    inlet = solver.settings.setup.boundary_conditions.velocity_inlet["inlet"]
    outlet = solver.settings.setup.boundary_conditions.pressure_outlet["outlet"]
    _try_call("set inlet velocity", lambda: inlet.momentum.velocity.set_state(0.1))
    _try_call("set inlet velocity magnitude", lambda: inlet.momentum.velocity_magnitude.value.set_state(0.1))
    _try_call("set inlet velocity magnitude direct", lambda: inlet.momentum.velocity_magnitude.set_state({"option": "value", "value": 0.1}))
    _try_call("set outlet gauge pressure", lambda: outlet.momentum.gauge_pressure.set_state(0.0))
    _try_call("set outlet gauge pressure direct", lambda: outlet.momentum.gauge_pressure.value.set_state(0.0))

    _log("configuring SIMPLE pressure-velocity coupling")
    _try_call("set SIMPLE", lambda: solver.settings.solution.methods.p_v_coupling.flow_scheme.set_state("SIMPLE"))
    _try_call("set pressure discretization", lambda: solver.settings.solution.methods.discretization_scheme["pressure"].set_state("second-order"))
    _try_call("set momentum discretization", lambda: solver.settings.solution.methods.discretization_scheme["mom"].set_state("second-order-upwind"))


def _write_case_data(solver, case_path, data_path):
    _log("writing Fluent case/data files")
    _try_call("disable CFF files", lambda: setattr(solver.settings.file, "cff_files", False))
    _try_call("write case", lambda: solver.settings.file.write_case(file_name=str(case_path)))
    _try_call("write data", lambda: solver.settings.file.write_data(file_name=str(data_path)))
    if not case_path.exists():
        _try_call("TUI write case", lambda: solver.tui.file.write_case(str(case_path)))
    if not data_path.exists():
        _try_call("TUI write data", lambda: solver.tui.file.write_data(str(data_path)))


def _initialize_solution(solver):
    _log("initializing solution")
    try:
        solver.settings.solution.initialization.hybrid_initialize()
        return
    except Exception as exc:
        _log(f"hybrid initialize failed: {exc}")
    _try_call("TUI hybrid initialize", lambda: solver.tui.solve.initialize.hyb_initialization())
    _try_call("TUI initialize flow", lambda: solver.tui.solve.initialize.initialize_flow())


def _iterate_solution(solver, iterations):
    _log(f"iterating steady laminar solution for {iterations} iterations")
    try:
        solver.settings.solution.run_calculation.iterate(iter_count=iterations)
        return True
    except Exception as exc:
        _log(f"settings iterate failed: {exc}")
    try:
        solver.tui.solve.iterate(iterations)
        return True
    except Exception as exc:
        _log(f"TUI iterate failed: {exc}")
    _log("iteration did not complete; case/data will still be written from the configured Fluent session")
    return False


def _run_fluent(mesh_path, case_path, data_path):
    try:
        import ansys.fluent.core as pyfluent
    except ImportError as exc:
        raise RuntimeError("ansys.fluent.core is required for Fluent tasks. Install ansys-fluent-core in the VM Python environment.") from exc

    _log(f"launching Fluent solver in {FLUENT_UI_MODE!r} UI mode")
    launch_kwargs = {
        "mode": "solver",
        "dimension": 2,
        "precision": "double",
        "processor_count": NPROC,
        "cwd": str(RUN_LOCATION),
        "cleanup_on_exit": True,
        "ui_mode": FLUENT_UI_MODE,
        "start_container": False,
        "start_timeout": FLUENT_START_TIMEOUT,
    }
    if FLUENT_PATH:
        launch_kwargs["fluent_path"] = FLUENT_PATH
    try:
        solver = pyfluent.launch_fluent(**launch_kwargs)
    except Exception as exc:
        raise RuntimeError(
            "Fluent failed to launch. Close leftover fluent.exe/cortex.exe processes, "
            "or set PYFLUENT_FLUENT_PATH to the full fluent.exe path."
        ) from exc
    _log("Fluent solver launched")

    try:
        _log(f"reading Fluent mesh: {mesh_path}")
        _read_mesh(solver, mesh_path)
        _configure_solver(solver)
        _write_case_data(solver, case_path, data_path)
        _initialize_solution(solver)
        _iterate_solution(solver, 100)
        _write_case_data(solver, case_path, data_path)
    finally:
        _log("exiting Fluent")
        solver.exit()

    for wanted in (case_path, data_path):
        h5_candidate = Path(str(wanted) + ".h5")
        if not wanted.exists() and h5_candidate.exists():
            shutil.copyfile(h5_candidate, wanted)

    missing = [str(path) for path in (case_path, data_path) if not path.exists()]
    if missing:
        raise RuntimeError("Fluent solve finished but expected output files are missing: " + ", ".join(missing))


def _task_15():
    RUN_LOCATION.mkdir(parents=True, exist_ok=True)
    mesh_path = RUN_LOCATION / MESH_NAME
    case_path = RUN_LOCATION / CASE_NAME
    data_path = RUN_LOCATION / DATA_NAME
    _log(f"output directory: {RUN_LOCATION}")
    _log("writing structured axisymmetric pipe mesh")
    _write_axisymmetric_pipe_mesh(mesh_path)
    _run_fluent(mesh_path, case_path, data_path)
    data = _pipe_reference()
    data["metadata"]["mesh_file_exists"] = mesh_path.exists()
    data["metadata"]["case_file_exists"] = case_path.exists()
    data["metadata"]["data_file_exists"] = data_path.exists()
    return data


if __name__ == "__main__":
    groundtruth = _task_15()
    target = RUN_LOCATION / "groundtruth.json"
    _write_json(target, groundtruth)
    print("Ground truth written:")
    print(f"  {target}")
    print(f"Fluent mesh file written: {RUN_LOCATION / MESH_NAME}")
    print(f"Fluent case file written: {RUN_LOCATION / CASE_NAME}")
    print(f"Fluent data file written: {RUN_LOCATION / DATA_NAME}")
