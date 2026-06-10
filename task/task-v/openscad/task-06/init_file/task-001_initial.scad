// Starter file for task-001.
// Edit this file in OpenSCAD to complete the requested hard task.
$fn = 64;

outer_w = 100;
outer_d = 60;
outer_h = 18;

module tray_shell() {
    difference() {
        cube([outer_w, outer_d, outer_h], center=false);
        translate([3, 3, 4]) cube([outer_w-6, outer_d-6, outer_h], center=false);
    }
}

tray_shell();
