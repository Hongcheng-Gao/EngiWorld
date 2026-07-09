# GUI Bonsai Daylight Optimization Benchmark

This directory contains five quantified GUI-only Bonsai/Blender daylight optimization tasks. Each task provides an initial IFC model, explicit constraints and site data, a reference optimized IFC, and a continuous evaluator that computes score from IFC geometry rather than self-reported metrics.

Contestants must use the Bonsai/Blender graphical interface and save `/home/user/Desktop/optimized.ifc`. The evaluator ignores score reports and parses real `IfcSpace`, `IfcWall`, `IfcSlab`, `IfcDoor`, `IfcWindow`, `IfcShadingDevice`, and fixed site-obstruction geometry.

| Task | Objective | Baseline score | Reference score |
| --- | --- | ---: | ---: |
| task-01 | Office shell daylight without overglazing | 0.331264 | 0.960247 |
| task-02 | Studio flat privacy daylight tradeoff | 0.423841 | 0.950387 |
| task-03 | Corner shop daylight and display restraint | 0.255823 | 0.821033 |
| task-04 | Clinic waiting room daylight with low clinical gain | 0.367748 | 0.885608 |
| task-05 | Learning room balanced window layout | 0.299147 | 0.952072 |

Per task, `init_file/constraints.json` documents allowed facades, WWR limits, sill/head limits, immutable objects, invalid conditions, and required outputs. `init_file/site.json` documents orientation weights and external obstructions. `ground_truth/optimized.ifc` is a non-unique reference solution used for sanity checking, not an answer the model should match.
