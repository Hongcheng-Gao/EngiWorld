$fn = 64;
difference() {
  cylinder(h = 3, r = 12);
  translate([0, 0, -1]) cylinder(h = 5, r = 4);
}
