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
- measured protective-panel solid area: `5850.0`
- panel coverage/open ratio: `1.0 / 0.0`
- z=0 mounting contact area: `5850.0`
- four corner mounting-zone coverage ratios: `[1.0, 1.0, 1.0, 1.0]`
- four perimeter-wall edge-band and 1.99 mm inward-probe coverage ratios at z=8: all `1.0`
- metric `solid_panel_coverage_per_volume`: `0.17945886`
- cleanup: desktop verified empty after the run

Changes saved:
- regenerated `init_file/baseline.stl` as the actual single exterior boundary of `starter.scad`, without duplicate internal contact faces
- replaced `ground_truth/optimized.stl` with the actual OpenSCAD CLI export
- updated `ground_truth/design_summary.json`, `reference_metrics.json`, and `score.json`
- updated `eval.py` reference metrics and reference score
- instruction, constraints, GT metadata, and evaluator were synchronized on 2026-08-02 to replace bbox area with measured solid coverage and enforce panel, contact-zone, wall-thickness, and opening constraints
