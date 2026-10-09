# GUI Completion Record: task-01

Status: regenerated, repaired, and independently validated on 2026-08-12.

Snapshot: `freecad-librecad-kicad-blender`

Software: LibreCAD 2.2.0.2, FreeCAD 0.21.2, KiCad PCB Editor 10.0.2, Blender 4.2.3 LTS.

## Repairs and rationale

- Re-generated all six GT files in their required real applications. This replaces the prior inconsistent artifacts with inspectable native outputs.
- Assigned the five KiCad footprints semantic references/values (`U1`, `J1`, `J2`, `LED1`, `LED2`), placed every footprint/pad and the transfer silkscreen within the closed board, and removed two text items from Edge.Cuts. This makes the board agree with the electronics instruction without constraining acceptable library families.
- Re-plotted only the four Edge.Cuts lines through KiCad as a 91.9988 x 57.9882 mm SVG. Its inherited style paints the four black strokes at full opacity, so the Blender handoff is visible rather than merely dimensioned.
- Rebuilt the Blender scene from the actual STL and SVG. The profile is a separate visible mesh; `LED_A_Lens` and `LED_B_Lens` are separate UV-sphere meshes with alpha 0.35 materials exported as `BLEND`.
- Tightened `eval.py` to check semantics and equivalence instead of exact GT bytes or footprint library names: native board structure, refs/values/pads/inside-board geometry, SVG inherited paint state, three-stage outline equality, transformed GLB accessors, STL vertex-shape overlap, profile geometry, and both transparent lenses.
- Final completion audit bound the four required texts to real `LABEL` entities and added dynamic lens-to-aperture/body alignment from the submitted stage-1 geometry; moving the lenses 1000 mm away now rejects.

## Validation matrix

Positive GT: `True`.

The unchanged init seed SHA-256 is `d695bf8cc01dccb0c7a3175f413ef39440e2460c013d6678c62cbd5973e4952a`, identical to `HEAD`.

| Isolated negative | Result | Rejection |
| --- | --- | --- |
| Move `J1` to `(300,300)` | `False` | footprint origin outside Edge.Cuts |
| SVG root `display:none` | `False` | no actually painted closed outline |
| SVG root `opacity=0` | `False` | no actually painted closed outline |
| Rename/remove one lens | `False` | missing required reachable lens mesh node |
| Keep GLB evidence names but remove mesh bindings | `False` | named evidence node has no mesh geometry |
| Remove only the profile mesh binding | `False` | profile evidence node has no mesh geometry |
| Dense 192-face full-box STL | `False` | fill ratio 1.0000 |

`python3 -m py_compile eval.py` and JSON parsing for `task-01.json` and `ground_truth/flow_spec.json` passed. Final artifact hashes are recorded in `ground_truth/GT_GENERATION.md`.

## Cleanup

After the final downloads and validations, all task deliverables, seed copies, evaluator outputs, KiCad sidecars/locks/history, Blender `.blend`/autosaves, temporary logs/scripts, and task-specific Trash entries were removed from the instance. LibreCAD, FreeCAD, KiCad/pcbnew/AppImage mount helpers, and Blender were terminated.

Final instance confirmation:

- `desktop_count 0`
- `task_tmp []`
- `trash_task []`
- `related_processes []`

The local isolated negative-test directories and evaluator output files were also removed after the matrix completed.

## Sources

- https://docs.librecad.org/en/2.2.0_a/
- https://github.com/LibreCAD/LibreCAD/releases/tag/2.2.0.2
- https://github.com/FreeCAD/FreeCAD/releases/tag/0.21.2
- https://github.com/yorikvanhavre/Draft-dxf-importer/tree/1.41
- https://wiki.freecad.org/Mesh_Export
- https://docs.kicad.org/10.0/en/pcbnew/pcbnew.html#plotting
- https://dev-docs.kicad.org/en/file-formats/sexpr-pcb/
- https://dev-docs.kicad.org/en/apis-and-binding/pcbnew/index.html
- https://www.w3.org/TR/SVG11/painting.html
- https://docs.blender.org/manual/en/4.2/addons/import_export/scene_gltf2.html
- https://docs.blender.org/manual/en/4.2/files/import_export/stl.html
- https://docs.blender.org/manual/en/4.2/addons/import_export/curve_svg.html
- https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html#materials
