// Generated with SolidPython2 for OpenSCAD task-033
$fn = 64;

difference() {
	minkowski() {
		translate(v = [-27.0, -18.0, 0]) {
			cube(size = [54, 36, 24]);
		}
		sphere(r = 3);
	}
	translate(v = [0, 0, 5]) {
		translate(v = [-25.0, -16.0, 0]) {
			cube(size = [50, 32, 30]);
		}
	}
}
