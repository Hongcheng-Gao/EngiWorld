# Task 04 Handoff Notes

Use the PCB outline center as package XY origin and the tray bottom outer face as Z=0. Do not rotate or mirror the KiCad coordinates. The board bottom is Z=9.0 and its top is Z=10.6.

The covering package is a tray from Z=0 to Z=23.1 plus a separate 3.2 mm lid from Z=23.2 to Z=26.4, leaving the specified 0.1 mm assembly separation so the two remain distinct solids. Its inner XY walls are X=+/-68 and Y=+/-47, leaving 4 mm around the 128 x 86 mm PCB. The lid inner face is 3.6 mm above the top of J1, the tallest component.

Create bored standoffs on all four KiCad mounting axes from Z=3.2 to Z=9.0. Each 3.7 mm bore must remain continuous through the base and standoff using the specified 0.5 mm Z overcut. Create both required 104 x 3 x 2.5 mm ribs at the exact bounds in the requirements, and retain each rib as a distinct installed solid so its bounds and keepout clearance remain independently auditable. The Q1-Q3 rib exclusions are projected radius-18 mm columns from the base top to the lid inner face; this makes rib clearance a real structural check rather than an automatically passing component-top check. Extra structural features are allowed only if they preserve all exclusions, accesses, board clearances, and guards.

J1 is a bounded 28 x 11 mm X_PLUS side window and J2 is a bounded 16 x 6 mm X_MINUS side window. Each opening must reach from its connector toward and through the named exterior wall, use the 0.5 mm cutter overcut, retain at least 2 mm guard material, and must not become a full-height slot.

KiCad is authoritative for outline, thickness, footprint centers, mounting axes, heights, and keepout radii. The requirements are authoritative for installed Z, tray/lid/rib/standoff geometry, materials, and tolerances. The connector CSV is authoritative for access direction and finished window dimensions.

FreeCAD must calculate material volume/mass, four side clearances, top clearance, per-rib intersection and separation from each Q keepout, both window continuity checks, standoff bores, and unintended interference from actual geometry. Blender must retain real tray, lid, PCB, component, and rib objects and visibly distinguish the three Q keepout columns, both ribs, and J1/J2 access directions.

Critical requirement: both required ribs must exist and remain outside Q1-Q3 projected keepout columns, while J1 remains externally accessible through the bounded X_PLUS wall window.
