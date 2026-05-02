// Generated with SolidPython2 for OpenSCAD task-022
$fn = 64;

difference() {
	union() {
		translate(v = [0, 0, 0]) {
			cylinder(h = 4, r = 32.0);
		}
		translate(v = [0, 0, 0]) {
			cylinder(h = 48, r = 12.0);
		}
		translate(v = [0, 0, 44]) {
			cylinder(h = 4, r = 32.0);
		}
	}
	translate(v = [0, 0, -1]) {
		cylinder(h = 50, r = 4.0);
	}
}
