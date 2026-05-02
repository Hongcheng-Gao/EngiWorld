<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE eagle SYSTEM "eagle.dtd">
<eagle version="7.7.0">
<drawing>
<settings>
<setting alwaysvectorfont="no"/>
<setting verticaltext="up"/>
</settings>
<grid distance="0.1" unitdist="inch" unit="inch" style="lines" multiple="1" display="yes" altdistance="0.01" altunitdist="inch" altunit="inch"/>
<layers>
<layer number="91" name="Nets" color="2" fill="1" visible="yes" active="yes"/>
<layer number="92" name="Busses" color="1" fill="1" visible="yes" active="yes"/>
<layer number="93" name="Pins" color="2" fill="1" visible="yes" active="yes"/>
<layer number="94" name="Symbols" color="4" fill="1" visible="yes" active="yes"/>
<layer number="95" name="Names" color="7" fill="1" visible="yes" active="yes"/>
<layer number="96" name="Values" color="7" fill="1" visible="yes" active="yes"/>
</layers>
<schematic xreflabel="%F%N/%S.%C%R" xrefpart="/%S.%C%R">
<libraries>
</libraries>
<attributes>
</attributes>
<variantdefs>
</variantdefs>
<classes>
<class number="0" name="default" width="0" drill="0">
</class>
<class number="1" name="SIG" width="0.15" drill="0">
</class>
<class number="2" name="PWR" width="0.4" drill="0">
</class>
<class number="3" name="HSPEED" width="0.2" drill="0">
</class>
</classes>
<parts>
</parts>
<sheets>
<sheet>
<plain>
</plain>
<instances>
</instances>
<busses>
</busses>
<nets>
<net name="VCC" class="0">
<segment>
<wire x1="0" y1="0" x2="10" y2="0" width="0.1524" layer="91"/>
<label x="5" y="0" size="1.778" layer="95"/>
</segment>
</net>
<net name="GND" class="0">
<segment>
<wire x1="0" y1="-5" x2="10" y2="-5" width="0.1524" layer="91"/>
<label x="5" y="-5" size="1.778" layer="95"/>
</segment>
</net>
<net name="CLK" class="0">
<segment>
<wire x1="0" y1="-10" x2="10" y2="-10" width="0.1524" layer="91"/>
<label x="5" y="-10" size="1.778" layer="95"/>
</segment>
</net>
<net name="DATA" class="0">
<segment>
<wire x1="0" y1="-15" x2="10" y2="-15" width="0.1524" layer="91"/>
<label x="5" y="-15" size="1.778" layer="95"/>
</segment>
</net>
<net name="RESET" class="0">
<segment>
<wire x1="0" y1="-20" x2="10" y2="-20" width="0.1524" layer="91"/>
<label x="5" y="-20" size="1.778" layer="95"/>
</segment>
</net>
</nets>
</sheet>
</sheets>
</schematic>
</drawing>
</eagle>
