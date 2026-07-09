// Task 09: Thermal camera calibration target PCB mount
// OpenSCAD stage generated from 01_kicad_mechanical_map.csv.
$fn = 64;
board = [118.000, 92.000, 1.600];
enclosure = [131.000, 105.000, 25.100];
wall = 2.500;
lid_clearance = 3.000;

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
    // J1 USB_C side/service keepout
    keepout_window(-56.000, 0.000, 10.000);
    // J2 SYNC side/service keepout
    keepout_window(56.000, 0.000, 8.000);
  }
}
// MH1 copied from KiCad at (-50.000, -38.000)
// MH2 copied from KiCad at (50.000, -38.000)
// MH3 copied from KiCad at (-50.000, 38.000)
// MH4 copied from KiCad at (50.000, 38.000)
union() {
  enclosure_shell();
  standoff(-50.000, -38.000);
  standoff(50.000, -38.000);
  standoff(-50.000, 38.000);
  standoff(50.000, 38.000);
}
