# GUI Feasibility Audit

Remote instance: `115.190.253.51`

Software: FreeCAD 0.21.2

Scope: `task-01` through `task-05`

Result: all five tasks are GUI-completable in FreeCAD and pass their own evaluator. No task instruction, init file, ground truth package, or eval logic needed to be modified.

## Summary

| Task | Status | Remote eval | Score | Metric | Eval bbox |
| --- | --- | --- | ---: | --- | --- |
| task-01 | PASS-GUI | valid | 1.0 | `cantilever_load_per_volume` | `100.0 x 42.0 x 29.0` |
| task-02 | PASS-GUI | valid | 1.0 | `shelf_offset_load_per_volume` | `120.0 x 50.0 x 36.0` |
| task-03 | PASS-GUI | valid | 1.0 | `tall_gusset_load_per_volume` | `82.0 x 62.0 x 62.0` |
| task-04 | PASS-GUI | valid | 1.0 | `clamp_bridge_load_per_volume` | `92.0 x 58.0 x 28.76` |
| task-05 | PASS-GUI | valid | 1.0 | `hinge_strip_load_per_volume` | `112.0 x 46.0 x 22.6` |

## Saved GUI Ground Truth Evidence

Each task has a GUI-exported STL saved under `_gui_validation`:

- `_gui_validation/task-01/optimized.gui-export.final.stl`
- `_gui_validation/task-02/optimized.gui-export.final.stl`
- `_gui_validation/task-03/optimized.gui-export.final.stl`
- `_gui_validation/task-04/optimized.gui-export.final.stl`
- `_gui_validation/task-05/optimized.gui-export.final.stl`

Each task also has the remote evaluator outputs saved as:

- `_gui_validation/task-XX/score.remote.json`
- `_gui_validation/task-XX/quant_metrics.remote.json`

## GUI Workflow Finding

All tasks are completable with the same FreeCAD GUI workflow:

1. Launch FreeCAD with the uploaded `baseline.stl`.
2. Switch to the Part workbench.
3. Delete the imported baseline mesh from the Model tree.
4. Use `Part > Create primitives...` and choose `Box`.
5. Create the support/load pads, ribs, and base plate through the primitive dialog.
6. Close the primitive panel, select all created Box objects, and use `File > Export...` to save `/home/user/Desktop/optimized.stl`.
7. Run the task evaluator.

The FreeCAD 0.21.2 primitive dialog exports Box positions as if the entered nonzero Position values are applied twice. For this GUI route, the reproducible completion records therefore enter half of the intended nonzero lower-left origin in the primitive dialog. The exported STL lands at the intended coordinates and passes evaluation.

Do not press Enter while editing primitive fields. In this dialog, Enter can trigger `Create` and produce duplicate objects. Click between fields and click `Create` exactly once per primitive.

## Remote Eval Environment Note

The remote image had an incompatible `/usr/local` NumPy ahead of the system NumPy/SciPy packages. The evaluator was run with:

```bash
PYTHONPATH=/usr/lib/python3/dist-packages python3 eval.py
```

This only changes Python import precedence for evaluation. It was not used for FreeCAD modeling or STL generation.

## Cleanup Verification

After each task, FreeCAD was closed and task files were removed from `/home/user/Desktop`. After task-05, the desktop was empty and there were no FreeCAD processes left.
