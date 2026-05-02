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
<deviceset name="*555" prefix="IC">
<gates><gate name="G$1" symbol="555N" x="0" y="0"/></gates>
<devices><device name="N" package=""></device></devices>
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
<library name="led">
<packages></packages>
<symbols></symbols>
<devicesets>
<deviceset name="LED" prefix="LED" uservalue="yes">
<gates><gate name="G$1" symbol="LED" x="0" y="0"/></gates>
<devices><device name="3MM" package=""></device></devices>
</deviceset>
</devicesets>
</library>
<library name="supply1">
<packages></packages>
<symbols></symbols>
<devicesets>
<deviceset name="GND" prefix="GND">
<gates><gate name="1" symbol="GND" x="0" y="0"/></gates>
<devices><device name=""></device></devices>
</deviceset>
<deviceset name="VCC" prefix="P+">
<gates><gate name="VCC" symbol="VCC" x="0" y="0"/></gates>
<devices><device name=""></device></devices>
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
<part name="IC1" library="linear" deviceset="*555" device="N"/>
<part name="R1" library="rcl" deviceset="R-EU_" device="0207/10" value="10k"/>
<part name="R2" library="rcl" deviceset="R-EU_" device="0207/10" value="100k"/>
<part name="C1" library="rcl" deviceset="C-EU" device="025-025X050" value="10u"/>
<part name="C2" library="rcl" deviceset="C-EU" device="025-025X050" value="100n"/>
<part name="LED1" library="led" deviceset="LED" device="3MM" value="RED"/>
<part name="R3" library="rcl" deviceset="R-EU_" device="0207/10" value="330"/>
<part name="VCC1" library="supply1" deviceset="VCC" device=""/>
<part name="GND1" library="supply1" deviceset="GND" device=""/>
<part name="GND2" library="supply1" deviceset="GND" device=""/>
</parts>
<sheets>
<sheet>
<plain></plain>
<instances>
<instance part="IC1" gate="G$1" x="50.8" y="50.8"/>
<instance part="R1" gate="G$1" x="30.48" y="68.58" rot="R90"/>
<instance part="R2" gate="G$1" x="30.48" y="55.88" rot="R90"/>
<instance part="C1" gate="G$1" x="30.48" y="40.64"/>
<instance part="C2" gate="G$1" x="76.2" y="55.88"/>
<instance part="LED1" gate="G$1" x="86.36" y="50.8" rot="R270"/>
<instance part="R3" gate="G$1" x="86.36" y="60.96" rot="R90"/>
<instance part="VCC1" gate="VCC" x="50.8" y="81.28"/>
<instance part="GND1" gate="1" x="30.48" y="27.94"/>
<instance part="GND2" gate="1" x="86.36" y="35.56"/>
</instances>
<busses></busses>
<nets>
<net name="VCC" class="0">
<segment>
<pinref part="VCC1" gate="VCC" pin="VCC"/>
<pinref part="IC1" gate="G$1" pin="VCC"/>
<pinref part="IC1" gate="G$1" pin="RESET"/>
<pinref part="C2" gate="G$1" pin="1"/>
<pinref part="R1" gate="G$1" pin="2"/>
<pinref part="R3" gate="G$1" pin="2"/>
<wire x1="50.8" y1="78.74" x2="50.8" y2="66.04" width="0.1524" layer="91"/>
</segment>
</net>
<net name="GND" class="0">
<segment>
<pinref part="GND1" gate="1" pin="GND"/>
<pinref part="IC1" gate="G$1" pin="GND"/>
<pinref part="C1" gate="G$1" pin="2"/>
<pinref part="C2" gate="G$1" pin="2"/>
<pinref part="LED1" gate="G$1" pin="C"/>
<pinref part="GND2" gate="1" pin="GND"/>
<wire x1="30.48" y1="30.48" x2="30.48" y2="35.56" width="0.1524" layer="91"/>
</segment>
</net>
<net name="OUT" class="0">
<segment>
<pinref part="IC1" gate="G$1" pin="OUT"/>
<pinref part="R3" gate="G$1" pin="1"/>
<wire x1="66.04" y1="55.88" x2="86.36" y2="55.88" width="0.1524" layer="91"/>
</segment>
</net>
<net name="THRES" class="0">
<segment>
<pinref part="IC1" gate="G$1" pin="THR"/>
<pinref part="IC1" gate="G$1" pin="TRIG"/>
<pinref part="R2" gate="G$1" pin="2"/>
<pinref part="C1" gate="G$1" pin="1"/>
<wire x1="30.48" y1="45.72" x2="30.48" y2="50.8" width="0.1524" layer="91"/>
</segment>
</net>
<net name="DISCH" class="0">
<segment>
<pinref part="IC1" gate="G$1" pin="DIS"/>
<pinref part="R1" gate="G$1" pin="1"/>
<pinref part="R2" gate="G$1" pin="1"/>
<wire x1="30.48" y1="60.96" x2="30.48" y2="63.5" width="0.1524" layer="91"/>
</segment>
</net>
</nets>
</sheet>
</sheets>
</schematic>
</drawing>
</eagle>
