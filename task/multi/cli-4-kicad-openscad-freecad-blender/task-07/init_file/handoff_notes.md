# Task 07 Handoff Notes

The KiCad board is authoritative for the outline, thickness, footprint centers, mounting-hole axes, component heights, and keepout radii. Requirements define installed Z placement, tray/lid/standoff geometry, the optical corridor, clearances, material, mass conversion, and tolerances. The connector CSV defines J1 access type, direction, finished dimensions, cutter bounds, and continuous-path bounds.

Use the PCB outline center as XY origin without rotating or mirroring KiCad X/Y. Z=0 is the tray bottom outer face, and Z_PLUS points toward the separate lid and F.Cu components. The tray ends at Z=10.1, the lid starts at Z=10.2, the PCB bottom is Z=5.2, and the PCB top is Z=6.2. The maximum component height is the maximum KiCad `HEIGHT_MM`, which is J1 at 2.8 mm; the J1 keepout radius of 8 mm is not a height.

The tray cavity is 74 x 50 mm, from X=-37 to 37 and Y=-25 to 25, so the 66 x 42 mm PCB has 4 mm clearance to every inner side wall. Each MH1-MH4 standoff starts at the base inner face Z=2.0, ends at the PCB bottom Z=5.2, has 5.6 mm outer diameter, and has a 2.6 mm bore cut from Z=1.5 to 5.7.

J1 requires the bounded 16 x 4.4 mm Y_MINUS side window with cutter/path bounds `[-8.0, -27.5, 5.4, 8.0, -24.5, 9.8]` in `[xmin, ymin, zmin, xmax, ymax, zmax]` order. It must be continuous through the relative wall and must not become a full-height slot. The fixed bounds leave 0.3 mm carrier material below the tray top, so the applicable minimum guard is 0.25 mm.

The optical corridor is the finite flat-capped cylinder of radius 0.5 mm whose axis starts at LED1 `[-16.0, 0.0, 8.2]` and ends at PD1 `[16.0, 0.0, 8.2]`. Carrier material means tray, lid, standoffs, and any added structural feature; it excludes the PCB, installed components, and review overlays. Carrier intersection with this cylinder may not exceed 0.05 mm3.

FreeCAD must derive PETG carrier volume/mass, all four side clearances, covered-component top clearance, four standoff bore checks, J1 window direction/continuity, optical endpoint/radius values, corridor/carrier intersection, and unintended interference from actual geometry. Blender must retain real tray, lid, PCB, component, and access-review objects and add a visible independent optical overlay matching both corridor endpoints and radius; save a native scene and render a review image.
