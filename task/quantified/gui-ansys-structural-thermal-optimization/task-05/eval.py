#!/usr/bin/env python3
from read_only_eval import main


CONFIG = {
    "kind": "solid_cantilever",
    "direction": "maximize",
    "baseline_files": ["baseline_apdl_solid_beam.db", "baseline_apdl_solid_beam.rst"],
    "submission_files": ["submission.db", "submission.rst"],
    "result_suffix": ".rst",
    "port_seed": 56350,
}


if __name__ == "__main__":
    raise SystemExit(main(CONFIG))
