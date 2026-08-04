// KiCad-generated OpenSCAD parameter handoff.
// Source: 01_kicad_mechanical_map.csv and 01_kicad_board.kicad_pcb.
$fn = 64;
board = [176.000, 38.000, 1.600];
enclosure = [190.000, 52.000, 23.600];
wall = 3.000;
lid_clearance = 6.000;

// [reference, kind, x_mm, y_mm, height_mm, keepout_radius_mm, role]
mechanical_features = [
  ["J1", "BUSBAR_POS", -54.000, 0.000, 8.000, 13.000, "connector_window"],
  ["J2", "BUSBAR_NEG", 54.000, 0.000, 8.000, 13.000, "connector_window"],
  ["U1", "CURRENT_SENSOR", 0.000, 0.000, 3.600, 12.000, "component_keepout"],
  ["TP1", "HV_TEST", -12.000, 14.000, 0.200, 3.000, "access_bore"],
  ["TP2", "HV_TEST", 12.000, 14.000, 0.200, 3.000, "access_bore"],
  ["MH1", "MOUNTING_HOLE", -78.000, -14.000, 0.000, 1.750, "standoff_axis"],
  ["MH2", "MOUNTING_HOLE", 78.000, -14.000, 0.000, 1.750, "standoff_axis"],
  ["MH3", "MOUNTING_HOLE", -78.000, 14.000, 0.000, 1.750, "standoff_axis"],
  ["MH4", "MOUNTING_HOLE", 78.000, 14.000, 0.000, 1.750, "standoff_axis"],
];

standoff_axes = [for (f = mechanical_features) if (f[6] == "standoff_axis") [f[2], f[3], f[5], f[0]]];
interface_features = [for (f = mechanical_features) if (f[6] == "connector_window" || f[6] == "access_bore" || f[6] == "antenna_keepout") [f[2], f[3], f[5], f[0], f[6]]];
