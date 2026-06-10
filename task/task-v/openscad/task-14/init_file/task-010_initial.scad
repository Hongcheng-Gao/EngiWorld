// Starter rounded nameplate for task-010.
$fn = 48;

plate_width = 80;
plate_height = 28;
corner_radius = 4;
plate_thickness = 5;
hole_diameter = 3;
hole_edge_offset = 10;

difference() {
  linear_extrude(height = plate_thickness)
    offset(r = corner_radius)
      square([plate_width - 2 * corner_radius, plate_height - 2 * corner_radius], center = true);

  for (x = [-plate_width / 2 + hole_edge_offset, plate_width / 2 - hole_edge_offset])
    for (y = [-plate_height / 2 + hole_edge_offset, plate_height / 2 - hole_edge_offset])
      translate([x, y, -1])
        cylinder(h = plate_thickness + 2, r = hole_diameter / 2);
}
