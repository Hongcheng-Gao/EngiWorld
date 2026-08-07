// Task 01 parameter seed. Complete the enclosure from the KiCad-derived map.
$fn = 48;
board = [86.000, 54.000, 1.600];
enclosure = [100.000, 68.000, 18.800];
wall = 3.000;
base_thickness = 3.000;
lid_thickness = 3.000;
side_clearance = 4.000;
standoff_height = 2.000;
board_bottom_z = base_thickness + standoff_height;

module board_reference() {
  %translate([-board[0]/2, -board[1]/2, board_bottom_z]) cube(board);
}

board_reference();
