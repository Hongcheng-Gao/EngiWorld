// KiCad-derived Task 05 OpenSCAD parameter handoff.
// Source map SHA-256: e5f29fd25f1eb995cdf0d4cb12f9a71cb962ee8d86f46c4c15306215bf67c84e
$fn = 96;
board_bbox = [94.000000, 70.000000, 1.600000];
board = board_bbox;
package_bbox = [107.600000, 83.600000, 20.400000];
enclosure = package_bbox;
cavity_xy = [102.000000, 78.000000];
wall_mm = 2.800000;
wall = wall_mm;
base_thickness = 2.800000;
tray_outer_top_z = 17.500000;
lid_inner_z = 17.600000;
lid_thickness = 2.800000;
lid_separation = 0.100000;
board_bottom_z = 6.600000;
board_top_z = 8.200000;
standoff_height = 3.800000;
standoff_od = 6.900000;
standoff_bore = 3.200000;
standoff_bore_overcut = 0.500000;
access_overcut = 0.500000;

// [ref, kind, x, y, height, keepout_radius, body_x, body_y, role]
mechanical_features = [
  ["MH1", "MOUNTING_HOLE", -40.000000, -28.000000, 0.000000, 0.000000, 0.000000, 0.000000, "standoff_axis"],
  ["MH2", "MOUNTING_HOLE", 40.000000, -28.000000, 0.000000, 0.000000, 0.000000, 0.000000, "standoff_axis"],
  ["MH3", "MOUNTING_HOLE", -40.000000, 28.000000, 0.000000, 0.000000, 0.000000, 0.000000, "standoff_axis"],
  ["MH4", "MOUNTING_HOLE", 40.000000, 28.000000, 0.000000, 0.000000, 0.000000, 0.000000, "standoff_axis"],
  ["TP1", "POGO_TARGET", -22.000000, -12.000000, 0.200000, 2.500000, 2.000000, 2.000000, "access_bore"],
  ["TP2", "POGO_TARGET", -6.000000, -12.000000, 0.200000, 2.500000, 2.000000, 2.000000, "access_bore"],
  ["TP3", "POGO_TARGET", 10.000000, -12.000000, 0.200000, 2.500000, 2.000000, 2.000000, "access_bore"],
  ["TP4", "POGO_TARGET", 26.000000, -12.000000, 0.200000, 2.500000, 2.000000, 2.000000, "access_bore"],
  ["J1", "EDGE_CONN", 0.000000, 33.000000, 4.400000, 11.000000, 22.000000, 12.000000, "connector_window"],
 ];

// [ref, x, y, board_hole_diameter]
standoff_axes = [
  ["MH1", -40.000000, -28.000000, 3.000000],
  ["MH2", 40.000000, -28.000000, 3.000000],
  ["MH3", -40.000000, 28.000000, 3.000000],
  ["MH4", 40.000000, 28.000000, 3.000000],
 ];

// [ref, x, y, diameter, cutter_zmin, cutter_zmax, path_zmin, path_zmax]
top_bores = [
  ["TP1", -22.000000, -12.000000, 5.000000, 17.100000, 20.900000, 8.400000, 20.900000],
  ["TP2", -6.000000, -12.000000, 5.000000, 17.100000, 20.900000, 8.400000, 20.900000],
  ["TP3", 10.000000, -12.000000, 5.000000, 17.100000, 20.900000, 8.400000, 20.900000],
  ["TP4", 26.000000, -12.000000, 5.000000, 17.100000, 20.900000, 8.400000, 20.900000],
 ];

// [ref, direction, xmin, ymin, zmin, xmax, ymax, zmax]
side_windows = [
  ["J1", "Y_PLUS", -11.000000, 38.500000, 7.400000, 11.000000, 42.300000, 13.400000],
 ];
