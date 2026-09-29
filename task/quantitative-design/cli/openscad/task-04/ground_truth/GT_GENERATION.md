# Ground Truth Generation

Generated and verified with OpenSCAD 2021.01 CLI on the remote Ubuntu task instance on 2026-07-08.

Workflow:
- upload `starter.scad`, `baseline.stl`, and `constraints.json` to `/home/user/Desktop`
- create the derived `/home/user/Desktop/optimized.scad`
- run `openscad -o /home/user/Desktop/optimized.stl /home/user/Desktop/optimized.scad`
- write `/home/user/Desktop/design_summary.json`
- run the task evaluator with `python3 /home/user/Desktop/eval.py`
- save the CLI-exported STL and evaluator metrics as this ground truth

The reference is not a unique answer. The evaluator assigns a continuous score from the submitted STL geometry. Before scoring, it verifies one connected watertight positive-volume solid, the coordinate envelope, a continuous z=0 contact footprint, and 4-16 separated tall-finger runs at the z=24 mm probe with minimum thickness, clear gap, and openness. The reference metrics in this directory and in `eval.py` are measured from the actual OpenSCAD CLI export.
