# Ground Truth Generation

Generated and verified with OpenSCAD 2021.01 CLI on the remote Ubuntu task instance on 2026-07-08.

Workflow:
- upload `starter.scad`, `baseline.stl`, and `constraints.json` to `/home/user/Desktop`
- create the derived `/home/user/Desktop/optimized.scad`
- run `openscad -o /home/user/Desktop/optimized.stl /home/user/Desktop/optimized.scad`
- write `/home/user/Desktop/design_summary.json`
- run the task evaluator with `python3 /home/user/Desktop/eval.py`
- save the CLI-exported STL and evaluator metrics as this ground truth

The reference is not a unique answer. The evaluator rasterizes actual solid occupancy instead of using bounding-box area. It requires one connected solid, a continuous protective panel at the tolerance-safe z=1.99 mm thickness probe, quantified z=0 corner mounting contact, and perimeter walls that pass both edge-band and 1.99 mm inward thickness probes with bounded openings at z=8.0 mm. It then assigns a continuous score from measured protective-panel solid area per material volume. The reference metrics in this directory and in `eval.py` are measured from the actual OpenSCAD CLI export.
