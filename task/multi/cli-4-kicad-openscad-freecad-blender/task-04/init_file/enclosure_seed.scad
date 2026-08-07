// Task 04 seed. The completed source must include 01_kicad_parameters.scad.
$fn = 48;
board_bbox = [128.0, 86.0, 1.6];
package_bbox = [142.4, 100.4, 26.4];
wall_mm = 3.2;
base_mm = 3.2;
lid_mm = 3.2;
board_bottom_z = 9.0;

module seed_board_reference() {
  translate([-board_bbox[0] / 2, -board_bbox[1] / 2, board_bottom_z])
    cube(board_bbox);
}

// Replace this reference with a tray, separate lid, bored standoffs, both
// required ribs, and bounded J1/J2 side windows from the trusted handoff.
seed_board_reference();
