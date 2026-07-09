# Task 02 Handoff Notes

The KiCad board file is the only authoritative source for footprint centers, mounting-hole axes, and component heights.
The OpenSCAD stage must derive enclosure windows, standoffs, and keepouts from the KiCad mechanical map.
The FreeCAD stage must assemble the board and enclosure and verify mass and clearance.
The Blender stage must produce a material-coded review scene that makes the critical keepouts visible.

Critical requirement: The OpenSCAD clamp must leave a keepout over L1 and the FreeCAD assembly must report positive clearance over the bulk capacitor.
