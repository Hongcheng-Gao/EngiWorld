// Task 03 package and RF shield generated from the KiCad parameter handoff.
// Input map SHA-256: f3d68f70b06402aa1429e5333d23c4cedf50cddd1cb1b93778b5081a119f6de3
include <01_kicad_parameters.scad>;

module package_shell() {
  difference() {
    translate([-enclosure[0]/2, -enclosure[1]/2, 0]) cube(enclosure);
    translate([-cavity[0]/2, -cavity[1]/2, base_thickness])
      cube([cavity[0], cavity[1], lid_inner_z - base_thickness]);
  }
}

module standoff(x, y) {
  translate([x, y, base_thickness]) cylinder(d=standoff_od, h=standoff_height);
}

module package_with_standoffs() {
  union() {
    package_shell();
    for (axis = standoff_axes) standoff(axis[1], axis[2]);
  }
}

module mounting_bores() {
  for (axis = standoff_axes)
    translate([axis[1], axis[2], -access_overcut])
      cylinder(d=standoff_bore, h=board_bottom_z + 2*access_overcut);
}

module side_access_cutouts() {
  for (access = side_accesses)
    translate([access[2], access[3], access[4]])
      cube([access[5]-access[2], access[6]-access[3], access[7]-access[4]]);
}

module top_access_cutouts() {
  for (access = top_accesses)
    translate([access[1], access[2], access[4]])
      cylinder(d=access[3], h=access[5]-access[4]);
}

module installed_package() {
  difference() {
    package_with_standoffs();
    mounting_bores();
    side_access_cutouts();
    top_access_cutouts();
  }
}

module rf_shield_can() {
  shield_outer_xy = [shield_inner_xy[0] + 2*shield_wall, shield_inner_xy[1] + 2*shield_wall];
  difference() {
    translate([shield_center[0]-shield_outer_xy[0]/2, shield_center[1]-shield_outer_xy[1]/2, board_top_z])
      cube([shield_outer_xy[0], shield_outer_xy[1], shield_outer_top_z-board_top_z]);
    translate([shield_center[0]-shield_inner_xy[0]/2, shield_center[1]-shield_inner_xy[1]/2, board_top_z-access_overcut])
      cube([shield_inner_xy[0], shield_inner_xy[1], shield_inner_top_z-board_top_z+access_overcut]);
  }
}

union() {
  installed_package();
  rf_shield_can();
}
