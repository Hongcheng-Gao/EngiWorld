// Task 07 real carrier geometry driven by the KiCad parameter handoff.
include <01_kicad_parameters.scad>;
$fn = 96;

module bounds_box(b) {
  translate([b[0], b[1], b[2]]) cube([b[3]-b[0], b[4]-b[1], b[5]-b[2]]);
}

module tray() {
  difference() {
    union() {
      difference() {
        translate([-package_bbox[0]/2, -package_bbox[1]/2, 0])
          cube([package_bbox[0], package_bbox[1], tray_top_z]);
        translate([cavity_bounds[0], cavity_bounds[1], base_mm])
          cube([cavity_bounds[2]-cavity_bounds[0], cavity_bounds[3]-cavity_bounds[1], tray_top_z-base_mm+0.5]);
      }
      for (axis = standoff_axes)
        translate([axis[1], axis[2], base_mm])
          cylinder(d=standoff_outer_diameter, h=standoff_height);
    }
    for (axis = standoff_axes)
      translate([axis[1], axis[2], standoff_bore_z[0]])
        cylinder(d=standoff_bore_diameter, h=standoff_bore_z[1]-standoff_bore_z[0]);
    for (window = side_windows)
      bounds_box([window[2],window[3],window[4],window[5],window[6],window[7]]);
  }
}

module lid() {
  translate([-package_bbox[0]/2, -package_bbox[1]/2, lid_inner_z])
    cube([package_bbox[0], package_bbox[1], lid_thickness]);
}

union() {
  tray();
  lid();
}
