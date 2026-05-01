// Generated with SolidPython2 for OpenSCAD task-002
$fn = 64;

difference() {
	translate(v = [-50.0, -30.0, 0]) {
		cube(size = [100, 60, 6]);
	}
	translate(v = [-38, -18, -1]) {
		cylinder(h = 8, r = 2.0);
	}
	translate(v = [38, -18, -1]) {
		cylinder(h = 8, r = 2.0);
	}
	translate(v = [-38, 18, -1]) {
		cylinder(h = 8, r = 2.0);
	}
	translate(v = [38, 18, -1]) {
		cylinder(h = 8, r = 2.0);
	}
}
