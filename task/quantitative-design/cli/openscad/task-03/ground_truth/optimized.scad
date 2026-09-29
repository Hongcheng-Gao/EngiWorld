// Reference beam proxy: continuous base, two longitudinal high-I webs, and
// four transverse ties under the documented simple-support/center-load case.
union() {
	translate(v = [65.0, 19.0, 2.0]) {
		cube(center = true, size = [130.0, 38.0, 4.0]);
	}
	translate(v = [65.0, 7.0, 23.0]) {
		cube(center = true, size = [126.0, 4.0, 38.0]);
	}
	translate(v = [65.0, 31.0, 23.0]) {
		cube(center = true, size = [126.0, 4.0, 38.0]);
	}
	translate(v = [20.0, 19.0, 21.0]) {
		cube(center = true, size = [5.0, 30.0, 34.0]);
	}
	translate(v = [50.0, 19.0, 21.0]) {
		cube(center = true, size = [5.0, 30.0, 34.0]);
	}
	translate(v = [80.0, 19.0, 21.0]) {
		cube(center = true, size = [5.0, 30.0, 34.0]);
	}
	translate(v = [110.0, 19.0, 21.0]) {
		cube(center = true, size = [5.0, 30.0, 34.0]);
	}
}
