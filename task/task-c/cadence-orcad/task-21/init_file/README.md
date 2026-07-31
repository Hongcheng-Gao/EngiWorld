Run Allegro's command-line placer on `fulladd.brd` and save the placed result as `fulladd_placed.brd` in the task output directory. Export the final component placement as `placement.csv` with columns `refdes,x_mm,y_mm,side,rot`.

Typical workflow:
1. Copy `fulladd.brd` into a writable working directory.
2. Run the Allegro placer from that directory, for example: `placement fulladd.brd fulladd_placed.brd`
3. Export `placement.csv` from the placed board.
4. Submit `fulladd_placed.brd` and `placement.csv`.
