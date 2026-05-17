<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE eagle SYSTEM "eagle.dtd">
<eagle version="7.7.0">
<drawing>
<settings>
<setting alwaysvectorfont="yes"/>
<setting verticaltext="up"/>
</settings>
<grid distance="0.1" unitdist="inch" unit="inch" style="lines" multiple="1" display="no" altdistance="0.01" altunitdist="inch" altunit="inch"/>
<layers>
<layer number="91" name="Nets" color="2" fill="1" visible="yes" active="yes"/>
<layer number="92" name="Busses" color="1" fill="1" visible="yes" active="yes"/>
<layer number="93" name="Pins" color="2" fill="1" visible="no" active="yes"/>
<layer number="94" name="Symbols" color="4" fill="1" visible="yes" active="yes"/>
<layer number="95" name="Names" color="7" fill="1" visible="yes" active="yes"/>
<layer number="96" name="Values" color="7" fill="1" visible="yes" active="yes"/>
</layers>
<schematic xreflabel="%F%N/%S.%C%R" xrefpart="/%S.%C%R">
<libraries>
<library name="simple">
<packages>
</packages>
<symbols>
<symbol name="BLOCK2">
<wire x1="-7.62" y1="5.08" x2="7.62" y2="5.08" width="0.254" layer="94"/>
<wire x1="7.62" y1="5.08" x2="7.62" y2="-5.08" width="0.254" layer="94"/>
<wire x1="7.62" y1="-5.08" x2="-7.62" y2="-5.08" width="0.254" layer="94"/>
<wire x1="-7.62" y1="-5.08" x2="-7.62" y2="5.08" width="0.254" layer="94"/>
<text x="-7.62" y="6.35" size="1.778" layer="95">&gt;NAME</text>
<pin name="VCC" x="-12.7" y="2.54" length="middle" direction="pwr"/>
<pin name="OUT" x="12.7" y="2.54" length="middle" direction="out" rot="R180"/>
</symbol>
</symbols>
<devicesets>
<deviceset name="BLOCK2" prefix="U" uservalue="no">
<gates>
<gate name="G$1" symbol="BLOCK2" x="0" y="0"/>
</gates>
<devices>
<device name="">
<technologies>
<technology name=""/>
</technologies>
</device>
</devices>
</deviceset>
</devicesets>
</library>
</libraries>
<attributes>
</attributes>
<variantdefs>
</variantdefs>
<classes>
<class number="0" name="default" width="0" drill="0"/>
</classes>
<parts>
<part name="U1" library="simple" deviceset="BLOCK2" device="" value="DRIVER"/>
<part name="U2" library="simple" deviceset="BLOCK2" device="" value="CONSUMER"/>
</parts>
<sheets>
<sheet>
<description>Sheet 1 - has U1 whose VCC pin needs to drive U2 on sheet 2.</description>
<plain>
<text x="50" y="120" size="3.048" layer="94">Sheet 1</text>
</plain>
<instances>
<instance part="U1" gate="G$1" x="80" y="100"/>
</instances>
<busses>
</busses>
<nets>
</nets>
</sheet>
<sheet>
<description>Sheet 2 - has U2 whose VCC pin must connect back to sheet 1's VCC.</description>
<plain>
<text x="50" y="120" size="3.048" layer="94">Sheet 2</text>
</plain>
<instances>
<instance part="U2" gate="G$1" x="80" y="100"/>
</instances>
<busses>
</busses>
<nets>
</nets>
</sheet>
</sheets>
</schematic>
</drawing>
</eagle>
