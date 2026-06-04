// Starter irregular base for task-001.
$fn = 64;

base_points = [
  [-32, -20],
  [18, -20],
  [32, -8],
  [26, 16],
  [-16, 20],
  [-32, 8]
];

x_scale = 1.00;
y_scale = 1.00;
total_height = 8.00;
top_chamfer = 0.00;
top_scale = 1.00;

module irregular_base() {
  translate([0, 0, -total_height / 2]) {
    if (top_chamfer <= 0) {
      linear_extrude(height = total_height)
        scale([x_scale, y_scale])
          polygon(base_points);
    } else {
      linear_extrude(height = total_height - top_chamfer)
        scale([x_scale, y_scale])
          polygon(base_points);

      translate([0, 0, total_height - top_chamfer])
        linear_extrude(height = top_chamfer, scale = top_scale)
          scale([x_scale, y_scale])
            polygon(base_points);
    }
  }
}

irregular_base();
