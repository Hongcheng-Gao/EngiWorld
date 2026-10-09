// Task 10 seed. The completed source must include 01_kicad_parameters.scad.
$fn = 64;
board_bbox = [82.0, 82.0, 1.2];
package_bbox = [95.4, 95.4, 35.4];
wall_mm = 2.7;
base_mm = 2.7;
lid_mm = 2.7;
tray_outer_top_z = 32.6;
lid_inner_z = 32.7;
board_bottom_z = 16.8;
board_top_z = board_bottom_z + board_bbox[2];
antenna_center = [0.0, 16.0];
antenna_radius = 24.0;
antenna_keepout_z = [23.2, 32.7];

module seed_board_reference() {
  %translate([-board_bbox[0] / 2, -board_bbox[1] / 2, board_bottom_z])
    cube(board_bbox);
}

module seed_lid_reference() {
  %translate([-package_bbox[0] / 2, -package_bbox[1] / 2, lid_inner_z])
    cube([package_bbox[0], package_bbox[1], lid_mm]);
}

module seed_antenna_reserved_volume_reference() {
  #translate([antenna_center[0], antenna_center[1], antenna_keepout_z[0]])
    cylinder(r=antenna_radius, h=antenna_keepout_z[1] - antenna_keepout_z[0]);
}

// Replace these references with the tray, separate lid, bored standoffs,
// J1 side window, and TP1 top bore. A1 remains an internal reserved air
// volume under the nonconductive lid; do not turn it into an aperture.
seed_board_reference();
seed_lid_reference();
seed_antenna_reserved_volume_reference();
