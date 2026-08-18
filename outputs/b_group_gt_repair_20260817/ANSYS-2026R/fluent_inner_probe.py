from __future__ import annotations

import hashlib
import json
import math
import shutil
import sys
import tempfile
import traceback
from pathlib import Path

import ansys.fluent.core as pyfluent
from ansys.fluent.core.services.field_data import CellElementType


DESKTOP = Path(r"C:\Users\user\Desktop")
LOG_PATH: Path | None = None
CONFIGS = {
    "poiseuille": {
        "case": "poiseuille_2d.cas", "data": "poiseuille_2d.dat",
        "bounds": (0.0, 1.0, 0.0, 0.002), "min_levels": (51, 11),
        "material": "water", "top_speed": None, "inlet_speed": 0.1,
    },
    "couette": {
        "case": "couette.cas", "data": "couette.dat",
        "bounds": (0.0, 0.1, 0.0, 0.002), "min_levels": (21, 11),
        "material": "water-liquid", "top_speed": 1.0,
    },
    "cavity": {
        "case": "cavity.cas", "data": "cavity.dat",
        "bounds": (0.0, 0.001, 0.0, 0.001), "levels": (21, 21),
        "material": "water-liquid", "top_speed": 0.1,
    },
}


def emit(name: str, value: object) -> None:
    line = "PROBE " + json.dumps({"check": name, "value": value}, default=str, sort_keys=True)
    print(line, flush=True)
    if LOG_PATH is not None:
        with LOG_PATH.open("a", encoding="utf-8") as stream:
            stream.write(line + "\n")


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
    raise ValueError("non-constant value: " + repr(state))


def report_value(values: object, name: str) -> float:
    if not isinstance(values, dict) or name not in values:
        raise ValueError("missing report value: " + name + " in " + repr(values))
    return float(values[name])


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def checked(name: str, value: object) -> bool:
    result = bool(value)
    emit(name, {"passed": result, "observed": value})
    return result


