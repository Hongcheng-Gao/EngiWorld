$fn=64;
module bga_stencil() {
  difference() {
    cube([50,50,0.3],center=true);
    for(ix=[0:7]) for(iy=[0:7])
      translate([(ix-3.5)*4,(iy-3.5)*4,0])
        cylinder(d=0.6,h=1,center=true,$fn=32);
  }
}
bga_stencil();
