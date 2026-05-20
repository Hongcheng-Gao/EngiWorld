// Generated with SolidPython2 for OpenSCAD task-013
$fn = 64;

difference() {
	cylinder(h = 12, r1 = 17, r2 = 13);
	translate(v = [0, 0, -1]) {
		cylinder(h = 14, r = 2.0);
	}
	translate(v = [0, 0, -0.1]) {
		cylinder(h = 2.2, r = 10);
	}
}
