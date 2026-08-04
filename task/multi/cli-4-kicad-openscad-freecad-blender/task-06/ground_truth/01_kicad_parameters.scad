// KiCad-generated OpenSCAD parameter handoff.
// Source: 01_kicad_mechanical_map.csv and 01_kicad_board.kicad_pcb.
$fn = 64;
board = [154.000, 58.000, 1.600];
enclosure = [168.800, 72.800, 22.000];
wall = 3.400;
lid_clearance = 4.500;

// [reference, kind, x_mm, y_mm, height_mm, keepout_radius_mm, role]
mechanical_features = [
  ["U1", "AFE", -38.000, 0.000, 1.100, 6.000, "component_keepout"],
  ["J1", "CELL_STACK", -74.000, 0.000, 7.800, 12.500, "connector_window"],
  ["J2", "SERVICE", 74.000, 0.000, 5.400, 10.000, "connector_window"],
  ["F1", "FUSE", 20.000, 16.000, 4.200, 9.000, "component_keepout"],
  ["NTC1", "THERMISTOR", 0.000, -20.000, 2.600, 5.000, "component_keepout"],
  ["MH1", "MOUNTING_HOLE", -68.000, -22.000, 0.000, 1.600, "standoff_axis"],
  ["MH2", "MOUNTING_HOLE", 68.000, -22.000, 0.000, 1.600, "standoff_axis"],
  ["MH3", "MOUNTING_HOLE", -68.000, 22.000, 0.000, 1.600, "standoff_axis"],
  ["MH4", "MOUNTING_HOLE", 68.000, 22.000, 0.000, 1.600, "standoff_axis"],
];

standoff_axes = [for (f = mechanical_features) if (f[6] == "standoff_axis") [f[2], f[3], f[5], f[0]]];
interface_features = [for (f = mechanical_features) if (f[6] == "connector_window" || f[6] == "access_bore" || f[6] == "antenna_keepout") [f[2], f[3], f[5], f[0], f[6]]];
