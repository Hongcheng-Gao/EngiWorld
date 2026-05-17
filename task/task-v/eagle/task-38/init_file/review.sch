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
<symbol name="RES">
<wire x1="-2.54" y1="0.889" x2="2.54" y2="0.889" width="0.1524" layer="94"/>
<wire x1="2.54" y1="0.889" x2="2.54" y2="-0.889" width="0.1524" layer="94"/>
<wire x1="2.54" y1="-0.889" x2="-2.54" y2="-0.889" width="0.1524" layer="94"/>
<wire x1="-2.54" y1="-0.889" x2="-2.54" y2="0.889" width="0.1524" layer="94"/>
<text x="-3.81" y="1.4986" size="1.778" layer="95">&gt;NAME</text>
<text x="-3.81" y="-3.302" size="1.778" layer="96">&gt;VALUE</text>
<pin name="1" x="-5.08" y="0" visible="off" length="short" direction="pas" swaplevel="1"/>
<pin name="2" x="5.08" y="0" visible="off" length="short" direction="pas" swaplevel="1" rot="R180"/>
</symbol>
<symbol name="CAP">
<wire x1="-2.032" y1="-0.762" x2="2.032" y2="-0.762" width="0.1524" layer="94"/>
<wire x1="1.778" y1="-1.778" x2="-1.778" y2="-1.778" width="0.4064" layer="94"/>
<text x="1.524" y="0.381" size="1.778" layer="95">&gt;NAME</text>
<pin name="1" x="0" y="2.54" visible="off" length="short" direction="pas" swaplevel="1" rot="R270"/>
<pin name="2" x="0" y="-5.08" visible="off" length="short" direction="pas" swaplevel="1" rot="R90"/>
</symbol>
<symbol name="DIP8">
<wire x1="-7.62" y1="7.62" x2="7.62" y2="7.62" width="0.254" layer="94"/>
<wire x1="7.62" y1="7.62" x2="7.62" y2="-7.62" width="0.254" layer="94"/>
<wire x1="7.62" y1="-7.62" x2="-7.62" y2="-7.62" width="0.254" layer="94"/>
<wire x1="-7.62" y1="-7.62" x2="-7.62" y2="7.62" width="0.254" layer="94"/>
<text x="-7.62" y="8.89" size="1.778" layer="95">&gt;NAME</text>
<pin name="IN" x="-12.7" y="5.08" length="middle" direction="in"/>
<pin name="OUT" x="12.7" y="5.08" length="middle" direction="out" rot="R180"/>
<pin name="VCC" x="0" y="12.7" length="middle" direction="pwr" rot="R270"/>
<pin name="GND" x="0" y="-12.7" length="middle" direction="pwr" rot="R90"/>
<pin name="NC1" x="-12.7" y="-5.08" length="middle" direction="nc"/>
</symbol>
</symbols>
<devicesets>
<deviceset name="RES" prefix="R" uservalue="yes">
<gates>
<gate name="G$1" symbol="RES" x="0" y="0"/>
</gates>
<devices>
<device name="">
<technologies>
<technology name=""/>
</technologies>
</device>
</devices>
</deviceset>
<deviceset name="CAP" prefix="C" uservalue="yes">
<gates>
<gate name="G$1" symbol="CAP" x="0" y="0"/>
</gates>
<devices>
<device name="">
<technologies>
<technology name=""/>
</technologies>
</device>
</devices>
</deviceset>
<deviceset name="AMP" prefix="U" uservalue="no">
<gates>
<gate name="G$1" symbol="DIP8" x="0" y="0"/>
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
<part name="U1" library="simple" deviceset="AMP" device="" value="AMP"/>
<part name="R1" library="simple" deviceset="RES" device="" value="10k"/>
<part name="R2" library="simple" deviceset="RES" device="" value="1k"/>
<part name="C1" library="simple" deviceset="CAP" device="" value="100n"/>
</parts>
<sheets>
<sheet>
<plain>
</plain>
<instances>
<instance part="U1" gate="G$1" x="100" y="100"/>
<instance part="R1" gate="G$1" x="70" y="105.08"/>
<instance part="R2" gate="G$1" x="130" y="105.08"/>
<instance part="C1" gate="G$1" x="50" y="80"/>
</instances>
<busses>
</busses>
<nets>
<net name="IN" class="0">
<segment>
<pinref part="U1" gate="G$1" pin="IN"/>
<pinref part="R1" gate="G$1" pin="2"/>
<wire x1="75.08" y1="105.08" x2="87.3" y2="105.08" width="0.1524" layer="91"/>
</segment>
</net>
<net name="OUT" class="0">
<segment>
<pinref part="U1" gate="G$1" pin="OUT"/>
<pinref part="R2" gate="G$1" pin="1"/>
<wire x1="112.7" y1="105.08" x2="124.92" y2="105.08" width="0.1524" layer="91"/>
</segment>
</net>
<net name="C1_TOP" class="0">
<segment>
<pinref part="C1" gate="G$1" pin="1"/>
<wire x1="50" y1="82.54" x2="50" y2="85" width="0.1524" layer="91"/>
</segment>
</net>
</nets>
</sheet>
</sheets>
</schematic>
</drawing>
</eagle>
