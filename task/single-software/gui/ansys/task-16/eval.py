from __future__ import annotations

import hashlib
import io
import math
import shutil
import subprocess
import tempfile
import warnings
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import ansys.fluent.core as pyfluent
from ansys.fluent.core.services.field_data import CellElementType, SurfaceDataType

warnings.filterwarnings("ignore")

DESKTOP = Path(r"C:\Users\user\Desktop")
LICENSE_FILE = DESKTOP / "license.py"
CONFIG = {'case': 'poiseuille_2d.cas',
 'data': 'poiseuille_2d.dat',
 'kind': 'poiseuille',
 'bounds': (0.0, 1.0, 0.0, 0.002),
 'min_levels': (51, 11),
 'material': 'water',
 'inlet_speed': 0.1}
CASE_FILE = DESKTOP / CONFIG["case"]
DATA_FILE = DESKTOP / CONFIG["data"]
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


def check_license() -> None:
    result = subprocess.run(
        ["python", str(LICENSE_FILE)], cwd=DESKTOP, capture_output=True, text=True,
        timeout=120, creationflags=0x08000000,
    )
    output = (result.stdout or "") + (result.stderr or "")
    if result.returncode != 0 or "[SUCCESS]" not in output:
        raise RuntimeError("ANSYS license setup failed")


def close(value: float, expected: float, tolerance: float) -> bool:
    try:
        value = float(value)
    except Exception:
        return False
    return math.isfinite(value) and abs(value - expected) <= tolerance


def constant_value(state: object) -> float:
    if isinstance(state, (int, float)):
        return float(state)
    if isinstance(state, dict):
        if state.get("option") == "value":
            return float(state["value"])
        if "value" in state and isinstance(state["value"], (int, float)):
            return float(state["value"])
    raise ValueError("non-constant value")


def report_value(values: object, name: str) -> float:
    if not isinstance(values, dict) or name not in values:
        raise ValueError("missing report value: " + name)
    return float(values[name])


def mesh_checks(session) -> bool:
    mesh = session.fields.field_data.get_mesh("fluid")
    if (
        mesh.nodes is None
        or mesh.elements is None
        or len(mesh.nodes) == 0
        or len(mesh.elements) == 0
    ):
        return False
    if any(element.element_type != CellElementType.QUADRILATERAL for element in mesh.elements):
        return False
    x_levels = sorted({round(float(node.x), 12) for node in mesh.nodes})
    y_levels = sorted({round(float(node.y), 12) for node in mesh.nodes})
    z_levels = {round(float(node.z), 12) for node in mesh.nodes}
    xmin, xmax, ymin, ymax = CONFIG["bounds"]
    if z_levels != {0.0}:
        return False
    if not (close(x_levels[0], xmin, 1.0e-9) and close(x_levels[-1], xmax, 1.0e-9)
            and close(y_levels[0], ymin, 1.0e-9) and close(y_levels[-1], ymax, 1.0e-9)):
        return False
    if "levels" in CONFIG and (len(x_levels), len(y_levels)) != tuple(CONFIG["levels"]):
        return False
    if "min_levels" in CONFIG:
        nx, ny = CONFIG["min_levels"]
        if len(x_levels) < nx or len(y_levels) < ny:
            return False
    return True


def wall_components(momentum: dict) -> list[float]:
    values = momentum.get("velocity_components", [])
    if isinstance(values, dict):
        values = list(values.values())
    return [constant_value(value) for value in values]


