// Generated with SolidPython2 for OpenSCAD task-020
$fn = 64;

union() {
	translate(v = [-40.0, -25.0, 0]) {
		cube(size = [80, 50, 4]);
	}
	translate(v = [-32, -17, 4]) {
		cylinder(h = 35, r = 4);
	}
	translate(v = [-32, 17, 4]) {
		cylinder(h = 35, r = 4);
	}
	translate(v = [32, -17, 4]) {
		cylinder(h = 35, r = 4);
	}
	translate(v = [32, 17, 4]) {
		cylinder(h = 35, r = 4);
	}
	difference() {
		translate(v = [-40.0, -25.0, 39]) {
			cube(size = [80, 50, 3]);
		}
		translate(v = [-32, -17, 38]) {
			cylinder(h = 5, r = 4.25);
		}
		translate(v = [-32, 17, 38]) {
			cylinder(h = 5, r = 4.25);
		}
		translate(v = [32, -17, 38]) {
			cylinder(h = 5, r = 4.25);
		}
		translate(v = [32, 17, 38]) {
			cylinder(h = 5, r = 4.25);
		}
	}
}
