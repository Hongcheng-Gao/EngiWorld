// Starter file for OpenSCAD task-039
$fn = 64;

module guard_blank() {
	translate(v = [-40.0, -27.0, 0]) {
		cube(size = [80, 54, 42]);
	}
}

guard_blank();
