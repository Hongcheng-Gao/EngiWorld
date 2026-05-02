// Generated with SolidPython2 for OpenSCAD task-031
$fn = 64;

union() {
	difference() {
		cube(center = true, size = [40, 30, 10]);
		cylinder(center = true, h = 20, r = 5);
	}
	translate(v = [0, 0, 10]) {
		cylinder(center = true, h = 8, r = 12);
	}
}
