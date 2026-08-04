// KiCad-generated OpenSCAD parameter handoff.
// Source: 01_kicad_mechanical_map.csv and 01_kicad_board.kicad_pcb.
$fn = 64;
board = [66.000, 42.000, 1.000];
enclosure = [78.000, 54.000, 12.200];
wall = 2.000;
lid_clearance = 1.200;

// [reference, kind, x_mm, y_mm, height_mm, keepout_radius_mm, role]
mechanical_features = [
  ["U1", "OPTICAL_ASIC", 0.000, 0.000, 0.800, 6.000, "component_keepout"],
  ["LED1", "EMITTER", -16.000, 0.000, 1.500, 4.000, "component_keepout"],
  ["PD1", "PHOTODIODE", 16.000, 0.000, 1.200, 4.000, "component_keepout"],
  ["J1", "FLEX", 0.000, -20.000, 2.800, 8.000, "connector_window"],
  ["FID1", "FIDUCIAL", -24.000, 14.000, 0.100, 2.000, "component_keepout"],
  ["MH1", "MOUNTING_HOLE", -26.000, -16.000, 0.000, 1.200, "standoff_axis"],
  ["MH2", "MOUNTING_HOLE", 26.000, -16.000, 0.000, 1.200, "standoff_axis"],
  ["MH3", "MOUNTING_HOLE", -26.000, 16.000, 0.000, 1.200, "standoff_axis"],
  ["MH4", "MOUNTING_HOLE", 26.000, 16.000, 0.000, 1.200, "standoff_axis"],
];

standoff_axes = [for (f = mechanical_features) if (f[6] == "standoff_axis") [f[2], f[3], f[5], f[0]]];
interface_features = [for (f = mechanical_features) if (f[6] == "connector_window" || f[6] == "access_bore" || f[6] == "antenna_keepout") [f[2], f[3], f[5], f[0], f[6]]];
