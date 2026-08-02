// Editable baseline. Replace the solid upper block with 6-16 Y-running fins.
// Final constraints: base >= 4 mm, fin thickness >= 1.5 mm, clear gap >= 3 mm.
base_size = [80, 50, 4];
starter_block_size = [73.6, 41, 10.64];

union() {
    translate([0, 0, 0]) cube(base_size);
    translate([3.2, 4.5, 4]) cube(starter_block_size);
}
