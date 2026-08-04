// KiCad-generated OpenSCAD parameter handoff.
// Source: 01_kicad_mechanical_map.csv and 01_kicad_board.kicad_pcb.
$fn = 64;
board = [72.000, 48.000, 1.200];
enclosure = [84.400, 60.400, 14.200];
wall = 2.200;
lid_clearance = 1.800;

// [reference, kind, x_mm, y_mm, height_mm, keepout_radius_mm, role]
mechanical_features = [
  ["U1", "RFIC", 0.000, 0.000, 0.900, 8.000, "component_keepout"],
  ["Y1", "TCXO", -18.000, 12.000, 2.000, 5.000, "component_keepout"],
  ["J1", "UFL_ANT", 32.000, 0.000, 2.400, 7.000, "connector_window"],
  ["J2", "MEZZ_CONN", -32.000, -12.000, 3.800, 9.000, "connector_window"],
  ["TP1", "TEST_PAD", 12.000, -18.000, 0.200, 3.000, "access_bore"],
  ["MH1", "MOUNTING_HOLE", -30.000, -18.000, 0.000, 1.300, "standoff_axis"],
  ["MH2", "MOUNTING_HOLE", 30.000, -18.000, 0.000, 1.300, "standoff_axis"],
  ["MH3", "MOUNTING_HOLE", -30.000, 18.000, 0.000, 1.300, "standoff_axis"],
  ["MH4", "MOUNTING_HOLE", 30.000, 18.000, 0.000, 1.300, "standoff_axis"],
];

standoff_axes = [for (f = mechanical_features) if (f[6] == "standoff_axis") [f[2], f[3], f[5], f[0]]];
interface_features = [for (f = mechanical_features) if (f[6] == "connector_window" || f[6] == "access_bore" || f[6] == "antenna_keepout") [f[2], f[3], f[5], f[0], f[6]]];
