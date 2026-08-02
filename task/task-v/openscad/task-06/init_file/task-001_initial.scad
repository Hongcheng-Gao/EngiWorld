// Starter shell for task-001. Units: millimetres.
// Preserve x=[-60,60], y=[-40,40], z=[0,28], wall=3, floor=4.
$fn = 64;

outer_w = 120;
outer_d = 80;
outer_h = 28;
wall = 3;
floor = 4;

module tray_shell() {
    difference() {
        translate([-outer_w/2, -outer_d/2, 0])
            cube([outer_w, outer_d, outer_h]);
        translate([-outer_w/2 + wall, -outer_d/2 + wall, floor])
            cube([outer_w - 2*wall, outer_d - 2*wall, outer_h + 1]);
    }
}

tray_shell();
