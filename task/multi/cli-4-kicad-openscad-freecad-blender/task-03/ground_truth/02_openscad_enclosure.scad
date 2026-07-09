// Task 03: RF daughtercard shield-can and inspection scene
// OpenSCAD stage generated from 01_kicad_mechanical_map.csv.
$fn = 64;
board = [72.000, 48.000, 1.200];
enclosure = [84.400, 60.400, 14.200];
wall = 2.200;
lid_clearance = 1.800;

module standoff(x, y) {
  translate([x, y, board[2]]) cylinder(d=5.980, h=wall + board[2]);
}
module keepout_window(x, y, r) {
  translate([x, y, enclosure[2]/2]) cube([2*r, wall*3, enclosure[2]], center=true);
}
module enclosure_shell() {
  difference() {
    translate([-enclosure[0]/2, -enclosure[1]/2, 0]) cube(enclosure);
    translate([-board[0]/2, -board[1]/2, wall]) cube([board[0], board[1], enclosure[2]]);
    // J1 UFL_ANT side/service keepout
    keepout_window(32.000, 0.000, 7.000);
    // J2 MEZZ_CONN side/service keepout
    keepout_window(-32.000, -12.000, 9.000);
  }
}
// MH1 copied from KiCad at (-30.000, -18.000)
// MH2 copied from KiCad at (30.000, -18.000)
// MH3 copied from KiCad at (-30.000, 18.000)
// MH4 copied from KiCad at (30.000, 18.000)
union() {
  enclosure_shell();
  standoff(-30.000, -18.000);
  standoff(30.000, -18.000);
  standoff(-30.000, 18.000);
  standoff(30.000, 18.000);
}
