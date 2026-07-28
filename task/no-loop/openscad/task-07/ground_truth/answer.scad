$fn=64;
module sensor_lid() {
  difference() {
    cube([60,30,3]);
    for(i=[0:5]) translate([5,3+i*4,1]) cube([50,2,3]);
    for(x=[5,55]) translate([x,15,-1]) cylinder(d=6,h=5,$fn=48);
  }
}
sensor_lid();
