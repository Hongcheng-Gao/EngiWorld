// Starter flange for task-003.
$fn = 64;

outside_diameter = 72;
thickness = 8;
center_hole_diameter = 20;
bolt_circle_radius = 26;
bolt_hole_diameter = 4;
bolt_hole_count = 6;

difference() {
  cylinder(h = thickness, r = outside_diameter / 2);

  translate([0, 0, -1])
    cylinder(h = thickness + 2, r = center_hole_diameter / 2);

  for (i = [0 : bolt_hole_count - 1]) {
    angle = 360 * i / bolt_hole_count;
    translate([bolt_circle_radius * cos(angle), bolt_circle_radius * sin(angle), -1])
      cylinder(h = thickness + 2, r = bolt_hole_diameter / 2);
  }
}
