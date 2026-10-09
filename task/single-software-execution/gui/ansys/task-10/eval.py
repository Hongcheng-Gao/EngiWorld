from __future__ import annotations

import hashlib
import io
import math
import shutil
import tempfile
import warnings
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import ansys.fluent.core as pyfluent
from ansys.fluent.core.services.field_data import CellElementType, SurfaceDataType


warnings.filterwarnings("ignore")


DESKTOP = Path(r"C:\Users\user\Desktop")
CASE_FILE = DESKTOP / "poiseuille_shear.cas"
DATA_FILE = DESKTOP / "poiseuille_shear.dat"
FILES = (CASE_FILE, DATA_FILE)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def require_files() -> dict[Path, str]:
    for path in FILES:
        if not path.is_file() or path.stat().st_size <= 0:
            raise FileNotFoundError(path.name)
    return {path: digest(path) for path in FILES}




def close(value: float, expected: float, tolerance: float) -> bool:
    return math.isfinite(float(value)) and abs(float(value) - expected) <= tolerance


def constant_value(state: object) -> float:
    if not isinstance(state, dict) or state.get("option") != "value":
        raise ValueError("non-constant property")
    return float(state["value"])


def mesh_checks(session) -> bool:
    mesh = session.fields.field_data.get_mesh("fluid")
    if len(mesh.elements) != 8000 or len(mesh.nodes) != 8421:
        return False
    if any(element.element_type != CellElementType.QUADRILATERAL for element in mesh.elements):
        return False
    x_levels = sorted({round(float(node.x), 12) for node in mesh.nodes})
    y_levels = sorted({round(float(node.y), 12) for node in mesh.nodes})
    z_levels = {round(float(node.z), 12) for node in mesh.nodes}
    if len(x_levels) != 401 or len(y_levels) != 21 or z_levels != {0.0}:
        return False
    if any(not close(value, index * 0.0005, 1.0e-9) for index, value in enumerate(x_levels)):
        return False
    if any(not close(value, index * 0.0001, 1.0e-10) for index, value in enumerate(y_levels)):
        return False
    return True


def report_value(values: object, name: str) -> float:
    if not isinstance(values, dict) or name not in values:
        raise ValueError(f"missing report for {name}")
    return float(values[name])


