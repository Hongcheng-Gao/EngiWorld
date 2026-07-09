// Seed OpenSCAD file for task 06; complete it from 01_kicad_mechanical_map.csv.
$fn = 32;
board = [154.000, 58.000, 1.600];
wall = 3.400;
module placeholder_board() {
  translate([-board[0]/2, -board[1]/2, 0]) cube(board);
}
placeholder_board();
