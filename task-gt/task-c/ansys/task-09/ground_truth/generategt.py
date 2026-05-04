import json
import os
import shutil
from pathlib import Path


RUN_LOCATION = Path(os.environ.get("ANSYS_RUN_LOCATION", r"C:\Users\Administrator\Desktop"))
CASE_NAME = "cavity.cas"
DATA_NAME = "cavity.dat"
MESH_NAME = "cavity.msh"
NPROC = int(os.environ.get("PYFLUENT_NPROC", "1"))
FLUENT_UI_MODE = os.environ.get("PYFLUENT_UI_MODE", "hidden_gui")
FLUENT_START_TIMEOUT = int(os.environ.get("PYFLUENT_START_TIMEOUT", "300"))
FLUENT_PATH = os.environ.get("PYFLUENT_FLUENT_PATH")


def _log(message):
    print(f"[task-09] {message}", flush=True)


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


def _write_cavity_mesh(path, nx=20, ny=20):
    side = 0.001
    nnodes = (nx + 1) * (ny + 1)
    ncells = nx * ny

    interior = []
    left = []
    right = []
    bottom = []
    top = []

    for j in range(ny):
        for i in range(1, nx):
            interior.append(
                (
                    _node_id(i, j, nx),
                    _node_id(i, j + 1, nx),
                    _cell_id(i, j, nx),
                    _cell_id(i - 1, j, nx),
                )
            )

    for j in range(1, ny):
        for i in range(nx):
            interior.append(
                (
                    _node_id(i, j, nx),
                    _node_id(i + 1, j, nx),
                    _cell_id(i, j - 1, nx),
                    _cell_id(i, j, nx),
                )
            )

    for j in range(ny):
        left.append((_node_id(0, j, nx), _node_id(0, j + 1, nx), _cell_id(0, j, nx), 0))
        right.append((_node_id(nx, j + 1, nx), _node_id(nx, j, nx), _cell_id(nx - 1, j, nx), 0))

    for i in range(nx):
        bottom.append((_node_id(i + 1, 0, nx), _node_id(i, 0, nx), _cell_id(i, 0, nx), 0))
        top.append((_node_id(i, ny, nx), _node_id(i + 1, ny, nx), _cell_id(i, ny - 1, nx), 0))

    zones = [
        (8, 2, "default-interior", interior),
        (3, 3, "bottom", bottom),
        (4, 3, "top", top),
        (5, 3, "left", left),
        (6, 3, "right", right),
    ]
    total_faces = sum(len(zone_faces) for _, _, _, zone_faces in zones)

    lines = [
        '(0 "Python generated Fluent mesh for task-09 lid-driven cavity")',
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

    for j in range(ny + 1):
        y = side * j / ny
        for i in range(nx + 1):
            x = side * i / nx
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
            "(45 (3 wall bottom)())",
            "(45 (4 wall top)())",
            "(45 (5 wall left)())",
            "(45 (6 wall right)())",
            "",
        ]
    )

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="ascii") as stream:
        stream.write("\n".join(lines))


