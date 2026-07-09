# Task 04 Handoff Notes

The KiCad board file is the only authoritative source for footprint centers, mounting-hole axes, and component heights.
The OpenSCAD stage must derive enclosure windows, standoffs, and keepouts from the KiCad mechanical map.
The FreeCAD stage must assemble the board and enclosure and verify mass and clearance.
The Blender stage must produce a material-coded review scene that makes the critical keepouts visible.

Critical requirement: The tray ribs must not enter the MOSFET bank keepouts and the phase terminal window must be on the X+ side.
