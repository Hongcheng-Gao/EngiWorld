# Library Consistency Check Report

Library: test.lbr
Devicesets scanned: 4
Symbols: 4, packages: 2

## Defects

- Symbol `AMP` has 2 pins named `IN`: **duplicate pin name**.
- Deviceset `REG_BADPAD` connect pin=`VOUT` pad=`99`: **missing pad** — pad `99` does not exist in package `SOT23-3`.
- Deviceset `BUF_UNCOVERED` connect pin=`NOPE`: **missing pin** — pin `NOPE` does not exist in symbol `BUF`.
- Deviceset `BUF_UNCOVERED` symbol `BUF` pin `EN`: **uncovered pin** — pin `EN` is not connected to any pad.

Total defects: 4

## Keywords

- missing pad
- duplicate pin
- missing pin
- uncovered pin
