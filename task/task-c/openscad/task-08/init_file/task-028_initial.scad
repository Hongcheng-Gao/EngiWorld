// Generated with SolidPython2 for OpenSCAD task-028
$fn = 64;

difference() {
	linear_extrude(height = 4) {
		offset(r = 4) {
			hull() {
				translate(v = [-20.0, 0, 0]) {
					circle(r = 10.0);
				}
				translate(v = [20.0, 0, 0]) {
					circle(r = 10.0);
				}
			}
		}
	}
	translate(v = [-25, 0, -1]) {
		cylinder(h = 6, r = 1.5);
	}
	translate(v = [0, 0, -1]) {
		cylinder(h = 6, r = 1.5);
	}
	translate(v = [25, 0, -1]) {
		cylinder(h = 6, r = 1.5);
	}
}
