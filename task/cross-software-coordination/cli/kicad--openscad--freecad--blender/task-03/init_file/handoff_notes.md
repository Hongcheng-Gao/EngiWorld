# Task 03 Handoff Notes

Software baseline for the final visualization stage: Blender 5.1.2 from this snapshot.

The KiCad board is authoritative for the outline, thickness, footprint centers, mounting-hole axes, component heights, and keepout radii. Requirements define package placement, the installed RF shield, protected volume, clearances, tolerances, and materials. The connector CSV defines each finished side window or top access bore.

Use the PCB outline center as XY origin. Z=0 is the package bottom outer face. Seat the PCB bottom at `board_bottom_z_mm`; the nominal PCB top is that value plus the KiCad thickness. A covering package lid is required.

The RF shield is an installed closed-top can centered on U1. Its protected volume is the axis-aligned inner XY box in `protected_volume`, from the nominal PCB top to `z_max_mm`. Containment and exclusion apply to the complete KiCad keepout cylinders, not only nominal component bodies. U1's keepout cylinder must be fully contained. J1's keepout cylinder must have zero intersection and positive separation from the protected volume. The shield must be a distinct installed solid so its geometry and mass remain independently auditable. It must have no positive-volume overlap with the package; shared boundary faces are allowed. Omitting it is not a valid solution.

J1 and J2 require bounded continuous side openings through the CSV wall directions. TP1 requires a continuous Z_PLUS cylindrical access bore through the covering lid. Every access uses the finished CSV dimensions, requirements overcut, and minimum guard material.

FreeCAD must calculate enclosure and shield volume/mass separately, actual PCB side clearance, U1 protected-volume containment, J1 protected-volume intersection and separation, J1/J2/TP1 access continuity, and unintended interference from geometry. Blender must retain package, shield, PCB, and component roles; visibly distinguish the protected volume, U1 inclusion, J1 exclusion, J2 opening, and TP1 bore; save a native scene and render a review image.
