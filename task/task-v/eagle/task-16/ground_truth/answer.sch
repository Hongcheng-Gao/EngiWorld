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
          <symbols>
<symbol name="555">
<wire x1="-7.62" y1="-10.16" x2="7.62" y2="-10.16" width="0.4064" layer="94"/>
<wire x1="7.62" y1="-10.16" x2="7.62" y2="10.16" width="0.4064" layer="94"/>
<wire x1="7.62" y1="10.16" x2="-7.62" y2="10.16" width="0.4064" layer="94"/>
<wire x1="-7.62" y1="10.16" x2="-7.62" y2="-10.16" width="0.4064" layer="94"/>
<pin name="TR" x="-10.16" y="7.62" length="short" direction="in"/>
<pin name="Q" x="10.16" y="7.62" length="short" direction="out" rot="R180"/>
<pin name="R" x="-10.16" y="2.54" length="short" direction="in" function="dot"/>
<pin name="CV" x="-10.16" y="-2.54" length="short" direction="in"/>
<pin name="THR" x="10.16" y="-2.54" length="short" direction="in" rot="R180"/>
<pin name="DIS" x="10.16" y="2.54" length="short" direction="in" rot="R180"/>
<pin name="V+" x="10.16" y="-7.62" length="short" direction="pwr" rot="R180"/>
<pin name="GND" x="-10.16" y="-7.62" length="short" direction="pwr"/>
</symbol>
</symbols>
<devicesets>
            <deviceset name="*555">
              <gates>
                <gate name="G$1" symbol="555" x="0" y="0" />
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
          <symbols>
<symbol name="R"><wire x1="-2.54" y1="0" x2="2.54" y2="0" width="0.254" layer="94"/><pin name="1" x="-5.08" y="0" length="short" direction="pas"/><pin name="2" x="5.08" y="0" length="short" direction="pas" rot="R180"/></symbol>
<symbol name="C"><wire x1="-0.635" y1="2.54" x2="-0.635" y2="-2.54" width="0.254" layer="94"/><wire x1="0.635" y1="2.54" x2="0.635" y2="-2.54" width="0.254" layer="94"/><pin name="1" x="-5.08" y="0" length="short" direction="pas"/><pin name="2" x="5.08" y="0" length="short" direction="pas" rot="R180"/></symbol>
</symbols>
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
          <symbols>
<symbol name="LED"><wire x1="-1.27" y1="1.27" x2="1.27" y2="0" width="0.254" layer="94"/><wire x1="1.27" y1="0" x2="-1.27" y2="-1.27" width="0.254" layer="94"/><pin name="A" x="-5.08" y="0" length="short" direction="pas"/><pin name="C" x="5.08" y="0" length="short" direction="pas" rot="R180"/></symbol>
</symbols>
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
                <pinref part="U1" gate="G$1" pin="V+" />
                <pinref part="U1" gate="G$1" pin="R" />
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
                <pinref part="LED1" gate="G$1" pin="C" />
              </segment>
            </net>
            <net name="TRIG_THRES" class="0">
              <segment>
                <wire x1="10" y1="26" x2="65" y2="26" width="0.1524" layer="91" />
                <label x="12" y="26" size="1.778" layer="95" />
                <pinref part="U1" gate="G$1" pin="TR" />
                <pinref part="U1" gate="G$1" pin="THR" />
                <pinref part="C1" gate="G$1" pin="1" />
                <pinref part="R2" gate="G$1" pin="2" />
              </segment>
            </net>
            <net name="DISCH" class="0">
              <segment>
                <wire x1="10" y1="34" x2="65" y2="34" width="0.1524" layer="91" />
                <label x="12" y="34" size="1.778" layer="95" />
                <pinref part="U1" gate="G$1" pin="DIS" />
                <pinref part="R1" gate="G$1" pin="2" />
                <pinref part="R2" gate="G$1" pin="1" />
              </segment>
            </net>
            <net name="OUT" class="0">
              <segment>
                <wire x1="10" y1="42" x2="65" y2="42" width="0.1524" layer="91" />
                <label x="12" y="42" size="1.778" layer="95" />
                <pinref part="U1" gate="G$1" pin="Q" />
                <pinref part="LED1" gate="G$1" pin="A" />
              </segment>
            </net>
            <net name="CTRL" class="0">
              <segment>
                <wire x1="10" y1="50" x2="65" y2="50" width="0.1524" layer="91" />
                <label x="12" y="50" size="1.778" layer="95" />
                <pinref part="U1" gate="G$1" pin="CV" />
              </segment>
            </net>
          </nets>
        </sheet>
      </sheets>
    </schematic>
  </drawing>
</eagle>
