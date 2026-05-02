// Generated with SolidPython2 for OpenSCAD task-030
$fn = 64;

union() {
	translate(v = [-40.0, -15.0, 0]) {
		cube(size = [80, 30, 4]);
	}
	translate(v = [-11, -5, 4]) {
		linear_extrude(height = 1) {
			text(size = 10, text = "A17");
		}
	}
}
