// Task 06: Battery BMS service-cover enclosure
// OpenSCAD stage consumes the KiCad-generated 01_kicad_parameters.scad handoff.
include <01_kicad_parameters.scad>;

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
    // J1 CELL_STACK side/service keepout
    keepout_window(-74.000, 0.000, 12.500);
    // J2 SERVICE side/service keepout
    keepout_window(74.000, 0.000, 10.000);
  }
}
// MH1 copied from KiCad at (-68.000, -22.000)
// MH2 copied from KiCad at (68.000, -22.000)
// MH3 copied from KiCad at (-68.000, 22.000)
// MH4 copied from KiCad at (68.000, 22.000)
union() {
  enclosure_shell();
  standoff(-68.000, -22.000);
  standoff(68.000, -22.000);
  standoff(-68.000, 22.000);
  standoff(68.000, 22.000);
}
