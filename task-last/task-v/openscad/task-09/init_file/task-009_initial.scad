// Generated with SolidPython2 for OpenSCAD task-009
$fn = 64;

difference() {
	square(center = true, size = [100, 35]);
	translate(v = [-40, 0, 0]) {
		circle(r = 3);
	}
	translate(v = [40, 0, 0]) {
		circle(r = 3);
	}
	square(center = true, size = [45, 12]);
}
