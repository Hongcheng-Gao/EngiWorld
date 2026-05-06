// Starter label plate for task-030.
$fn = 48;

label_text = "TXT";
text_size = 10;
raised_text_height = 1.0;
plate_width = 80;
plate_height = 30;
plate_thickness = 4;

union() {
  translate([-plate_width / 2, -plate_height / 2, 0])
    cube([plate_width, plate_height, plate_thickness]);

  translate([-12, -5, plate_thickness])
    linear_extrude(height = raised_text_height)
      text(label_text, size = text_size);
}
