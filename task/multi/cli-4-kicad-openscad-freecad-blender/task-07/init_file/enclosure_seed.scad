// Task 07 seed. The completed source must include 01_kicad_parameters.scad.
$fn = 64;
board_bbox = [66.0, 42.0, 1.0];
package_bbox = [78.0, 54.0, 12.2];
wall_mm = 2.0;
base_mm = 2.0;
lid_mm = 2.0;
tray_outer_top_z = 10.1;
lid_inner_z = 10.2;
board_bottom_z = 5.2;
board_top_z = board_bottom_z + board_bbox[2];
standoff_height = board_bottom_z - base_mm;
optical_start = [-16.0, 0.0, 8.2];
optical_end = [16.0, 0.0, 8.2];
optical_radius = 0.5;

module seed_board_reference() {
  %translate([-board_bbox[0] / 2, -board_bbox[1] / 2, board_bottom_z])
    cube(board_bbox);
}

module seed_lid_reference() {
  %translate([-package_bbox[0] / 2, -package_bbox[1] / 2, lid_inner_z])
    cube([package_bbox[0], package_bbox[1], lid_mm]);
}

module seed_optical_corridor_reference() {
  %translate(optical_start)
    rotate([0, 90, 0]) cylinder(r=optical_radius, h=optical_end[0] - optical_start[0]);
}

// Replace these references with the tray, separate lid, bored standoffs, and
// bounded J1 Y_MINUS window while preserving the complete optical corridor.
seed_board_reference();
seed_lid_reference();
seed_optical_corridor_reference();
