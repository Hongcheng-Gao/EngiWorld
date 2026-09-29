// Coordinate reference for task-038. Preserve this bracket while adding ribs:
// base x=[-50,50], y=[-30,30], z=[0,5]
// upright x=[-50,50], y=[25,30], z=[5,40]
$fn = 64;

union() {
	translate(v = [-50.0, -30.0, 0]) {
		cube(size = [100, 60, 5]);
	}
	translate(v = [-50, 25, 5]) {
		cube(size = [100, 5, 35]);
	}
}
