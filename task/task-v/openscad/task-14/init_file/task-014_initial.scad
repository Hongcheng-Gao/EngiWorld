$fn = 64;

shaft_diameter = 5;
shaft_length = 18;
shoulder_diameter = 10;
shoulder_thickness = 0;
flat_y = 3;
groove_width = 0;
groove_root_diameter = 10;

module support_pin() {
  difference() {
    union() {
      cylinder(h = shaft_length, d = shaft_diameter);
      if (shoulder_thickness > 0) {
        translate([0, 0, shaft_length])
          cylinder(h = shoulder_thickness, d = shoulder_diameter);
      }
    }

    translate([-shaft_diameter, flat_y, -1])
      cube([shaft_diameter * 2, shaft_diameter, shaft_length + 2]);

    if (groove_width > 0) {
      translate([0, 0, shaft_length + shoulder_thickness / 2])
        rotate_extrude()
          translate([groove_root_diameter / 2, -groove_width / 2])
            square([shoulder_diameter, groove_width]);
    }
  }
}

support_pin();
