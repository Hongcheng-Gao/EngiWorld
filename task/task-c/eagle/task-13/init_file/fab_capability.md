# Fab Capability Summary — 6-layer HDI Process

Published process capabilities for a mid-tier HDI shop. Encode every applicable
value as EAGLE design-rule parameters in a `.dru` file.

## Electrical clearances and trace widths

- Minimum copper-to-copper clearance: **0.1 mm** (applies to wire-wire,
  wire-pad, wire-via, pad-pad, pad-via, via-via, smd-smd, smd-pad, smd-via).
- Minimum trace (track) width: **0.09 mm**.
- Minimum drill hole diameter for through-hole / via drill: **0.15 mm**.

## Microvia parameters

- Microvia drill diameter: **0.1 mm**.
- Microvia finished pad diameter: **0.2 mm**.

## Layer stackup

- Six copper layers in a 1-u / 2 / 5 / 6 / 2-u HDI arrangement:
  - Layer 1 = outer, built up (u) over layer 2.
  - Layers 2..5 = four inner cores.
  - Layer 6 = outer, built up (u) over layer 5.
- Express in EAGLE's `layerSetup` string: a 6-layer form such as
  `(1+(2+(3*4)+5)+6)` (the `+` token denotes a buildup/microvia transition,
  `*` denotes a standard core).

## Copper thickness (mtCopper)

- Outer copper (layers 1, 6): **0.5 oz** each ~ 0.0175 mm.
- Inner copper (layers 2, 3, 4, 5): **0.5 oz** each ~ 0.0175 mm.
- Supply copper thickness for all six copper layers; EAGLE accepts a list of
  16 space-separated millimetre values (remaining 10 entries may repeat the
  default 0.035 mm). Only the six leading entries are validated by the grader.

## Required `.dru` parameters

Author `hdi_6layer.dru` as an INI-style `key = value` file with at least the
following keys (more is fine):

- `mdWireWire`, `mdWirePad`, `mdWireVia`, `mdPadPad`, `mdPadVia`, `mdViaVia`,
  `mdSmdPad`, `mdSmdVia`, `mdSmdSmd` — all <= 0.1 mm.
- `msWidth` — trace width <= 0.09 mm.
- `mdDrill` — <= 0.15 mm.
- `msDrill` — through-hole drill minimum <= 0.15 mm.
- `msMicroVia` — microvia drill <= 0.1 mm.
- `layerSetup` — 6-layer expression containing at minimum the digits 1..6.
- `mtCopper` — space-separated copper thicknesses; first six at <= 0.018 mm.

A value may be expressed in `mm`, `mil`, `um`, or `inch` units; the grader
normalises to millimetres before comparing.
