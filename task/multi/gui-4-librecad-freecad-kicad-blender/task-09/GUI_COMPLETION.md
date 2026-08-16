# GUI Completion Record: task-09

Status: real four-application GT generated and evaluator validation passed on 2026-08-13.

Instance: `i-yeslqxefpc4c5qx3440g` (`freecad-librecad-kicad-blender`). Versions: LibreCAD 2.2.0.2, FreeCAD 0.21.2, KiCad 10.0.2, Blender 4.2.3.

The supplied init DXF was retained unchanged (SHA-256 `fdbb723af3e6865854350e20fe7f6cb47899e862a0e2a65147d0c2ca26cacde0`). It is a valid construction seed: a 105 x 48 guide rectangle, diagonals, four reference circles, and seed labels; it intentionally omits the final two 2.8 mm holes and both strap slots.

Every stage was handled independently in its named application. LibreCAD produced the completed DXF; FreeCAD imported it and exported both the physical STL and labeled handoff DXF; KiCad created a native padded/netted board and plotted its Edge.Cuts SVG; Blender natively imported the STL/SVG, added visible pogo/slot geometry, aligned the SVG to the cradle, and exported the GLB.

The evaluator checks semantic equivalence instead of byte equality. It accepts relocated labels, reasonable alternative closed slot dimensions, and native `gr_line`, `gr_rect`, or `gr_arc` Edge.Cuts when they form the same simple 105 x 48 boundary. It rejects missing/duplicate required geometry, box or surface-only STL fakes, disconnected handoffs, text-only KiCad boards, missing nets, invisible or self-crossing SVGs, inactive or malformed GLB nodes, displaced handoffs, and hidden/tiny/misaligned or incorrectly materialed pogo/slot geometry.

The final audit made the chain contract explicit in the instruction: KiCad must retain the complete handoff graphics and `FREECAD_TO_KICAD`/`EW4G09` text on Dwgs.User before deriving Edge.Cuts. It also changed KiCad 10 pad-net validation from normalized substring search to the exact names serialized as `(net "NAME")`. The unchanged real GT and a moved-label equivalent evaluate `True`; replacing every exact `VBAT` pad assignment with `NOTVBAT` evaluates `False`.

Remote cleanup is recorded after final validation in the repository-level repair report. No task-09 remote artifact is reused for task-10.
