$fn = 64;
module cube_core() { cube([32, 32, 32], center = true); }
module cylinder_clip() { cylinder(h = 40, r = 18, center = true); }
cube_core();
