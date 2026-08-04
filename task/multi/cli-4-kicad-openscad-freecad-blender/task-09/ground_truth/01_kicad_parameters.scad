// KiCad-generated OpenSCAD parameter handoff.
// Source: 01_kicad_mechanical_map.csv and 01_kicad_board.kicad_pcb.
$fn = 64;
board = [118.000, 92.000, 1.600];
enclosure = [131.000, 105.000, 25.100];
wall = 2.500;
lid_clearance = 3.000;

// [reference, kind, x_mm, y_mm, height_mm, keepout_radius_mm, role]
mechanical_features = [
  ["U1", "THERMAL_SENSOR", 0.000, 18.000, 2.000, 8.000, "component_keepout"],
  ["H1", "HEATER_ZONE", -24.000, -12.000, 1.000, 18.000, "component_keepout"],
  ["H2", "HEATER_ZONE", 24.000, -12.000, 1.000, 18.000, "component_keepout"],
  ["J1", "USB_C", -56.000, 0.000, 4.600, 10.000, "connector_window"],
  ["J2", "SYNC", 56.000, 0.000, 4.000, 8.000, "connector_window"],
  ["MH1", "MOUNTING_HOLE", -50.000, -38.000, 0.000, 1.500, "standoff_axis"],
  ["MH2", "MOUNTING_HOLE", 50.000, -38.000, 0.000, 1.500, "standoff_axis"],
  ["MH3", "MOUNTING_HOLE", -50.000, 38.000, 0.000, 1.500, "standoff_axis"],
  ["MH4", "MOUNTING_HOLE", 50.000, 38.000, 0.000, 1.500, "standoff_axis"],
];

standoff_axes = [for (f = mechanical_features) if (f[6] == "standoff_axis") [f[2], f[3], f[5], f[0]]];
interface_features = [for (f = mechanical_features) if (f[6] == "connector_window" || f[6] == "access_bore" || f[6] == "antenna_keepout") [f[2], f[3], f[5], f[0], f[6]]];
