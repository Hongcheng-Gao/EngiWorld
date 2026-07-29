#!/usr/bin/env python3
from read_only_eval import main


CONFIG = {
    "kind": "beam_modal",
    "direction": "maximize",
    "baseline_files": ["baseline_apdl_fixed_beam_modal.db", "baseline_apdl_fixed_beam_modal.rst"],
    "submission_files": ["submission.db", "submission.rst"],
    "result_suffix": ".rst",
    "port_seed": 56330,
    "section": {"outer": [6.0, 16.0], "area": [50.0, 160.0], "wall": [1.0, 4.0]},
}


if __name__ == "__main__":
    raise SystemExit(main(CONFIG))
