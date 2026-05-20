$fn = 64;
linear_extrude(height = 18)
  difference() {
    circle(r = 23);
    circle(r = 15);
    translate([-30, -30]) square([60, 30]);
  }
