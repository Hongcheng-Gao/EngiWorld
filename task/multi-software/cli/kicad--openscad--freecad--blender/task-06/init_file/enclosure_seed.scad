// Task 06 seed. The completed source must include 01_kicad_parameters.scad.
$fn = 64;
board_bbox = [154.0, 58.0, 1.6];
package_bbox = [168.8, 72.8, 22.0];
wall_mm = 3.4;
base_mm = 3.4;
lid_mm = 3.4;
tray_outer_top_z = 18.5;
lid_inner_z = 18.6;
board_bottom_z = 4.7;
board_top_z = board_bottom_z + board_bbox[2];
standoff_height = board_bottom_z - base_mm;
f1_body_top_z = board_top_z + 4.2;
f1_path_z = [10.5, 22.5];
f1_lid_cutter_z = [18.1, 22.5];

module seed_board_reference() {
  %translate([-board_bbox[0] / 2, -board_bbox[1] / 2, board_bottom_z])
    cube(board_bbox);
}

module seed_lid_reference() {
  %translate([-package_bbox[0] / 2, -package_bbox[1] / 2, lid_inner_z])
    cube([package_bbox[0], package_bbox[1], lid_mm]);
}

// Replace these references with the tray, separate lid, bored standoffs,
// bounded J1/J2 opposite-side windows, and the cylindrical F1 top opening.
seed_board_reference();
seed_lid_reference();
