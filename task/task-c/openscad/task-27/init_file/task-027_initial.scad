// Generated with SolidPython2 for OpenSCAD task-027
$fn = 64;

difference() {
	scale(v = [1.2, 1.0, 1.4]) {
		import(file = "task-027_seed.stl", origin = [0, 0]);
	}
	translate(v = [0, 0, -5]) {
		cylinder(h = 32, r = 2.0);
	}
}
