// Starter file for task-017.
// Edit this file in OpenSCAD to complete the requested hard task.
$fn = 64;

tile = [70, 70, 8];
// Keep the starter centered in XY with its bottom on z=0.
translate([-tile[0] / 2, -tile[1] / 2, 0]) cube(tile, center=false);
