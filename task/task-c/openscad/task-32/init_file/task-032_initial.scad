// Generated with SolidPython2 for OpenSCAD task-032
$fn = 64;

difference() {
	hull() {
		translate(v = [-25, 0, 0]) {
			cylinder(h = 6, r = 13);
		}
		translate(v = [25, 0, 0]) {
			cylinder(h = 6, r = 13);
		}
	}
	translate(v = [-25, 0, -1]) {
		cylinder(h = 8, r = 2.0);
	}
	translate(v = [25, 0, -1]) {
		cylinder(h = 8, r = 2.0);
	}
}
