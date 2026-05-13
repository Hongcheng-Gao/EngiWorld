# SolidCAM LibreCAD-style failure audit

Date: 2026-05-13

Scope:
- `D:/Engiworld/task/task-v/solidcam/task-01` through `task-20`
- `D:/Engiworld/task/task-c/solidcam/task-21` through `task-40`
- Audit focus: whether SolidCAM has the same failure pattern found in LibreCAD, where `eval.py` was effectively written against a copied/hidden ground truth instead of the task instruction.

## Executive Summary

I did not find the LibreCAD-style all-zero root cause in SolidCAM.

The SolidCAM evaluators do not compare the submitted output to `ground_truth` files by full-file equality, hash, copied summary, or a `DXF_SPECS`-style exact summary. They check instruction-level signals such as expected output filenames, NC/G-code basics, tools, spindle/feed values, Z levels, feature coordinates, work offsets, fixture clearance, forbidden collision points, or operation terms.

The initial files are task-specific and are not one copied template:
- 40/40 tasks have `init_file` content.
- No duplicate initial-file hashes were found across the SolidCAM tasks.
- Task-specific inputs include distinct STEP geometry plus, for CLI-style tasks, relevant `tools.csv`, `params.json`, `variants.json`, `post_config.json`, or `hole_table.csv` seed files.

Output contract is clean:
- Task roots contain only `eval.py` and `task-xx.json`.
- No `eval-windows.py`, `eval-ubuntu.py`, `task-xx-windows.json`, or `task-xx-ubuntu.json` remain.
- Instructions and active eval specs require only `.nc`/`.gcode` outputs.
- No task requires output `.csv`, `.txt`, `.json`, or `.pdf`.
- Ground truth outputs are only `.nc` and `.gcode`.

Validation:
- Ground-truth positive self-test: `40/40` passed.
- Shallow fake-output rejection for strengthened tasks: `task-20/23/30/31/33/35/37/38` all returned `false`.
- Search for exact-GT-match patterns found no active `ground_truth`, `summarize`, `DXF_SPECS`, `filecmp`, `hashlib`, `md5`, or `sha256` scoring logic.

## Fix Applied During This Audit

`task-v` tasks still contained a generic UI/process sentence:

`Use the SolidCAM CAM-Part, Coordinate System, Stock, Tool Table, operation, simulation/verify, and post-processing dialogs as needed, then save ...`

This was removed from `task-v/task-01` through `task-v/task-20`. The instructions now keep the task requirements and output path without unnecessary GUI/process wording.

## LibreCAD Failure Pattern Check

| LibreCAD failure mode | SolidCAM status |
|---|---|
| GT copied from a shared template while instruction says something else | Not found. Initial STEP/input files are task-specific; no duplicate init-file hashes. |
| Evaluator checks exact GT summary/full file instead of instruction | Not found. Eval checks rule fields derived from instruction/seed features, not a GT file summary. |
| Hidden required output types such as `.csv`, `.txt`, `.json`, `.pdf` | Not found. Active required outputs are `.nc` and one `.gcode` task. |
| Instruction vague, eval demands many unstated template entities | Mostly not found. Geometry coordinates are usually derived from named seed STEP/input files. |
| GT positive fails its own evaluator | Not found. All 40 GT outputs pass their own eval. |

## Repair Summary

The previously noted residual issues have been fixed without adding any non-NC output requirement.

- `task-19`: removed the hidden `min_motion: 20` requirement; eval now checks the explicit A-axis rotary output and T1.
- `task-20`: relaxed side-specific tool checks so side A no longer requires a B-side-only tool set, and side B no longer requires all tools.
- `task-23`: strengthened three independent profile programs with seed-derived outside-contour points and Z evidence.
- `task-30`: added fixture-clearance checking from `fixture.step` plus representative pocket points.
- `task-31`: strengthened turning evidence with spindle/feed values from `tools.csv` and X/Z turning motion.
- `task-33`: strengthened hole recognition by requiring all 24 seed-derived hole XY locations, four tool groups, spindle/feed values, and arc/thread/bore evidence.
- `task-35`: added safe-hole inclusion, risky-hole exclusion, spindle/feed values, and fixture-clearance rectangles.
- `task-37`: made A/B-side checks side-specific: side A pocket evidence; side B counterbore point evidence with the correct tool subset.
- `task-38`: strengthened Mill-Turn evidence with turning motion, C/Y live-tool motion, and tool spindle/feed values.
- `task-39`: removed the hidden `min_motion: 20` requirement; instruction now explicitly says to use A-axis rotary output, and eval checks A-axis plus supplied spindle/feed values.

