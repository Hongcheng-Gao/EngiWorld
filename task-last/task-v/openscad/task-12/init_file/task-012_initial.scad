// Starter tapered nozzle for task-012.
$fn = 64;

height = 34;
bottom_od = 26;
top_od = 12;
bottom_bore_diameter = 14;
top_bore_diameter = 5;

difference() {
  cylinder(h = height, r1 = bottom_od / 2, r2 = top_od / 2);
  translate([0, 0, -1])
    cylinder(h = height + 2, r1 = bottom_bore_diameter / 2, r2 = top_bore_diameter / 2);
}
