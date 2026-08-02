// Editable baseline. Preserve a continuous >=2 mm protective panel and add
// >=2 mm perimeter walls reaching above z=8; four 10x10 mm corner contact
// zones on the z=0 underside must remain at least 90% covered.
panel_size = [90, 65, 2.5];
starter_block_size = [82.8, 53.3, 6.84];

union() {
    cube(panel_size);
    translate([3.6, 5.85, 2.5]) cube(starter_block_size);
}
