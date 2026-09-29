// Task 05 tray/lid generated from the trusted KiCad parameter handoff.
// Input map SHA-256: e5f29fd25f1eb995cdf0d4cb12f9a71cb962ee8d86f46c4c15306215bf67c84e
// Input parameter SHA-256: 6fd3e1bd95fe6ddae1e125a53df5e7df0fd32d94081efdd8e3781e42b19e3597
include <01_kicad_parameters.scad>;

module tray_shell() {
  difference() {
    translate([-package_bbox[0]/2, -package_bbox[1]/2, 0])
      cube([package_bbox[0], package_bbox[1], tray_outer_top_z]);
    translate([-cavity_xy[0]/2, -cavity_xy[1]/2, base_thickness])
      cube([cavity_xy[0], cavity_xy[1], tray_outer_top_z-base_thickness+access_overcut]);
  }
}

module standoff(axis) {
  translate([axis[1], axis[2], base_thickness])
    cylinder(d=standoff_od, h=standoff_height);
}

module structural_tray() {
  union() {
    tray_shell();
    for (axis = standoff_axes) standoff(axis);
  }
}

module mounting_bores() {
  for (axis = standoff_axes)
    translate([axis[1], axis[2], base_thickness-standoff_bore_overcut])
      cylinder(d=standoff_bore, h=standoff_height+2*standoff_bore_overcut);
}

module bounded_side_windows() {
  for (access = side_windows)
    translate([access[2], access[3], access[4]])
      cube([access[5]-access[2], access[6]-access[3], access[7]-access[4]]);
}

module installed_tray() {
  difference() {
    structural_tray();
    mounting_bores();
    bounded_side_windows();
  }
}

module lid_bores() {
  for (access = top_bores)
    translate([access[1], access[2], access[4]])
      cylinder(d=access[3], h=access[5]-access[4]);
}

module separate_lid() {
  difference() {
    translate([-package_bbox[0]/2, -package_bbox[1]/2, lid_inner_z])
      cube([package_bbox[0], package_bbox[1], lid_thickness]);
    lid_bores();
  }
}

installed_tray();
separate_lid();
