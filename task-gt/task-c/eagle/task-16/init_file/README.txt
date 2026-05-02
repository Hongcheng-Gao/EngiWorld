task-33 — Assign swaplevel attributes on differential-driver pins
=================================================================

Open init_file/diff_driver.lbr in EAGLE's library editor. It contains a
single <symbol> "DIFF_DRIVER" whose 8 pins
(DP0/DN0, DP1/DN1, DP2/DN2, DP3/DN3) all currently carry swaplevel="0".

Task: assign swaplevel values pairwise so that within-pair swaps become
legal but cross-pair swaps do not:

    DP0, DN0  ->  swaplevel = 1
    DP1, DN1  ->  swaplevel = 2
    DP2, DN2  ->  swaplevel = 3
    DP3, DN3  ->  swaplevel = 4

GUI steps (library editor, symbol mode):
  1. Double-click each pin (or use the INFO / CHANGE command).
  2. In the Properties dialog set the "Swaplevel" field to the target.
  3. Save as diff_driver.lbr.

Deliverable: diff_driver.lbr with the updated swaplevel attributes.
