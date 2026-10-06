# Task 01 Handoff Notes

The KiCad board is authoritative for the board outline, thickness, footprint centers, mounting-hole axes, and component heights. Mechanical requirements define the enclosure envelope, seating plane, clearances, tolerances, and material. The connector CSV defines aperture direction and size.
Use the PCB outline center as XY origin. Z=0 is the enclosure bottom outer face and Z increases toward the lid.
The OpenSCAD stage must derive the cavity, through-apertures, standoffs, and screw bores from the KiCad mechanical map and the supplied requirements.
The FreeCAD stage must assemble the real KiCad STEP board with the OpenSCAD enclosure, add component bodies from the authoritative map/requirements, and calculate mass, interference, side clearance, and U1-to-lid clearance from geometry.
The Blender stage must consume the FreeCAD mesh handoff, assign materials to actual objects, include visible J1/J2 aperture overlays and a U1 clearance overlay, save a .blend scene, and render the review image.

Critical requirement: USB-C and sensor FFC side windows must align to their KiCad footprint centers while preserving the lid clearance above U1.

J1 exits through the X_MINUS wall and J2 exits through the X_PLUS wall. Both apertures must provide a continuous void from the connector body to the enclosure exterior while leaving wall material around the opening. U1 clearance means the minimum Z distance from the U1 body top to a lid inner face that covers the U1 XY projection; an absent lid does not satisfy the requirement.

The submitted installed geometry may represent the covering lid as integral with the side walls or as a separate closed part. A particular parting-seam construction is not required, but a real 3 mm covering solid and the required measured clearance are required.

For each connector, `vertical_margin_mm` is the per-side opening allowance above and below the connector body, not the remaining wall outside the opening. Therefore `window_height_mm = KiCad HEIGHT_MM + 2 * vertical_margin_mm`; center that window at the connector body's nominal Z center. The connector CSV deliberately does not repeat height or keepout radius because those values remain authoritative in KiCad.

All `component_bodies_mm` arrays use `[x, y, z]` axis order. Connector `body_x_mm` and `body_y_mm` use the same enclosure/PCB X and Y axes.
