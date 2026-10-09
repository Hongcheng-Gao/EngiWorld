# Task-05 Ground Truth Generation

Generated independently on 2026-08-12 in the designated `freecad-librecad-kicad-blender` snapshot. No package-generated, simulated, or offline replacement artifact is used as GT.

- LibreCAD 2.2.0.2 opened the provided seed and saved a 150 x 90 mm closed L outline, three closed tie-slot outlines, six exact HOLE circles, and the four required LABEL texts with GUIDE entities removed.
- FreeCAD 0.21.2 imported the LibreCAD output. Its real mesh exporter produced a watertight 150 x 90 x 24 mm L bracket with the six through-holes, three slots, raised wall/fold, and cable inlet. The same FreeCAD document exported the L interface, six circles, and two ShapeString labels as DXF.
- KiCad 10.0.2 imported the complete FreeCAD handoff onto `Dwgs.User`; its outer L interface was represented as six native `Edge.Cuts` segments. The board contains native J1, D1, and TP1 footprints with five pads, one positive-area native rule-area keepout, the imported handoff graphics, and native transfer silkscreen. KiCad Plot exported the six-segment Edge.Cuts SVG.
- Blender 4.2.3 natively imported the real FreeCAD STL and KiCad SVG, retained both as visible full-scale meshes, and created one connected opaque black cable that enters the bracket and crosses above and below the base through each of the three tie slots. Blender's glTF 2.0 exporter produced the binary GLB.

Three tie slots are the current GT implementation. The instruction's `TIE1`/`TIE2` wording and evaluator require at least two; equivalent submissions are checked against every slot they actually provide rather than against a hidden fixed count of three.

Frozen artifact SHA-256:

```text
444304678f2dd1b2d3008eda548e0c5475b87db5695690cb6ad2d5ce6a7e92e8  stage1_l_cable_strain_bracket.dxf
7218e799b8bb4bbf10a1395ad4cac5714b69c779b336ceb368030d8cd0346c6e  stage2_l_cable_strain_bracket.stl
dc880a5c051c1a8632140e74bd38002dde503d19236b8b587dd2edf5a18bad80  stage2_l_cable_strain_bracket_handoff_outline.dxf
f2e684777f7cd7887b4a6c28f286dd49024f28065bdd91be5556ad39afd3dd9f  stage3_l_cable_strain_bracket_board.kicad_pcb
c4b2014d3af013a4d0c080cf16d5f719661207398b1f5d7a1c2e3892bdb8013b  stage3_l_cable_strain_bracket_board_profile.svg
d4d262f2e00bce105b23fdd26bfac772b905479f6160af4ba6e6eda53f80dea4  stage4_l_cable_strain_bracket.glb
```

The unchanged init seed SHA-256 is `0fb90439cc0d2290c8cc7f35161ac55f7698089ffc7a4d631bb9d8bb4ae366fb`.

Official references:

- https://github.com/LibreCAD/LibreCAD/releases/tag/2.2.0.2
- https://docs.librecad.org/en/2.2.0_a/
- https://github.com/FreeCAD/FreeCAD/releases/tag/0.21.2
- https://wiki.freecad.org/Draft_DXF
- https://wiki.freecad.org/Std_Export
- https://wiki.freecad.org/Mesh_Export
- https://www.kicad.org/blog/2026/05/KiCad-10.0.2-Release/
- https://docs.kicad.org/10.0/en/pcbnew/pcbnew.html#importing-graphics
- https://docs.kicad.org/10.0/en/pcbnew/pcbnew.html#working-with-footprints
- https://docs.kicad.org/10.0/en/pcbnew/pcbnew.html#board-outlines
- https://docs.kicad.org/10.0/en/pcbnew/pcbnew.html#plotting
- https://docs.blender.org/manual/en/4.2/files/import_export/stl.html
- https://docs.blender.org/manual/en/4.2/addons/import_export/curve_svg.html
- https://docs.blender.org/manual/en/4.2/addons/import_export/scene_gltf2.html
