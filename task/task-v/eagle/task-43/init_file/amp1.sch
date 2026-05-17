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
<library name="linear">
<packages></packages>
<symbols></symbols>
<devicesets>
<deviceset name="LM358" prefix="U">
<gates><gate name="A" symbol="OPAMP" x="0" y="0"/></gates>
<devices><device name="" package=""></device></devices>
</deviceset>
</devicesets>
</library>
<library name="rcl">
<packages></packages>
<symbols></symbols>
<devicesets>
<deviceset name="R-EU_" prefix="R" uservalue="yes">
<gates><gate name="G$1" symbol="R-EU" x="0" y="0"/></gates>
<devices><device name="0207/10" package=""></device></devices>
</deviceset>
<deviceset name="C-EU" prefix="C" uservalue="yes">
<gates><gate name="G$1" symbol="C-EU" x="0" y="0"/></gates>
<devices><device name="025-025X050" package=""></device></devices>
</deviceset>
</devicesets>
</library>
</libraries>
<attributes></attributes>
<variantdefs></variantdefs>
<classes>
<class number="0" name="default" width="0" drill="0"/>
</classes>
<parts>
<part name="U1" library="linear" deviceset="LM358" device=""/>
<part name="R1" library="rcl" deviceset="R-EU_" device="0207/10" value="10k"/>
<part name="C1" library="rcl" deviceset="C-EU" device="025-025X050" value="100n"/>
</parts>
<sheets>
<sheet>
<plain></plain>
<instances>
<instance part="U1" gate="A" x="50.8" y="50.8"/>
<instance part="R1" gate="G$1" x="40.64" y="45.72" rot="R90"/>
<instance part="C1" gate="G$1" x="60.96" y="45.72"/>
</instances>
<busses></busses>
<nets>
<net name="IN" class="0">
<segment>
<pinref part="U1" gate="A" pin="IN+"/>
<pinref part="R1" gate="G$1" pin="1"/>
<wire x1="40.64" y1="45.72" x2="50.8" y2="45.72" width="0.1524" layer="91"/>
</segment>
</net>
<net name="OUT" class="0">
<segment>
<pinref part="U1" gate="A" pin="OUT"/>
<pinref part="C1" gate="G$1" pin="1"/>
<wire x1="55.88" y1="50.8" x2="60.96" y2="50.8" width="0.1524" layer="91"/>
</segment>
</net>
</nets>
</sheet>
</sheets>
</schematic>
</drawing>
</eagle>
