// KiCad-generated OpenSCAD parameter handoff.
// Source: 01_kicad_mechanical_map.csv and 01_kicad_board.kicad_pcb.
$fn = 64;
board = [104.000, 62.000, 1.600];
enclosure = [117.200, 75.200, 18.600];
wall = 2.600;
lid_clearance = 2.400;

// [reference, kind, x_mm, y_mm, height_mm, keepout_radius_mm, role]
mechanical_features = [
  ["U1", "REGULATOR_QFN", -8.000, 0.000, 1.000, 5.000, "component_keepout"],
  ["L1", "INDUCTOR", 18.000, 4.000, 6.400, 12.000, "component_keepout"],
  ["C1", "BULK_CAP", 34.000, -18.000, 8.200, 8.000, "component_keepout"],
  ["J1", "POWER_IN", -48.000, 12.000, 5.000, 10.500, "connector_window"],
  ["J2", "POWER_OUT", 48.000, -12.000, 5.000, 10.500, "connector_window"],
  ["MH1", "MOUNTING_HOLE", -44.000, -24.000, 0.000, 1.500, "standoff_axis"],
  ["MH2", "MOUNTING_HOLE", 44.000, -24.000, 0.000, 1.500, "standoff_axis"],
  ["MH3", "MOUNTING_HOLE", -44.000, 24.000, 0.000, 1.500, "standoff_axis"],
  ["MH4", "MOUNTING_HOLE", 44.000, 24.000, 0.000, 1.500, "standoff_axis"],
];

standoff_axes = [for (f = mechanical_features) if (f[6] == "standoff_axis") [f[2], f[3], f[5], f[0]]];
interface_features = [for (f = mechanical_features) if (f[6] == "connector_window" || f[6] == "access_bore" || f[6] == "antenna_keepout") [f[2], f[3], f[5], f[0], f[6]]];
