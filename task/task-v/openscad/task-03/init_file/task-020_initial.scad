// Starter file for task-020.
// Edit this file in OpenSCAD to complete the requested hard task.
$fn = 64;

module plate(w, d, t) {
    cube([w, d, t], center=true);
}

plate(100, 60, 4);
