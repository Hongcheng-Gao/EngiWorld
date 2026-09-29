$fn = 120;
module probe_card_fixture() {
    difference() {
        cylinder(h=5,d=120);
        translate([0,0,-1]) cylinder(h=7,d=36);
        for (a=[0:45:315]) rotate([0,0,a]) translate([50,0,-1]) cylinder(h=7,d=4);
    }
}
probe_card_fixture();
