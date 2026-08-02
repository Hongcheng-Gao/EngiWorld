$fn = 48;

label_height = 0.8;
groove_depth = 1;

module step_block() {
  difference() {
    union() {
      translate([0, 0, 2.5])
        cube([40, 20, 5], center = true);
      translate([0, 0, 7.5])
        cube([30, 20, 5], center = true);
      translate([0, 0, 12.5])
        cube([20, 20, 5], center = true);
    }

    if (groove_depth > 0) {
      for (z = [2.5, 7.5, 12.5]) {
        translate([0, -10 + groove_depth / 2, z])
          cube([14, groove_depth, 1], center = true);
      }
    }
  }
}

step_block();

if (label_height > 0) {
  translate([17.5, 0, 5])
    linear_extrude(height = label_height)
      text("5", size = 3.2, font = "Liberation Sans:style=Regular",
           halign = "center", valign = "center");
  translate([12.5, 0, 10])
    linear_extrude(height = label_height)
      text("10", size = 2.6, font = "Liberation Sans:style=Regular",
           halign = "center", valign = "center");
  translate([0, 0, 15])
    linear_extrude(height = label_height)
      text("15", size = 4, font = "Liberation Sans:style=Regular",
           halign = "center", valign = "center");
}
