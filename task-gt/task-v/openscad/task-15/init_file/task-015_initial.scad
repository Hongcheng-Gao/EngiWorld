// Generated with SolidPython2 for OpenSCAD task-015
$fn = 64;

union() {
	difference() {
		translate(v = [-27.5, -12.0, 0]) {
			cube(size = [55, 24, 3]);
		}
		translate(v = [-18, 0, -1]) {
			cylinder(h = 5, r = 1.5);
		}
		translate(v = [18, 0, -1]) {
			cylinder(h = 5, r = 1.5);
		}
	}
	translate(v = [-18, 14, 7]) {
		rotate(a = [90, 0, 0]) {
			difference() {
				cylinder(h = 14, r = 4);
				cylinder(h = 16, r = 1.5);
			}
		}
	}
	translate(v = [0, 14, 7]) {
		rotate(a = [90, 0, 0]) {
			difference() {
				cylinder(h = 14, r = 4);
				cylinder(h = 16, r = 1.5);
			}
		}
	}
	translate(v = [18, 14, 7]) {
		rotate(a = [90, 0, 0]) {
			difference() {
				cylinder(h = 14, r = 4);
				cylinder(h = 16, r = 1.5);
			}
		}
	}
}
