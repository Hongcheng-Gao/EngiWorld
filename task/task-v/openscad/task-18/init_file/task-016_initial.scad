// Starter file for task-016.
// Edit this file in OpenSCAD to complete the requested hard task.
$fn = 64;

base = [80, 45, 5];
back = [80, 5, 35];
cube(base, center=true);
translate([0, 20, 18]) cube(back, center=true);
