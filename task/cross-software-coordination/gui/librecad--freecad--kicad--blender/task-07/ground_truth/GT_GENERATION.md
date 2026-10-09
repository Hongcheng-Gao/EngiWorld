# Task-07 GT generation

All six GT artifacts were regenerated sequentially on mapped instance `i-yeslqxefpc4c5qx3440g` (`freecad-librecad-kicad-blender`, private `10.0.6.53`) on 2026-08-13. The unchanged init seed SHA-256 is `d336ed4dc48fcdb6cbee1fa0cdeac0fb1f09032565e7bb29425d1301f4767502`.

- LibreCAD 2.2.0.2 opened the seed and saved `stage1_sbc_hat_mount_plate.dxf` with one closed outline, five holes, two closed clearance regions, and four labels.
- FreeCAD 0.21.2 imported that DXF, created the opened/ring-standoff body, exported the STL, and exported the same model's interface plus two ShapeStrings as the handoff DXF.
- KiCad 10.0.2 imported the complete FreeCAD handoff with `File > Import > Graphics`, retained 278 imported members on `Dwgs.User`, added a native 85 x 65 `Edge.Cuts`, four native footprints/54 pads, a camera rule-area keepout, and F.SilkS text. PCB Editor saved the board and its Plot dialog generated the PCBNEW SVG.
- Blender 4.2.3 imported the STL with `File > Import > STL` and the SVG with `File > Import > Scalable Vector Graphics (.svg)`. The SVG was converted to four mesh-bound full-scale edges; four brass standoffs, an aligned GPIO40 header with 40 pins, and a board plane were added. `File > Export > glTF 2.0` generated the binary GLB.

Post-generation evaluator hardening did not change any frozen GT artifact. Isolated reruns accepted the real GT, a smaller positive-area camera rule region still overlapping the submitted CAM region, and the unchanged visible brass material renamed without `BRASS` in its name. They rejected an empty active GLB scene and black metallic standoffs. Clearance geometry is evaluated from each submission's two semantically labeled stage-1 KEEP_OUT regions rather than the GT's exact rectangle dimensions or coordinates.

SHA-256:

```text
975c19e1b628c7a95c2a729f35de497d2c0df70627f714735f99ae6fd357db5f  stage1_sbc_hat_mount_plate.dxf
a0b8ee44cf7d8a3f7a83780b5faeca6cafefcc43d5cc3daf945feaf0f1a6b866  stage2_sbc_hat_mount_plate.stl
a34aa74cc86e22186ec1b19bdc7609ac0357d88c4623aaa122186bba0ca90a0b  stage2_sbc_hat_mount_plate_handoff_outline.dxf
d1d9fe6703959e6ab3aa483d00e9a15fdd3bf9c6511192dda706dc6e26199f50  stage3_sbc_hat_mount_plate_board.kicad_pcb
2299e54cd2a75d00c71b6a3184123972e59f55b079f49e52a9ea587bba0515d3  stage3_sbc_hat_mount_plate_board_profile.svg
74a4e25024e813743c756e1a7b48f123e8abc97aa94b48382272b4273a86bc86  stage4_sbc_hat_mount_plate.glb
```

Official sources:

- https://github.com/LibreCAD/LibreCAD/releases/tag/2.2.0.2
- https://docs.librecad.org/en/2.2.0_a/
- https://github.com/FreeCAD/FreeCAD/releases/tag/0.21.2
- https://wiki.freecad.org/Draft_DXF
- https://wiki.freecad.org/Mesh_Export
- https://www.kicad.org/blog/2026/05/KiCad-10.0.2-Release/
- https://docs.kicad.org/10.0/en/pcbnew/pcbnew.html#importing-graphics
- https://docs.kicad.org/10.0/en/pcbnew/pcbnew.html#working-with-footprints
- https://docs.kicad.org/10.0/en/pcbnew/pcbnew.html#board-outlines
- https://docs.kicad.org/10.0/en/pcbnew/pcbnew.html#plotting
- https://docs.blender.org/manual/en/4.2/files/import_export/stl.html
- https://docs.blender.org/manual/en/4.2/addons/import_export/curve_svg.html
- https://docs.blender.org/manual/en/4.2/addons/import_export/scene_gltf2.html
