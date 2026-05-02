// Generated with SolidPython2 for OpenSCAD task-037
$fn = 64;

difference() {
	rotate(a = [90, 0, 0]) {
		rotate_extrude(angle = 360) {
			polygon(points = [[4, -8], [25, -8], [21, -2], [18, 0], [21, 2], [25, 8], [4, 8]]);
		}
	}
	rotate(a = [90, 0, 0]) {
		cylinder(center = true, h = 20, r = 4);
	}
}
