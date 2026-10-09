// Task 05 seed. The completed source must include 01_kicad_parameters.scad.
$fn = 64;
board_bbox = [94.0, 70.0, 1.6];
package_bbox = [107.6, 83.6, 20.4];
wall_mm = 2.8;
base_mm = 2.8;
lid_mm = 2.8;
tray_outer_top_z = 17.5;
lid_inner_z = 17.6;
board_bottom_z = 6.6;
board_top_z = board_bottom_z + board_bbox[2];
standoff_height = board_bottom_z - base_mm;
pogo_target_top_z = board_top_z + 0.2;
pogo_path_z = [8.4, 20.9];
pogo_lid_bore_z = [17.1, 20.9];

module seed_board_reference() {
  %translate([-board_bbox[0] / 2, -board_bbox[1] / 2, board_bottom_z])
    cube(board_bbox);
}

module seed_lid_reference() {
  %translate([-package_bbox[0] / 2, -package_bbox[1] / 2, lid_inner_z])
    cube([package_bbox[0], package_bbox[1], lid_mm]);
}

// Replace these references with a tray, separate lid, bored standoffs, four
// continuous TP bores, and the bounded J1 Y_PLUS side window from the handoff.
seed_board_reference();
seed_lid_reference();