def main() -> int:
    global LOG_PATH
    kind = sys.argv[1]
    config = CONFIGS[kind]
    LOG_PATH = DESKTOP / (kind + "_inner_probe.log")
    LOG_PATH.write_text("", encoding="utf-8")
    source_case = DESKTOP / config["case"]
    source_data = DESKTOP / config["data"]
    temporary = None
    if len(sys.argv) > 2 and sys.argv[2] == "temp":
        temporary = tempfile.TemporaryDirectory(prefix="ansys_fluent_probe_", ignore_cleanup_errors=True)
        work_root = Path(temporary.name)
        case_path = work_root / "case.cas"
        data_path = work_root / "case.dat"
        shutil.copy2(source_case, case_path)
        shutil.copy2(source_data, data_path)
    else:
        work_root = DESKTOP
        case_path = source_case
        data_path = source_data
    emit("input_files", {
        "case": {"path": str(case_path), "size": case_path.stat().st_size, "sha256": digest(case_path)},
        "data": {"path": str(data_path), "size": data_path.stat().st_size, "sha256": digest(data_path)},
    })
    session = pyfluent.launch_fluent(
        mode="solver", dimension=2, precision="double", processor_count=1,
        ui_mode="no_gui_or_graphics", cwd=work_root, cleanup_on_exit=True,
        start_watchdog=False,
    )
    passed = True
    try:
        session.settings.file.read(file_type="case-data", file_name=str(case_path))
        mesh = session.fields.field_data.get_mesh("fluid")
        x_levels = sorted({round(float(node.x), 12) for node in mesh.nodes})
        y_levels = sorted({round(float(node.y), 12) for node in mesh.nodes})
        z_levels = {round(float(node.z), 12) for node in mesh.nodes}
        element_types = sorted({str(element.element_type) for element in mesh.elements})
        mesh_observed = {
            "nodes": len(mesh.nodes), "elements": len(mesh.elements),
            "element_types": element_types, "x_count": len(x_levels), "y_count": len(y_levels),
            "x_bounds": [x_levels[0], x_levels[-1]], "y_bounds": [y_levels[0], y_levels[-1]],
            "z_levels": sorted(z_levels),
        }
        emit("mesh_observed", mesh_observed)
        xmin, xmax, ymin, ymax = config["bounds"]
        mesh_ok = len(mesh.nodes) > 0 and len(mesh.elements) > 0
        mesh_ok &= all(element.element_type == CellElementType.QUADRILATERAL for element in mesh.elements)
        mesh_ok &= z_levels == {0.0}
        mesh_ok &= close(x_levels[0], xmin, 1.0e-9) and close(x_levels[-1], xmax, 1.0e-9)
        mesh_ok &= close(y_levels[0], ymin, 1.0e-9) and close(y_levels[-1], ymax, 1.0e-9)
        if "levels" in config:
            mesh_ok &= (len(x_levels), len(y_levels)) == tuple(config["levels"])
        if "min_levels" in config:
            nx, ny = config["min_levels"]
            mesh_ok &= len(x_levels) >= nx and len(y_levels) >= ny
        passed &= checked("mesh", mesh_ok)

        setup = session.settings.setup
        solver = setup.general.solver.get_state()
        viscous = setup.models.viscous.get_state()
        materials = setup.materials.fluid
        material_names = list(materials)
        fluid = setup.cell_zone_conditions.fluid["fluid"].get_state()
        methods = session.settings.solution.methods.get_state()
        initialization = session.settings.solution.initialization.get_state()
        run = session.settings.solution.run_calculation.get_state()
        surfaces = session.fields.field_info.get_surfaces_info()
        emit("solver", solver)
        emit("viscous", viscous)
        emit("material_names", material_names)
        emit("fluid_zone", fluid)
        emit("methods", methods)
        emit("initialization", initialization)
        emit("run_calculation", run)
        emit("surfaces", surfaces)
        passed &= checked("solver", solver.get("type") == "pressure-based" and solver.get("two_dim_space") == "planar" and solver.get("time") == "steady")
        passed &= checked("viscous_laminar", viscous.get("model") == "laminar")
        material_exists = config["material"] in materials
        passed &= checked("material_exists", material_exists)
        if material_exists:
            material = materials[config["material"]].get_state()
            emit("material_state", material)
            passed &= checked("material_density", close(constant_value(material.get("density")), 998.2, 0.05))
            passed &= checked("material_viscosity", close(constant_value(material.get("viscosity")), 0.001003, 5.0e-7))
        else:
            passed = False
        passed &= checked("fluid_material", fluid.get("general", {}).get("material") == config["material"])
        passed &= checked("simple", methods.get("p_v_coupling", {}).get("flow_scheme") == "SIMPLE")
        schemes = methods.get("spatial_discretization", {}).get("discretization_scheme", {})
        passed &= checked("pressure_scheme", schemes.get("pressure") in {"second-order", "presto!"})
        passed &= checked("momentum_scheme", schemes.get("mom") in {"second-order-upwind", "quick"})
        passed &= checked("hybrid_initialization", initialization.get("initialization_type") == "hybrid")
        passed &= checked("saved_iteration_count", int(run.get("parameters", {}).get("iter_count", 0)) >= 100)

        reports = session.settings.results.report.surface_integrals
        if kind == "poiseuille":
            expected = {"inlet": "velocity-inlet", "outlet": "pressure-outlet", "top": "wall", "bottom": "wall"}
            passed &= checked("surface_types", {name: surfaces.get(name, {}).get("zone_type") for name in expected} == expected)
            inlet = setup.boundary_conditions.velocity_inlet["inlet"].get_state().get("momentum", {})
            outlet = setup.boundary_conditions.pressure_outlet["outlet"].get_state().get("momentum", {})
            top = setup.boundary_conditions.wall["top"].get_state().get("momentum", {})
            bottom = setup.boundary_conditions.wall["bottom"].get_state().get("momentum", {})
            emit("boundary_states", {"inlet": inlet, "outlet": outlet, "top": top, "bottom": bottom})
            components = inlet.get("velocity_components", [])
            passed &= checked("inlet_components", len(components) == 2 and close(constant_value(components[0]), 0.1, 1.0e-6) and close(constant_value(components[1]), 0.0, 1.0e-8))
            passed &= checked("outlet_pressure", close(constant_value(outlet.get("gauge_pressure")), 0.0, 1.0e-4))
            passed &= checked("stationary_walls", all(w.get("wall_motion") == "Stationary Wall" and w.get("shear_condition") == "No Slip" for w in (top, bottom)))
            values = {
                "inlet_velocity": report_value(reports.get_area_weighted_avg(report_of="x-velocity", surface_names=["inlet"]), "inlet"),
                "outlet_velocity": report_value(reports.get_area_weighted_avg(report_of="x-velocity", surface_names=["outlet"]), "outlet"),
                "inlet_mass_flow": report_value(reports.get_mass_flow_rate(surface_names=["inlet"]), "inlet"),
                "outlet_mass_flow": report_value(reports.get_mass_flow_rate(surface_names=["outlet"]), "outlet"),
            }
            values["imbalance"] = abs(values["inlet_mass_flow"] + values["outlet_mass_flow"]) / max(abs(values["inlet_mass_flow"]), abs(values["outlet_mass_flow"]), 1.0e-30)
            emit("physical_reports", values)
            passed &= checked("physical_solution", close(values["inlet_velocity"], 0.1, 0.002) and 0.095 < values["outlet_velocity"] < 0.105 and values["imbalance"] < 0.005)
        elif kind == "couette":
            side_types = {surfaces.get("left", {}).get("zone_type"), surfaces.get("right", {}).get("zone_type")}
            passed &= checked("surface_types", surfaces.get("top", {}).get("zone_type") == "wall" and surfaces.get("bottom", {}).get("zone_type") == "wall" and (side_types == {"symmetry"} or all(value and "periodic" in value for value in side_types)))
            bottom = setup.boundary_conditions.wall["bottom"].get_state().get("momentum", {})
            top = setup.boundary_conditions.wall["top"].get_state().get("momentum", {})
            emit("boundary_states", {"top": top, "bottom": bottom})
            components = top.get("velocity_components", [])
            if isinstance(components, dict):
                components = list(components.values())
            components = [constant_value(value) for value in components]
            passed &= checked("bottom_wall", bottom.get("wall_motion") == "Stationary Wall" and bottom.get("shear_condition") == "No Slip")
            passed &= checked("top_wall", top.get("wall_motion") == "Moving Wall" and len(components) >= 2 and close(components[0], 1.0, 1.0e-6) and close(components[1], 0.0, 1.0e-8))
            values = {
                "top_velocity": report_value(reports.get_area_weighted_avg(report_of="x-velocity", surface_names=["top"]), "top"),
                "bottom_velocity": report_value(reports.get_area_weighted_avg(report_of="x-velocity", surface_names=["bottom"]), "bottom"),
                "top_shear": abs(report_value(reports.get_area_weighted_avg(report_of="wall-shear", surface_names=["top"]), "top")),
                "bottom_shear": abs(report_value(reports.get_area_weighted_avg(report_of="wall-shear", surface_names=["bottom"]), "bottom")),
            }
            emit("physical_reports", values)
            passed &= checked("physical_solution", close(values["top_velocity"], 1.0, 0.01) and abs(values["bottom_velocity"]) < 0.01 and 0.45 < values["top_shear"] < 0.56 and 0.45 < values["bottom_shear"] < 0.56)
        else:
            passed &= checked("surface_types", all(surfaces.get(name, {}).get("zone_type") == "wall" for name in ("top", "bottom", "left", "right")))
            walls = {name: setup.boundary_conditions.wall[name].get_state().get("momentum", {}) for name in ("top", "bottom", "left", "right")}
            emit("boundary_states", walls)
            passed &= checked("stationary_walls", all(walls[name].get("wall_motion") == "Stationary Wall" and walls[name].get("shear_condition") == "No Slip" for name in ("bottom", "left", "right")))
            components = walls["top"].get("velocity_components", [])
            if isinstance(components, dict):
                components = list(components.values())
            components = [constant_value(value) for value in components]
            passed &= checked("top_wall", walls["top"].get("wall_motion") == "Moving Wall" and len(components) >= 2 and close(components[0], 0.1, 1.0e-6) and close(components[1], 0.0, 1.0e-8))
            lid = report_value(reports.get_area_weighted_avg(report_of="x-velocity", surface_names=["top"]), "top")
            emit("physical_reports", {"lid_velocity": lid})
            passed &= checked("physical_solution", close(lid, 0.1, 0.002))
    except Exception as exc:
        passed = False
        emit("exception", {"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()})
    finally:
        session.exit(timeout=15, wait=20)
        if temporary is not None:
            temporary.cleanup()
    result_line = "INNER_RESULT=" + ("True" if passed else "False")
    print(result_line, flush=True)
    with LOG_PATH.open("a", encoding="utf-8") as stream:
        stream.write(result_line + "\n")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
