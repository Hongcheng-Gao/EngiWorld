// Generated with SolidPython2 for OpenSCAD task-036
$fn = 64;

union() {
	translate(v = [-52.0, -35.0, 0]) {
		cube(size = [104, 70, 8]);
	}
	translate(v = [-40, -22.5, 8]) {
		difference() {
			cylinder(h = 10, r = 7);
			cylinder(h = 12, r = 2);
		}
	}
	translate(v = [-40, 22.5, 8]) {
		difference() {
			cylinder(h = 10, r = 7);
			cylinder(h = 12, r = 2);
		}
	}
	translate(v = [0, -22.5, 8]) {
		difference() {
			cylinder(h = 10, r = 7);
			cylinder(h = 12, r = 2);
		}
	}
	translate(v = [0, 22.5, 8]) {
		difference() {
			cylinder(h = 10, r = 7);
			cylinder(h = 12, r = 2);
		}
	}
	translate(v = [40, -22.5, 8]) {
		difference() {
			cylinder(h = 10, r = 7);
			cylinder(h = 12, r = 2);
		}
	}
	translate(v = [40, 22.5, 8]) {
		difference() {
			cylinder(h = 10, r = 7);
			cylinder(h = 12, r = 2);
		}
	}
}
