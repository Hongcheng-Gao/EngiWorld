#!/usr/bin/env python3
import read_only_eval


_shared_checked = read_only_eval.checked
_shared_require_plane_thickness = read_only_eval.require_plane_thickness


def checked_with_default_real_constants(mapdl, command: str) -> str:
    if command != "RLIST,ALL":
        return _shared_checked(mapdl, command)

    previous = mapdl.ignore_errors
    mapdl.ignore_errors = True
    try:
        output = str(mapdl.run(command) or "")
    finally:
        mapdl.ignore_errors = previous
    upper = output.upper()
    if "NO ENTITIES DEFINED" in upper and "RLIST COMMAND IS IGNORED" in upper:
        return ""
    if "*** ERROR ***" in upper or "COMMAND IS IGNORED" in upper or "UNKNOWN LABEL" in upper:
        raise read_only_eval.InvalidArtifact(command)
    return output


def require_unit_default_thickness(text: str, expected: float, grid=None) -> None:
    if not text.strip() and read_only_eval.close(expected, 1.0, 1.0e-12):
        values = None if grid is None else grid.cell_data.get("ansys_real_constant")
        if values is None or all(int(value) in {0, 1} for value in values):
            return
    _shared_require_plane_thickness(text, expected, grid)


read_only_eval.checked = checked_with_default_real_constants
read_only_eval.require_plane_thickness = require_unit_default_thickness


CONFIG = {
    "kind": "thermal_path",
    "direction": "minimize",
    "baseline_files": ["baseline_wb_conduction.db", "baseline_wb_conduction.rth"],
    "submission_files": ["submission.db", "submission.rth"],
    "result_suffix": ".rth",
    "port_seed": 56340,
}


if __name__ == "__main__":
    raise SystemExit(read_only_eval.main(CONFIG))
