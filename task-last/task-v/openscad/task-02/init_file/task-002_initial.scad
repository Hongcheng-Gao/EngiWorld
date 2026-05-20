// Starter plate for task-002.
$fn = 48;

plate_width = 100;
plate_depth = 60;
plate_thickness = 6;
hole_diameter = 4;
edge_offset = 10;

difference() {
  translate([-plate_width / 2, -plate_depth / 2, 0])
    cube([plate_width, plate_depth, plate_thickness]);

  for (x = [-plate_width / 2 + edge_offset, plate_width / 2 - edge_offset])
    for (y = [-plate_depth / 2 + edge_offset, plate_depth / 2 - edge_offset])
      translate([x, y, -1])
        cylinder(h = plate_thickness + 2, r = hole_diameter / 2);
}
