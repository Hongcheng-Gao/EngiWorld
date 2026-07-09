// Seed OpenSCAD file for task 01; complete it from 01_kicad_mechanical_map.csv.
$fn = 32;
board = [86.000, 54.000, 1.600];
wall = 3.000;
module placeholder_board() {
  translate([-board[0]/2, -board[1]/2, 0]) cube(board);
}
placeholder_board();
