// Task 02 clamp generated from the KiCad parameter handoff.
// Input map SHA-256: aa23616766c9679e420b656f42ec366d770c9152e6bfb53739d21be5004ff0bc
include <01_kicad_parameters.scad>;

module shell() {
  difference() {
    translate([-enclosure[0]/2, -enclosure[1]/2, 0]) cube(enclosure);
    translate([-cavity[0]/2, -cavity[1]/2, base_thickness]) cube(cavity);
  }
}

module standoff(x, y) {
  translate([x, y, base_thickness]) cylinder(d=standoff_od, h=standoff_height);
}

module screw_bore(x, y) {
  translate([x, y, -overcut]) cylinder(d=standoff_bore, h=board_bottom_z + 2*overcut);
}

module u1_contact_pad() {
  translate([u1_contact[0] - u1_contact[2]/2, u1_contact[1] - u1_contact[3]/2, u1_contact[4]])
    cube([u1_contact[2], u1_contact[3], u1_contact[5] - u1_contact[4]]);
}

module installed_clamp() {
  union() {
    shell();
    u1_contact_pad();
    for (axis = standoff_axes) standoff(axis[1], axis[2]);
  }
}

difference() {
  installed_clamp();
  for (aperture = apertures)
    translate([aperture[2], aperture[3], aperture[4]])
      cube([aperture[5]-aperture[2], aperture[6]-aperture[3], aperture[7]-aperture[4]]);
  for (axis = standoff_axes) screw_bore(axis[1], axis[2]);
  translate([l1_keepout[0], l1_keepout[1], l1_keepout[3]])
    cylinder(r=l1_keepout[2], h=l1_keepout[4]-l1_keepout[3]);
  translate([c1_clearance[0], c1_clearance[1], c1_clearance[3]])
    cylinder(r=c1_clearance[2], h=c1_clearance[4]-c1_clearance[3]);
}
