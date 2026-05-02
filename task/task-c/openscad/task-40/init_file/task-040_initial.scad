// Generated with SolidPython2 for OpenSCAD task-040
$fn = 64;

difference() {
	linear_extrude(height = 8) {
		offset(r = 6) {
			square(center = true, size = [84, 60]);
		}
	}
	translate(v = [0, 0, -1]) {
		cylinder(h = 10, r = 14.0);
	}
	translate(v = [-30, -20, -1]) {
		cylinder(h = 10, r = 2.0);
	}
	translate(v = [-30, 20, -1]) {
		cylinder(h = 10, r = 2.0);
	}
	translate(v = [30, -20, -1]) {
		cylinder(h = 10, r = 2.0);
	}
	translate(v = [30, 20, -1]) {
		cylinder(h = 10, r = 2.0);
	}
	translate(v = [19.091883092036785, 19.091883092036785, -1]) {
		cylinder(h = 10, r = 1.5);
	}
	translate(v = [-19.09188309203678, 19.091883092036785, -1]) {
		cylinder(h = 10, r = 1.5);
	}
	translate(v = [-19.091883092036788, -19.09188309203678, -1]) {
		cylinder(h = 10, r = 1.5);
	}
	translate(v = [19.091883092036777, -19.091883092036788, -1]) {
		cylinder(h = 10, r = 1.5);
	}
}
