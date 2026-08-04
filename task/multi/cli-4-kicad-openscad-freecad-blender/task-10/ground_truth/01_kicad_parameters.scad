// KiCad-generated OpenSCAD parameter handoff.
// Source: 01_kicad_mechanical_map.csv and 01_kicad_board.kicad_pcb.
$fn = 64;
board = [82.000, 82.000, 1.200];
enclosure = [95.400, 95.400, 35.400];
wall = 2.700;
lid_clearance = 7.500;

// [reference, kind, x_mm, y_mm, height_mm, keepout_radius_mm, role]
mechanical_features = [
  ["A1", "PATCH_ANTENNA", 0.000, 16.000, 5.200, 24.000, "antenna_keepout"],
  ["U1", "GNSS_SOC", -14.000, -18.000, 1.100, 7.000, "component_keepout"],
  ["J1", "SMA_EDGE", 40.000, -12.000, 7.200, 12.000, "connector_window"],
  ["BT1", "BACKUP_CELL", -30.000, 26.000, 4.800, 11.000, "component_keepout"],
  ["TP1", "RF_TEST", 18.000, -30.000, 0.200, 3.000, "access_bore"],
  ["MH1", "MOUNTING_HOLE", -34.000, -34.000, 0.000, 1.400, "standoff_axis"],
  ["MH2", "MOUNTING_HOLE", 34.000, -34.000, 0.000, 1.400, "standoff_axis"],
  ["MH3", "MOUNTING_HOLE", -34.000, 34.000, 0.000, 1.400, "standoff_axis"],
  ["MH4", "MOUNTING_HOLE", 34.000, 34.000, 0.000, 1.400, "standoff_axis"],
];

standoff_axes = [for (f = mechanical_features) if (f[6] == "standoff_axis") [f[2], f[3], f[5], f[0]]];
interface_features = [for (f = mechanical_features) if (f[6] == "connector_window" || f[6] == "access_bore" || f[6] == "antenna_keepout") [f[2], f[3], f[5], f[0], f[6]]];
