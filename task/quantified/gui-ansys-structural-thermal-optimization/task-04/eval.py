#!/usr/bin/env python3
from read_only_eval import main


CONFIG = {
    "kind": "thermal_path",
    "direction": "minimize",
    "baseline_files": ["baseline_wb_conduction.db", "baseline_wb_conduction.rth"],
    "submission_files": ["submission.db", "submission.rth"],
    "result_suffix": ".rth",
    "port_seed": 56340,
}


if __name__ == "__main__":
    raise SystemExit(main(CONFIG))
