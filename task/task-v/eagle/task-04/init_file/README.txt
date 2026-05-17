mylib_xc6206 -- EAGLE 7.x library to build from scratch
=======================================================

Deliverable: mylib_xc6206.lbr

Build a new EAGLE library that describes an XC6206 style 3-terminal LDO in
an SOT-23-3 package. The library must contain:

1) A PCB <package> whose name contains the substring "SOT" (e.g. "SOT23"
   or "SOT23-3") with three SMD pads named "1", "2", "3".

   Approximate SOT-23-3 pad geometry (mm):
      pad "1"  x=-0.95  y=-1.10   dx=1.0  dy=1.4
      pad "2"  x=+0.95  y=-1.10   dx=1.0  dy=1.4
      pad "3"  x= 0.00  y=+1.10   dx=1.0  dy=1.4

   Include at least one silkscreen / documentation element on layer 21
   (tPlace) or layer 51 (tDocu) -- a body outline is fine. Include a
   pin-1 marker: either a small shape near pad 1 or the text "1" on
   tPlace/tNames.

2) A <symbol> with exactly three <pin> elements:
      pin name="VIN"   direction="in"   (or "pas")
      pin name="GND"   direction="pwr"  (or "sup")
      pin name="VOUT"  direction="out"  (or "pas")

3) A <deviceset prefix="U"> binding that <symbol> (via a single <gate>)
   to the SOT-23-3 <package> (via a single <device>), with a <connects>
   block mapping the three pin names to pad numbers. Pinout for a real
   XC6206 in SOT-23-3 is:
      VIN  -> pad 1
      GND  -> pad 2
      VOUT -> pad 3
   The grader accepts any connects layout as long as every pin name
   appears exactly once.

The file must be valid XML parseable by Python's xml.etree.ElementTree;
an EAGLE <!DOCTYPE eagle SYSTEM "eagle.dtd"> declaration is fine (Python
ignores it when no external resolver is installed).

A realistic reference for pad geometry is bundled at
    /zfspool/zangyihe/eagle/eagle-7.7.0/lbr/ref-packages.lbr
under <package name="SOT23"> (2-pad transistor outline; add a third pad
for SOT-23-3).