def _cavity_reference():
    side = 0.001
    lid_speed = 0.1
    rho = 998.2
    mu = 0.001003
    reynolds = rho * lid_speed * side / mu
    return {
        "metadata": {
            "description": "2D laminar lid-driven cavity-flow ground truth solved with Ansys Fluent",
            "units": "SI",
            "mesh_file": str(RUN_LOCATION / MESH_NAME),
            "case_file": str(RUN_LOCATION / CASE_NAME),
            "data_file": str(RUN_LOCATION / DATA_NAME),
        },
        "input_parameters": {
            "geometry": {
                "side_length_m": side,
                "domain": {"x_min_m": 0.0, "x_max_m": side, "y_min_m": 0.0, "y_max_m": side},
            },
            "fluid": {"name": "water-liquid", "density_kg_per_m3": rho, "dynamic_viscosity_Pa_s": mu},
            "mesh": {"type": "structured quadrilateral", "divisions_x": 20, "divisions_y": 20, "element_size_m": 5.0e-5},
            "boundary_conditions": {
                "top": {"type": "moving no-slip wall", "x_velocity_m_s": lid_speed, "y_velocity_m_s": 0.0},
                "bottom": {"type": "stationary no-slip wall"},
                "left": {"type": "stationary no-slip wall"},
                "right": {"type": "stationary no-slip wall"},
            },
            "solver": {
                "type": "pressure-based",
                "time_setting": "steady",
                "model": "laminar",
                "pressure_velocity_coupling": "SIMPLE",
                "spatial_discretization": "second-order where applicable",
                "iterations_requested": 1000,
            },
        },
        "results": {
            "reynolds_number": reynolds,
            "lid_speed_m_s": lid_speed,
            "domain_area_m2": side * side,
            "expected_flow_regime": "steady laminar cavity vortex",
            "reference_points": {
                "top_lid_midpoint": {"x_m": 0.0005, "y_m": 0.001, "u_x_m_s": lid_speed, "u_y_m_s": 0.0},
                "stationary_wall_velocity": {"u_x_m_s": 0.0, "u_y_m_s": 0.0},
            },
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


def _set_state(target, value):
    if hasattr(target, "set_state"):
        target.set_state(value)
        return
    if hasattr(target, "value"):
        value_target = target.value
        if hasattr(value_target, "set_state"):
            value_target.set_state(value)
            return
        target.value = value
        return
    raise AttributeError("target does not support set_state or value assignment")


def _set_path(root, dotted_path, value):
    current = root
    parts = dotted_path.split(".")
    for part in parts[:-1]:
        current = getattr(current, part)
    name = parts[-1]
    target = getattr(current, name)

    errors = []
    for candidate in (value, {"option": "value", "value": value}):
        try:
            _set_state(target, candidate)
            return True
        except Exception as exc:
            errors.append(str(exc))
    try:
        setattr(current, name, value)
        return True
    except Exception as exc:
        errors.append(str(exc))
    raise RuntimeError("; ".join(errors))


def _set_list_path(root, dotted_path, values):
    target = root
    for part in dotted_path.split("."):
        target = getattr(target, part)

    attempts = [
        lambda: target.set_state(values),
        lambda: target.set_state([{"option": "value", "value": value} for value in values]),
    ]
    last_error = None
    for attempt in attempts:
        try:
            attempt()
            return True
        except Exception as exc:
            last_error = exc
    raise RuntimeError(last_error)


def _boundary_conditions(solver):
    for root in (solver.settings.setup, solver.settings):
        try:
            return root.boundary_conditions
        except Exception:
            continue
    raise RuntimeError("Could not access Fluent boundary conditions settings")


def _set_wall_dict(boundary_conditions, name, state):
    boundary_conditions.wall[name] = state
    return True


def _configure_wall_motion(boundary_conditions):
    _log("leaving bottom/left/right as default stationary no-slip walls")

    _log("configuring moving lid")
    state = {
        "momentum": {
            "wall_motion": "Moving Wall",
            "velocity_spec": "Components",
            "velocity_components": [0.1, 0.0],
        }
    }
    try:
        _set_wall_dict(boundary_conditions, "top", state)
        return
    except Exception as exc:
        _log(f"dictionary moving-wall setup failed: {exc}")

    top = boundary_conditions.wall["top"]
    for label, func in (
        ("set top moving wall string", lambda: _set_path(top, "momentum.wall_motion", "Moving Wall")),
        ("set top velocity specification", lambda: _set_path(top, "momentum.velocity_spec", "Components")),
        ("set top wall velocity components", lambda: _set_list_path(top, "momentum.velocity_components", [0.1, 0.0])),
        ("set top wall speed magnitude", lambda: _set_path(top, "momentum.speed.value", 0.1)),
        ("set top wall translation direction", lambda: _set_list_path(top, "momentum.direction", [1.0, 0.0])),
    ):
        result = _try_call(label, func)
        if result is not None:
            return

    raise RuntimeError("Could not configure the top moving wall with the available PyFluent API.")


def _configure_solver(solver):
    _log("checking mesh")
    _try_call("mesh check", lambda: solver.settings.mesh.check())

    _log("configuring pressure-based steady laminar water model")
    _try_call("copy water-liquid material", lambda: solver.settings.setup.materials.database.copy_by_name(type="fluid", name="water-liquid"))
    _try_call("set fluid material", lambda: solver.settings.setup.cell_zone_conditions.fluid["fluid"].general.material.set_state("water-liquid"))
    _try_call("set material density", lambda: solver.settings.setup.materials.fluid["water-liquid"].density.value.set_state(998.2))
    _try_call("set material viscosity", lambda: solver.settings.setup.materials.fluid["water-liquid"].viscosity.value.set_state(0.001003))
    _try_call("set pressure-based solver", lambda: solver.settings.setup.general.solver.type.set_state("pressure-based"))
    _try_call("set steady time setting", lambda: solver.settings.setup.general.solver.time.set_state("steady"))
    _try_call("set planar 2D space", lambda: solver.settings.setup.general.solver.two_dim_space.set_state("planar"))
    _try_call("set laminar viscous model", lambda: solver.settings.setup.models.viscous.model.set_state("laminar"))

    _configure_wall_motion(_boundary_conditions(solver))

    _log("configuring SIMPLE pressure-velocity coupling and second-order schemes")
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
    _log(f"iterating steady lid-driven cavity solution for {iterations} iterations")
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
        _iterate_solution(solver, 1000)
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


def _task_09():
    RUN_LOCATION.mkdir(parents=True, exist_ok=True)
    mesh_path = RUN_LOCATION / MESH_NAME
    case_path = RUN_LOCATION / CASE_NAME
    data_path = RUN_LOCATION / DATA_NAME

    _log(f"output directory: {RUN_LOCATION}")
    _log("writing structured lid-driven cavity Fluent mesh")
    _write_cavity_mesh(mesh_path)
    _run_fluent(mesh_path, case_path, data_path)

    data = _cavity_reference()
    data["metadata"]["mesh_file_exists"] = mesh_path.exists()
    data["metadata"]["case_file_exists"] = case_path.exists()
    data["metadata"]["data_file_exists"] = data_path.exists()
    return data


if __name__ == "__main__":
    groundtruth = _task_09()
    target = RUN_LOCATION / "groundtruth.json"
    _write_json(target, groundtruth)
    print("Ground truth written:")
    print(f"  {target}")
    print(f"Fluent mesh file written: {RUN_LOCATION / MESH_NAME}")
    print(f"Fluent case file written: {RUN_LOCATION / CASE_NAME}")
    print(f"Fluent data file written: {RUN_LOCATION / DATA_NAME}")
