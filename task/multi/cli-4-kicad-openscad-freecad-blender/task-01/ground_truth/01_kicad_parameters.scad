// KiCad-generated OpenSCAD parameter handoff.
// Source: 01_kicad_mechanical_map.csv and 01_kicad_board.kicad_pcb.
$fn = 64;
board = [86.000, 54.000, 1.600];
enclosure = [100.000, 68.000, 18.800];
wall = 3.000;
lid_clearance = 4.200;

// [reference, kind, x_mm, y_mm, height_mm, keepout_radius_mm, role]
mechanical_features = [
  ["U1", "MCU", -18.000, 4.000, 2.100, 7.000, "component_keepout"],
  ["U2", "BARO", 16.000, 8.000, 1.400, 6.000, "component_keepout"],
  ["J1", "USB_C", -39.000, 0.000, 4.600, 10.000, "connector_window"],
  ["J2", "SENSOR_FFC", 33.000, -16.000, 3.000, 8.500, "connector_window"],
  ["D1", "STATUS_LED", 4.000, 22.000, 1.200, 4.000, "component_keepout"],
  ["MH1", "MOUNTING_HOLE", -36.000, -22.000, 0.000, 1.600, "standoff_axis"],
  ["MH2", "MOUNTING_HOLE", 36.000, -22.000, 0.000, 1.600, "standoff_axis"],
  ["MH3", "MOUNTING_HOLE", -36.000, 22.000, 0.000, 1.600, "standoff_axis"],
  ["MH4", "MOUNTING_HOLE", 36.000, 22.000, 0.000, 1.600, "standoff_axis"],
];

standoff_axes = [for (f = mechanical_features) if (f[6] == "standoff_axis") [f[2], f[3], f[5], f[0]]];
interface_features = [for (f = mechanical_features) if (f[6] == "connector_window" || f[6] == "access_bore" || f[6] == "antenna_keepout") [f[2], f[3], f[5], f[0], f[6]]];
