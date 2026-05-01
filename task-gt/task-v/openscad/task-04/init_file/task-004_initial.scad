// Generated with SolidPython2 for OpenSCAD task-004
$fn = 64;

difference() {
	union() {
		translate(v = [0, 0, 0]) {
			cylinder(h = 18, r = 21.0);
		}
		translate(v = [0, 0, 18]) {
			cylinder(h = 22, r = 16.0);
		}
	}
	translate(v = [0, 0, -1]) {
		cylinder(h = 42, r = 9.0);
	}
}
