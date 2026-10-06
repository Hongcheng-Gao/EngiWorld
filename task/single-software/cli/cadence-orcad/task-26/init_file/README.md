[English](README.md) | [简体中文](README_CN.md)

Export the real Allegro via reports for `HSD_FPGA_final.brd`.

Required files:
- `vialist_net.txt`
- `vialist_netlayer.txt`

Typical workflow:
1. Copy `HSD_FPGA_final.brd` into a writable working directory.
2. Run `report -v vialist_net HSD_FPGA_final.brd vialist_net.txt`
3. Run `report -v vialist_netlayer HSD_FPGA_final.brd vialist_netlayer.txt`
4. Submit both files.
