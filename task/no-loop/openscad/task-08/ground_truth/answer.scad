$fn=64;
module probe_spacer() {
  difference() {
    cylinder(d=80,h=5,$fn=128);
    translate([0,0,-1]) cylinder(d=50,h=7,$fn=128);
    for(a=[0:22.5:337.5]) rotate([0,0,a])
      translate([32,0,-1]) cylinder(d=2,h=7,$fn=24);
  }
}
probe_spacer();
