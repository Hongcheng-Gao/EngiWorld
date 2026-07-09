// Seed OpenSCAD file for task 09; complete it from 01_kicad_mechanical_map.csv.
$fn = 32;
board = [118.000, 92.000, 1.600];
wall = 2.500;
module placeholder_board() {
  translate([-board[0]/2, -board[1]/2, 0]) cube(board);
}
placeholder_board();
