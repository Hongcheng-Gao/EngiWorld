// Starter connector for task-004.
$fn = 64;

lower_od = 38;
upper_od = 28;
lower_height = 18;
transition_height = 0;
total_height = 40;
bore_diameter = 18;

difference() {
  union() {
    cylinder(h = lower_height, r = lower_od / 2);
    if (transition_height > 0) {
      translate([0, 0, lower_height])
        cylinder(h = transition_height, r1 = lower_od / 2, r2 = upper_od / 2);
    }
    translate([0, 0, lower_height + transition_height])
      cylinder(h = total_height - lower_height - transition_height, r = upper_od / 2);
  }

  translate([0, 0, -1])
    cylinder(h = total_height + 2, r = bore_diameter / 2);
}
