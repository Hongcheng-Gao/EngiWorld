// Generated with SolidPython2 for OpenSCAD task-021
$fn = 64;

difference() {
	union() {
		translate(v = [-45.0, -35.0, 0]) {
			cube(size = [90, 70, 5]);
		}
		translate(v = [-45, 30, 5]) {
			cube(size = [90, 5, 60]);
		}
	}
	translate(v = [0, 30, 25]) {
		cube(center = true, size = [12, 8, 32]);
	}
}
