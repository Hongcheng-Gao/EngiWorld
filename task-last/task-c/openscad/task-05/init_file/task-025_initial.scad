// Starter ribbed wheel for task-025.
$fn = 64;

ribs = 12;
outside_diameter = 38;
height = 16;
center_hole_diameter = 6;

difference() {
  union() {
    cylinder(h = height, r = outside_diameter / 2);
    for (i = [0 : ribs - 1])
      rotate([0, 0, 360 * i / ribs])
        translate([8, -1, 0])
          cube([12, 2, height]);
  }

  translate([0, 0, -1])
    cylinder(h = height + 2, r = center_hole_diameter / 2);
}
