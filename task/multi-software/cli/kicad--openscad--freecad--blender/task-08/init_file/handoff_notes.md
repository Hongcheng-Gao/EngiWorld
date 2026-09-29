# Task 08 Handoff Notes

The KiCad board is authoritative for the outline, thickness, footprint centers, mounting-hole axes, component heights, and keepout radii. Requirements define installed Z placement, tray/lid/standoff geometry, creepage-web measurement, clearances, material, mass conversion, and tolerances. The connector CSV defines each access type, direction, finished dimensions, cutter bounds, and continuous-path bounds.

Use the PCB outline center as XY origin without rotating or mirroring KiCad X/Y. Z=0 is the tray bottom outer face, and Z_PLUS points toward the separate lid and F.Cu components. The tray ends at Z=20.5, the lid starts at Z=20.6, the PCB bottom is Z=5.0, and the PCB top is Z=6.6. The maximum component height is the maximum KiCad `HEIGHT_MM`, which is 8.0 mm at J1/J2; the 13 mm keepout radius is not a height.

The tray cavity is 184 x 46 mm, from X=-92 to 92 and Y=-23 to 23, so the 176 x 38 mm PCB has 4 mm clearance to every inner side wall. Each MH1-MH4 standoff starts at the base inner face Z=3.0, ends at the PCB bottom Z=5.0, has 8.0 mm outer diameter, and has a 3.7 mm bore cut from Z=2.5 to 5.5.

J1 and J2 require separate bounded 26 x 10 mm Y_PLUS side windows. Their respective wall cutters are `[-67.0, 22.5, 5.6, -41.0, 26.5, 15.6]` and `[41.0, 22.5, 5.6, 67.0, 26.5, 15.6]`. Their enclosure-free paths extend inward to Y=13.0 as recorded in the CSV. Bounds use `[xmin, ymin, zmin, xmax, ymax, zmax]`; neither access may become a full-height slot or merge with the other.

TP1 and TP2 each require a one-to-one cylindrical 6 mm finished-diameter Z_PLUS lid bore. The lid cutters run from Z=20.1 to 24.1, and each continuous enclosure-free path runs from its KiCad target top Z=6.8 to exterior Z=24.1, using the XY bounds in the CSV.

Measure the Y_PLUS side-wall web at the wall mid-plane Y=24.5 and window mid-height Z=10.6. The straight edge-to-edge segment from `[-41.0, 24.5, 10.6]` to `[41.0, 24.5, 10.6]` is nominally 82 mm and must be at least 80 mm. The probe box `[-41.0, 24.25, 10.35, 41.0, 24.75, 10.85]` has nominal volume 20.5 mm3; it must remain a single connected G10 material web with no more than 0.1 mm3 missing material.

FreeCAD must derive G10 carrier volume/mass, all four side clearances, covered-component top clearance, four standoff bore checks, all four access checks, busbar-window separation, creepage segment length and material continuity, and unintended interference from actual geometry. Blender must retain real tray, lid, PCB, component, access-review, and creepage-web objects; visibly distinguish J1, J2, TP1, TP2, and the measured web; save a native scene and render a review image.
