$fn=64;
module dicing_jig() {
  difference() {
    cube([100,80,6]);
    for(x=[10:10:90]) translate([x,-1,4]) cube([1,82,3]);
    for(y=[10:10:70]) translate([-1,y,4]) cube([102,1,3]);
    for(x=[8,92]) for(y=[8,72])
      translate([x,y,-1]) cylinder(d=5,h=8,$fn=48);
  }
}
dicing_jig();
