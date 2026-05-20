// Generated with SolidPython2 for OpenSCAD task-005
$fn = 64;

difference() {
	union() {
		translate(v = [-40.0, -25.0, 0]) {
			cube(size = [80, 50, 6]);
		}
		translate(v = [-40, 19, 6]) {
			cube(size = [80, 6, 36]);
		}
	}
	translate(v = [-25, 0, -1]) {
		cylinder(h = 8, r = 2.5);
	}
	translate(v = [25, 0, -1]) {
		cylinder(h = 8, r = 2.5);
	}
}
