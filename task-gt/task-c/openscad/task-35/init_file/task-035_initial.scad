// Generated with SolidPython2 for OpenSCAD task-035
$fn = 64;

difference() {
	translate(v = [-36.0, -18.0, 0]) {
		cube(size = [72, 36, 4]);
	}
	translate(v = [0, 0, -1]) {
		linear_extrude(height = 6) {
			scale(v = [0.5, 0.5, 1]) {
				import(file = "task-035_logo.dxf", origin = [0, 0]);
			}
		}
	}
}
