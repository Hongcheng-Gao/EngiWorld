// Starter nozzle for task-012.
$fn = 64;

lower_height = 10;
taper_height = 18;
neck_height = 10;
exit_chamfer_height = 0;

lower_od = 28;
middle_od = 18;
exit_od = 12;

bottom_bore_diameter = 14;
middle_bore_diameter = 8;
exit_bore_diameter = 5;
bore_lower_height = 12;
side_hole_diameter = 0;

total_height = lower_height + taper_height + neck_height + exit_chamfer_height;

difference() {
  union() {
    cylinder(h = lower_height, r = lower_od / 2);

    translate([0, 0, lower_height])
      cylinder(h = taper_height, r1 = lower_od / 2, r2 = middle_od / 2);

    translate([0, 0, lower_height + taper_height])
      cylinder(h = neck_height, r = middle_od / 2);

    if (exit_chamfer_height > 0) {
      translate([0, 0, lower_height + taper_height + neck_height])
        cylinder(h = exit_chamfer_height, r1 = middle_od / 2, r2 = exit_od / 2);
    }
  }

  translate([0, 0, -1])
    cylinder(h = bore_lower_height + 2, r = bottom_bore_diameter / 2);

  translate([0, 0, bore_lower_height])
    cylinder(h = max(total_height - bore_lower_height - exit_chamfer_height + 1, 1), r = middle_bore_diameter / 2);

  if (exit_chamfer_height > 0) {
    translate([0, 0, total_height - exit_chamfer_height])
      cylinder(h = exit_chamfer_height + 1, r1 = middle_bore_diameter / 2, r2 = exit_bore_diameter / 2);
  }

  if (side_hole_diameter > 0) {
    translate([-20, 0, 18])
      rotate([0, 90, 0])
        cylinder(h = 40, d = side_hole_diameter);
  }
}
