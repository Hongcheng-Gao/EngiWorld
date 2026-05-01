// Generated with SolidPython2 for OpenSCAD task-017
$fn = 64;

union() {
	linear_extrude(height = 18) {
		difference() {
			circle(r = 23);
			circle(r = 15);
			translate(v = [-30, -30, 0]) {
				square(size = [60, 30]);
			}
		}
	}
	translate(v = [0, -18, 0]) {
		difference() {
			translate(v = [-33.0, -8.0, 0]) {
				cube(size = [66, 16, 18]);
			}
			translate(v = [-24, -18, -1]) {
				cylinder(h = 20, r = 2.5);
			}
			translate(v = [24, -18, -1]) {
				cylinder(h = 20, r = 2.5);
			}
		}
	}
}
