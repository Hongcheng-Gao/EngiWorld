// Starter hex nut for task-018.
$fn = 48;

across_flats = 22;
nut_height = 8;
hole_diameter = 8;

difference() {
  cylinder($fn = 6, h = nut_height, r = across_flats / sqrt(3));
  translate([0, 0, -1])
    cylinder(h = nut_height + 2, r = hole_diameter / 2);
}
