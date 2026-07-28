$fn=64;
module wafer_cassette() {
  union() {
    cube([150,6,126]); translate([0,134,0]) cube([150,6,126]);
    cube([150,140,6]);
    for(i=[0:11]) {
      translate([5,6,10+i*10]) cube([140,4,3]);
      translate([5,130,10+i*10]) cube([140,4,3]);
    }
  }
}
wafer_cassette();
