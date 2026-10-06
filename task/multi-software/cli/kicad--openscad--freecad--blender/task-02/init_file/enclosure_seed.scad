// Task 02 parameter seed. Complete the clamp from the KiCad-derived map.
$fn = 64;
board = [104.000, 62.000, 1.600];
enclosure = [117.200, 75.200, 18.600];
wall = 2.600;
base_thickness = 2.600;
lid_thickness = 2.600;
standoff_height = 1.200;
board_bottom_z = base_thickness + standoff_height;
lid_inner_z = enclosure[2] - lid_thickness;

module board_reference() {
  %translate([-board[0]/2, -board[1]/2, board_bottom_z]) cube(board);
}

board_reference();
