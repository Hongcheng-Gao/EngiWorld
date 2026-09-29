[English](README.md) | [简体中文](README_CN.md)

# task-21

Use Allegro's command-line placer on `init_file/fulladd.brd`, save the real
placed result as `output/fulladd_placed.brd`, and export `output/placement.csv`
with the columns `refdes,x_mm,y_mm,side,rot`.

Typical workflow:
1. Copy `fulladd.brd` into a writable working directory.
2. Run the placer from that directory, for example:
   `placement fulladd.brd fulladd_placed.brd`
3. Export the final component placement to `placement.csv`.
4. Submit the emitted Allegro database and placement report.
