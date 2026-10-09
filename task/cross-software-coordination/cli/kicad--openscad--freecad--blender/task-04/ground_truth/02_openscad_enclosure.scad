// Task 04 tray generated from the trusted KiCad parameter handoff.
// Input map SHA-256: a95e43a307b43a59dee372801111bf89a2c11ec5aa672969767d49f14b8dfc0e
// Input parameter SHA-256: 98f9b803344c5d4357071a0bc2b27cc617b024d4f79f4a85029ce09587a2cd4d
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

module required_rib(rib) {
  translate([rib[1], rib[2], rib[3]])
    cube([rib[4]-rib[1], rib[5]-rib[2], rib[6]-rib[3]]);
}

module structural_tray() {
  union() {
    tray_shell();
    for (axis = standoff_axes) standoff(axis);
    for (rib = required_ribs) required_rib(rib);
  }
}

module mounting_bores() {
  for (axis = standoff_axes)
    translate([axis[1], axis[2], -standoff_bore_overcut])
      cylinder(d=standoff_bore, h=board_bottom_z+2*standoff_bore_overcut);
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

module separate_lid() {
  translate([-package_bbox[0]/2, -package_bbox[1]/2, lid_inner_z])
    cube([package_bbox[0], package_bbox[1], lid_thickness]);
}

installed_tray();
separate_lid();
