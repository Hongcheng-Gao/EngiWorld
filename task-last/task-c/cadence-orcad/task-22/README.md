# task-22

Export the real Allegro cross-section report for
`init_file/HSD_FPGA_final.brd`.

Typical workflow:
1. Copy `HSD_FPGA_final.brd` into a writable working directory.
2. Run `report -v x-section HSD_FPGA_final.brd x-section.txt`
3. Submit `output/x-section.txt`.
