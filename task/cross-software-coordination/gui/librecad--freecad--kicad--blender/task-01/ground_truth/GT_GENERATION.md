# Ground Truth Generation: task-01

All six ground-truth artifacts were regenerated independently in the assigned `freecad-librecad-kicad-blender` instance. No offline or simulated artifact is used as GT.

## Real-software provenance

- LibreCAD 2.2.0.2 opened the supplied seed, removed GUIDE entities, completed the 92 x 58 geometry and required labels, and saved `stage1_sensor_node_enclosure.dxf`.
- FreeCAD 0.21.2 imported stage 1, modeled the detailed open enclosure, exported the watertight `stage2_sensor_node_enclosure.stl`, and exported the labeled four-edge handoff through Draft DXF importer 1.41.
- KiCad PCB Editor 10.0.2 imported that handoff on Edge.Cuts. The native pcbnew board contains five semantic footprints (`U1`, `J1`, `J2`, `LED1`, `LED2`), 46 pads, exactly four closed Edge.Cuts lines, no Edge.Cuts text, and one F.SilkS transfer block. All footprint geometry, pads, references/values, and transfer text are within the 92 x 58 board. KiCad plotted only Edge.Cuts with Fit page to board to create the visible four-path SVG.
- Blender 4.2.3 LTS natively imported the stage-2 STL and stage-3 SVG. The SVG curves were given visible thickness and converted to a distinct mesh. Blender added `LED_A_Lens` and `LED_B_Lens` as visible mesh objects with alpha 0.35 translucent materials, then exported the scene through its glTF Binary exporter.

## Cross-stage checks

- The normalized FreeCAD handoff, KiCad Edge.Cuts, and painted SVG are the same closed 92 x 58 rectangle.
- The Blender enclosure node preserves the STL vertex geometry after glTF node transforms and axis conversion.
- The Blender profile node preserves a thin, visibly meshed 92 x 58 SVG outline.
- Both lens nodes bind separate nondegenerate meshes and materials exported with `alphaMode=BLEND`.

## Final artifact hashes

| File | SHA-256 |
| --- | --- |
| `stage1_sensor_node_enclosure.dxf` | `0a29341900ae278216f1255ea1b5536444b8dada6919b086aa05455670ca577a` |
| `stage2_sensor_node_enclosure.stl` | `734c53bcdd51702879ade5c8b31c051d97b6dc27d47308e74ef7affdab102cb4` |
| `stage2_sensor_node_enclosure_handoff_outline.dxf` | `4e1ce45b844b791cedf3bb8b1b68182361bfbabf5718abcf2e7b908cc7c9d83e` |
| `stage3_sensor_node_enclosure_board.kicad_pcb` | `869675b00348b8f673db691bfe1b7727c8e8a339e544c62354f6b10035d3f04f` |
| `stage3_sensor_node_enclosure_board_profile.svg` | `ef170e280e35fc3b4c2ee72f196ff04f6a55f6a345d1ca5f0632bb5c6c850a26` |
| `stage4_sensor_node_enclosure.glb` | `ee0125ecb73c31955b65b1612ff0b6b1409809d2fc240b4292c52df24da2924e` |

The unchanged init seed SHA-256 is `d695bf8cc01dccb0c7a3175f413ef39440e2460c013d6678c62cbd5973e4952a`.

## Official references

- LibreCAD 2.2.0 manual: https://docs.librecad.org/en/2.2.0_a/
- LibreCAD 2.2.0.2 release: https://github.com/LibreCAD/LibreCAD/releases/tag/2.2.0.2
- FreeCAD 0.21.2 release: https://github.com/FreeCAD/FreeCAD/releases/tag/0.21.2
- FreeCAD Draft DXF importer 1.41: https://github.com/yorikvanhavre/Draft-dxf-importer/tree/1.41
- FreeCAD mesh export: https://wiki.freecad.org/Mesh_Export
- KiCad 10 plotting and SVG options: https://docs.kicad.org/10.0/en/pcbnew/pcbnew.html#plotting
- KiCad board S-expression format: https://dev-docs.kicad.org/en/file-formats/sexpr-pcb/
- KiCad pcbnew Python bindings: https://dev-docs.kicad.org/en/apis-and-binding/pcbnew/index.html
- SVG paint and visibility semantics: https://www.w3.org/TR/SVG11/painting.html
- Blender 4.2 glTF importer/exporter: https://docs.blender.org/manual/en/4.2/addons/import_export/scene_gltf2.html
- Blender 4.2 STL import: https://docs.blender.org/manual/en/4.2/files/import_export/stl.html
- Blender 4.2 SVG import: https://docs.blender.org/manual/en/4.2/addons/import_export/curve_svg.html
- glTF 2.0 material alpha semantics: https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html#materials
