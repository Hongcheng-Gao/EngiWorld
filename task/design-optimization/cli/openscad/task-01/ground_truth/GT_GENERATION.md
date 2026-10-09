# Ground Truth Generation

Generated and verified with OpenSCAD 2021.01 CLI on the remote Ubuntu task instance on 2026-07-08.

Workflow:
- upload `starter.scad`, `baseline.stl`, and `constraints.json` to `/home/user/Desktop`
- create the derived `/home/user/Desktop/optimized.scad`
- run `openscad -o /home/user/Desktop/optimized.stl /home/user/Desktop/optimized.scad`
- write `/home/user/Desktop/design_summary.json`
- run the task evaluator with `python3 /home/user/Desktop/eval.py`
- save the CLI-exported STL and evaluator metrics as this ground truth

The reference is not a unique answer. The evaluator first requires one connected, watertight solid, a quantified z=0 contact base, and straight fins with enforceable minimum thickness and externally open spacing. It then assigns a continuous geometry-proxy score using the connected exterior-shell area minus the bottom contact area, divided by material volume. This is not a thermal or CFD result. The reference metrics in this directory and in `eval.py` are measured from the actual OpenSCAD CLI export.
