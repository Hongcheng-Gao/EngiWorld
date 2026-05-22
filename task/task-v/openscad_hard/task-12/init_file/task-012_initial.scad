// Starter file for task-012.
// Edit this file in OpenSCAD to complete the requested hard task.
$fn = 64;

difference() {
    cylinder(d=50, h=24);
    translate([0,0,-1]) cylinder(d=16, h=26);
}
