# Task 09 Handoff Notes

The KiCad board is authoritative for the outline, thickness, footprint centers, mounting-hole axes, component heights, and keepout radii. Requirements define installed Z placement, tray/lid/standoff geometry, heater exposure, clearances, material, mass conversion, and tolerances. The connector CSV defines each access type, direction, finished dimensions, cutter bounds, and continuous-path bounds.

Use the PCB outline center as XY origin without rotating or mirroring KiCad X/Y. Z=0 is the tray bottom outer face, and Z_PLUS points toward the separate lid and F.Cu components. The tray ends at Z=22.5, the lid starts at Z=22.6, the PCB bottom is Z=13.4, and the PCB top is Z=15.0. The maximum component height is the maximum KiCad `HEIGHT_MM`, which is J1 at 4.6 mm.

The tray cavity is 126 x 100 mm, from X=-63 to 63 and Y=-50 to 50, so the 118 x 92 mm PCB has 4 mm clearance to every inner side wall. Each MH1-MH4 standoff starts at the base inner face Z=2.5, ends at the PCB bottom Z=13.4, has 6.9 mm outer diameter, and has a 3.2 mm bore cut from Z=2.0 to 13.9.

J1 requires the bounded 20 x 6.2 mm X_MINUS window with cutter `[-66.0, -10.0, 14.2, -62.5, 10.0, 20.4]` and enclosure-free path extending inward to X=-49.0. J2 requires the bounded 16 x 5.6 mm X_PLUS window with cutter `[62.5, -8.0, 14.2, 66.0, 8.0, 19.8]` and path extending inward to X=49.0. Bounds use `[xmin, ymin, zmin, xmax, ymax, zmax]`; both accesses must be continuous through their relative walls and must not become full-height slots.

H1 and H2 each require an independent cylindrical 36 mm finished-diameter Z_PLUS top opening on the KiCad axis. Their respective lid-cutter bounds are `[-42.0, -30.0, 22.1, -6.0, 6.0, 25.6]` and `[6.0, -30.0, 22.1, 42.0, 6.0, 25.6]`. Each enclosure-free path runs from heater body top Z=16.0 to exterior Z=25.6. Each complete radius-18 projected keepout from PCB top Z=15.0 to exterior may intersect carrier material by no more than 0.1 mm3 and must retain at least 99% open area. The two openings remain distinct with a nominal 12 mm edge gap, never less than 10 mm.

FreeCAD must derive black-PA12 mount volume/mass, all four side clearances, covered-component top clearance, four standoff bore checks, all four access checks, per-heater carrier intersection/open-area ratio, heater-opening edge gap, and unintended interference from actual geometry. Blender must retain real tray, lid, PCB, component, access-review, and heater-zone objects; visibly distinguish H1, H2, J1, and J2 in a non-occluded review; save a native scene and render a review image.
