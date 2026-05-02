// Generated with SolidPython2 for OpenSCAD task-026
$fn = 64;

difference() {
	linear_extrude(height = 6) {
		import(file = "task-026_profile.dxf", origin = [0, 0]);
	}
	translate(v = [0, 0, -1]) {
		cylinder(h = 8, r = 5.0);
	}
}
