// Task 08: High-current busbar insulator carrier
// OpenSCAD stage generated from 01_kicad_mechanical_map.csv.
$fn = 64;
board = [176.000, 38.000, 1.600];
enclosure = [190.000, 52.000, 23.600];
wall = 3.000;
lid_clearance = 6.000;

module standoff(x, y) {
  translate([x, y, board[2]]) cylinder(d=8.050, h=wall + board[2]);
}
module keepout_window(x, y, r) {
  translate([x, y, enclosure[2]/2]) cube([2*r, wall*3, enclosure[2]], center=true);
}
module enclosure_shell() {
  difference() {
    translate([-enclosure[0]/2, -enclosure[1]/2, 0]) cube(enclosure);
    translate([-board[0]/2, -board[1]/2, wall]) cube([board[0], board[1], enclosure[2]]);
    // J1 BUSBAR_POS side/service keepout
    keepout_window(-54.000, 0.000, 13.000);
    // J2 BUSBAR_NEG side/service keepout
    keepout_window(54.000, 0.000, 13.000);
  }
}
// MH1 copied from KiCad at (-78.000, -14.000)
// MH2 copied from KiCad at (78.000, -14.000)
// MH3 copied from KiCad at (-78.000, 14.000)
// MH4 copied from KiCad at (78.000, 14.000)
union() {
  enclosure_shell();
  standoff(-78.000, -14.000);
  standoff(78.000, -14.000);
  standoff(-78.000, 14.000);
  standoff(78.000, 14.000);
}
