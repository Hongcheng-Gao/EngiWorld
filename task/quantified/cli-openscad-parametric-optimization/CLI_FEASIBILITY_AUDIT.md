# CLI Feasibility Audit

Date: 2026-07-08
Remote instance: Ubuntu OpenSCAD 2021.01, `openscad` at `/usr/bin/openscad`

All five tasks were verified one by one through CLI-only OpenSCAD operation on the remote instance. For each task, `/home/user/Desktop` was cleared before setup, the task init files were uploaded, `optimized.scad` was created as a derived OpenSCAD source, `openscad -o optimized.stl optimized.scad` was run, `design_summary.json` was written, the task evaluator was run, generated GT artifacts were downloaded, and the desktop was cleared again.

| Task | Status | Eval valid | Reference score | Key metric |
| --- | --- | --- | --- | --- |
| task-01 | PASS-CLI | true | 1.0 | `surface_per_volume = 0.93398245` |
| task-02 | PASS-CLI | true | 0.995556 | `footprint_per_volume = 0.17945886` |
| task-03 | PASS-CLI | true | 0.997333 | `span_height_per_volume = 0.07476994` |
| task-04 | PASS-CLI | true | 0.995 | `clearance_surface_mix = 0.41015241` |
| task-05 | PASS-CLI | true | 0.99 | `low_profile_surface_density = 0.68648173` |

No task instruction or config change was required. The saved modifications are limited to official ground-truth artifacts, reference metrics in `eval.py`, and verification documentation.

The previous GT STL files were generated outside the actual OpenSCAD CLI export path. OpenSCAD CSG export merges touching boxes, so its measured surface area and volume can differ from a raw box-composition mesh. The current GT files now use the actual OpenSCAD CLI-exported STL, and the reference metrics match that exported geometry.
