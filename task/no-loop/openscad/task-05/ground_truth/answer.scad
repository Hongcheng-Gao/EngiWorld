$fn=64;
module die_tray() {
  difference() {
    cube([100,80,6]);
    for(ix=[0:4]) for(iy=[0:3])
      translate([8+ix*18,7+iy*18,2]) cube([12,12,5]);
  }
}
die_tray();
