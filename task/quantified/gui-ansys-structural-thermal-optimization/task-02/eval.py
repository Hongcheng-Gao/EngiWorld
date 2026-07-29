#!/usr/bin/env python3
from read_only_eval import main


CONFIG = {
    "kind": "beam_buckling",
    "direction": "maximize",
    "baseline_files": ["baseline_wb_buckling.db", "baseline_wb_buckling.rst"],
    "submission_files": ["submission.db", "submission.rst"],
    "result_suffix": ".rst",
    "port_seed": 56320,
    "section": {"outer": [8.0, 20.0], "area": [80.0, 160.0], "wall": [1.0, 4.0]},
}


if __name__ == "__main__":
    raise SystemExit(main(CONFIG))
