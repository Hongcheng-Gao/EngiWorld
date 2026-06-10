// Starter file for task-005.
// Edit this file in OpenSCAD to complete the requested hard task.
$fn = 64;

module vertical_pipe() {
    difference() {
        cylinder(d=30, h=40);
        translate([0,0,-1]) cylinder(d=12, h=42);
    }
}

vertical_pipe();
