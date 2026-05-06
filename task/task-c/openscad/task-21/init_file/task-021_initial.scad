// Starter bracket parameters for task-021.
$fn = 48;

width = 70;
depth = 50;
base_height = 5;
back_height = 60;
back_thickness = 5;
slot_width = 8;
slot_height = 28;

difference() {
  union() {
    translate([-width / 2, -depth / 2, 0])
      cube([width, depth, base_height]);
    translate([-width / 2, depth / 2 - back_thickness, base_height])
      cube([width, back_thickness, back_height]);
  }

  translate([0, depth / 2 - back_thickness / 2, base_height + back_height / 2])
    cube([slot_width, back_thickness + 3, slot_height], center = true);
}
