# GUI Feasibility Audit

Owner: taozhuo

Task family: `task/multi/gui-4-librecad-freecad-kicad-blender`

Remote instance used during this audit: `115.191.26.197`

## Scope

The reference process requires checking whether each task can be completed through GUI operations and whether the resulting files pass that task's own `eval.py`. It also requires documenting each task, fixing tasks that are not GUI-completable without changing the core task logic, keeping instruction/eval/init/GT consistent, and clearing the instance Desktop plus closing applications after every task.

## Finding

The original task family was not reliably GUI-completable as written. The blocker was the KiCad-to-Blender handoff: the tasks asked Blender to import `stage3_*_board_profile.dxf`, but the provided Blender 4.2.3 installation has STL, SVG, FBX, and glTF import support and no bundled DXF import add-on. This made the original DXF handoff from KiCad to Blender unsuitable for a deterministic GUI-only workflow.

## Applied Fix

The four-software transfer logic is preserved:

- LibreCAD still produces the stage-1 mechanical DXF.
- FreeCAD still consumes the LibreCAD DXF and produces the stage-2 STL plus FreeCAD-to-KiCad handoff DXF.
- KiCad still consumes the FreeCAD handoff and creates the PCB/profile handoff.
- Blender still consumes the FreeCAD STL and KiCad handoff and exports the final GLB.

The KiCad-to-Blender handoff was changed from DXF to SVG, because Blender can import SVG through its GUI. Each task now requires both:

- `stage3_*_board.kicad_pcb`
- `stage3_*_board_profile.svg`

The evaluator checks both the native KiCad board content and the SVG handoff before checking the final GLB.

## Files Updated

For all 10 tasks:

- `task-XX.json`
- `eval.py`
- `ground_truth/flow_spec.json`
- `ground_truth/GT_GENERATION.md`
- `ground_truth/stage4_*.glb`
- `ground_truth/stage3_*_board.kicad_pcb`
- `ground_truth/stage3_*_board_profile.svg`
- `GUI_COMPLETION.md`

The stale `ground_truth/stage3_*_board_profile.dxf` files were removed.

## Verification Performed

1. Inspected the provided instance and confirmed the GUI software locations:
   - LibreCAD: `/usr/bin/librecad`
   - FreeCAD: `/usr/bin/freecad`
   - KiCad: `/home/user/Applications/kicad-10.0.2/kicad-10.0.2-x86_64.AppImage`
   - Blender: `/home/user/Applications/blender-4.2.3-linux-x64/blender`
2. Confirmed Blender's bundled add-ons include SVG import but not DXF import.
3. Launched the KiCad GUI from the AppImage and confirmed a `KiCad 10.0` window was visible.
4. Launched the Blender GUI and confirmed an `(Unsaved) - Blender 4.2.3 LTS` window was visible.
5. Uploaded task-01's seed file through the task setup path, launched LibreCAD with that seed, and confirmed the `LibreCAD - [seed_sensor_node_enclosure.dxf]` window was visible.
6. Regenerated GT artifacts for all 10 tasks with the GUI-friendly SVG handoff.
7. Ran each task's `eval.py` locally against its own `ground_truth` directory using `OUTPUT_ROOT`; result: `10/10 PASS`.
8. Uploaded each task's seed, GT artifacts, and `eval.py` to the remote instance one task at a time and ran the task evaluator; result: `10/10 PASS`.
9. After each remote task validation, removed all Desktop files and closed/killed LibreCAD, FreeCAD, KiCad, Blender, and related GUI processes.
10. Final remote instance check showed Desktop count `0` and no related GUI processes.

Remote validation report path on the local machine:

`/tmp/engiworld_gui4_gt_validation_after_svg_report.json`

GUI startup screenshots saved on the local machine:

- `/tmp/engiworld_kicad_gui_start.png`
- `/tmp/engiworld_blender_gui_start.png`
- `/tmp/engiworld_task01_librecad_seed_open.png`

## Per-Task Records

Each task has its own `GUI_COMPLETION.md` with the task-specific token, filenames, required geometry, board tokens, Blender GUI-export evidence, GUI workflow, modification reason, and validation status:

- `task-01/GUI_COMPLETION.md`
- `task-02/GUI_COMPLETION.md`
- `task-03/GUI_COMPLETION.md`
- `task-04/GUI_COMPLETION.md`
- `task-05/GUI_COMPLETION.md`
- `task-06/GUI_COMPLETION.md`
- `task-07/GUI_COMPLETION.md`
- `task-08/GUI_COMPLETION.md`
- `task-09/GUI_COMPLETION.md`
- `task-10/GUI_COMPLETION.md`


## Strict Blender GUI Export Pass

