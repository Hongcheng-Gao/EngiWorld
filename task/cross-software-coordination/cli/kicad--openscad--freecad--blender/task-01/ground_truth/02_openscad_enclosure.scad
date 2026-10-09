// Task 01 enclosure generated from 01_kicad_mechanical_map.csv.
// Input map SHA-256: c999cd1ca91771298d82bd2c82f6ea6ded1dd55cb864fd420768199dbae181b0
$fn = 64;
board = [86.000, 54.000, 1.600];
enclosure = [100.000, 68.000, 18.800];
cavity = [94.000, 62.000, 12.800];
wall = 3.000;
base_thickness = 3.000;
lid_thickness = 3.000;
board_bottom_z = 5.000;
standoff_height = 2.000;
standoff_od = 7.200;
standoff_bore = 3.400;
overcut = 0.500;

module shell() {
  difference() {
    translate([-enclosure[0]/2, -enclosure[1]/2, 0]) cube(enclosure);
    translate([-cavity[0]/2, -cavity[1]/2, base_thickness]) cube(cavity);
  }
}

module standoff(x, y) {
  translate([x, y, base_thickness]) cylinder(d=standoff_od, h=standoff_height);
}

module screw_bore(x, y) {
  translate([x, y, -overcut]) cylinder(d=standoff_bore, h=board_bottom_z + 2*overcut);
}

module enclosure_with_standoffs() {
  union() {
    shell();
    standoff(-36.000, -22.000); // MH1
    standoff(36.000, -22.000); // MH2
    standoff(-36.000, 22.000); // MH3
    standoff(36.000, 22.000); // MH4
  }
}

difference() {
  enclosure_with_standoffs();
  // J1 X_MINUS through-aperture
  translate([-50.500, -6.500, 5.900])
    cube([4.000, 13.000, 6.000]);
  // J2 X_PLUS through-aperture
  translate([46.500, -25.000, 6.100])
    cube([4.000, 18.000, 4.000]);
  screw_bore(-36.000, -22.000); // MH1
  screw_bore(36.000, -22.000); // MH2
  screw_bore(-36.000, 22.000); // MH3
  screw_bore(36.000, 22.000); // MH4
}
