#!/usr/bin/env python3
from read_only_eval import main


CONFIG = {
    "kind": "plate_mass",
    "direction": "minimize",
    "baseline_files": ["baseline_apdl_hole_plate.db", "baseline_apdl_hole_plate.rst"],
    "submission_files": ["submission.db", "submission.rst"],
    "result_suffix": ".rst",
    "port_seed": 56310,
}


if __name__ == "__main__":
    raise SystemExit(main(CONFIG))
