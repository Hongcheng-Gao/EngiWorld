from __future__ import annotations

import json
import sys
from pathlib import Path

import ansys.fluent.core as pyfluent


desktop = Path(r"C:\Users\user\Desktop")
case_name = sys.argv[1]
session = pyfluent.launch_fluent(
    mode="solver", dimension=2, precision="double", processor_count=1,
    ui_mode="no_gui_or_graphics", cwd=desktop, cleanup_on_exit=True,
    start_watchdog=False,
)
try:
    session.settings.file.read(file_type="case-data", file_name=str(desktop / case_name))
    setup = session.settings.setup
    targets = {
        "viscous": setup.models.viscous,
        "fluid_collection": setup.materials.fluid,
        "first_material": setup.materials.fluid[list(setup.materials.fluid)[0]],
        "fluid_zone": setup.cell_zone_conditions.fluid["fluid"],
        "velocity_inlet": setup.boundary_conditions.velocity_inlet,
        "solution_initialization": session.settings.solution.initialization,
        "run_calculation": session.settings.solution.run_calculation,
        "file": session.settings.file,
    }
    for name, target in targets.items():
        public = sorted(item for item in dir(target) if not item.startswith("_"))
        print("API " + json.dumps({"target": name, "type": str(type(target)), "public": public}, sort_keys=True), flush=True)
finally:
    session.exit(timeout=15, wait=20)
