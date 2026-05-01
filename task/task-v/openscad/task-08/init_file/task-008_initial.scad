// Generated with SolidPython2 for OpenSCAD task-008
$fn = 64;

union() {
	translate(v = [-40.0, -15.0, 0]) {
		cube(size = [80, 30, 4]);
	}
	translate(v = [-30, -4, 4]) {
		linear_extrude(height = 1.2) {
			text(halign = "left", size = 8, text = "OPENSCAD", valign = "baseline");
		}
	}
}
