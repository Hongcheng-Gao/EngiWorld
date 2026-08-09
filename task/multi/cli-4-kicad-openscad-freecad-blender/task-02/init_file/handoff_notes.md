# Task 02 Handoff Notes

The KiCad board is authoritative for the outline, thickness, footprint centers, mounting-hole axes, component heights, and keepout radii. Mechanical requirements define the package envelope, PCB seating plane, clamp contact, clearances, tolerances, and material. The connector CSV defines finished side-window directions and sizes.
Use the PCB outline center as XY origin. Z=0 is the package bottom outer face, and Z increases toward the covering lid. `component_bodies` dimensions use `[x, y, z]` order.
The OpenSCAD stage must derive the cavity, side windows, bored standoffs, covering lid, and component keepouts from the KiCad-derived map and supplied requirements. The U1 thermal contact may be modeled there or installed as a separate real solid in the final FreeCAD assembly.
The FreeCAD stage must assemble the real KiCad STEP board, the OpenSCAD clamp, and real component proxy solids. It must calculate mass, interference, side clearance, U1 contact gap, L1 keepout intrusion, and C1 clearance from geometry.
The Blender stage must consume the FreeCAD mesh handoff, retain the real enclosure/PCB/component objects, visibly mark the J1 path, J2 path, L1 keepout, C1 clearance, and U1 contact as independently identifiable mesh overlays, save a native scene, and render the review image.

Critical requirement: the full L1 interior keepout must remain empty and C1 clearance must be at least `minimum_c1_clamp_clearance_mm`.

The L1 keepout is the vertical cylinder centered on the KiCad L1 footprint, using its `KEEPOUT_RADIUS_MM`, from the nominal PCB top to the covering lid inner face. No internal clamp, rib, boss, or other package material may intrude into that cylinder. The 2.6 mm covering lid above its inner face is required and is not part of the interior keepout volume; deleting the lid does not satisfy the requirement.

C1 clearance is the minimum upward Z distance from the C1 body top to the nearest installed clamp or lid material that covers any part of the KiCad C1 keepout-radius region. It must be at least `minimum_c1_clamp_clearance_mm`; an absent covering solid does not count as infinite clearance.

The U1 contact pad is a real 6 x 6 mm clamp solid centered on U1. It runs continuously from a lower face whose non-negative gap to the nominal U1 body top is within `maximum_u1_contact_gap_mm` to the lid inner face. The installed lid and contact structure may be integral or separate installed parts, but a disconnected floating sheet is not a contact structure.

J1 exits through the X_MINUS wall and J2 through the X_PLUS wall. Each finished opening uses the connector CSV width and height, is centered on its footprint in Y, is centered vertically on the nominal connector body, and extends by `aperture_overcut_mm` beyond both wall faces while retaining at least `minimum_aperture_guard_mm` of wall material around every opening edge.
