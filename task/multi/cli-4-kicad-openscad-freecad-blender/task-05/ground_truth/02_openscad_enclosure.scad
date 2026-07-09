// Task 05: Pogo-pin bed adapter with board-derived pin field
// OpenSCAD stage generated from 01_kicad_mechanical_map.csv.
$fn = 64;
board = [94.000, 70.000, 1.600];
enclosure = [107.600, 83.600, 20.400];
wall = 2.800;
lid_clearance = 5.000;

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
    // J1 EDGE_CONN side/service keepout
    keepout_window(0.000, 33.000, 11.000);
  }
}
// MH1 copied from KiCad at (-40.000, -28.000)
// MH2 copied from KiCad at (40.000, -28.000)
// MH3 copied from KiCad at (-40.000, 28.000)
// MH4 copied from KiCad at (40.000, 28.000)
union() {
  enclosure_shell();
  standoff(-40.000, -28.000);
  standoff(40.000, -28.000);
  standoff(-40.000, 28.000);
  standoff(40.000, 28.000);
}
