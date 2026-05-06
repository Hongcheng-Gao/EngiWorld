// Starter knob for task-011.
$fn = 64;

knob_diameter = 44;
knob_height = 18;
shaft_hole_diameter = 6;
recess_count = 8;
recess_depth = 1.5;

difference() {
  cylinder(h = knob_height, r = knob_diameter / 2);

  translate([0, 0, -1])
    cylinder(h = knob_height + 2, r = shaft_hole_diameter / 2);

  for (i = [0 : recess_count - 1])
    rotate([0, 0, 360 * i / recess_count])
      translate([knob_diameter / 2 - recess_depth, 0, knob_height / 2])
        rotate([0, 90, 0])
          cylinder(h = 8, r = 2, center = true);
}
