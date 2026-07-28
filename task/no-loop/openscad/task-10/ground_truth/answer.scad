$fn=64;
module sensor_cap() {
  difference() {
    cylinder(d=24,h=10,$fn=96);
    translate([0,0,2]) cylinder(d=18,h=9,$fn=96);
    translate([0,0,-1]) cylinder(d=8,h=12,$fn=64);
    for(a=[45:90:315]) rotate([0,0,a])
      translate([9,0,-1]) cylinder(d=1.2,h=12,$fn=24);
  }
}
sensor_cap();