def inspect_case_data(root: Path) -> bool:
    check_license()
    session = pyfluent.launch_fluent(
        mode="solver", dimension=2, precision="double", processor_count=1,
        ui_mode="no_gui_or_graphics", cwd=root, cleanup_on_exit=True,
        start_watchdog=False,
    )
    try:
        session.settings.file.read(file_type="case-data", file_name=str(root / "case.cas"))
        if not mesh_checks(session):
            return False

        setup = session.settings.setup
        solver = setup.general.solver.get_state()
        viscous = setup.models.viscous.get_state()
        materials = setup.materials.fluid
        if CONFIG["material"] not in materials:
            return False
        water = materials[CONFIG["material"]].get_state()
        fluid = setup.cell_zone_conditions.fluid["fluid"].get_state()
        methods = session.settings.solution.methods.get_state()
        initialization = session.settings.solution.initialization.get_state()
        run = session.settings.solution.run_calculation.get_state()
        surfaces = session.fields.field_info.get_surfaces_info()

        if solver.get("type") != "pressure-based" or solver.get("two_dim_space") != "planar" or solver.get("time") != "steady":
            return False
        if viscous.get("model") != "laminar":
            return False
        if not close(constant_value(water.get("density")), 998.2, 0.05):
            return False
        if not close(constant_value(water.get("viscosity")), 0.001003, 5.0e-7):
            return False
        if fluid.get("general", {}).get("material") != CONFIG["material"]:
            return False
        if methods.get("p_v_coupling", {}).get("flow_scheme") != "SIMPLE":
            return False
        schemes = methods.get("spatial_discretization", {}).get("discretization_scheme", {})
        if schemes.get("pressure") not in {"second-order", "presto!"}:
            return False
        if schemes.get("mom") not in {"second-order-upwind", "quick"}:
            return False
        if initialization.get("initialization_type") != "hybrid":
            return False
        if int(run.get("parameters", {}).get("iter_count", 0)) < 100:
            return False

        kind = CONFIG["kind"]
        reports = session.settings.results.report.surface_integrals
        if kind == "cavity":
            for name in ("top", "bottom", "left", "right"):
                if surfaces.get(name, {}).get("zone_type") != "wall":
                    return False
            top = setup.boundary_conditions.wall["top"].get_state().get("momentum", {})
            for name in ("bottom", "left", "right"):
                wall = setup.boundary_conditions.wall[name].get_state().get("momentum", {})
                if wall.get("wall_motion") != "Stationary Wall" or wall.get("shear_condition") != "No Slip":
                    return False
            if top.get("wall_motion") != "Moving Wall":
                return False
            components = wall_components(top)
            if len(components) < 2 or not close(components[0], CONFIG["top_speed"], 1.0e-6) or not close(components[1], 0.0, 1.0e-8):
                return False
            lid = report_value(reports.get_area_weighted_avg(report_of="x-velocity", surface_names=["top"]), "top")
            return close(lid, CONFIG["top_speed"], 0.002)

        if kind == "poiseuille":
            expected = {"inlet": "velocity-inlet", "outlet": "pressure-outlet", "top": "wall", "bottom": "wall"}
            if any(surfaces.get(name, {}).get("zone_type") != zone for name, zone in expected.items()):
                return False
            inlet = setup.boundary_conditions.velocity_inlet["inlet"].get_state().get("momentum", {})
            outlet = setup.boundary_conditions.pressure_outlet["outlet"].get_state().get("momentum", {})
            components = inlet.get("velocity_components", [])
            if len(components) != 2 or not close(constant_value(components[0]), CONFIG["inlet_speed"], 1.0e-6) or not close(constant_value(components[1]), 0.0, 1.0e-8):
                return False
            if not close(constant_value(outlet.get("gauge_pressure")), 0.0, 1.0e-4):
                return False
            for name in ("top", "bottom"):
                wall = setup.boundary_conditions.wall[name].get_state().get("momentum", {})
                if wall.get("wall_motion") != "Stationary Wall" or wall.get("shear_condition") != "No Slip":
                    return False
            inlet_v = report_value(reports.get_area_weighted_avg(report_of="x-velocity", surface_names=["inlet"]), "inlet")
            outlet_v = report_value(reports.get_area_weighted_avg(report_of="x-velocity", surface_names=["outlet"]), "outlet")
            inlet_m = report_value(reports.get_mass_flow_rate(surface_names=["inlet"]), "inlet")
            outlet_m = report_value(reports.get_mass_flow_rate(surface_names=["outlet"]), "outlet")
            imbalance = abs(inlet_m + outlet_m) / max(abs(inlet_m), abs(outlet_m), 1.0e-30)
            return close(inlet_v, 0.1, 0.002) and 0.095 < outlet_v < 0.105 and imbalance < 0.005

        if kind == "couette":
            if surfaces.get("top", {}).get("zone_type") != "wall" or surfaces.get("bottom", {}).get("zone_type") != "wall":
                return False
            side_types = {surfaces.get("left", {}).get("zone_type"), surfaces.get("right", {}).get("zone_type")}
            if not (side_types == {"symmetry"} or all(value and "periodic" in value for value in side_types)):
                return False
            bottom = setup.boundary_conditions.wall["bottom"].get_state().get("momentum", {})
            top = setup.boundary_conditions.wall["top"].get_state().get("momentum", {})
            if bottom.get("wall_motion") != "Stationary Wall" or bottom.get("shear_condition") != "No Slip":
                return False
            if top.get("wall_motion") != "Moving Wall":
                return False
            components = wall_components(top)
            if len(components) < 2 or not close(components[0], 1.0, 1.0e-6) or not close(components[1], 0.0, 1.0e-8):
                return False
            top_v = report_value(reports.get_area_weighted_avg(report_of="x-velocity", surface_names=["top"]), "top")
            bottom_v = report_value(reports.get_area_weighted_avg(report_of="x-velocity", surface_names=["bottom"]), "bottom")
            top_shear = abs(report_value(reports.get_area_weighted_avg(report_of="wall-shear", surface_names=["top"]), "top"))
            bottom_shear = abs(report_value(reports.get_area_weighted_avg(report_of="wall-shear", surface_names=["bottom"]), "bottom"))
            return (close(top_v, 1.0, 0.01) and abs(bottom_v) < 0.01
                    and 0.45 < top_shear < 0.56 and 0.45 < bottom_shear < 0.56)

        return False
    finally:
        session.exit(timeout=15, wait=20)


def evaluate() -> bool:
    try:
        before = require_files()
    except Exception:
        return False
    passed = False
    try:
        with tempfile.TemporaryDirectory(prefix="ansys_fluent_eval_", ignore_cleanup_errors=True) as temp:
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
