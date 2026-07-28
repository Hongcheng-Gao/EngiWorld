$fn=64;
module flipchip_fixture() {
  difference() {
    union() {
      cube([60,60,8]);
      translate([8,8,8]) cube([4,44,5]);
      translate([48,8,8]) cube([4,44,5]);
    }
    translate([12,12,4]) cube([36,36,6]);
    for(x=[6,54]) for(y=[6,54])
      translate([x,y,-1]) cylinder(d=4,h=10,$fn=40);
  }
}
flipchip_fixture();
