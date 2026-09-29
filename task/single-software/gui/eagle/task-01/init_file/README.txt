[English](README.txt) | [简体中文](README_CN.txt)

task-01 — 555 astable blinker schematic (structural XML only)
==============================================================

GOAL
----
Create a file called `blinker.sch` at the root of your submission that, when
parsed as XML, describes a 555-timer astable "LED blinker" schematic. The
grader performs structural-only validation — it does NOT run EAGLE, does NOT
run ERC, and does NOT verify pin-level connectivity. It only checks that the
file parses and that the required parts / net elements / values exist.

WHAT THE GRADER CHECKS
----------------------
1. The file parses as well-formed XML.
2. At least one <part> has its deviceset or device attribute matching the
   regex /555/ (case-insensitive). The `linear` library (shipped here as
   `linear.lbr`) already contains a `*555` deviceset that satisfies this.
3. Parts with these refdes exist (case-insensitive): R1, R2, C1, C2,
   and either LED1 or D1.
4. At least one VCC supply part and one GND supply part exist. Either:
     (a) library="supply1" (or "supply2") with deviceset "VCC" / "GND"; or
     (b) a part whose refdes starts with VCC / GND / SUP.
   The `supply1.lbr` here ships the standard VCC and GND pseudo-devices.
5. There are >= 3 <net> elements inside <sheet><nets>. Typical set is
   VCC, GND, OUT (plus THRES / DISCH inside the timing network).
6. R1/R2 values look like resistors (e.g. "10k", "100k", "2.2M") and C1
   looks like a capacitance (e.g. "10u", "100n", "47nF"). Empty string
   or literal "?" is rejected.

LIBRARIES INCLUDED
------------------
- linear.lbr  — from EAGLE 7.7.0, contains the *555 deviceset.
- supply1.lbr — VCC / GND / +V / +12V pseudo-parts.
- rcl.lbr     — resistors and capacitors (R-EU_, C-EU).
- led.lbr     — LED deviceset.

You do NOT need to copy the full library contents into your .sch file — the
grader only reads <part ...> attribute values.

HINTS
-----
- EAGLE schematic skeleton:
    <?xml version="1.0" encoding="utf-8"?>
    <!DOCTYPE eagle SYSTEM "eagle.dtd">
    <eagle version="7.7.0">
      <drawing>
        <settings>.../</settings>
        <grid .../>
        <layers>.../</layers>
        <schematic xreflabel="..." xrefpart="...">
          <libraries>.../</libraries>
          <attributes/> <variantdefs/> <classes>.../</classes>
          <parts>
            <part name="IC1" library="linear" deviceset="*555" device="N"/>
            <part name="R1"  library="rcl" deviceset="R-EU_" device="0207/10" value="10k"/>
            ...
          </parts>
          <sheets>
            <sheet>
              <plain/> <instances>.../</instances> <busses/>
              <nets>
                <net name="VCC" class="0"><segment>...</segment></net>
                ...
              </nets>
            </sheet>
          </sheets>
        </schematic>
      </drawing>
    </eagle>

- Keep the file small — a few kilobytes is typical. Omit wires/instances if
  you only need to pass the grader.
- For a real 555 astable, pick R1/R2/C1 such that
    f = 1.44 / ((R1 + 2 R2) C1)
  gives 1-2 Hz. E.g. R1=10k, R2=100k, C1=10u → ~0.68 Hz.
