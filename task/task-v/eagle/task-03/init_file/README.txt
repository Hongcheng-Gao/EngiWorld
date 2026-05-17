Task 28 — Configure a 4-layer stackup in EAGLE
==============================================

Target stackup (top to bottom):
    L1  SIG   (top, outer signal)   -- finished copper 35 um
    ---- 0.2  mm FR-4 prepreg
    L2  GND   (inner plane)         -- base copper 35 um
    ---- 1.065 mm FR-4 core
    L3  PWR   (inner plane)         -- base copper 35 um
    ---- 0.2  mm FR-4 prepreg
    L16 SIG   (bottom, outer signal)-- finished copper 35 um

Total finished thickness ~1.6 mm.  FR-4 dielectric (Dk ~4.3 @ 1 GHz).

Open `stackup_seed.brd` in EAGLE's board editor. In Tools -> DRC, switch the
board from its current 2-layer setup to a 4-layer build-up using layers
1 / 2 / 3 / 16 and dielectric thicknesses 0.200 mm / 1.065 mm / 0.200 mm.

Also tighten these fabrication minima:
  mdWireWire, mdWirePad, mdWireVia, mdPadPad, mdPadVia, mdViaVia >= 0.15 mm
  mdDrill >= 0.30 mm
  msWidth >= 0.15 mm

Save the updated board as `hspeed_4layer.brd`.
