# Task 05 Handoff Notes

The KiCad board is authoritative for the outline, thickness, footprint centers, mounting-hole axes, component heights, and keepout radii. Requirements define installed Z placement, tray/lid/standoff geometry, clearances, material, and tolerances. The connector CSV defines access type, direction, finished dimensions, cutter bounds, and continuous-path bounds.

Use the PCB outline center as XY origin without rotating or mirroring KiCad X/Y. Z=0 is the tray bottom outer face, and Z_PLUS points toward the separate lid and F.Cu components. The tray ends at Z=17.5, the lid starts at Z=17.6, the PCB bottom is Z=6.6, and the PCB top is Z=8.2.

The tray cavity must be 102 x 78 mm, from X=-51 to 51 and Y=-39 to 39, so the 94 x 70 mm PCB has 4 mm clearance to every inner side wall. Each MH1-MH4 standoff starts at the base inner face Z=2.8, ends at the PCB bottom Z=6.6, has 6.9 mm outer diameter, and has a 3.2 mm bore cut with 0.5 mm Z overcut.

TP1-TP4 each require a one-to-one 5.0 mm finished-diameter Z_PLUS lid bore on the KiCad target axis. The lid cutter runs from Z=17.1 to 20.9, and the complete access column from the target top Z=8.4 to exterior Z=20.9 must contain no residual enclosure material. J1 requires the bounded 22 x 6 mm Y_PLUS side window with cutter bounds `[-11.0, 38.5, 7.4, 11.0, 42.3, 13.4]` in `[xmin, ymin, zmin, xmax, ymax, zmax]` order. It is not a full-height slot.

FreeCAD must derive enclosure volume/mass, all four side clearances, component top clearances, standoff bore checks, per-target pogo access continuity, J1 access continuity, and unintended interference from actual submitted geometry. Blender must retain real tray, lid, PCB, component, and access-review objects; visibly distinguish TP1-TP4 and J1; save a native scene and render a review image.
