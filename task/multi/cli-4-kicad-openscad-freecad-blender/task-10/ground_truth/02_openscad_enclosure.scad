// Task 10: GNSS antenna keepout enclosure flow
// OpenSCAD stage generated from 01_kicad_mechanical_map.csv.
$fn = 64;
board = [82.000, 82.000, 1.200];
enclosure = [95.400, 95.400, 35.400];
wall = 2.700;
lid_clearance = 7.500;

module standoff(x, y) {
  translate([x, y, board[2]]) cylinder(d=6.440, h=wall + board[2]);
}
module keepout_window(x, y, r) {
  translate([x, y, enclosure[2]/2]) cube([2*r, wall*3, enclosure[2]], center=true);
}
module enclosure_shell() {
  difference() {
    translate([-enclosure[0]/2, -enclosure[1]/2, 0]) cube(enclosure);
    translate([-board[0]/2, -board[1]/2, wall]) cube([board[0], board[1], enclosure[2]]);
    // A1 PATCH_ANTENNA side/service keepout
    keepout_window(0.000, 16.000, 24.000);
    // J1 SMA_EDGE side/service keepout
    keepout_window(40.000, -12.000, 12.000);
  }
}
// MH1 copied from KiCad at (-34.000, -34.000)
// MH2 copied from KiCad at (34.000, -34.000)
// MH3 copied from KiCad at (-34.000, 34.000)
// MH4 copied from KiCad at (34.000, 34.000)
union() {
  enclosure_shell();
  standoff(-34.000, -34.000);
  standoff(34.000, -34.000);
  standoff(-34.000, 34.000);
  standoff(34.000, 34.000);
}
