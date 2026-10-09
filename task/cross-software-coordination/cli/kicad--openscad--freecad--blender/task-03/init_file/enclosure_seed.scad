// Task 03 parameter seed. Complete the package and RF shield from the KiCad-derived map.
$fn = 64;
board = [72.000, 48.000, 1.200];
enclosure = [84.400, 60.400, 12.200];
wall = 2.200;
base_thickness = 2.200;
lid_thickness = 2.200;
standoff_height = 1.000;
board_bottom_z = base_thickness + standoff_height;
board_top_z = board_bottom_z + board[2];
lid_inner_z = enclosure[2] - lid_thickness;
shield_inner_xy = [24.000, 22.000];
shield_wall = 1.000;
shield_inner_top_z = 8.800;
shield_outer_top_z = 9.800;

module board_reference() {
  %translate([-board[0]/2, -board[1]/2, board_bottom_z]) cube(board);
}

board_reference();
