<?xml version='1.0' encoding='utf-8'?>
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
<library name="rcl">
<packages>
<package name="R0402">
<smd name="1" x="-0.5" y="0" dx="0.5" dy="0.6" layer="1" />
<smd name="2" x="0.5" y="0" dx="0.5" dy="0.6" layer="1" />
</package>
<package name="C0402">
<smd name="1" x="-0.5" y="0" dx="0.5" dy="0.6" layer="1" />
<smd name="2" x="0.5" y="0" dx="0.5" dy="0.6" layer="1" />
</package>
</packages>
<symbols>
<symbol name="R-EU">
<wire x1="-2.54" y1="-0.889" x2="2.54" y2="-0.889" width="0.254" layer="94" />
<wire x1="2.54" y1="0.889" x2="-2.54" y2="0.889" width="0.254" layer="94" />
<wire x1="2.54" y1="-0.889" x2="2.54" y2="0.889" width="0.254" layer="94" />
<wire x1="-2.54" y1="-0.889" x2="-2.54" y2="0.889" width="0.254" layer="94" />
<pin name="1" x="-5.08" y="0" visible="off" length="short" direction="pas" swaplevel="1" />
<pin name="2" x="5.08" y="0" visible="off" length="short" direction="pas" swaplevel="1" rot="R180" />
</symbol>
<symbol name="C-EU">
<wire x1="0" y1="0" x2="0" y2="-0.508" width="0.1524" layer="94" />
<wire x1="0" y1="-2.54" x2="0" y2="-2.032" width="0.1524" layer="94" />
<pin name="1" x="0" y="2.54" visible="off" length="short" direction="pas" swaplevel="1" rot="R270" />
<pin name="2" x="0" y="-5.08" visible="off" length="short" direction="pas" swaplevel="1" rot="R90" />
</symbol>
</symbols>
<devicesets>
<deviceset name="R-EU_" prefix="R" uservalue="yes">
<gates>
<gate name="G$1" symbol="R-EU" x="0" y="0" />
</gates>
<devices>
<device name="R0402" package="R0402">
<connects>
<connect gate="G$1" pin="1" pad="1" />
<connect gate="G$1" pin="2" pad="2" />
</connects>
<technologies>
<technology name="" />
</technologies>
</device>
</devices>
</deviceset>
<deviceset name="C-EU" prefix="C" uservalue="yes">
<gates>
<gate name="G$1" symbol="C-EU" x="0" y="0" />
</gates>
<devices>
<device name="C0402" package="C0402">
<connects>
<connect gate="G$1" pin="1" pad="1" />
<connect gate="G$1" pin="2" pad="2" />
</connects>
<technologies>
<technology name="" />
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
<class number="0" name="default" width="0" drill="0">
</class>
</classes>
<parts>
<part name="C1" library="rcl" deviceset="C-EU" device="C0402" value="100n" />
<part name="C2" library="rcl" deviceset="C-EU" device="C0402" value="100n" />
<part name="R1" library="rcl" deviceset="R-EU_" device="R0402" value="10k" />
<part name="R2" library="rcl" deviceset="R-EU_" device="R0402" value="10k" />
<part name="R_TIE" library="rcl" deviceset="R-EU_" device="R0402" value="0R" /></parts>
<sheets>
<sheet>
<plain>
</plain>
<instances>
<instance part="C1" gate="G$1" x="20" y="40" />
<instance part="C2" gate="G$1" x="40" y="40" />
<instance part="R1" gate="G$1" x="60" y="40" />
<instance part="R2" gate="G$1" x="80" y="40" />
<instance part="R_TIE" gate="G$1" x="100" y="40" /></instances>
<busses>
</busses>
<nets>
<net name="AGND" class="0">
<segment>
<pinref part="C1" gate="G$1" pin="2" />
<pinref part="C2" gate="G$1" pin="2" />
<wire x1="20" y1="34.92" x2="40" y2="34.92" width="0.1524" layer="91" />
</segment>
<segment><pinref part="R_TIE" gate="G$1" pin="1" /><wire x1="94.92" y1="40" x2="92.0" y2="40" width="0.1524" layer="91" /></segment></net>
<net name="DGND" class="0">
<segment>
<pinref part="R1" gate="G$1" pin="2" />
<pinref part="R2" gate="G$1" pin="2" />
<wire x1="65.08" y1="40" x2="74.92" y2="40" width="0.1524" layer="91" />
</segment>
<segment><pinref part="R_TIE" gate="G$1" pin="2" /><wire x1="105.08" y1="40" x2="108.0" y2="40" width="0.1524" layer="91" /></segment></net>
</nets>
</sheet>
</sheets>
</schematic>
</drawing>
</eagle>