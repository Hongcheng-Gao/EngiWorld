# Task-07 completion

Status: PASS after real-software regeneration and task-specific validation.

The former GT was invalid: package-created DXFs, a 12-face full-box STL, a board with no footprints or pads, a handwritten SVG, and a GLB whose SVG evidence node had no mesh. The instruction was clarified only where the design goal already required native electronics and a visible exploded mount scene.

Validation on the mapped instance returned `True` for the six downloaded GT artifacts. The evaluator checks exact LibreCAD geometry/layers; a watertight non-box FreeCAD body with holes, clearance openings, and raised standoffs; a real ShapeString handoff; native KiCad outline/import group/footprints/pads/keepout/silkscreen; painted PCBNEW SVG geometry; and mesh-bound Blender STL/SVG/standoffs/GPIO40 geometry.

An isolated 21-case negative matrix returned `False` for every case, including the old package GT, full-box STL, incomplete handoff, token-only board, missing pad, open Edge.Cuts, missing keepout, viewBox-only SVG, handwritten SVG, meshless STL/SVG nodes, shifted standoff, and missing brass material. A dynamic equivalent positive with the Blender board/profile/standoffs/header assembly shifted together by 10 mm returned `True`, confirming that a reasonable exploded height is not locked to the GT.

A final completion audit removed the remaining GT-coordinate and name shortcuts. The two stage-1 clearance regions are now identified by positive-area topology and containment of the submitted `GPIO40` and `CAM` labels; FreeCAD openings are derived from those submitted regions; and the KiCad F.Cu camera rule area only needs positive area and overlap with the submitted CAM region. An inset camera keepout equivalent returned `True`. GLB evidence is now restricted to the active scene, and each standoff's bound material must be visibly gold/brass colored and metallic without depending on its name. The unchanged real GT and a renamed `Equivalent_Gold_Metal` material returned `True`; an empty active scene and black metallic standoffs each returned `False`.

Remote cleanup after validation removed the seed, all six deliverables, FreeCAD source/backups, Blender source, KiCad sidecars/locks/plot extras, evaluator outputs, `/tmp/task07_*`, recovery/history records, Trash content, and the one-time KiPython startup hook. Final counts were: Desktop task files `0`; `/tmp/task07_*` `0`; Trash entries `0`; recovery/task files `0`; related application processes `0`; KiCad mounts `0`; history hits `0`; Desktop history files `0`; KiPython startup hook `0` bytes.
