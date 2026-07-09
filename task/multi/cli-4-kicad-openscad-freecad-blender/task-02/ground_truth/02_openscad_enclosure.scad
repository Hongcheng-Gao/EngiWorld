// Task 02: Buck regulator heat-spreader clamp package
// OpenSCAD stage generated from 01_kicad_mechanical_map.csv.
$fn = 64;
board = [104.000, 62.000, 1.600];
enclosure = [117.200, 75.200, 18.600];
wall = 2.600;
lid_clearance = 2.400;

module standoff(x, y) {
  translate([x, y, board[2]]) cylinder(d=6.900, h=wall + board[2]);
}
module keepout_window(x, y, r) {
  translate([x, y, enclosure[2]/2]) cube([2*r, wall*3, enclosure[2]], center=true);
}
module enclosure_shell() {
  difference() {
    translate([-enclosure[0]/2, -enclosure[1]/2, 0]) cube(enclosure);
    translate([-board[0]/2, -board[1]/2, wall]) cube([board[0], board[1], enclosure[2]]);
    // J1 POWER_IN side/service keepout
    keepout_window(-48.000, 12.000, 10.500);
    // J2 POWER_OUT side/service keepout
    keepout_window(48.000, -12.000, 10.500);
  }
}
// MH1 copied from KiCad at (-44.000, -24.000)
// MH2 copied from KiCad at (44.000, -24.000)
// MH3 copied from KiCad at (-44.000, 24.000)
// MH4 copied from KiCad at (44.000, 24.000)
union() {
  enclosure_shell();
  standoff(-44.000, -24.000);
  standoff(44.000, -24.000);
  standoff(-44.000, 24.000);
  standoff(44.000, 24.000);
}
