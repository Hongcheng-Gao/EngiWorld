// Starter file for task-020. Units: millimetres.
// Preserve this base at x=[-65,65], y=[-45,45], z=[0,6], then add the
// explicitly positioned top plate, posts, clearance holes, slots, and holes.
$fn = 64;

module plate(w, d, t) {
    translate([-w / 2, -d / 2, 0]) cube([w, d, t]);
}

plate(130, 90, 6);
