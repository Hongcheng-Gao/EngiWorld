# Task-06 Ground Truth Generation

Generated independently on 2026-08-12 and 2026-08-13 in the designated `freecad-librecad-kicad-blender` snapshot. No simulated, package-generated, or offline replacement artifact is used as GT.

- LibreCAD 2.2.0.2 opened the provided seed and saved one closed 145 x 95 mm OUTLINE, the exact six GRILLE/HOLE circles, twelve real radial grille spokes, and EW4G06/PWM/RPM/FAN on LABEL, with GUIDE entities removed.
- FreeCAD 0.21.2 imported the LibreCAD output. Its mesh exporter produced a watertight 145 x 95 x 10 mm manufactured panel with a fan opening, twelve grille spokes, four mounting holes, an encoder hole/boss, and a raised rim. The same FreeCAD document exported the closed interface and two ShapeString labels as DXF.
- KiCad 10.0.2 imported the complete FreeCAD handoff through `File > Import > Graphics`. The final native board serializes the 296 imported members on `Dwgs.User`, four native outer `Edge.Cuts` segments, J1/SW1/DS1/SW2-SW5 native footprints with 20 pads, and the required native F.SilkS tokens. KiCad Plot generated the four-path Edge.Cuts SVG.
- Blender 4.2.3 used `File > Import > STL` and `File > Import > Scalable Vector Graphics (.svg)`. The SVG paths were restored to their actual 145 x 95 mm scale and aligned to the STL. The scene retains the real STL body, four imported SVG edge meshes, one raised encoder knob, and four independent raised buttons aligned to SW2-SW5. Blender's glTF 2.0 GUI exporter produced the binary GLB.

Post-generation evaluator regression re-ran the frozen six-file GT in an isolated directory and returned `True`. Material-only equivalents with arbitrary visible opaque colors, including glTF `OPAQUE` materials whose stored alpha is zero, also returned `True`; setting those same active-scene feature materials to `BLEND` with alpha zero returned `False`. No GT artifact was changed by this local evaluator hardening.

Frozen artifact SHA-256:

```text
49c60df707394f2a158ce48136e0779161dc8a280cb4d00c9533dfd622afe221  stage1_fan_control_panel.dxf
c3998ce73d73dcb3fad850fe769321b172c0c174d0cca8122bfb6865554e35a9  stage2_fan_control_panel.stl
df6a10e2c93e12d6694da7b09fd2bc481cf246f9735b952d3c6ae474dc2e1380  stage2_fan_control_panel_handoff_outline.dxf
1d7f9073b223e36622edf33b00b203b6fa37c2cbe245439c58391af97cbd919e  stage3_fan_control_panel_board.kicad_pcb
86f9bea5aecf558914c84d7479783dc79b39aba750428ab209aae8fbd9fed2be  stage3_fan_control_panel_board_profile.svg
2d09316400925300ef20d5e6ac143b879016b58d7474ab270753cf7ef4e3672e  stage4_fan_control_panel.glb
```

The unchanged init seed SHA-256 is `bffdb3346d7e5226ba597e3a172561306bfb82a0a5b8ec30826d2c2a1e16bd56`.

Official references:

- https://github.com/LibreCAD/LibreCAD/releases/tag/2.2.0.2
- https://docs.librecad.org/en/2.2.0_a/
- https://docs.librecad.org/en/2.2.0_a/guides/cmdline.html
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
