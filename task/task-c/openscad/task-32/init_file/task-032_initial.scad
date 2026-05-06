// Starter cylinders for task-032.
$fn = 64;

cylinder_radius = 13;
base_height = 6;
cylinder_spacing = 50;

union() {
  translate([-cylinder_spacing / 2, 0, 0])
    cylinder(h = base_height, r = cylinder_radius);
  translate([cylinder_spacing / 2, 0, 0])
    cylinder(h = base_height, r = cylinder_radius);
}
