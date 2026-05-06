$fn = 48;
module spool(flange_od=52, barrel_od=18, total_width=36, shaft_hole_d=6) {
  difference() {
    union() {
      cylinder(h = 4, r = flange_od/2);
      translate([0,0,total_width-4]) cylinder(h = 4, r = flange_od/2);
      cylinder(h = total_width, r = barrel_od/2);
    }
    translate([0,0,-1]) cylinder(h = total_width+2, r = shaft_hole_d/2);
  }
}
spool();
