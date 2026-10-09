[English](README.md) | [简体中文](README_CN.md)

Generate the real Allegro Gerber artwork set for `demo.brd`.

Required files:
- `TOP.art`
- `BOTTOM.art`
- `POWER.art`
- `GND.art`
- `photoplot.log`

Typical workflow:
1. Copy `demo.brd` and `art_param.txt` into the same writable working directory.
2. Run `artwork demo.brd`
3. Collect the five output files above and submit them.
