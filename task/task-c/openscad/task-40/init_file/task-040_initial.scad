// Starter parametric adapter plate for task-040.
$fn = 64;

plate_width = 90;
plate_height = 66;
plate_thickness = 8;
corner_radius = 5;
center_hole_diameter = 28;
rect_hole_diameter = 4;
rect_pitch_x = 60;
rect_pitch_y = 40;
circle_hole_diameter = 3;
circle_pitch_diameter = 50;

difference() {
  linear_extrude(height = plate_thickness)
    offset(r = corner_radius)
      square([plate_width - 2 * corner_radius, plate_height - 2 * corner_radius], center = true);

  translate([0, 0, -1])
    cylinder(h = plate_thickness + 2, r = center_hole_diameter / 2);

  for (x = [-rect_pitch_x / 2, rect_pitch_x / 2])
    for (y = [-rect_pitch_y / 2, rect_pitch_y / 2])
      translate([x, y, -1])
        cylinder(h = plate_thickness + 2, r = rect_hole_diameter / 2);

  for (angle = [45, 135, 225, 315])
    translate([(circle_pitch_diameter / 2) * cos(angle), (circle_pitch_diameter / 2) * sin(angle), -1])
      cylinder(h = plate_thickness + 2, r = circle_hole_diameter / 2);
}
