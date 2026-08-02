// Reference: full 2.5 mm protective panel, 3 mm continuous perimeter walls,
// and three 2.4 mm reinforcing ribs. All four corner contact zones are solid.
union() {
	translate(v = [45.0, 32.5, 1.25]) {
		cube(center = true, size = [90.0, 65.0, 2.5]);
	}
	translate(v = [45.0, 1.5, 9.25]) {
		cube(center = true, size = [90.0, 3.0, 13.5]);
	}
	translate(v = [45.0, 63.5, 9.25]) {
		cube(center = true, size = [90.0, 3.0, 13.5]);
	}
	translate(v = [1.5, 32.5, 9.25]) {
		cube(center = true, size = [3.0, 65.0, 13.5]);
	}
	translate(v = [88.5, 32.5, 9.25]) {
		cube(center = true, size = [3.0, 65.0, 13.5]);
	}
	translate(v = [45.0, 18.0, 7.5]) {
		cube(center = true, size = [82.0, 2.4, 10.0]);
	}
	translate(v = [45.0, 32.5, 7.5]) {
		cube(center = true, size = [82.0, 2.4, 10.0]);
	}
	translate(v = [45.0, 47.0, 7.5]) {
		cube(center = true, size = [82.0, 2.4, 10.0]);
	}
}
