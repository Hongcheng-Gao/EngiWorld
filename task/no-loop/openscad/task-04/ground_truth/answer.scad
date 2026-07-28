$fn=64;
module photomask_holder() {
  difference() {
    union() {
      cube([160,160,8]);
      for(x=[5,145]) for(y=[5,145]) translate([x,y,8]) cube([10,10,4]);
    }
    translate([15,15,-1]) cube([130,130,10]);
  }
}
photomask_holder();
