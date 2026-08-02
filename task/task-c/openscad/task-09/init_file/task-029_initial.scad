// Coordinate reference for task-029:
// plate x=[-48,48], y=[-26,26], z=[0,5] mm.
plate_size = [96, 52, 5];
plate_origin = [-48, -26, 0];

translate(plate_origin) cube(plate_size);
