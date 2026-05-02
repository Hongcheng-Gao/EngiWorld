// Generated with SolidPython2 for OpenSCAD task-039
$fn = 64;

difference() {
	difference() {
		translate(v = [-40.0, -27.0, 0]) {
			cube(size = [80, 54, 42]);
		}
		translate(v = [0, 0, 3]) {
			translate(v = [-37.5, -24.5, 0]) {
				cube(size = [75, 49, 38]);
			}
		}
		scale(v = [1.05, 1.05, 1.05]) {
			import(file = "task-039_motor.stl", origin = [0, 0]);
		}
	}
	rotate(a = [90, 0, 0]) {
		translate(v = [-24, 20, 16]) {
			cylinder(h = 60, r = 1.5);
		}
	}
	rotate(a = [90, 0, 0]) {
		translate(v = [-14, 20, 16]) {
			cylinder(h = 60, r = 1.5);
		}
	}
	rotate(a = [90, 0, 0]) {
		translate(v = [-4, 20, 16]) {
			cylinder(h = 60, r = 1.5);
		}
	}
	rotate(a = [90, 0, 0]) {
		translate(v = [6, 20, 16]) {
			cylinder(h = 60, r = 1.5);
		}
	}
	rotate(a = [90, 0, 0]) {
		translate(v = [16, 20, 16]) {
			cylinder(h = 60, r = 1.5);
		}
	}
	rotate(a = [90, 0, 0]) {
		translate(v = [26, 20, 16]) {
			cylinder(h = 60, r = 1.5);
		}
	}
}
