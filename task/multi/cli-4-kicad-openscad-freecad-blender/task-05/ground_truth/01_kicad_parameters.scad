// KiCad-generated OpenSCAD parameter handoff.
// Source: 01_kicad_mechanical_map.csv and 01_kicad_board.kicad_pcb.
$fn = 64;
board = [94.000, 70.000, 1.600];
enclosure = [107.600, 83.600, 20.400];
wall = 2.800;
lid_clearance = 5.000;

// [reference, kind, x_mm, y_mm, height_mm, keepout_radius_mm, role]
mechanical_features = [
  ["TP1", "POGO_TARGET", -22.000, -12.000, 0.200, 2.500, "access_bore"],
  ["TP2", "POGO_TARGET", -6.000, -12.000, 0.200, 2.500, "access_bore"],
  ["TP3", "POGO_TARGET", 10.000, -12.000, 0.200, 2.500, "access_bore"],
  ["TP4", "POGO_TARGET", 26.000, -12.000, 0.200, 2.500, "access_bore"],
  ["J1", "EDGE_CONN", 0.000, 33.000, 4.400, 11.000, "connector_window"],
  ["MH1", "MOUNTING_HOLE", -40.000, -28.000, 0.000, 1.500, "standoff_axis"],
  ["MH2", "MOUNTING_HOLE", 40.000, -28.000, 0.000, 1.500, "standoff_axis"],
  ["MH3", "MOUNTING_HOLE", -40.000, 28.000, 0.000, 1.500, "standoff_axis"],
  ["MH4", "MOUNTING_HOLE", 40.000, 28.000, 0.000, 1.500, "standoff_axis"],
];

standoff_axes = [for (f = mechanical_features) if (f[6] == "standoff_axis") [f[2], f[3], f[5], f[0]]];
interface_features = [for (f = mechanical_features) if (f[6] == "connector_window" || f[6] == "access_bore" || f[6] == "antenna_keepout") [f[2], f[3], f[5], f[0], f[6]]];
