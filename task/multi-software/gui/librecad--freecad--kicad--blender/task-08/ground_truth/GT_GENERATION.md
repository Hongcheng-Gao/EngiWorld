# Task-08 GT generation

All six GT artifacts were regenerated sequentially on 2026-08-13 in mapped instance `i-yeslqxefpc4c5qx3440g` (`freecad-librecad-kicad-blender`, private `10.0.6.53`). The init seed was inspected and retained unchanged; SHA-256: `b02fef7271a50b1f77549b97a18cd2aa0c7195bd69ad14d4e38ca36a6fd15b94`.

- LibreCAD 2.2.0.2 opened the seed and saved a drawing with one closed 165 x 52 outline, eight closed 15 x 20 windows, four mounting holes, five labels, and no GUIDE entity.
- FreeCAD 0.21.2 imported the LibreCAD DXF, built one watertight non-box solid with four bores and eight real window openings, and exported the 165 x 52 x 14 STL. For an unambiguous downstream contract, the handoff was reopened in FreeCAD, two Draft Text objects carrying `FREECAD_TO_KICAD` and `EW4G08` were added, and FreeCAD's Draft DXF exporter wrote the interface as four connected `LINE` entities plus the two exact `TEXT` entities.
- KiCad 10.0.2 imported the complete regenerated FreeCAD DXF with `File > Import > Graphics`, retained its graphics, and added exact native `Dwgs.User` text objects for `FREECAD_TO_KICAD` and `EW4G08` so the FreeCAD-to-KiCad handoff remains machine-verifiable. The board keeps a native closed 165 x 52 Edge.Cuts cycle, eight 2-pad terminal footprints, one 4-pad power footprint, 20 native pads, native channel/power nets, and actual F.SilkS text. PCB Editor's Plot dialog regenerated the PCBNEW SVG from Edge.Cuts with zero errors and zero warnings.
- Blender 4.2.3 imported the STL with its native STL importer and imported the PCBNEW SVG as four native curves. Those curves were restored to millimeter scale, converted into four mesh-bound aligned profile edges, and retained with the real STL. The scene binds a transparent-smoke transmission material to the STL, includes eight independent window-frame meshes and real triangulated `CH1` through `CH8` text meshes, and was exported with Blender's glTF Binary exporter.

SHA-256:

```text
494de71456e576cbc0c8cb2af0ee1f9474a1eed1b3edb86806344800ab62d766  stage1_terminal_cover_long.dxf
79af9e223b4f44c2146cacddb8def3ba8dbc3865ae019c486166a751797a00eb  stage2_terminal_cover_long.stl
9a80558e7412f5cd6723fce0ef09c5a828d2af4469d6ea758bce09dcda1b162a  stage2_terminal_cover_long_handoff_outline.dxf
476b2361fd5ca9cbf652eaf8bba3c2e3cb0c024146e144a4bbb7ec7307721bea  stage3_terminal_cover_long_board.kicad_pcb
e0019f0ac677aa85864adf16ec193cf65243a8bca75fb06425f2d4f333972cc1  stage3_terminal_cover_long_board_profile.svg
957143649f66845092434d2a8cc473a22cf9ea799cd02defd4c3a12077f58568  stage4_terminal_cover_long.glb
```

Validation on the real instance passed every artifact check after the downstream regeneration. The final isolated matrix accepted the real GT, a moved-label DXF, an equivalent PCBNEW `rect` SVG, and an equivalent native KiCad `gr_rect` board outline. It rejected a solid-box STL, missing or arbitrary handoff labels, disconnected/repeated handoff lines, default-invisible and ancestor-hidden SVG outlines, crossing/overlapping Edge.Cuts, a GLB import outside the active scene, wrong parent transforms or geometry-center alignment, invalid topology, a tiny window mesh, and cover materials lacking both alpha transparency and glTF transmission. Every case used its own temporary directory and matched the expected result.

An additional post-generation regression, without changing the frozen GT, accepted a standards-based transparent cover using `KHR_materials_transmission` with alpha 1 and rejected a KiCad board whose exact `GND` pad-net assignments were renamed to the substring lookalike `BARGND`. This confirms both supported transparency paths and exact KiCad 10 net-name handling.

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

Cleanup after closure: all four applications were closed; the seed, six deliverables, `.blend`/`.FCStd`/backup files, KiCad sidecars and locks, task scripts, screenshots, recovery data, history entries, trash entries, and malformed early-import residue were removed. Process, Desktop, `/tmp`, recovery, history, trash, and mount checks all returned zero task-specific residue. During task-08 startup, a stale task-07 FreeCAD recovery item was also discovered and removed with FreeCAD Document Recovery `Cleanup`.
