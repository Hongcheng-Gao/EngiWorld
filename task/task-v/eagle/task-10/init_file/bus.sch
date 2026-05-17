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
<library name="generic">
<packages>
</packages>
<symbols>
<symbol name="DRIVER3">
<wire x1="-10.16" y1="7.62" x2="10.16" y2="7.62" width="0.254" layer="94"/>
<wire x1="10.16" y1="7.62" x2="10.16" y2="-7.62" width="0.254" layer="94"/>
<wire x1="10.16" y1="-7.62" x2="-10.16" y2="-7.62" width="0.254" layer="94"/>
<wire x1="-10.16" y1="-7.62" x2="-10.16" y2="7.62" width="0.254" layer="94"/>
<text x="-10.16" y="8.89" size="1.778" layer="95">&gt;NAME</text>
<text x="-10.16" y="-10.16" size="1.778" layer="96">&gt;VALUE</text>
<pin name="ADDR0" x="15.24" y="5.08" length="middle" rot="R180"/>
<pin name="ADDR1" x="15.24" y="0" length="middle" rot="R180"/>
<pin name="ADDR2" x="15.24" y="-5.08" length="middle" rot="R180"/>
</symbol>
<symbol name="RECEIVER3">
<wire x1="-10.16" y1="7.62" x2="10.16" y2="7.62" width="0.254" layer="94"/>
<wire x1="10.16" y1="7.62" x2="10.16" y2="-7.62" width="0.254" layer="94"/>
<wire x1="10.16" y1="-7.62" x2="-10.16" y2="-7.62" width="0.254" layer="94"/>
<wire x1="-10.16" y1="-7.62" x2="-10.16" y2="7.62" width="0.254" layer="94"/>
<text x="-10.16" y="8.89" size="1.778" layer="95">&gt;NAME</text>
<text x="-10.16" y="-10.16" size="1.778" layer="96">&gt;VALUE</text>
<pin name="ADDR0" x="-15.24" y="5.08" length="middle"/>
<pin name="ADDR1" x="-15.24" y="0" length="middle"/>
<pin name="ADDR2" x="-15.24" y="-5.08" length="middle"/>
</symbol>
</symbols>
<devicesets>
<deviceset name="DRIVER3" prefix="U" uservalue="no">
<gates>
<gate name="G$1" symbol="DRIVER3" x="0" y="0"/>
</gates>
<devices>
<device name="">
<technologies>
<technology name=""/>
</technologies>
</device>
</devices>
</deviceset>
<deviceset name="RECEIVER3" prefix="U" uservalue="no">
<gates>
<gate name="G$1" symbol="RECEIVER3" x="0" y="0"/>
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
<part name="U1" library="generic" deviceset="DRIVER3" device="" value="DRIVER"/>
<part name="U2" library="generic" deviceset="RECEIVER3" device="" value="RECEIVER"/>
</parts>
<sheets>
<sheet>
<plain>
</plain>
<instances>
<instance part="U1" gate="G$1" x="50.8" y="100"/>
<instance part="U2" gate="G$1" x="127" y="100"/>
</instances>
<busses>
<bus name="ADDR[2..0]">
<segment>
<wire x1="66.04" y1="100" x2="111.76" y2="100" width="0.762" layer="92"/>
<label x="78.74" y="101.6" size="1.778" layer="95"/>
</segment>
</bus>
</busses>
<nets>
</nets>
</sheet>
</sheets>
</schematic>
</drawing>
</eagle>
