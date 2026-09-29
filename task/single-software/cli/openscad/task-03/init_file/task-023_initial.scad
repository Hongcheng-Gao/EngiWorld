// Generated with SolidPython2 for OpenSCAD task-023
$fn = 64;

difference() {
	projection(cut = false) {
		union() {
			translate(v = [-30.0, -17.5, 0]) {
				cube(size = [60, 35, 5]);
			}
			translate(v = [-30, 14, 5]) {
				cube(size = [60, 5, 30]);
			}
		}
	}
	translate(v = [-22, 0, 0]) {
		circle(r = 2);
	}
	translate(v = [22, 0, 0]) {
		circle(r = 2);
	}
}
