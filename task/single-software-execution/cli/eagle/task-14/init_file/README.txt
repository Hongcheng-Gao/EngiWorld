[English](README.txt) | [简体中文](README_CN.txt)

LM324 Quad Operational Amplifier — EAGLE Library Authoring Brief
=================================================================

Deliverable: lm324.lbr at the root of your submission.

The LM324 is a classic 14-pin DIP quad op-amp: one device, one symbol, one
package, but FOUR electrically identical op-amp "gates" (A/B/C/D) sharing a
single V+ / V- supply pair. Your job is to author a complete EAGLE library
that represents it.

Pinout (industry standard, DIP-14):
-----------------------------------
  Pin  1  = Gate A  OUT
  Pin  2  = Gate A  IN-
  Pin  3  = Gate A  IN+
  Pin  4  =         V+          (shared by all four gates)
  Pin  5  = Gate B  IN+
  Pin  6  = Gate B  IN-
  Pin  7  = Gate B  OUT
  Pin  8  = Gate C  OUT
  Pin  9  = Gate C  IN-
  Pin 10  = Gate C  IN+
  Pin 11  =         V-          (shared by all four gates)
  Pin 12  = Gate D  IN+
  Pin 13  = Gate D  IN-
  Pin 14  = Gate D  OUT

Required library structure:
---------------------------
* <package name="DIP-14"> with 14 through-hole <pad> elements named "1"..."14"
  (standard 2.54 mm pitch, ~7.62 mm row spacing is fine).
* <symbol name="OPAMP"> with exactly 5 pins named IN+, IN-, OUT, V+, V-.
* <deviceset prefix="U"> with four <gate> entries whose attributes are:
    name="A" symbol="OPAMP" ... swaplevel="1"
    name="B" symbol="OPAMP" ... swaplevel="1"
    name="C" symbol="OPAMP" ... swaplevel="1"
    name="D" symbol="OPAMP" ... swaplevel="1"
  Using swaplevel="1" on every gate tells ERC that any gate may be swapped
  with any other — useful because all four op-amps are electrically identical.
* Inside the single <device package="DIP-14">, a <connects> block mapping
  every (gate, pin) → pad combination:
    A/IN-  -> 2   A/IN+  -> 3   A/OUT  -> 1   A/V+ -> 4  A/V- -> 11
    B/IN-  -> 6   B/IN+  -> 5   B/OUT  -> 7   B/V+ -> 4  B/V- -> 11
    C/IN-  -> 9   C/IN+  -> 10  C/OUT  -> 8   C/V+ -> 4  C/V- -> 11
    D/IN-  -> 13  D/IN+  -> 12  D/OUT  -> 14  D/V+ -> 4  D/V- -> 11

Note that every gate's V+ maps to pad 4 and every gate's V- maps to pad 11,
capturing the shared supply.

The grader performs XML-structural checks only; it does NOT open the file in
EAGLE. As long as the file parses as XML and satisfies the above structure
(package with 14 pads, symbol with 5 pins, deviceset with 4 gates all at
swaplevel="1", and <connects> with the right gate→pin→pad rows) it will
pass.