After the first audit, `task-01` showed that a normal Blender GUI export after importing the stage-2 STL and stage-3 SVG produced a valid `.glb` but failed the old evaluator because the old check expected hand-authored material/metadata tokens. The task family was therefore tightened to the GUI-supported evidence that Blender naturally exports: the asset generator must indicate Blender, the GLB must contain the imported stage-2 STL object name, and it must contain the imported SVG object filename such as `stage3_sensor_node_enclosure_board_profile.svg`. The SVG file itself is separately validated for `EDGE_FROM_STAGE2_HANDOFF`.

All 10 tasks were then re-run one at a time without uploading any stage-4 GLB. For each task, Blender imported the task-specific STL through `File > Import > STL`, imported the task-specific SVG through `File > Import > Scalable Vector Graphics (.svg)`, exported the required stage-4 `.glb` through `File > Export > glTF 2.0`, and the updated `eval.py` returned `True`. Each task was cleaned afterward. Local evidence artifacts for this pass are saved under `/tmp/engiworld_gui4_blender_export_only/task-01` through `/tmp/engiworld_gui4_blender_export_only/task-10`, with summary `/tmp/engiworld_gui4_blender_export_only/summary.json`.

## Evidence Boundary

The completed checks prove that the task definitions, instructions, ground truth files, and evaluators are internally consistent and pass on the provided instance, and that the original non-GUI-friendly DXF-to-Blender handoff has been replaced by a Blender-supported GUI import format. They now include a real Blender GUI export of every stage-4 GLB, but they still do not claim that the LibreCAD, FreeCAD, and KiCad intermediate files were fully redrawn from the seed through full mouse/keyboard GUI operation during this audit run.

## Final Consistency Check 2026-07-08

After the strict Blender GUI export pass, the task configs and evaluators were tightened again:

- All 10 task JSON files now use `quantified_score`, not `exact_match` or `score_from_stdout_last_line`.
- Each `eval.py` writes `score.json` and `quant_metrics.json` with `score=1.0` for a passing full-chain validation and `score=0.0` for failure, while still printing `True`/`False` for direct command-line checks.
- A repository scan found no stale `stage3_*_board_profile.dxf` ground-truth files and no old GLB token requirements such as `BODY_FROM_STAGE2_STL`, `PCB_FROM_STAGE3_DXF`, or `CHAIN_STAGE2_STAGE3_TO_BLENDER`.
- A structured consistency check verified that every task instruction, JSON config, `flow_spec.json`, init file, GT file, intermediate-output manifest, related-app list, and eval dependency list agree.
- Running all 10 eval scripts locally against their own `ground_truth` directories returned `10/10 PASS`; temporary local `score.json`, `quant_metrics.json`, and `eval_*.txt` files were removed afterward.
- A final remote cleanup check on `115.191.26.197` returned Desktop count `0`, no LibreCAD/FreeCAD/KiCad/Blender-related GUI processes, and only the Desktop Icons window.

After the strict Blender GUI export pass, all 10 tasks were run again one at a time on `115.191.26.197` to save the real GUI-generated stage-4 files. Blender imported the task-specific stage-2 STL and stage-3 SVG through GUI menus, exported glTF Binary through the GUI, and the Files GUI was used to rename `untitled.glb` to the required `stage4_*.glb` when Blender kept the default filename. Each exported GLB passed the task evaluator on the instance, was downloaded through the OSWorld `/file` endpoint, and was copied into the matching `ground_truth/stage4_*.glb`. The checked-in stage-4 GT files are therefore the downloaded Blender GUI exports, not package-generated fallback GLBs. Local evidence and downloaded copies are preserved under `/tmp/engiworld_gui4_downloaded_gui_gt`, with `/tmp/engiworld_gui4_downloaded_gui_gt/summary.json` showing all 10 tasks passing.

## Additional Manual Instance Evidence

On 2026-07-08, all 10 tasks were rechecked one at a time on `115.191.26.197` with direct GUI evidence for the handoff path. For each task:

- The task-specific seed DXF opened in LibreCAD from the Desktop.
- The task-specific stage-1 DXF opened and imported in FreeCAD.
- The task-specific stage-3 `.kicad_pcb` opened in KiCad PCB Editor.
- Blender 4.2.3 used `File > Import > Scalable Vector Graphics (.svg)` to import the task-specific stage-3 SVG handoff through the GUI file browser. For `task-01`, the Import menu was also captured showing both `STL (.stl)` and `Scalable Vector Graphics (.svg)`, the two required Blender handoff formats.
- The task evaluator returned `True` on the instance after the GUI checks.
- The instance was cleaned after the task: Desktop count `0`, no related GUI processes, and only the Desktop Icons window remained.

Local evidence artifacts were saved under `/tmp/engiworld_gui4_manual/task-01` through `/tmp/engiworld_gui4_manual/task-10`. Each task directory contains screenshots for uploaded Desktop state, LibreCAD seed opening, FreeCAD stage-1 opening, KiCad board opening, Blender startup, Blender SVG import, plus `07_eval_output.txt` and cleanup logs.
