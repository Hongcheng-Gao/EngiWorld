# Ground Truth Generation

Generated and verified with OpenSCAD 2021.01 CLI on the remote Ubuntu task instance on 2026-07-08.

Workflow:
- upload `starter.scad`, `baseline.stl`, and `constraints.json` to `/home/user/Desktop`
- create the derived `/home/user/Desktop/optimized.scad`
- run `openscad -o /home/user/Desktop/optimized.stl /home/user/Desktop/optimized.scad`
- write `/home/user/Desktop/design_summary.json`
- run the task evaluator with `python3 /home/user/Desktop/eval.py`
- save the CLI-exported STL and evaluator metrics as this ground truth

The reference is not a unique answer. The evaluator assigns a continuous score from the submitted STL geometry. The reference metrics in this directory and in `eval.py` are measured from the actual OpenSCAD CLI export.
