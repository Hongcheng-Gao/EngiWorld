$fn = 96;
module wafer_carrier() {
    difference() {
        union() {
            difference() { cylinder(h=4, d=110); translate([0,0,-1]) cylinder(h=6, d=78); }
            translate([0,0,4]) difference() { cylinder(h=3, d=96); translate([0,0,-1]) cylinder(h=5, d=78); }
        }
        for (a=[0,120,240]) rotate([0,0,a]) translate([46,0,-1]) cylinder(h=9, d=4);
    }
}
wafer_carrier();
