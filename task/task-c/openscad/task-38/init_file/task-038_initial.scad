// Generated with SolidPython2 for OpenSCAD task-038
$fn = 64;

union() {
	union() {
		translate(v = [-50.0, -30.0, 0]) {
			cube(size = [100, 60, 5]);
		}
		translate(v = [-50, 25, 5]) {
			cube(size = [100, 5, 35]);
		}
	}
	translate(v = [-40, 5, 5]) {
		rotate(a = [90, 0, 90]) {
			linear_extrude(height = 3) {
				polygon(points = [[0, 0], [28, 0], [0, 32]]);
			}
		}
	}
	translate(v = [-20, 5, 5]) {
		rotate(a = [90, 0, 90]) {
			linear_extrude(height = 3) {
				polygon(points = [[0, 0], [28, 0], [0, 32]]);
			}
		}
	}
	translate(v = [0, 5, 5]) {
		rotate(a = [90, 0, 90]) {
			linear_extrude(height = 3) {
				polygon(points = [[0, 0], [28, 0], [0, 32]]);
			}
		}
	}
	translate(v = [20, 5, 5]) {
		rotate(a = [90, 0, 90]) {
			linear_extrude(height = 3) {
				polygon(points = [[0, 0], [28, 0], [0, 32]]);
			}
		}
	}
	translate(v = [40, 5, 5]) {
		rotate(a = [90, 0, 90]) {
			linear_extrude(height = 3) {
				polygon(points = [[0, 0], [28, 0], [0, 32]]);
			}
		}
	}
}
