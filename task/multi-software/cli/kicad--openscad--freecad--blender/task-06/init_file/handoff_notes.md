# Task 06 Handoff Notes

The KiCad board is authoritative for the outline, thickness, footprint centers, mounting-hole axes, component heights, and keepout radii. Requirements define installed Z placement, tray/lid/standoff geometry, clearance, material, mass conversion, and tolerances. The connector CSV defines each access type, direction, finished dimensions, cutter bounds, and continuous-path bounds.

Use the PCB outline center as XY origin without rotating or mirroring KiCad X/Y. Z=0 is the tray bottom outer face, and Z_PLUS points toward the separate lid and F.Cu components. The tray ends at Z=18.5, the lid starts at Z=18.6, the PCB bottom is Z=4.7, and the PCB top is Z=6.3. The maximum component height is the maximum KiCad `HEIGHT_MM`, which is J1 at 7.8 mm; a keepout radius is not a height.

The tray cavity is 162 x 66 mm, from X=-81 to 81 and Y=-33 to 33, so the 154 x 58 mm PCB has 4 mm clearance to every inner side wall. Each MH1-MH4 standoff starts at the base inner face Z=3.4, ends at the PCB bottom Z=4.7, has 7.4 mm outer diameter, and has a 3.4 mm bore cut from Z=2.9 to 5.2.

J1 requires the bounded 25 x 9.4 mm X_MINUS window with cutter/path bounds `[-84.9, -12.5, 5.5, -80.5, 12.5, 14.9]`. J2 requires the bounded 20 x 7 mm X_PLUS window with bounds `[80.5, -10.0, 5.5, 84.9, 10.0, 12.5]`. Bounds use `[xmin, ymin, zmin, xmax, ymax, zmax]`; neither access may become a full-height slot.

F1 requires a cylindrical 18 mm finished-diameter Z_PLUS top opening. Its lid cutter occupies the cylinder bounded by `[11.0, 7.0, 18.1, 29.0, 25.0, 22.5]`, and the continuous path above the F1 body uses `[11.0, 7.0, 10.5, 29.0, 25.0, 22.5]`. The full KiCad F1 keepout cylinder from PCB top Z=6.3 to exterior Z=22.5 must have no enclosure-material intersection; the installed F1 body is intentional and is not enclosure interference.

FreeCAD must derive FR-PC enclosure volume/mass, all four side clearances, covered-component top clearance, four standoff bore checks, J1/J2 window continuity and direction, F1 keepout exclusion/opening continuity, and unintended interference from actual geometry. Blender must retain real tray, lid, PCB, component, and access-review objects; visibly distinguish J1, J2, and F1; save a native scene and render a review image.
