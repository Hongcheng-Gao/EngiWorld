$fn = 48;
module qfn_tray() {
    difference() {
        translate([-44,-32,0]) cube([88,64,4]);
        for (row=[0:2]) for (col=[0:3]) translate([-28+col*18,-18+row*18,2]) cube([10,8,3], center=true);
        for (x=[-38,38]) translate([x,26,-1]) cylinder(h=6,d=3);
    }
}
qfn_tray();
