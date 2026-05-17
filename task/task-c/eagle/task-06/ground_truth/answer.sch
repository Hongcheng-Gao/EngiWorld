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
<library name="v-reg">
<packages>
<package name="SOT223">
<description>&lt;b&gt;SOT-223&lt;/b&gt;</description>
<smd name="1" x="-2.3" y="-3.1" dx="1.5" dy="1.5" layer="1"/>
<smd name="2" x="0" y="-3.1" dx="1.5" dy="1.5" layer="1"/>
<smd name="3" x="2.3" y="-3.1" dx="1.5" dy="1.5" layer="1"/>
<smd name="4" x="0" y="3.1" dx="3.5" dy="1.5" layer="1"/>
</package>
</packages>
<symbols>
<symbol name="AMS1117">
<wire x1="-7.62" y1="5.08" x2="7.62" y2="5.08" width="0.254" layer="94"/>
<wire x1="7.62" y1="5.08" x2="7.62" y2="-5.08" width="0.254" layer="94"/>
<wire x1="7.62" y1="-5.08" x2="-7.62" y2="-5.08" width="0.254" layer="94"/>
<wire x1="-7.62" y1="-5.08" x2="-7.62" y2="5.08" width="0.254" layer="94"/>
<text x="-7.62" y="6.35" size="1.778" layer="95">&gt;NAME</text>
<text x="-7.62" y="-7.62" size="1.778" layer="96">&gt;VALUE</text>
<pin name="VIN" x="-12.7" y="2.54" length="middle"/>
<pin name="GND" x="0" y="-10.16" length="middle" rot="R90"/>
<pin name="VOUT" x="12.7" y="2.54" length="middle" rot="R180"/>
</symbol>
</symbols>
<devicesets>
<deviceset name="AMS1117-5.0" prefix="U" uservalue="no">
<description>&lt;b&gt;AMS1117-5.0 5V LDO Regulator (SOT-223)&lt;/b&gt;&lt;br/&gt;
Replaces LM7805: pin IN maps to pad 3, GND maps to pad 1+4(tab), OUT maps to pad 2.</description>
<gates>
<gate name="G$1" symbol="AMS1117" x="0" y="0"/>
</gates>
<devices>
<device name="SOT223" package="SOT223">
<connects>
<connect gate="G$1" pin="VIN" pad="3"/>
<connect gate="G$1" pin="GND" pad="1 4"/>
<connect gate="G$1" pin="VOUT" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
</devices>
</deviceset>
</devicesets>
</library>
<library name="rcl">
<packages>
<package name="C050-025X075">
<description>&lt;b&gt;CAPACITOR&lt;/b&gt; 2.5mm pitch</description>
<pad name="1" x="-2.54" y="0" drill="0.8" shape="octagon"/>
<pad name="2" x="2.54" y="0" drill="0.8" shape="octagon"/>
</package>
</packages>
<symbols>
<symbol name="C-EU">
<wire x1="-2.032" y1="-0.762" x2="2.032" y2="-0.762" width="0.1524" layer="94"/>
<wire x1="1.778" y1="-1.778" x2="-1.778" y2="-1.778" width="0.4064" layer="94"/>
<text x="1.524" y="0.381" size="1.778" layer="95">&gt;NAME</text>
<text x="1.524" y="-4.699" size="1.778" layer="96">&gt;VALUE</text>
<pin name="1" x="0" y="2.54" visible="off" length="short" direction="pas" swaplevel="1" rot="R270"/>
<pin name="2" x="0" y="-5.08" visible="off" length="short" direction="pas" swaplevel="1" rot="R90"/>
</symbol>
</symbols>
<devicesets>
<deviceset name="C-EU" prefix="C" uservalue="yes">
<description>&lt;b&gt;CAPACITOR&lt;/b&gt;, European symbol</description>
<gates>
<gate name="G$1" symbol="C-EU" x="0" y="0"/>
</gates>
<devices>
<device name="050-025X075" package="C050-025X075">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
</devices>
</deviceset>
</devicesets>
</library>
<library name="supply1">
<packages>
</packages>
<symbols>
<symbol name="GND">
<wire x1="-1.905" y1="0" x2="1.905" y2="0" width="0.254" layer="94"/>
<text x="-2.54" y="-0.254" size="1.778" layer="96" align="top-left">&gt;VALUE</text>
<pin name="GND" x="0" y="2.54" visible="off" length="short" direction="sup" rot="R270"/>
</symbol>
<symbol name="VCC">
<wire x1="1.27" y1="-1.905" x2="0" y2="0" width="0.254" layer="94"/>
<wire x1="0" y1="0" x2="-1.27" y2="-1.905" width="0.254" layer="94"/>
<text x="-2.54" y="-2.54" size="1.778" layer="96">&gt;VALUE</text>
<pin name="VCC" x="0" y="-2.54" visible="off" length="short" direction="sup" rot="R90"/>
</symbol>
</symbols>
<devicesets>
<deviceset name="GND" prefix="GND">
<description>&lt;b&gt;SUPPLY SYMBOL&lt;/b&gt;</description>
<gates>
<gate name="1" symbol="GND" x="0" y="0"/>
</gates>
<devices>
<device name="">
<technologies>
<technology name=""/>
</technologies>
</device>
</devices>
</deviceset>
<deviceset name="VCC" prefix="P+">
<description>&lt;b&gt;SUPPLY SYMBOL&lt;/b&gt;</description>
<gates>
<gate name="VCC" symbol="VCC" x="0" y="0"/>
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
<part name="U1" library="v-reg" deviceset="AMS1117-5.0" device="SOT223" value="AMS1117-5.0"/>
<part name="C1" library="rcl" deviceset="C-EU" device="050-025X075" value="100n"/>
<part name="C2" library="rcl" deviceset="C-EU" device="050-025X075" value="10u"/>
<part name="VIN1" library="supply1" deviceset="VCC" device=""/>
<part name="GND1" library="supply1" deviceset="GND" device=""/>
<part name="GND2" library="supply1" deviceset="GND" device=""/>
</parts>
<sheets>
<sheet>
<plain>
</plain>
<instances>
<instance part="U1" gate="G$1" x="100.33" y="101.6"/>
<instance part="C1" gate="G$1" x="76.2" y="96.52"/>
<instance part="C2" gate="G$1" x="124.46" y="96.52"/>
<instance part="VIN1" gate="VCC" x="76.2" y="111.76"/>
<instance part="GND1" gate="1" x="76.2" y="86.36"/>
<instance part="GND2" gate="1" x="124.46" y="86.36"/>
</instances>
<busses>
</busses>
<nets>
<net name="VIN" class="0">
<segment>
<pinref part="U1" gate="G$1" pin="VIN"/>
<pinref part="C1" gate="G$1" pin="1"/>
<pinref part="VIN1" gate="VCC" pin="VCC"/>
<wire x1="76.2" y1="104.14" x2="76.2" y2="109.22" width="0.1524" layer="91"/>
<wire x1="76.2" y1="104.14" x2="87.63" y2="104.14" width="0.1524" layer="91"/>
</segment>
</net>
<net name="GND" class="0">
<segment>
<pinref part="U1" gate="G$1" pin="GND"/>
<pinref part="C1" gate="G$1" pin="2"/>
<pinref part="C2" gate="G$1" pin="2"/>
<pinref part="GND1" gate="1" pin="GND"/>
<pinref part="GND2" gate="1" pin="GND"/>
<wire x1="100.33" y1="91.44" x2="100.33" y2="88.9" width="0.1524" layer="91"/>
<wire x1="76.2" y1="88.9" x2="76.2" y2="91.44" width="0.1524" layer="91"/>
<wire x1="124.46" y1="88.9" x2="124.46" y2="91.44" width="0.1524" layer="91"/>
</segment>
</net>
<net name="VOUT" class="0">
<segment>
<pinref part="U1" gate="G$1" pin="VOUT"/>
<pinref part="C2" gate="G$1" pin="1"/>
<wire x1="113.03" y1="104.14" x2="124.46" y2="104.14" width="0.1524" layer="91"/>
</segment>
</net>
</nets>
</sheet>
</sheets>
</schematic>
</drawing>
</eagle>
