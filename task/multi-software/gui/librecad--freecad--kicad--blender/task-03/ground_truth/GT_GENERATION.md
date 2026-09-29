# Task-03 Ground Truth Generation

Generated independently on 2026-08-12 in the designated `freecad-librecad-kicad-blender` snapshot. No package-generated or offline replacement artifact is used.

- LibreCAD 2.2.0.2 opened the provided seed and saved the layered stage-1 DXF. The result has one 125 x 78 outline, three SLOT zones, seven fin guides, five holes, four labels, and no GUIDE layer.
- FreeCAD 0.21.2 imported stage 1. A Part carrier with plate, terminal zones, heatsink base, seven fins, and five through holes was exported through FreeCAD's mesh exporter. The same model produced the four-edge/five-hole handoff DXF and two ShapeString label blocks through FreeCAD's DXF exporter.
- KiCad 10.0.2 created a native pcbnew board with five semantic footprints, 16 pads, the matching four-segment Edge.Cuts outline, one Dwgs.User heatsink rectangle, and native F.SilkS transfer text. The exact AppImage `kicad-cli pcb export svg` plotted the Edge.Cuts SVG.
- Blender 4.2.3 imported the real stage-2 STL and stage-3 SVG, corrected SVG millimetre scale, retained the imported objects, and exported the assembled GLB. Because Blender 4.2 imports KiCad's open SVG paths as edge-only meshes that glTF omits, four thin full-scale visible edge meshes were derived in the Blender scene while retaining the original imported path objects.

The listed SLOT dimensions, fin X positions, and Blender object names describe this real GT only. The evaluator accepts geometrically equivalent layouts and renamed assembly objects when the required semantic topology, materials, counts, and spatial assembly remain correct.

Frozen artifact SHA-256:

```text
740c4f4780bd30b5f5747955aa73cd0f2270b602a4b4aa5aa83bf12cb21f7557  stage1_motor_driver_heatsink_carrier.dxf
890f22b80bf752e813f371d19b35877b86644dbd6eed56df1c1dcf66606ead6e  stage2_motor_driver_heatsink_carrier.stl
b1ce2ad4aca5e6899def6f711ac7b481c8c7be079a036f680f6bac14069dd68f  stage2_motor_driver_heatsink_carrier_handoff_outline.dxf
913a5194ff69ff54b9a4177a2ae703710df0f06e2caa4b465703f4c14de8f8e9  stage3_motor_driver_heatsink_carrier_board.kicad_pcb
e9589e0989b7e75eb7638df78ff421c42a8aeaab9e345c7882c92b715800c03b  stage3_motor_driver_heatsink_carrier_board_profile.svg
04a4764aac13d4c9ee3c649d9784c033f3408e18a276ac764fcbad04f7264224  stage4_motor_driver_heatsink_carrier.glb
```

The unchanged init seed SHA-256 is `4770358f24f551c81265d474fe13476b6252cffd12d134bf32c694996d405a56`.

Official references:

- https://github.com/LibreCAD/LibreCAD/releases/tag/2.2.0.2
- https://docs.librecad.org/en/2.2.0_a/
- https://github.com/FreeCAD/FreeCAD/releases/tag/0.21.2
- https://wiki.freecad.org/Draft_DXF
- https://wiki.freecad.org/Mesh_Export
- https://www.kicad.org/blog/2026/05/KiCad-10.0.2-Release/
- https://docs.kicad.org/10.0/en/pcbnew/pcbnew.html#board-outlines
- https://docs.kicad.org/10.0/en/pcbnew/pcbnew.html#plotting
- https://docs.blender.org/manual/en/4.2/files/import_export/stl.html
- https://docs.blender.org/manual/en/4.2/addons/import_export/curve_svg.html
- https://docs.blender.org/manual/en/4.2/addons/import_export/scene_gltf2.html
