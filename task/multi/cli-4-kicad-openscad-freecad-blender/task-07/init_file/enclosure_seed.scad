// Seed OpenSCAD file for task 07; complete it from 01_kicad_mechanical_map.csv.
$fn = 32;
board = [66.000, 42.000, 1.000];
wall = 2.000;
module placeholder_board() {
  translate([-board[0]/2, -board[1]/2, 0]) cube(board);
}
placeholder_board();