def inspect_case_data(root: Path) -> bool:
    session = pyfluent.launch_fluent(
        mode="solver",
        dimension=2,
        precision="double",
        processor_count=1,
        ui_mode="no_gui_or_graphics",
        cwd=root,
        cleanup_on_exit=True,
        start_watchdog=False,
    )
    try:
        session.settings.file.read(file_type="case-data", file_name=str(root / "case.cas"))
        if not mesh_checks(session):
            return False

        setup = session.settings.setup
        solver = setup.general.solver.get_state()
        viscous = setup.models.viscous.get_state()
        water = setup.materials.fluid["water-liquid"].get_state()
        fluid = setup.cell_zone_conditions.fluid["fluid"].get_state()
        inlet = setup.boundary_conditions.velocity_inlet["inlet"].get_state()
        outlet = setup.boundary_conditions.pressure_outlet["outlet"].get_state()
        top = setup.boundary_conditions.wall["top"].get_state()
        bottom = setup.boundary_conditions.wall["bottom"].get_state()
        methods = session.settings.solution.methods.get_state()
        initialization = session.settings.solution.initialization.get_state()
        run = session.settings.solution.run_calculation.get_state()
        surfaces = session.fields.field_info.get_surfaces_info()

        if solver.get("type") != "pressure-based":
            return False
        if solver.get("two_dim_space") != "planar" or solver.get("time") != "steady":
            return False
        if viscous.get("model") != "laminar":
            return False
        if not close(constant_value(water.get("density")), 998.2, 0.05):
            return False
        if not close(constant_value(water.get("viscosity")), 0.001003, 5.0e-7):
            return False
        if fluid.get("general", {}).get("material") != "water-liquid":
            return False

        expected_zone_types = {
            "inlet": "velocity-inlet",
            "outlet": "pressure-outlet",
            "top": "wall",
            "bottom": "wall",
        }
        for name, zone_type in expected_zone_types.items():
            if surfaces.get(name, {}).get("zone_type") != zone_type:
                return False

        inlet_momentum = inlet.get("momentum", {})
        components = inlet_momentum.get("velocity_components", [])
        if inlet_momentum.get("velocity_specification_method") != "Components":
            return False
        if len(components) != 2:
            return False
        if not close(constant_value(components[0]), 0.2, 1.0e-6):
            return False
        if not close(constant_value(components[1]), 0.0, 1.0e-8):
            return False
        if not close(constant_value(outlet.get("momentum", {}).get("gauge_pressure")), 0.0, 1.0e-4):
            return False
        for wall in (top, bottom):
            momentum = wall.get("momentum", {})
            if momentum.get("wall_motion") != "Stationary Wall":
                return False
            if momentum.get("shear_condition") != "No Slip":
                return False

        if methods.get("p_v_coupling", {}).get("flow_scheme") != "SIMPLE":
            return False
        schemes = methods.get("spatial_discretization", {}).get("discretization_scheme", {})
        if schemes.get("pressure") != "second-order":
            return False
        if schemes.get("mom") != "second-order-upwind":
            return False
        if initialization.get("initialization_type") != "hybrid":
            return False
        if int(run.get("parameters", {}).get("iter_count", 0)) != 500:
            return False

        expected_faces = {"inlet": 20, "outlet": 20, "top": 400, "bottom": 400}
        for name, expected in expected_faces.items():
            face_data = session.fields.field_data.get_surface_data(
                data_types=[SurfaceDataType.FacesConnectivity], surfaces=[name]
            )
            connectivity = face_data[name][SurfaceDataType.FacesConnectivity]
            if len(connectivity) != expected:
                return False

        reports = session.settings.results.report.surface_integrals
        inlet_velocity = report_value(
            reports.get_area_weighted_avg(report_of="x-velocity", surface_names=["inlet"]),
            "inlet",
        )
        outlet_velocity = report_value(
            reports.get_area_weighted_avg(report_of="x-velocity", surface_names=["outlet"]),
            "outlet",
        )
        bottom_shear = report_value(
            reports.get_area_weighted_avg(report_of="wall-shear", surface_names=["bottom"]),
            "bottom",
        )
        top_shear = report_value(
            reports.get_area_weighted_avg(report_of="wall-shear", surface_names=["top"]),
            "top",
        )
        inlet_mass = report_value(reports.get_mass_flow_rate(surface_names=["inlet"]), "inlet")
        outlet_mass = report_value(reports.get_mass_flow_rate(surface_names=["outlet"]), "outlet")
        mass_scale = max(abs(inlet_mass), abs(outlet_mass), 1.0e-30)
        imbalance = abs(inlet_mass + outlet_mass) / mass_scale

        values = (
            inlet_velocity,
            outlet_velocity,
            bottom_shear,
            top_shear,
            inlet_mass,
            outlet_mass,
            imbalance,
        )
        return (
            all(math.isfinite(value) for value in values)
            and close(inlet_velocity, 0.2, 0.002)
            and 0.19 < outlet_velocity < 0.21
            and 0.45 < abs(bottom_shear) < 0.8
            and 0.45 < abs(top_shear) < 0.8
            and 0.39 < abs(inlet_mass) < 0.41
            and 0.39 < abs(outlet_mass) < 0.41
            and imbalance < 0.005
        )
    finally:
        session.exit(timeout=15, wait=20)


def evaluate() -> bool:
    try:
        before = require_files()
    except Exception:
        return False

    passed = False
    try:
        with tempfile.TemporaryDirectory(
            prefix="ansys_task10_eval_", ignore_cleanup_errors=True
        ) as temp:
            root = Path(temp)
            shutil.copy2(CASE_FILE, root / "case.cas")
            shutil.copy2(DATA_FILE, root / "case.dat")
            passed = inspect_case_data(root)
    except Exception:
        passed = False

    try:
        after = {path: digest(path) for path in FILES}
    except Exception:
        return False
    return passed and before == after


if __name__ == "__main__":
    with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
        result = evaluate()
    print("True" if result else "False")
