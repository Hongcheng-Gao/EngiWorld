[English](README.txt) | [简体中文](README_CN.txt)

Task 35 — Tighten DRC thresholds in-board
=========================================

Open `loose.brd` in EAGLE and use Tools -> DRC to tighten these six seeded
thresholds:

    mdWireWire  >= 0.15 mm
    mdWirePad   >= 0.15 mm
    mdWireVia   >= 0.15 mm
    mdDrill     >= 0.30 mm
    msWidth     >= 0.15 mm
    msDrill     >= 0.30 mm

Save the updated board as:

    tight.brd
