$fn = 48;
module heatsink() {
    difference() {
        union() {
            translate([-30,-22.5,0]) cube([60,45,4]);
            for (x=[-24:6:24]) translate([x-1,-22.5,4]) cube([2,45,22]);
        }
        for (x=[-25,25]) for (y=[-17.5,17.5]) translate([x,y,-1]) cylinder(h=7,d=4);
    }
}
heatsink();
