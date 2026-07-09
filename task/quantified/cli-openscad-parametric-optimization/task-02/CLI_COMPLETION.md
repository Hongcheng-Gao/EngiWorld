# CLI Completion Verification

Status: PASS-CLI

Date: 2026-07-08
Remote environment: Ubuntu, OpenSCAD 2021.01 at `/usr/bin/openscad`
Task: `quant-cli-openscad-parametric-task-02-ubuntu`

Procedure:
- cleaned `/home/user/Desktop` before setup and verified it was empty
- uploaded `starter.scad`, `baseline.stl`, and `constraints.json`
- created `/home/user/Desktop/optimized.scad` as a derived OpenSCAD source
- ran `openscad -o /home/user/Desktop/optimized.stl /home/user/Desktop/optimized.scad`
- wrote `/home/user/Desktop/design_summary.json` with `case_id` and token `EWQSCAD02`
- uploaded `eval.py` and ran `python3 /home/user/Desktop/eval.py`
- downloaded the generated GT artifacts
- killed any remaining OpenSCAD process and cleared `/home/user/Desktop`

Result:
- valid: `true`
- reference score: `0.995556`
- bbox: `[90.0, 65.0, 16.0]`
- volume: `32598.0`
- surface area: `25585.0`
- metric `footprint_per_volume`: `0.17945886`
- cleanup: desktop verified empty after the run

Changes saved:
- replaced `ground_truth/optimized.stl` with the actual OpenSCAD CLI export
- updated `ground_truth/design_summary.json`, `reference_metrics.json`, and `score.json`
- updated `eval.py` reference metrics and reference score
- no instruction or task config change was required
