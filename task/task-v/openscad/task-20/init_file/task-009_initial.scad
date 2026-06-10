// Starter 2D plate for task-009.
$fn = 64;

module rounded_slot(length, width) {
  hull() {
    translate([-(length - width) / 2, 0])
      circle(d = width);
    translate([(length - width) / 2, 0])
      circle(d = width);
  }
}

difference() {
  square(center = true, size = [100, 35]);

  translate([-40, 0])
    circle(r = 3);
  translate([40, 0])
    circle(r = 3);

  square(center = true, size = [45, 12]);
}
