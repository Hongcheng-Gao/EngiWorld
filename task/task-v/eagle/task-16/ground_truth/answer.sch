<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE eagle SYSTEM "eagle.dtd">
<eagle version="7.7.0">
  <drawing>
    <settings>
      <setting alwaysvectorfont="yes" />
      <setting verticaltext="up" />
    </settings>
    <grid distance="0.1" unitdist="inch" unit="inch" style="lines" multiple="1" display="no" altdistance="0.01" altunitdist="inch" altunit="inch" />
    <layers>
      <layer number="91" name="Nets" color="2" fill="1" visible="yes" active="yes" />
      <layer number="92" name="Busses" color="1" fill="1" visible="yes" active="yes" />
      <layer number="93" name="Pins" color="2" fill="1" visible="no" active="yes" />
      <layer number="94" name="Symbols" color="4" fill="1" visible="yes" active="yes" />
      <layer number="95" name="Names" color="7" fill="1" visible="yes" active="yes" />
      <layer number="96" name="Values" color="7" fill="1" visible="yes" active="yes" />
    </layers>
    <schematic xreflabel="%F%N/%S.%C%R" xrefpart="/%S.%C%R">
      <libraries>
        <library name="linear">
          <devicesets>
            <deviceset name="*555">
              <gates>
                <gate name="G$1" symbol="*555" x="0" y="0" />
              </gates>
              <devices>
                <device name="">
                  <technologies>
                    <technology name="" />
                  </technologies>
                </device>
              </devices>
            </deviceset>
          </devicesets>
        </library>
        <library name="rcl">
          <devicesets>
            <deviceset name="R">
              <gates>
                <gate name="G$1" symbol="R" x="0" y="0" />
              </gates>
              <devices>
                <device name="">
                  <technologies>
                    <technology name="" />
                  </technologies>
                </device>
              </devices>
            </deviceset>
            <deviceset name="C">
              <gates>
                <gate name="G$1" symbol="C" x="0" y="0" />
              </gates>
              <devices>
                <device name="">
                  <technologies>
                    <technology name="" />
                  </technologies>
                </device>
              </devices>
            </deviceset>
          </devicesets>
        </library>
        <library name="led">
          <devicesets>
            <deviceset name="LED">
              <gates>
                <gate name="G$1" symbol="LED" x="0" y="0" />
              </gates>
              <devices>
                <device name="">
                  <technologies>
                    <technology name="" />
                  </technologies>
                </device>
              </devices>
            </deviceset>
          </devicesets>
        </library>
      </libraries>
      <attributes />
      <variantdefs />
      <classes>
        <class number="0" name="default" width="0" drill="0" />
      </classes>
      <parts>
        <part name="U1" library="linear" deviceset="*555" device="" />
        <part name="R1" library="rcl" deviceset="R" device="" value="10k" />
        <part name="R2" library="rcl" deviceset="R" device="" value="47k" />
        <part name="C1" library="rcl" deviceset="C" device="" value="100n" />
        <part name="C2" library="rcl" deviceset="C" device="" value="10u" />
        <part name="LED1" library="led" deviceset="LED" device="" value="red" />
      </parts>
      <sheets>
        <sheet>
          <plain />
          <instances>
            <instance part="U1" gate="G$1" x="50" y="40" />
            <instance part="R1" gate="G$1" x="20" y="55" />
            <instance part="R2" gate="G$1" x="20" y="40" />
            <instance part="C1" gate="G$1" x="20" y="25" />
            <instance part="C2" gate="G$1" x="75" y="55" />
            <instance part="LED1" gate="G$1" x="80" y="35" />
          </instances>
          <busses />
          <nets>
            <net name="VCC" class="0">
              <segment>
                <wire x1="10" y1="10" x2="65" y2="10" width="0.1524" layer="91" />
                <label x="12" y="10" size="1.778" layer="95" />
                <pinref part="U1" gate="G$1" pin="VCC" />
                <pinref part="R1" gate="G$1" pin="1" />
                <pinref part="C2" gate="G$1" pin="1" />
              </segment>
            </net>
            <net name="GND" class="0">
              <segment>
                <wire x1="10" y1="18" x2="65" y2="18" width="0.1524" layer="91" />
                <label x="12" y="18" size="1.778" layer="95" />
                <pinref part="U1" gate="G$1" pin="GND" />
                <pinref part="C1" gate="G$1" pin="2" />
                <pinref part="C2" gate="G$1" pin="2" />
                <pinref part="LED1" gate="G$1" pin="K" />
              </segment>
            </net>
            <net name="TRIG_THRES" class="0">
              <segment>
                <wire x1="10" y1="26" x2="65" y2="26" width="0.1524" layer="91" />
                <label x="12" y="26" size="1.778" layer="95" />
                <pinref part="U1" gate="G$1" pin="TRIG" />
                <pinref part="U1" gate="G$1" pin="THRES" />
                <pinref part="C1" gate="G$1" pin="1" />
                <pinref part="R2" gate="G$1" pin="2" />
              </segment>
            </net>
            <net name="DISCH" class="0">
              <segment>
                <wire x1="10" y1="34" x2="65" y2="34" width="0.1524" layer="91" />
                <label x="12" y="34" size="1.778" layer="95" />
                <pinref part="U1" gate="G$1" pin="DISCH" />
                <pinref part="R1" gate="G$1" pin="2" />
                <pinref part="R2" gate="G$1" pin="1" />
              </segment>
            </net>
            <net name="OUT" class="0">
              <segment>
                <wire x1="10" y1="42" x2="65" y2="42" width="0.1524" layer="91" />
                <label x="12" y="42" size="1.778" layer="95" />
                <pinref part="U1" gate="G$1" pin="OUT" />
                <pinref part="LED1" gate="G$1" pin="A" />
              </segment>
            </net>
            <net name="CTRL" class="0">
              <segment>
                <wire x1="10" y1="50" x2="65" y2="50" width="0.1524" layer="91" />
                <label x="12" y="50" size="1.778" layer="95" />
                <pinref part="U1" gate="G$1" pin="CTRL" />
              </segment>
            </net>
          </nets>
        </sheet>
      </sheets>
    </schematic>
  </drawing>
</eagle>
