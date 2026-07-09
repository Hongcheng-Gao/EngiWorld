// Task 01: Environmental sensor pod board-to-enclosure release
// OpenSCAD stage generated from 01_kicad_mechanical_map.csv.
$fn = 64;
board = [86.000, 54.000, 1.600];
enclosure = [100.000, 68.000, 18.800];
wall = 3.000;
lid_clearance = 4.200;

module standoff(x, y) {
  translate([x, y, board[2]]) cylinder(d=7.360, h=wall + board[2]);
}
module keepout_window(x, y, r) {
  translate([x, y, enclosure[2]/2]) cube([2*r, wall*3, enclosure[2]], center=true);
}
module enclosure_shell() {
  difference() {
    translate([-enclosure[0]/2, -enclosure[1]/2, 0]) cube(enclosure);
    translate([-board[0]/2, -board[1]/2, wall]) cube([board[0], board[1], enclosure[2]]);
    // J1 USB_C side/service keepout
    keepout_window(-39.000, 0.000, 10.000);
    // J2 SENSOR_FFC side/service keepout
    keepout_window(33.000, -16.000, 8.500);
  }
}
// MH1 copied from KiCad at (-36.000, -22.000)
// MH2 copied from KiCad at (36.000, -22.000)
// MH3 copied from KiCad at (-36.000, 22.000)
// MH4 copied from KiCad at (36.000, 22.000)
union() {
  enclosure_shell();
  standoff(-36.000, -22.000);
  standoff(36.000, -22.000);
  standoff(-36.000, 22.000);
  standoff(36.000, 22.000);
}
