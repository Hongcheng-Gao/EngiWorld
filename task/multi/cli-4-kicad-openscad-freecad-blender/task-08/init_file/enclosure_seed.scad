// Task 08 seed. The completed source must include 01_kicad_parameters.scad.
$fn = 64;
board_bbox = [176.0, 38.0, 1.6];
package_bbox = [190.0, 52.0, 23.6];
wall_mm = 3.0;
base_mm = 3.0;
lid_mm = 3.0;
tray_outer_top_z = 20.5;
lid_inner_z = 20.6;
board_bottom_z = 5.0;
board_top_z = board_bottom_z + board_bbox[2];
standoff_height = board_bottom_z - base_mm;
tp_target_top_z = board_top_z + 0.2;
tp_path_z = [6.8, 24.1];
tp_lid_cutter_z = [20.1, 24.1];
creepage_segment_start = [-41.0, 24.5, 10.6];
creepage_segment_end = [41.0, 24.5, 10.6];
creepage_probe_bounds = [-41.0, 24.25, 10.35, 41.0, 24.75, 10.85];

module seed_board_reference() {
  %translate([-board_bbox[0] / 2, -board_bbox[1] / 2, board_bottom_z])
    cube(board_bbox);
}

module seed_lid_reference() {
  %translate([-package_bbox[0] / 2, -package_bbox[1] / 2, lid_inner_z])
    cube([package_bbox[0], package_bbox[1], lid_mm]);
}

module seed_creepage_web_reference() {
  %translate([creepage_probe_bounds[0], creepage_probe_bounds[1], creepage_probe_bounds[2]])
    cube([
      creepage_probe_bounds[3] - creepage_probe_bounds[0],
      creepage_probe_bounds[4] - creepage_probe_bounds[1],
      creepage_probe_bounds[5] - creepage_probe_bounds[2]
    ]);
}

// Replace these references with the tray, separate lid, bored standoffs, two
// independent busbar windows, and two TP lid bores while retaining the web.
seed_board_reference();
seed_lid_reference();
seed_creepage_web_reference();
