// KiCad-derived Task 04 OpenSCAD parameter handoff.
// Source map SHA-256: a95e43a307b43a59dee372801111bf89a2c11ec5aa672969767d49f14b8dfc0e
$fn = 64;
board_bbox = [128.000000, 86.000000, 1.600000];
board = board_bbox;
package_bbox = [142.400000, 100.400000, 26.400000];
enclosure = package_bbox;
cavity_xy = [136.000000, 94.000000];
wall_mm = 3.200000;
wall = wall_mm;
base_thickness = 3.200000;
tray_outer_top_z = 23.100000;
lid_inner_z = 23.200000;
lid_separation = 0.100000;
lid_thickness = 3.200000;
board_bottom_z = 9.000000;
board_top_z = 10.600000;
standoff_height = 5.800000;
standoff_od = 8.000000;
standoff_bore = 3.700000;
standoff_bore_overcut = 0.500000;
access_overcut = 0.500000;

// [ref, kind, x, y, height, keepout_radius, body_x, body_y, role]
mechanical_features = [
  ["MH1", "MOUNTING_HOLE", -54.000000, -36.000000, 0.000000, 0.000000, 0.000000, 0.000000, "standoff_axis"],
  ["MH2", "MOUNTING_HOLE", 54.000000, -36.000000, 0.000000, 0.000000, 0.000000, 0.000000, "standoff_axis"],
  ["MH3", "MOUNTING_HOLE", -54.000000, 36.000000, 0.000000, 0.000000, 0.000000, 0.000000, "standoff_axis"],
  ["MH4", "MOUNTING_HOLE", 54.000000, 36.000000, 0.000000, 0.000000, 0.000000, 0.000000, "standoff_axis"],
  ["Q1", "MOSFET_BANK", -28.000000, 10.000000, 5.500000, 18.000000, 22.000000, 16.000000, "rib_keepout"],
  ["Q2", "MOSFET_BANK", 0.000000, 10.000000, 5.500000, 18.000000, 22.000000, 16.000000, "rib_keepout"],
  ["Q3", "MOSFET_BANK", 28.000000, 10.000000, 5.500000, 18.000000, 22.000000, 16.000000, "rib_keepout"],
  ["J1", "PHASE_TERMINAL", 58.000000, 0.000000, 9.000000, 14.000000, 12.000000, 24.000000, "connector_window"],
  ["J2", "HALL_SENSOR", -58.000000, -18.000000, 4.000000, 8.000000, 10.000000, 14.000000, "connector_window"],
];
// [ref, x, y, hole_diameter]
standoff_axes = [
  ["MH1", -54.000000, -36.000000, 3.500000],
  ["MH2", 54.000000, -36.000000, 3.500000],
  ["MH3", -54.000000, 36.000000, 3.500000],
  ["MH4", 54.000000, 36.000000, 3.500000],
];
// [id, xmin, ymin, zmin, xmax, ymax, zmax]
required_ribs = [
  ["RIB_NEG_Y", -52.000000, -33.500000, 3.200000, 52.000000, -30.500000, 5.700000],
  ["RIB_POS_Y", -52.000000, 32.500000, 3.200000, 52.000000, 35.500000, 5.700000],
];
// [ref, direction, xmin, ymin, zmin, xmax, ymax, zmax]
side_windows = [
  ["J1", "X_PLUS", 52.000000, -14.000000, 9.600000, 71.700000, 14.000000, 20.600000],
  ["J2", "X_MINUS", -71.700000, -26.000000, 9.600000, -53.000000, -10.000000, 15.600000],
];
// [ref, x, y, radius, zmin, zmax]
rib_keepout_columns = [
  ["Q1", -28.000000, 10.000000, 18.000000, 3.200000, 23.200000],
  ["Q2", 0.000000, 10.000000, 18.000000, 3.200000, 23.200000],
  ["Q3", 28.000000, 10.000000, 18.000000, 3.200000, 23.200000],
];
