$fn = 48;
module channel(a,b,w=2,d=1.2) {
    hull() {
        translate([a[0],a[1],3-d]) cylinder(h=d+0.2,d=w);
        translate([b[0],b[1],3-d]) cylinder(h=d+0.2,d=w);
    }
}
module microfluidic_lid() {
    difference() {
        translate([-26,-16,0]) cube([52,32,3]);
        channel([-20,-10],[20,-10]);
        channel([20,-10],[20,-5]);
        channel([20,-5],[-20,-5]);
        channel([-20,-5],[-20,0]);
        channel([-20,0],[20,0]);
        channel([20,0],[20,5]);
        channel([20,5],[-20,5]);
        channel([-20,5],[-20,10]);
        channel([-20,10],[20,10]);
        translate([-20,-10,-1]) cylinder(h=5,d=3);
        translate([20,10,-1]) cylinder(h=5,d=3);
    }
}
microfluidic_lid();
