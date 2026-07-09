// Seed OpenSCAD file for task 03; complete it from 01_kicad_mechanical_map.csv.
$fn = 32;
board = [72.000, 48.000, 1.200];
wall = 2.200;
module placeholder_board() {
  translate([-board[0]/2, -board[1]/2, 0]) cube(board);
}
placeholder_board();
