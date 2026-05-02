DRC Regression Detection Task
==============================

You are given two board revisions (before.kicad_pcb, after.kicad_pcb) and
a DRC ruleset (rules.kicad_dru, min clearance 0.2 mm).

1. Produce diff.json identifying newly introduced violations and resolved ones.
2. Produce fixed.kicad_pcb that resolves only the newly introduced violations
   while preserving all other edits in after.kicad_pcb.

Output files: output/diff.json and output/fixed.kicad_pcb
