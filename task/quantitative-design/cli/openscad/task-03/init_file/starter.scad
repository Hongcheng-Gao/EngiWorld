// Editable baseline for the documented x=2/128 mm simple-support and
// 100 N center-load proxy. Replace the low solid block with a connected,
// high-I longitudinal load path while preserving support and load patches.
base_size = [130, 38, 4];
starter_block_size = [119.6, 31.16, 17.1];

union() {
    cube(base_size);
    translate([5.2, 3.42, 4]) cube(starter_block_size);
}
