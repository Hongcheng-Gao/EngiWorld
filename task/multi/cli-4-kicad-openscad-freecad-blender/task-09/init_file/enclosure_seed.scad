// Task 09 seed. The completed source must include 01_kicad_parameters.scad.
$fn = 64;
board_bbox = [118.0, 92.0, 1.6];
package_bbox = [131.0, 105.0, 25.1];
wall_mm = 2.5;
base_mm = 2.5;
lid_mm = 2.5;
tray_outer_top_z = 22.5;
lid_inner_z = 22.6;
board_bottom_z = 13.4;
board_top_z = board_bottom_z + board_bbox[2];
standoff_height = board_bottom_z - base_mm;
heater_body_top_z = board_top_z + 1.0;
heater_path_z = [16.0, 25.6];
heater_lid_cutter_z = [22.1, 25.6];

module seed_board_reference() {
  %translate([-board_bbox[0] / 2, -board_bbox[1] / 2, board_bottom_z])
    cube(board_bbox);
}

module seed_lid_reference() {
  %translate([-package_bbox[0] / 2, -package_bbox[1] / 2, lid_inner_z])
    cube([package_bbox[0], package_bbox[1], lid_mm]);
}

module seed_heater_opening_reference(x, y) {
  %translate([x, y, heater_lid_cutter_z[0]])
    cylinder(d=36.0, h=heater_lid_cutter_z[1] - heater_lid_cutter_z[0]);
}

// Replace these references with the tray, separate lid, bored standoffs,
// opposite-side connector windows, and two independent heater openings.
seed_board_reference();
seed_lid_reference();
seed_heater_opening_reference(-24.0, -12.0);
seed_heater_opening_reference(24.0, -12.0);
