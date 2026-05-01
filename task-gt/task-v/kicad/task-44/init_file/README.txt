Board-Setup Manufacturing Defaults
==================================

Open the loadable board project in KiCad PCB Editor, then use Board Setup to
apply the routing minima and default drawing/text settings listed in
`fab_setup.json`.

Keep the worksheet board itself unchanged: do not move the routed rails,
outline, fabrication note, or courtyard guide. Save the updated project and a
matching board copy as:

    output/board.kicad_pro
    output/board.kicad_pcb
