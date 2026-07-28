$fn=64;
module heat_spreader() {
  union() {
    cube([50,50,3]);
    for(i=[0:8]) translate([3+i*5.5,2.5,3]) cube([1.5,45,12]);
  }
}
heat_spreader();