### Remaining Optional Cleanup

The generated eval template still contains helper branches for JSON/CSV/PDF/text checking, but no active `SPEC` currently requires those output types. This is not a scoring issue because every active file rule is `.nc` or `.gcode`.

Recommendation: optional cleanup only. Removing unused helpers would make future reviews easier, but it is not required for correctness.

## Per-task Audit Table

| Task | Status | Notes |
|---|---|---|
| task-01 | OK | Face milling instruction, plate seed, and NC checks align. |
| task-02 | OK | Outside profile checks align with seed outline, T1, spindle/feed, and Z target. |
| task-03 | OK | Four-hole drilling instruction aligns with two-tool and four-point NC checks. |
| task-04 | OK | Centered pocket instruction aligns with pocket term, Z, and pocket-corner checks. |
| task-05 | OK | Chamfer instruction aligns with outside and four-hole-mouth point checks. |
| task-06 | OK | Face/drill/profile instruction aligns with tools, operation terms, and hole points. |
| task-07 | OK | Dual-pocket/iMachining instruction aligns with rough/finish terms, tools, Zs, and points. |
| task-08 | OK | Through/stepped-hole instruction aligns with six feature points and tools. |
| task-09 | OK | Rest-machining instruction aligns with two-tool, floor-Z, and rest-term checks. |
| task-10 | OK | `.gcode` output, inside/outside profile, kerf/profile terms, and feature points align. |
| task-11 | OK | Fixture-clearance instruction is actively checked with `min_clearance: 3`. |
| task-12 | OK | Manual tool table and operation instruction aligns with four tools and operation terms. |
| task-13 | OK | Two-coordinate-system instruction aligns with G54/G55-style work-offset checks. |
| task-14 | OK | Safe-hole drilling aligns with ten required points and two forbidden risky points. |
| task-15 | OK | 3D rough/finish spherical task aligns with tools, Zs, and rough/finish terms. |
| task-16 | OK | Turning task aligns with OD/groove/center-drill tool and term checks. |
| task-17 | OK | Complex fixture clearance is actively checked with `min_clearance: 4`. |
| task-18 | OK | Six M8 thread holes align with six points, Z target, and drill/thread tools. |
| task-19 | OK | A-axis rotary output is checked without hidden motion-count minimum. |
| task-20 | OK | Two-side outputs and side feature points align with side-specific tool subsets. |
| task-21 | OK | CLI face-milling task aligns with tool, spindle/feed, and Z checks. |
| task-22 | OK | Slot machining aligns with tool, spindle/feed, Z, and slot-point checks. |
| task-23 | OK | Three independent profile jobs now check each seed part's outside contour and Z target. |
| task-24 | OK | Hole-table task aligns with ten coordinate checks and depth/tool evidence. |
| task-25 | OK | Multi-feature tool-library task aligns with face/pocket/drill/profile terms and listed tools. |
| task-26 | OK | Pocket/drill/profile job aligns with three tools and operation terms. |
| task-27 | OK | Five variants align with five NC files and variant-specific Z targets. |
| task-28 | OK | Rest machining aligns with T1/T2, floor Z, and rest term. |
| task-29 | OK | Four-part work-offset task aligns with G54/G55/G56/G57 checks. |
| task-30 | OK | Fixture-clearance and pocket-point checks are active. |
| task-31 | OK | Turning tools, spindle/feed values, and X/Z turning motion are checked. |
| task-32 | OK | Params-driven task aligns with tools, spindle/feed values, and operation terms. |
| task-33 | OK | All 24 seed hole centers, tool groups, spindle/feed values, and arc evidence are checked. |
| task-34 | OK | Post settings align with program number and sequence-number checks. |
| task-35 | OK | Safe holes, risky-hole exclusion, fixture clearance, and tool parameters are checked. |
| task-36 | OK | Revision-B-only output aligns with output filename, tools, and revision-B term. |
| task-37 | OK | A-side and B-side output checks now use side-specific geometry and tool subsets. |
| task-38 | OK | Mill-Turn output now checks turning motion, live-tool C/Y motion, and tool parameters. |
| task-39 | OK | A-axis rotary output and supplied tool parameters are checked without hidden motion-count minimum. |
| task-40 | OK | Final benchmark aligns with five tool classes and six operation terms. |

## Bottom Line

SolidCAM does not show the specific LibreCAD all-zero failure mode. The residual strictness/coverage issues found in this audit have been repaired while keeping outputs limited to `.nc`/`.gcode`.
