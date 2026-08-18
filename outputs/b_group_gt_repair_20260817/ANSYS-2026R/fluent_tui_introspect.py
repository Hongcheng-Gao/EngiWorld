from __future__ import annotations

import inspect
import json
from pathlib import Path

import ansys.fluent.core as pyfluent


desktop = Path(r"C:\Users\user\Desktop")
session = pyfluent.launch_fluent(
    mode="solver", dimension=2, precision="double", processor_count=1,
    ui_mode="no_gui_or_graphics", cwd=desktop, cleanup_on_exit=True,
    start_watchdog=False,
)
try:
    session.settings.file.read(file_type="case-data", file_name=str(desktop / "couette.cas"))
    targets = {
        "mesh": session.tui.mesh,
        "mesh_modify_zones": session.tui.mesh.modify_zones,
        "define_boundary_conditions": session.tui.define.boundary_conditions,
    }
    settings_command = session.settings.mesh.modify_zones.create_periodic_interface
    print("SETTINGS " + json.dumps({"public": sorted(item for item in dir(settings_command) if not item.startswith("_")), "argument_names": settings_command.argument_names}, default=str, sort_keys=True), flush=True)
    for argument_name in ("creation_method", "interface_name", "periodic_zone", "shadow_zone", "rotational_periodic", "auto_compute_offset", "translational_offset", "create_periodic", "create_matching"):
        try:
            argument = getattr(settings_command, argument_name)
        except Exception as exc:
            print("SETTINGS " + json.dumps({"argument": argument_name, "access_error": type(exc).__name__ + ": " + str(exc)}, sort_keys=True), flush=True)
            continue
        record = {"argument": argument_name, "type": str(type(argument))}
        for method_name in ("get_allowed_values", "get_state"):
            if hasattr(argument, method_name):
                try:
                    record[method_name] = getattr(argument, method_name)()
                except Exception as exc:
                    record[method_name] = type(exc).__name__ + ": " + str(exc)
        for attr_name in ("allowed-values", "allowed_values"):
            try:
                record["get_attr:" + attr_name] = argument.get_attr(attr_name)
            except Exception as exc:
                record["get_attr:" + attr_name] = type(exc).__name__ + ": " + str(exc)
        try:
            record["completer"] = argument.get_completer_info()
        except Exception as exc:
            record["completer"] = type(exc).__name__ + ": " + str(exc)
        print("SETTINGS " + json.dumps(record, default=str, sort_keys=True), flush=True)
    try:
        result = settings_command(
            creation_method="conformal",
            interface_name="couette-periodic",
            periodic_zone="left",
            shadow_zone="right",
            rotational_periodic=False,
            auto_compute_offset=True,
        )
        print("SETTINGS " + json.dumps({"command_result": result}, default=str, sort_keys=True), flush=True)
        print("SETTINGS " + json.dumps({"surfaces_after_command": session.fields.field_info.get_surfaces_info()}, default=str, sort_keys=True), flush=True)
    except Exception as exc:
        print("SETTINGS " + json.dumps({"command_exception": type(exc).__name__ + ": " + str(exc)}, sort_keys=True), flush=True)
    for name, target in targets.items():
        public = sorted(item for item in dir(target) if not item.startswith("_"))
        print("TUI " + json.dumps({"target": name, "public": public}, sort_keys=True), flush=True)
        for command_name in public:
            if "period" not in command_name:
                continue
            command = getattr(target, command_name)
            try:
                signature = str(inspect.signature(command))
            except Exception as exc:
                signature = type(exc).__name__ + ": " + str(exc)
            print("TUI " + json.dumps({"target": name + "." + command_name, "signature": signature, "doc": command.__doc__}, default=str, sort_keys=True), flush=True)
    try:
        result = session.tui.mesh.modify_zones.make_periodic("left", "right")
        print("TUI " + json.dumps({"target": "make_periodic_call", "result": result}, default=str, sort_keys=True), flush=True)
        print("TUI " + json.dumps({"target": "surfaces_after", "result": session.fields.field_info.get_surfaces_info()}, default=str, sort_keys=True), flush=True)
    except Exception as exc:
        print("TUI " + json.dumps({"target": "make_periodic_exception", "type": type(exc).__name__, "message": str(exc)}, sort_keys=True), flush=True)
    try:
        result = session.tui.mesh.modify_zones.create_periodic_interface()
        print("TUI " + json.dumps({"target": "create_periodic_interface_call", "result": result}, default=str, sort_keys=True), flush=True)
        print("TUI " + json.dumps({"target": "surfaces_after_create", "result": session.fields.field_info.get_surfaces_info()}, default=str, sort_keys=True), flush=True)
    except Exception as exc:
        print("TUI " + json.dumps({"target": "create_periodic_interface_exception", "type": type(exc).__name__, "message": str(exc)}, sort_keys=True), flush=True)
finally:
    session.exit(timeout=15, wait=20)
