from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path

import ansys.fluent.core as pyfluent


DESKTOP = Path(r"C:\Users\user\Desktop")
LOG_PATH: Path | None = None


def emit(step: str, value: object) -> None:
    line = "GEN " + json.dumps({"step": step, "value": value}, default=str, sort_keys=True)
    print(line, flush=True)
    if LOG_PATH is not None:
        with LOG_PATH.open("a", encoding="utf-8") as stream:
            stream.write(line + "\n")


def set_constant(target, value: float) -> None:
    target.set_state({"option": "value", "value": value})


def rename_material(fluids, old: str, new: str) -> None:
    if new in fluids:
        return
    try:
        fluids.rename(new=new, old=old)
        return
    except Exception as first:
        emit("rename_material_first_attempt", {"type": type(first).__name__, "message": str(first)})
    try:
        fluids[old].rename(new_name=new)
        return
    except Exception as second:
        emit("rename_material_second_attempt", {"type": type(second).__name__, "message": str(second)})
        raise


def main() -> int:
    global LOG_PATH
    kind = sys.argv[1]
    if kind == "poiseuille":
        source = "poiseuille_2d.cas"
        output = "poiseuille_2d_candidate.cas"
        material_old = "water-liquid"
        material_new = "water"
        iterations = 1200
    elif kind == "couette":
        source = "couette.cas"
        output = "couette_candidate.cas"
        material_old = "water-liquid"
        material_new = "water-liquid"
        iterations = 1200
    else:
        raise ValueError(kind)
    LOG_PATH = DESKTOP / (kind + "_generation_steps.log")
    LOG_PATH.write_text("", encoding="utf-8")

    session = pyfluent.launch_fluent(
        mode="solver", dimension=2, precision="double", processor_count=1,
        ui_mode="no_gui_or_graphics", cwd=DESKTOP, cleanup_on_exit=True,
        start_watchdog=False,
    )
    try:
        session.settings.file.read(file_type="case-data", file_name=str(DESKTOP / source))
        setup = session.settings.setup
        emit("loaded", {"source": source, "viscous": setup.models.viscous.get_state()})

        setup.models.viscous.model.set_state("laminar")
        fluids = setup.materials.fluid
        rename_material(fluids, material_old, material_new)
        material = fluids[material_new]
        set_constant(material.density, 998.2)
        set_constant(material.viscosity, 0.001003)
        setup.cell_zone_conditions.fluid["fluid"].general.material.set_state(material_new)

        methods = session.settings.solution.methods
        methods.p_v_coupling.flow_scheme.set_state("SIMPLE")
        schemes = methods.spatial_discretization.discretization_scheme
        schemes.set_state({"pressure": "second-order", "mom": "second-order-upwind"})

        if kind == "poiseuille":
            inlet = setup.boundary_conditions.velocity_inlet["inlet"].momentum
            inlet.velocity_specification_method.set_state("Components")
            inlet.velocity_components.set_state([
                {"option": "value", "value": 0.1},
                {"option": "value", "value": 0.0},
            ])
            set_constant(setup.boundary_conditions.pressure_outlet["outlet"].momentum.gauge_pressure, 0.0)
        else:
            bottom = setup.boundary_conditions.wall["bottom"].momentum
            top = setup.boundary_conditions.wall["top"].momentum
            emit("preserved_boundaries", {"bottom": bottom.get_state(), "top": top.get_state()})
            session.settings.mesh.modify_zones.create_periodic_interface(
                creation_method="conformal",
                interface_name="left",
                periodic_zone="left",
                shadow_zone="right",
                rotational_periodic=False,
                auto_compute_offset=True,
            )
            emit("periodic_surfaces", session.fields.field_info.get_surfaces_info())

        initialization = session.settings.solution.initialization
        if kind == "couette":
            initialization.initialization_type.set_state("standard")
            emit("standard_defaults_before", initialization.defaults.get_state())
            initialization.defaults.set_state({"x-velocity": 0.5, "y-velocity": 0.0})
            initialization.standard_initialize()
        else:
            initialization.initialization_type.set_state("hybrid")
            initialization.hybrid_initialize()
        run = session.settings.solution.run_calculation
        run.parameters.iter_count.set_state(iterations)
        emit("configured", {
            "viscous": setup.models.viscous.get_state(),
            "materials": list(fluids),
            "material": material.get_state(),
            "fluid": setup.cell_zone_conditions.fluid["fluid"].get_state(),
            "methods": methods.get_state(),
            "initialization": initialization.get_state(),
            "run": run.get_state(),
        })
        if kind == "couette":
            schemes.set_state({"pressure": "second-order", "mom": "first-order-upwind"})
            run.iterate(iter_count=500)
            schemes.set_state({"pressure": "second-order", "mom": "second-order-upwind"})
            run.parameters.iter_count.set_state(iterations)
            run.iterate(iter_count=iterations)
            initialization.initialization_type.set_state("hybrid")
        else:
            run.iterate(iter_count=iterations)

        reports = session.settings.results.report.surface_integrals
        if kind == "poiseuille":
            physical = {
                "inlet_velocity": reports.get_area_weighted_avg(report_of="x-velocity", surface_names=["inlet"]),
                "outlet_velocity": reports.get_area_weighted_avg(report_of="x-velocity", surface_names=["outlet"]),
                "inlet_mass_flow": reports.get_mass_flow_rate(surface_names=["inlet"]),
                "outlet_mass_flow": reports.get_mass_flow_rate(surface_names=["outlet"]),
            }
        else:
            physical = {
                "top_velocity": reports.get_area_weighted_avg(report_of="x-velocity", surface_names=["top"]),
                "bottom_velocity": reports.get_area_weighted_avg(report_of="x-velocity", surface_names=["bottom"]),
                "top_shear": reports.get_area_weighted_avg(report_of="wall-shear", surface_names=["top"]),
                "bottom_shear": reports.get_area_weighted_avg(report_of="wall-shear", surface_names=["bottom"]),
            }
        emit("physical_reports", physical)

        session.settings.file.cff_files.set_state(False)
        session.settings.file.write(file_type="case-data", file_name=str(DESKTOP / output))
        emit("written", {
            "case": str(DESKTOP / output),
            "case_exists": (DESKTOP / output).is_file(),
            "data_exists": (DESKTOP / output.replace(".cas", ".dat")).is_file(),
        })
        (DESKTOP / (kind + "_candidate.done")).write_text("success\n", encoding="utf-8")
        return 0
    except Exception as exc:
        emit("exception", {"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()})
        (DESKTOP / (kind + "_candidate.failed")).write_text(traceback.format_exc(), encoding="utf-8")
        return 1
    finally:
        session.exit(timeout=15, wait=20)


if __name__ == "__main__":
    raise SystemExit(main())
