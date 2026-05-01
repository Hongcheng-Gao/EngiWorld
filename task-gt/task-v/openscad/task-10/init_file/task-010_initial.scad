// Generated with SolidPython2 for OpenSCAD task-010
$fn = 64;

difference() {
	linear_extrude(height = 5) {
		offset(r = 6) {
			square(center = true, size = [78, 20]);
		}
	}
	translate(v = [-35, -11, -1]) {
		cylinder(h = 7, r = 1.5);
	}
	translate(v = [-35, 11, -1]) {
		cylinder(h = 7, r = 1.5);
	}
	translate(v = [35, -11, -1]) {
		cylinder(h = 7, r = 1.5);
	}
	translate(v = [35, 11, -1]) {
		cylinder(h = 7, r = 1.5);
	}
}
