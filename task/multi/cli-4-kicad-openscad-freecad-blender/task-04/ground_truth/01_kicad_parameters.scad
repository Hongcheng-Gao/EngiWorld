// KiCad-generated OpenSCAD parameter handoff.
// Source: 01_kicad_mechanical_map.csv and 01_kicad_board.kicad_pcb.
$fn = 64;
board = [128.000, 86.000, 1.600];
enclosure = [142.400, 100.400, 26.400];
wall = 3.200;
lid_clearance = 3.600;

// [reference, kind, x_mm, y_mm, height_mm, keepout_radius_mm, role]
mechanical_features = [
  ["Q1", "MOSFET_BANK", -28.000, 10.000, 5.500, 18.000, "component_keepout"],
  ["Q2", "MOSFET_BANK", 0.000, 10.000, 5.500, 18.000, "component_keepout"],
  ["Q3", "MOSFET_BANK", 28.000, 10.000, 5.500, 18.000, "component_keepout"],
  ["J1", "PHASE_TERMINAL", 58.000, 0.000, 9.000, 14.000, "connector_window"],
  ["J2", "HALL_SENSOR", -58.000, -18.000, 4.000, 8.000, "connector_window"],
  ["MH1", "MOUNTING_HOLE", -54.000, -36.000, 0.000, 1.750, "standoff_axis"],
  ["MH2", "MOUNTING_HOLE", 54.000, -36.000, 0.000, 1.750, "standoff_axis"],
  ["MH3", "MOUNTING_HOLE", -54.000, 36.000, 0.000, 1.750, "standoff_axis"],
  ["MH4", "MOUNTING_HOLE", 54.000, 36.000, 0.000, 1.750, "standoff_axis"],
];

standoff_axes = [for (f = mechanical_features) if (f[6] == "standoff_axis") [f[2], f[3], f[5], f[0]]];
interface_features = [for (f = mechanical_features) if (f[6] == "connector_window" || f[6] == "access_bore" || f[6] == "antenna_keepout") [f[2], f[3], f[5], f[0], f[6]]];
