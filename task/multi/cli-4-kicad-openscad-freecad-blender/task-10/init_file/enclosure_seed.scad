// Seed OpenSCAD file for task 10; complete it from 01_kicad_mechanical_map.csv.
$fn = 32;
board = [82.000, 82.000, 1.200];
wall = 2.700;
module placeholder_board() {
  translate([-board[0]/2, -board[1]/2, 0]) cube(board);
}
placeholder_board();
