// Generated with SolidPython2 for OpenSCAD task-006
$fn = 64;

difference() {
	translate(v = [-21.0, -12.0, 0]) {
		cube(size = [42, 24, 12]);
	}
	rotate(a = [90, 0, 0]) {
		translate(v = [0, 12, 0]) {
			cylinder(h = 28, r = 8);
		}
	}
	translate(v = [0, 0, -1]) {
		cylinder(h = 14, r = 2.0);
	}
}
