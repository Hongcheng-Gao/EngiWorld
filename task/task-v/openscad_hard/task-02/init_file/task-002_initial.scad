// Starter file for task-002.
// Edit this file in OpenSCAD to complete the requested hard task.
$fn = 64;

height = 20;
body_d = 48;

module pulley_blank() {
    cylinder(d=body_d, h=height);
}

pulley_blank();
