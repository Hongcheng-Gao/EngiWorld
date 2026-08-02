$fn = 64;

module yz_prism(x_min, thickness, profile) {
    multmatrix([
        [0, 0, 1, x_min],
        [1, 0, 0, 0],
        [0, 1, 0, 0],
        [0, 0, 0, 1]
    ])
        linear_extrude(height = thickness)
            polygon(points = profile);
}

difference() {
    union() {
        translate([-40, -28, 0]) cube([80, 56, 8]);

        translate([-33, -18, 8]) cube([6, 36, 44]);
        translate([27, -18, 8]) cube([6, 36, 44]);

        yz_prism(-33, 6, [[12, 8], [26, 8], [12, 44]]);
        yz_prism(27, 6, [[12, 8], [26, 8], [12, 44]]);
    }

    translate([0, 0, 34])
        rotate([0, 90, 0])
            cylinder(h = 68, d = 12, center = true);

    for (x = [-25, 25], y = [-15, 15])
        translate([x, y, -1]) cylinder(h = 10, d = 6);
}
