<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE eagle SYSTEM "eagle.dtd">
<eagle version="6.1">
<drawing>
<settings>
<setting alwaysvectorfont="yes"/>
<setting verticaltext="up"/>
</settings>
<grid distance="0.1" unitdist="inch" unit="inch" style="lines" multiple="1" display="no" altdistance="0.01" altunitdist="inch" altunit="inch"/>
<layers>
<layer number="1" name="Top" color="4" fill="1" visible="no" active="no"/>
<layer number="16" name="Bottom" color="1" fill="1" visible="no" active="no"/>
<layer number="17" name="Pads" color="2" fill="1" visible="no" active="no"/>
<layer number="18" name="Vias" color="2" fill="1" visible="no" active="no"/>
<layer number="19" name="Unrouted" color="6" fill="1" visible="no" active="no"/>
<layer number="20" name="Dimension" color="15" fill="1" visible="no" active="no"/>
<layer number="21" name="tPlace" color="7" fill="1" visible="no" active="no"/>
<layer number="22" name="bPlace" color="7" fill="1" visible="no" active="no"/>
<layer number="23" name="tOrigins" color="15" fill="1" visible="no" active="no"/>
<layer number="24" name="bOrigins" color="15" fill="1" visible="no" active="no"/>
<layer number="25" name="tNames" color="7" fill="1" visible="no" active="no"/>
<layer number="26" name="bNames" color="7" fill="1" visible="no" active="no"/>
<layer number="27" name="tValues" color="7" fill="1" visible="no" active="no"/>
<layer number="28" name="bValues" color="7" fill="1" visible="no" active="no"/>
<layer number="29" name="tStop" color="7" fill="3" visible="no" active="no"/>
<layer number="30" name="bStop" color="7" fill="6" visible="no" active="no"/>
<layer number="31" name="tCream" color="7" fill="4" visible="no" active="no"/>
<layer number="32" name="bCream" color="7" fill="5" visible="no" active="no"/>
<layer number="33" name="tFinish" color="6" fill="3" visible="no" active="no"/>
<layer number="34" name="bFinish" color="6" fill="6" visible="no" active="no"/>
<layer number="35" name="tGlue" color="7" fill="4" visible="no" active="no"/>
<layer number="36" name="bGlue" color="7" fill="5" visible="no" active="no"/>
<layer number="37" name="tTest" color="7" fill="1" visible="no" active="no"/>
<layer number="38" name="bTest" color="7" fill="1" visible="no" active="no"/>
<layer number="39" name="tKeepout" color="4" fill="11" visible="no" active="no"/>
<layer number="40" name="bKeepout" color="1" fill="11" visible="no" active="no"/>
<layer number="41" name="tRestrict" color="4" fill="10" visible="no" active="no"/>
<layer number="42" name="bRestrict" color="1" fill="10" visible="no" active="no"/>
<layer number="43" name="vRestrict" color="2" fill="10" visible="no" active="no"/>
<layer number="44" name="Drills" color="7" fill="1" visible="no" active="no"/>
<layer number="45" name="Holes" color="7" fill="1" visible="no" active="no"/>
<layer number="46" name="Milling" color="3" fill="1" visible="no" active="no"/>
<layer number="47" name="Measures" color="7" fill="1" visible="no" active="no"/>
<layer number="48" name="Document" color="7" fill="1" visible="no" active="no"/>
<layer number="49" name="Reference" color="7" fill="1" visible="no" active="no"/>
<layer number="51" name="tDocu" color="7" fill="1" visible="no" active="no"/>
<layer number="52" name="bDocu" color="7" fill="1" visible="no" active="no"/>
<layer number="91" name="Nets" color="2" fill="1" visible="yes" active="yes"/>
<layer number="92" name="Busses" color="1" fill="1" visible="yes" active="yes"/>
<layer number="93" name="Pins" color="2" fill="1" visible="no" active="yes"/>
<layer number="94" name="Symbols" color="4" fill="1" visible="yes" active="yes"/>
<layer number="95" name="Names" color="7" fill="1" visible="yes" active="yes"/>
<layer number="96" name="Values" color="7" fill="1" visible="yes" active="yes"/>
<layer number="97" name="Info" color="7" fill="1" visible="yes" active="yes"/>
<layer number="98" name="Guide" color="6" fill="1" visible="yes" active="yes"/>
</layers>
<schematic xreflabel="%F%N/%S.%C%R" xrefpart="/%S.%C%R">
<libraries>
<library name="frames">
<packages>
</packages>
<symbols>
<symbol name="DINA4_P">
<wire x1="0" y1="0" x2="180.34" y2="0" width="0.4064" layer="94"/>
<wire x1="180.34" y1="0" x2="180.34" y2="264.16" width="0.4064" layer="94"/>
<wire x1="180.34" y1="264.16" x2="0" y2="264.16" width="0.4064" layer="94"/>
<wire x1="0" y1="264.16" x2="0" y2="0" width="0.4064" layer="94"/>
</symbol>
<symbol name="DOCFIELD">
<wire x1="0" y1="0" x2="71.12" y2="0" width="0.254" layer="94"/>
<wire x1="101.6" y1="15.24" x2="87.63" y2="15.24" width="0.254" layer="94"/>
<wire x1="0" y1="0" x2="0" y2="5.08" width="0.254" layer="94"/>
<wire x1="0" y1="5.08" x2="71.12" y2="5.08" width="0.254" layer="94"/>
<wire x1="0" y1="5.08" x2="0" y2="15.24" width="0.254" layer="94"/>
<wire x1="101.6" y1="15.24" x2="101.6" y2="5.08" width="0.254" layer="94"/>
<wire x1="71.12" y1="5.08" x2="71.12" y2="0" width="0.254" layer="94"/>
<wire x1="71.12" y1="5.08" x2="87.63" y2="5.08" width="0.254" layer="94"/>
<wire x1="71.12" y1="0" x2="101.6" y2="0" width="0.254" layer="94"/>
<wire x1="87.63" y1="15.24" x2="87.63" y2="5.08" width="0.254" layer="94"/>
<wire x1="87.63" y1="15.24" x2="0" y2="15.24" width="0.254" layer="94"/>
<wire x1="87.63" y1="5.08" x2="101.6" y2="5.08" width="0.254" layer="94"/>
<wire x1="101.6" y1="5.08" x2="101.6" y2="0" width="0.254" layer="94"/>
<wire x1="0" y1="15.24" x2="0" y2="22.86" width="0.254" layer="94"/>
<wire x1="101.6" y1="35.56" x2="0" y2="35.56" width="0.254" layer="94"/>
<wire x1="101.6" y1="35.56" x2="101.6" y2="22.86" width="0.254" layer="94"/>
<wire x1="0" y1="22.86" x2="101.6" y2="22.86" width="0.254" layer="94"/>
<wire x1="0" y1="22.86" x2="0" y2="35.56" width="0.254" layer="94"/>
<wire x1="101.6" y1="22.86" x2="101.6" y2="15.24" width="0.254" layer="94"/>
<text x="1.27" y="1.27" size="2.54" layer="94" font="vector">Date:</text>
<text x="12.7" y="1.27" size="2.54" layer="94" font="vector">&gt;LAST_DATE_TIME</text>
<text x="72.39" y="1.27" size="2.54" layer="94" font="vector">Sheet:</text>
<text x="86.36" y="1.27" size="2.54" layer="94" font="vector">&gt;SHEET</text>
<text x="88.9" y="11.43" size="2.54" layer="94" font="vector">REV:</text>
<text x="1.27" y="19.05" size="2.54" layer="94" font="vector">TITLE:</text>
<text x="1.27" y="11.43" size="2.54" layer="94" font="vector">Document Number:</text>
<text x="17.78" y="19.05" size="2.54" layer="94" font="vector">&gt;DRAWING_NAME</text>
</symbol>
</symbols>
<devicesets>
<deviceset name="DINA4_P" prefix="F" uservalue="yes">
<description>Frame&lt;p&gt;
DIN A4 format &lt;b&gt;portrait&lt;/b&gt; with extra doc field</description>
<gates>
<gate name="G$1" symbol="DINA4_P" x="0" y="0"/>
<gate name="G$2" symbol="DOCFIELD" x="78.74" y="0" addlevel="must"/>
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
<library name="microchip">
<packages>
<package name="SO-18W">
<description>Small Outline Wide Plastic Gull Wing (300 mil Body) : SO</description>
<wire x1="-5.6642" y1="-3.6957" x2="5.6388" y2="-3.6957" width="0.127" layer="21"/>
<wire x1="5.6388" y1="-3.6957" x2="5.6388" y2="3.6703" width="0.127" layer="21"/>
<wire x1="5.6388" y1="3.6703" x2="-5.6642" y2="3.6703" width="0.127" layer="21"/>
<wire x1="-5.6642" y1="3.6703" x2="-5.6642" y2="-3.6957" width="0.127" layer="21"/>
<circle x="-4.6736" y="-2.7813" radius="0.5334" width="0.127" layer="21"/>
<smd name="1" x="-5.08" y="-4.7879" dx="0.762" dy="1.143" layer="1"/>
<smd name="2" x="-3.81" y="-4.7879" dx="0.762" dy="1.143" layer="1"/>
<smd name="3" x="-2.54" y="-4.7879" dx="0.762" dy="1.143" layer="1"/>
<smd name="4" x="-1.27" y="-4.7879" dx="0.762" dy="1.143" layer="1"/>
<smd name="5" x="0" y="-4.7879" dx="0.762" dy="1.143" layer="1"/>
<smd name="6" x="1.27" y="-4.7879" dx="0.762" dy="1.143" layer="1"/>
<smd name="7" x="2.54" y="-4.7879" dx="0.762" dy="1.143" layer="1"/>
<smd name="8" x="3.81" y="-4.7879" dx="0.762" dy="1.143" layer="1"/>
<smd name="9" x="5.08" y="-4.7879" dx="0.762" dy="1.143" layer="1"/>
<smd name="10" x="5.08" y="4.7879" dx="0.762" dy="1.143" layer="1"/>
<smd name="11" x="3.81" y="4.7879" dx="0.762" dy="1.143" layer="1"/>
<smd name="12" x="2.54" y="4.7879" dx="0.762" dy="1.143" layer="1"/>
<smd name="13" x="1.27" y="4.7879" dx="0.762" dy="1.143" layer="1"/>
<smd name="14" x="0" y="4.7879" dx="0.762" dy="1.143" layer="1"/>
<smd name="15" x="-1.27" y="4.7879" dx="0.762" dy="1.143" layer="1"/>
<smd name="16" x="-2.54" y="4.7879" dx="0.762" dy="1.143" layer="1"/>
<smd name="17" x="-3.81" y="4.7879" dx="0.762" dy="1.143" layer="1"/>
<smd name="18" x="-5.08" y="4.7879" dx="0.762" dy="1.143" layer="1"/>
<text x="-3.81" y="0.9779" size="1.778" layer="25" ratio="10">&gt;NAME</text>
<text x="-3.81" y="-1.5621" size="1.778" layer="27" ratio="10">&gt;VALUE</text>
<rectangle x1="4.8768" y1="3.7211" x2="5.2832" y2="5.0673" layer="51"/>
<rectangle x1="3.6068" y1="3.7211" x2="4.0132" y2="5.0673" layer="51"/>
<rectangle x1="2.3368" y1="3.7211" x2="2.7432" y2="5.0673" layer="51"/>
<rectangle x1="1.0668" y1="3.7211" x2="1.4732" y2="5.0673" layer="51"/>
<rectangle x1="-0.2032" y1="3.7211" x2="0.2032" y2="5.0673" layer="51"/>
<rectangle x1="-1.4732" y1="3.7211" x2="-1.0668" y2="5.0673" layer="51"/>
<rectangle x1="-2.7432" y1="3.7211" x2="-2.3368" y2="5.0673" layer="51"/>
<rectangle x1="-4.0132" y1="3.7211" x2="-3.6068" y2="5.0673" layer="51"/>
<rectangle x1="-5.2832" y1="3.7211" x2="-4.8768" y2="5.0673" layer="51"/>
<rectangle x1="-5.2832" y1="-5.0927" x2="-4.8768" y2="-3.7465" layer="51"/>
<rectangle x1="-4.0132" y1="-5.0927" x2="-3.6068" y2="-3.7465" layer="51"/>
<rectangle x1="-2.7432" y1="-5.0927" x2="-2.3368" y2="-3.7465" layer="51"/>
<rectangle x1="-1.4732" y1="-5.0927" x2="-1.0668" y2="-3.7465" layer="51"/>
<rectangle x1="-0.2032" y1="-5.0927" x2="0.2032" y2="-3.7465" layer="51"/>
<rectangle x1="1.0668" y1="-5.0927" x2="1.4732" y2="-3.7465" layer="51"/>
<rectangle x1="2.3368" y1="-5.0927" x2="2.7432" y2="-3.7465" layer="51"/>
<rectangle x1="3.6068" y1="-5.0927" x2="4.0132" y2="-3.7465" layer="51"/>
<rectangle x1="4.8768" y1="-5.0927" x2="5.2832" y2="-3.7465" layer="51"/>
</package>
<package name="DIL18">
<description>Plastic Dual In Line : P</description>
<wire x1="-11.684" y1="-0.635" x2="-11.684" y2="-2.54" width="0.127" layer="21"/>
<wire x1="-11.684" y1="-0.635" x2="-11.684" y2="0.635" width="0.127" layer="21" curve="180"/>
<wire x1="11.684" y1="-2.54" x2="-11.684" y2="-2.54" width="0.127" layer="21"/>
<wire x1="11.684" y1="-2.54" x2="11.684" y2="2.54" width="0.127" layer="21"/>
<wire x1="-11.684" y1="2.54" x2="11.684" y2="2.54" width="0.127" layer="21"/>
<wire x1="-11.684" y1="2.54" x2="-11.684" y2="0.635" width="0.127" layer="21"/>
<pad name="1" x="-10.16" y="-3.81" drill="0.8128" diameter="1.6002"/>
<pad name="2" x="-7.62" y="-3.81" drill="0.8128" diameter="1.6002" shape="octagon"/>
<pad name="3" x="-5.08" y="-3.81" drill="0.8128" diameter="1.6002" shape="octagon"/>
<pad name="4" x="-2.54" y="-3.81" drill="0.8128" diameter="1.6002" shape="octagon"/>
<pad name="5" x="0" y="-3.81" drill="0.8128" diameter="1.6002" shape="octagon"/>
<pad name="6" x="2.54" y="-3.81" drill="0.8128" diameter="1.6002" shape="octagon"/>
<pad name="7" x="5.08" y="-3.81" drill="0.8128" diameter="1.6002" shape="octagon"/>
<pad name="8" x="7.62" y="-3.81" drill="0.8128" diameter="1.6002" shape="octagon"/>
<pad name="9" x="10.16" y="-3.81" drill="0.8128" diameter="1.6002" shape="octagon"/>
<pad name="10" x="10.16" y="3.81" drill="0.8128" diameter="1.6002" shape="octagon"/>
<pad name="11" x="7.62" y="3.81" drill="0.8128" diameter="1.6002" shape="octagon"/>
<pad name="12" x="5.08" y="3.81" drill="0.8128" diameter="1.6002" shape="octagon"/>
<pad name="13" x="2.54" y="3.81" drill="0.8128" diameter="1.6002" shape="octagon"/>
<pad name="14" x="0" y="3.81" drill="0.8128" diameter="1.6002" shape="octagon"/>
<pad name="15" x="-2.54" y="3.81" drill="0.8128" diameter="1.6002" shape="octagon"/>
<pad name="16" x="-5.08" y="3.81" drill="0.8128" diameter="1.6002" shape="octagon"/>
<pad name="17" x="-7.62" y="3.81" drill="0.8128" diameter="1.6002" shape="octagon"/>
<pad name="18" x="-10.16" y="3.81" drill="0.8128" diameter="1.6002" shape="octagon"/>
<text x="-7.62" y="0.1778" size="1.778" layer="25" ratio="10">&gt;NAME</text>
<text x="-10.4648" y="-2.2098" size="1.27" layer="21" ratio="12">1</text>
<text x="-11.2014" y="0.9652" size="1.27" layer="21" ratio="12">18</text>
<text x="9.525" y="-2.2098" size="1.27" layer="21" ratio="12">9</text>
<text x="9.398" y="0.9652" size="1.27" layer="21" ratio="12">10</text>
<text x="-7.62" y="-1.905" size="1.778" layer="27" ratio="10">&gt;VALUE</text>
</package>
</packages>
<symbols>
<symbol name="13IO-1">
<wire x1="10.16" y1="-20.32" x2="-10.16" y2="-20.32" width="0.4064" layer="94"/>
<wire x1="-10.16" y1="-20.32" x2="-10.16" y2="17.78" width="0.4064" layer="94"/>
<wire x1="-10.16" y1="17.78" x2="10.16" y2="17.78" width="0.4064" layer="94"/>
<wire x1="10.16" y1="17.78" x2="10.16" y2="-20.32" width="0.4064" layer="94"/>
<text x="-10.16" y="19.05" size="1.778" layer="95">&gt;NAME</text>
<text x="-10.16" y="-22.86" size="1.778" layer="96">&gt;VALUE</text>
<pin name="!MCLR" x="-12.7" y="-2.54" length="short" direction="in"/>
<pin name="OSC1" x="-12.7" y="7.62" length="short" direction="in"/>
<pin name="RA0" x="12.7" y="-17.78" length="short" rot="R180"/>
<pin name="RA1" x="12.7" y="-15.24" length="short" rot="R180"/>
<pin name="RA2" x="12.7" y="-12.7" length="short" rot="R180"/>
<pin name="RA3" x="12.7" y="-10.16" length="short" rot="R180"/>
<pin name="T0CKI/RA4" x="12.7" y="-7.62" length="short" rot="R180"/>
<pin name="RB0" x="12.7" y="-2.54" length="short" rot="R180"/>
<pin name="RB1" x="12.7" y="0" length="short" rot="R180"/>
<pin name="RB2" x="12.7" y="2.54" length="short" rot="R180"/>
<pin name="RB3" x="12.7" y="5.08" length="short" rot="R180"/>
<pin name="RB4" x="12.7" y="7.62" length="short" rot="R180"/>
<pin name="RB5" x="12.7" y="10.16" length="short" rot="R180"/>
<pin name="RB6" x="12.7" y="12.7" length="short" rot="R180"/>
<pin name="RB7" x="12.7" y="15.24" length="short" rot="R180"/>
<pin name="OSC2" x="-12.7" y="2.54" length="short" direction="out"/>
<pin name="VSS" x="-12.7" y="-17.78" length="short" direction="pwr"/>
<pin name="VDD" x="-12.7" y="15.24" length="short" direction="pwr"/>
</symbol>
</symbols>
<devicesets>
<deviceset name="PIC16F8*" prefix="IC" uservalue="yes">
<description>Microcontroller&lt;p&gt;
8-Bit PIC16F8X Family - CMOS Flash/EEPROM&lt;p&gt;
Pin Compatible :&lt;p&gt;
PIC16F83, PIC16CR83, PIC16F84A, PIC16CR84&lt;p&gt;
see also &lt;a href=PIC16C*&gt;PIC16C*&lt;/a&gt;</description>
<gates>
<gate name="G$1" symbol="13IO-1" x="0" y="0"/>
</gates>
<devices>
<device name="SO" package="SO-18W">
<connects>
<connect gate="G$1" pin="!MCLR" pad="4"/>
<connect gate="G$1" pin="OSC1" pad="16"/>
<connect gate="G$1" pin="OSC2" pad="15"/>
<connect gate="G$1" pin="RA0" pad="17"/>
<connect gate="G$1" pin="RA1" pad="18"/>
<connect gate="G$1" pin="RA2" pad="1"/>
<connect gate="G$1" pin="RA3" pad="2"/>
<connect gate="G$1" pin="RB0" pad="6"/>
<connect gate="G$1" pin="RB1" pad="7"/>
<connect gate="G$1" pin="RB2" pad="8"/>
<connect gate="G$1" pin="RB3" pad="9"/>
<connect gate="G$1" pin="RB4" pad="10"/>
<connect gate="G$1" pin="RB5" pad="11"/>
<connect gate="G$1" pin="RB6" pad="12"/>
<connect gate="G$1" pin="RB7" pad="13"/>
<connect gate="G$1" pin="T0CKI/RA4" pad="3"/>
<connect gate="G$1" pin="VDD" pad="14"/>
<connect gate="G$1" pin="VSS" pad="5"/>
</connects>
<technologies>
<technology name="3"/>
<technology name="4A"/>
</technologies>
</device>
<device name="P" package="DIL18">
<connects>
<connect gate="G$1" pin="!MCLR" pad="4"/>
<connect gate="G$1" pin="OSC1" pad="16"/>
<connect gate="G$1" pin="OSC2" pad="15"/>
<connect gate="G$1" pin="RA0" pad="17"/>
<connect gate="G$1" pin="RA1" pad="18"/>
<connect gate="G$1" pin="RA2" pad="1"/>
<connect gate="G$1" pin="RA3" pad="2"/>
<connect gate="G$1" pin="RB0" pad="6"/>
<connect gate="G$1" pin="RB1" pad="7"/>
<connect gate="G$1" pin="RB2" pad="8"/>
<connect gate="G$1" pin="RB3" pad="9"/>
<connect gate="G$1" pin="RB4" pad="10"/>
<connect gate="G$1" pin="RB5" pad="11"/>
<connect gate="G$1" pin="RB6" pad="12"/>
<connect gate="G$1" pin="RB7" pad="13"/>
<connect gate="G$1" pin="T0CKI/RA4" pad="3"/>
<connect gate="G$1" pin="VDD" pad="14"/>
<connect gate="G$1" pin="VSS" pad="5"/>
</connects>
<technologies>
<technology name="3"/>
<technology name="4A"/>
</technologies>
</device>
</devices>
</deviceset>
</devicesets>
</library>
<library name="linear">
<packages>
<package name="TO92">
<description>3 lead plastic package</description>
<wire x1="-2.0945" y1="-1.651" x2="-0.7864" y2="2.5484" width="0.127" layer="21" curve="-111.097684" cap="flat"/>
<wire x1="0.7864" y1="2.5484" x2="2.0945" y2="-1.651" width="0.127" layer="21" curve="-111.097684" cap="flat"/>
<wire x1="-2.0945" y1="-1.651" x2="2.0945" y2="-1.651" width="0.127" layer="21"/>
<wire x1="-2.2537" y1="-0.254" x2="-0.2863" y2="-0.254" width="0.127" layer="51"/>
<wire x1="-2.6548" y1="-0.254" x2="-2.2537" y2="-0.254" width="0.127" layer="21"/>
<wire x1="-0.2863" y1="-0.254" x2="0.2863" y2="-0.254" width="0.127" layer="21"/>
<wire x1="2.2537" y1="-0.254" x2="2.6548" y2="-0.254" width="0.127" layer="21"/>
<wire x1="0.2863" y1="-0.254" x2="2.2537" y2="-0.254" width="0.127" layer="51"/>
<wire x1="-0.7864" y1="2.5484" x2="0.7864" y2="2.5484" width="0.127" layer="51" curve="-34.298964" cap="flat"/>
<pad name="1" x="-1.27" y="0" drill="0.8128" shape="octagon"/>
<pad name="2" x="0" y="1.905" drill="0.8128" shape="octagon"/>
<pad name="3" x="1.27" y="0" drill="0.8128" shape="octagon"/>
<text x="3.175" y="0.635" size="1.27" layer="25" ratio="10">&gt;NAME</text>
<text x="3.175" y="-1.27" size="1.27" layer="27" ratio="10">&gt;VALUE</text>
<text x="-2.032" y="0" size="1.27" layer="51" ratio="10">1</text>
<text x="-0.635" y="0.635" size="1.27" layer="51" ratio="10">2</text>
<text x="1.016" y="0" size="1.27" layer="51" ratio="10">3</text>
</package>
</packages>
<symbols>
<symbol name="78XX">
<wire x1="-7.62" y1="-5.08" x2="7.62" y2="-5.08" width="0.4064" layer="94"/>
<wire x1="7.62" y1="-5.08" x2="7.62" y2="2.54" width="0.4064" layer="94"/>
<wire x1="7.62" y1="2.54" x2="-7.62" y2="2.54" width="0.4064" layer="94"/>
<wire x1="-7.62" y1="2.54" x2="-7.62" y2="-5.08" width="0.4064" layer="94"/>
<text x="-7.62" y="5.715" size="1.778" layer="95">&gt;NAME</text>
<text x="-7.62" y="3.175" size="1.778" layer="96">&gt;VALUE</text>
<text x="-2.032" y="-4.318" size="1.524" layer="95">GND</text>
<pin name="VI" x="-10.16" y="0" length="short" direction="in"/>
<pin name="GND" x="0" y="-7.62" visible="pad" length="short" direction="pas" rot="R90"/>
<pin name="VO" x="10.16" y="0" length="short" direction="out" rot="R180"/>
</symbol>
</symbols>
<devicesets>
<deviceset name="78LXXZ" prefix="U" uservalue="yes">
<description>V-Reg.&lt;p&gt;
positiv voltage regulator / low power TO92</description>
<gates>
<gate name="A1" symbol="78XX" x="0" y="0"/>
</gates>
<devices>
<device name="" package="TO92">
<connects>
<connect gate="A1" pin="GND" pad="2"/>
<connect gate="A1" pin="VI" pad="3"/>
<connect gate="A1" pin="VO" pad="1"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
</devices>
</deviceset>
</devicesets>
</library>
<library name="capacitor-wima">
<packages>
<package name="C10B4">
<description>Capacitor&lt;p&gt;
MKS4 outline 13.4 x 4 mm / RM 10.16 mm</description>
<wire x1="-3.175" y1="1.27" x2="-3.175" y2="0" width="0.4064" layer="21"/>
<wire x1="-2.286" y1="1.27" x2="-2.286" y2="0" width="0.4064" layer="21"/>
<wire x1="3.81" y1="0" x2="-2.286" y2="0" width="0.127" layer="21"/>
<wire x1="-2.286" y1="0" x2="-2.286" y2="-1.27" width="0.4064" layer="21"/>
<wire x1="-3.81" y1="0" x2="-3.175" y2="0" width="0.127" layer="21"/>
<wire x1="-3.175" y1="0" x2="-3.175" y2="-1.27" width="0.4064" layer="21"/>
<wire x1="-6.096" y1="2.032" x2="6.096" y2="2.032" width="0.127" layer="21"/>
<wire x1="6.604" y1="1.524" x2="6.604" y2="-1.524" width="0.127" layer="21"/>
<wire x1="6.096" y1="-2.032" x2="-6.096" y2="-2.032" width="0.127" layer="21"/>
<wire x1="-6.604" y1="-1.524" x2="-6.604" y2="1.524" width="0.127" layer="21"/>
<wire x1="6.096" y1="2.032" x2="6.604" y2="1.524" width="0.127" layer="21" curve="-90"/>
<wire x1="6.096" y1="-2.032" x2="6.604" y2="-1.524" width="0.127" layer="21" curve="90"/>
<wire x1="-6.604" y1="-1.524" x2="-6.096" y2="-2.032" width="0.127" layer="21" curve="90"/>
<wire x1="-6.604" y1="1.524" x2="-6.096" y2="2.032" width="0.127" layer="21" curve="-90"/>
<pad name="1" x="-5.08" y="0" drill="1.016" diameter="2.159" shape="octagon"/>
<pad name="2" x="5.08" y="0" drill="1.016" diameter="2.159" shape="octagon"/>
<text x="-1.524" y="0.381" size="1.27" layer="25" ratio="10">&gt;NAME</text>
<text x="-1.524" y="-1.651" size="1.27" layer="27" ratio="10">&gt;VALUE</text>
</package>
<package name="C10B5">
<description>Capacitor&lt;p&gt;
MKS4 outline 13.4 x 5 mm / RM 10.16 mm</description>
<wire x1="-3.175" y1="1.27" x2="-3.175" y2="0" width="0.4064" layer="21"/>
<wire x1="-2.286" y1="1.27" x2="-2.286" y2="0" width="0.4064" layer="21"/>
<wire x1="3.81" y1="0" x2="-2.286" y2="0" width="0.127" layer="21"/>
<wire x1="-2.286" y1="0" x2="-2.286" y2="-1.27" width="0.4064" layer="21"/>
<wire x1="-3.81" y1="0" x2="-3.175" y2="0" width="0.127" layer="21"/>
<wire x1="-3.175" y1="0" x2="-3.175" y2="-1.27" width="0.4064" layer="21"/>
<wire x1="-6.096" y1="2.54" x2="6.096" y2="2.54" width="0.127" layer="21"/>
<wire x1="6.604" y1="2.032" x2="6.604" y2="-2.032" width="0.127" layer="21"/>
<wire x1="6.096" y1="-2.54" x2="-6.096" y2="-2.54" width="0.127" layer="21"/>
<wire x1="-6.604" y1="-2.032" x2="-6.604" y2="2.032" width="0.127" layer="21"/>
<wire x1="6.096" y1="2.54" x2="6.604" y2="2.032" width="0.127" layer="21" curve="-90"/>
<wire x1="6.096" y1="-2.54" x2="6.604" y2="-2.032" width="0.127" layer="21" curve="90"/>
<wire x1="-6.604" y1="-2.032" x2="-6.096" y2="-2.54" width="0.127" layer="21" curve="90"/>
<wire x1="-6.604" y1="2.032" x2="-6.096" y2="2.54" width="0.127" layer="21" curve="-90"/>
<pad name="1" x="-5.08" y="0" drill="1.016" diameter="2.159" shape="octagon"/>
<pad name="2" x="5.08" y="0" drill="1.016" diameter="2.159" shape="octagon"/>
<text x="-1.524" y="0.635" size="1.27" layer="25" ratio="10">&gt;NAME</text>
<text x="-1.524" y="-1.905" size="1.27" layer="27" ratio="10">&gt;VALUE</text>
</package>
<package name="C10B6">
<description>Capacitor&lt;p&gt;
MKS4 outline 13.4 x 6 mm / RM 10.16 mm</description>
<wire x1="-3.175" y1="1.27" x2="-3.175" y2="0" width="0.4064" layer="21"/>
<wire x1="-2.286" y1="1.27" x2="-2.286" y2="0" width="0.4064" layer="21"/>
<wire x1="3.81" y1="0" x2="-2.286" y2="0" width="0.127" layer="21"/>
<wire x1="-2.286" y1="0" x2="-2.286" y2="-1.27" width="0.4064" layer="21"/>
<wire x1="-3.81" y1="0" x2="-3.175" y2="0" width="0.127" layer="21"/>
<wire x1="-3.175" y1="0" x2="-3.175" y2="-1.27" width="0.4064" layer="21"/>
<wire x1="-6.096" y1="3.048" x2="6.096" y2="3.048" width="0.127" layer="21"/>
<wire x1="6.604" y1="2.54" x2="6.604" y2="-2.54" width="0.127" layer="21"/>
<wire x1="6.096" y1="-3.048" x2="-6.096" y2="-3.048" width="0.127" layer="21"/>
<wire x1="-6.604" y1="-2.54" x2="-6.604" y2="2.54" width="0.127" layer="21"/>
<wire x1="6.096" y1="3.048" x2="6.604" y2="2.54" width="0.127" layer="21" curve="-90"/>
<wire x1="6.096" y1="-3.048" x2="6.604" y2="-2.54" width="0.127" layer="21" curve="90"/>
<wire x1="-6.604" y1="-2.54" x2="-6.096" y2="-3.048" width="0.127" layer="21" curve="90"/>
<wire x1="-6.604" y1="2.54" x2="-6.096" y2="3.048" width="0.127" layer="21" curve="-90"/>
<pad name="1" x="-5.08" y="0" drill="1.016" diameter="2.159" shape="octagon"/>
<pad name="2" x="5.08" y="0" drill="1.016" diameter="2.159" shape="octagon"/>
<text x="-1.524" y="0.762" size="1.27" layer="25" ratio="10">&gt;NAME</text>
<text x="-1.524" y="-2.032" size="1.27" layer="27" ratio="10">&gt;VALUE</text>
</package>
<package name="C15B5">
<description>Capacitor&lt;p&gt;
MKS4 outline 18 x 5 mm / RM 15 mm</description>
<wire x1="-5.08" y1="1.27" x2="-5.08" y2="0" width="0.4064" layer="21"/>
<wire x1="-5.08" y1="0" x2="-5.08" y2="-1.27" width="0.4064" layer="21"/>
<wire x1="-4.191" y1="1.27" x2="-4.191" y2="0" width="0.4064" layer="21"/>
<wire x1="-4.191" y1="0" x2="-4.191" y2="-1.27" width="0.4064" layer="21"/>
<wire x1="-4.191" y1="0" x2="6.096" y2="0" width="0.127" layer="21"/>
<wire x1="-5.08" y1="0" x2="-6.096" y2="0" width="0.127" layer="21"/>
<wire x1="9.017" y1="2.032" x2="9.017" y2="-2.032" width="0.127" layer="21"/>
<wire x1="8.509" y1="-2.54" x2="-8.509" y2="-2.54" width="0.127" layer="21"/>
<wire x1="-9.017" y1="-2.032" x2="-9.017" y2="2.032" width="0.127" layer="21"/>
<wire x1="-8.509" y1="2.54" x2="8.509" y2="2.54" width="0.127" layer="21"/>
<wire x1="8.509" y1="2.54" x2="9.017" y2="2.032" width="0.127" layer="21" curve="-90"/>
<wire x1="8.509" y1="-2.54" x2="9.017" y2="-2.032" width="0.127" layer="21" curve="90"/>
<wire x1="-9.017" y1="-2.032" x2="-8.509" y2="-2.54" width="0.127" layer="21" curve="90"/>
<wire x1="-9.017" y1="2.032" x2="-8.509" y2="2.54" width="0.127" layer="21" curve="-90"/>
<pad name="1" x="-7.493" y="0" drill="1.016" diameter="2.159" shape="octagon"/>
<pad name="2" x="7.493" y="0" drill="1.016" diameter="2.159" shape="octagon"/>
<text x="-3.429" y="0.635" size="1.397" layer="25" ratio="10">&gt;NAME</text>
<text x="-3.429" y="-2.032" size="1.397" layer="27" ratio="10">&gt;VALUE</text>
</package>
<package name="C15B6">
<description>Capacitor&lt;p&gt;
MKS4 outline 18 x 6 mm / RM 15 mm</description>
<wire x1="-5.08" y1="1.27" x2="-5.08" y2="0" width="0.4064" layer="21"/>
<wire x1="-5.08" y1="0" x2="-5.08" y2="-1.27" width="0.4064" layer="21"/>
<wire x1="-4.191" y1="1.27" x2="-4.191" y2="0" width="0.4064" layer="21"/>
<wire x1="-4.191" y1="0" x2="-4.191" y2="-1.27" width="0.4064" layer="21"/>
<wire x1="-4.191" y1="0" x2="6.096" y2="0" width="0.127" layer="21"/>
<wire x1="-5.08" y1="0" x2="-6.096" y2="0" width="0.127" layer="21"/>
<wire x1="9.017" y1="2.54" x2="9.017" y2="-2.54" width="0.127" layer="21"/>
<wire x1="8.509" y1="-3.048" x2="-8.509" y2="-3.048" width="0.127" layer="21"/>
<wire x1="-9.017" y1="-2.54" x2="-9.017" y2="2.54" width="0.127" layer="21"/>
<wire x1="-8.509" y1="3.048" x2="8.509" y2="3.048" width="0.127" layer="21"/>
<wire x1="8.509" y1="3.048" x2="9.017" y2="2.54" width="0.127" layer="21" curve="-90"/>
<wire x1="8.509" y1="-3.048" x2="9.017" y2="-2.54" width="0.127" layer="21" curve="90"/>
<wire x1="-9.017" y1="-2.54" x2="-8.509" y2="-3.048" width="0.127" layer="21" curve="90"/>
<wire x1="-9.017" y1="2.54" x2="-8.509" y2="3.048" width="0.127" layer="21" curve="-90"/>
<pad name="1" x="-7.493" y="0" drill="1.016" diameter="2.159" shape="octagon"/>
<pad name="2" x="7.493" y="0" drill="1.016" diameter="2.159" shape="octagon"/>
<text x="-3.429" y="0.635" size="1.397" layer="25" ratio="10">&gt;NAME</text>
<text x="-3.429" y="-2.032" size="1.397" layer="27" ratio="10">&gt;VALUE</text>
</package>
<package name="C15B7">
<description>Capacitor&lt;p&gt;
MKS4 outline 18 x 7 mm / RM 15 mm</description>
<wire x1="-5.08" y1="1.27" x2="-5.08" y2="0" width="0.4064" layer="21"/>
<wire x1="-5.08" y1="0" x2="-5.08" y2="-1.27" width="0.4064" layer="21"/>
<wire x1="-4.191" y1="1.27" x2="-4.191" y2="0" width="0.4064" layer="21"/>
<wire x1="-4.191" y1="0" x2="-4.191" y2="-1.27" width="0.4064" layer="21"/>
<wire x1="-4.191" y1="0" x2="6.096" y2="0" width="0.127" layer="21"/>
<wire x1="-5.08" y1="0" x2="-6.096" y2="0" width="0.127" layer="21"/>
<wire x1="9.017" y1="3.048" x2="9.017" y2="-3.048" width="0.127" layer="21"/>
<wire x1="8.509" y1="-3.556" x2="-8.509" y2="-3.556" width="0.127" layer="21"/>
<wire x1="-9.017" y1="-3.048" x2="-9.017" y2="3.048" width="0.127" layer="21"/>
<wire x1="-8.509" y1="3.556" x2="8.509" y2="3.556" width="0.127" layer="21"/>
<wire x1="8.509" y1="3.556" x2="9.017" y2="3.048" width="0.127" layer="21" curve="-90"/>
<wire x1="8.509" y1="-3.556" x2="9.017" y2="-3.048" width="0.127" layer="21" curve="90"/>
<wire x1="-9.017" y1="-3.048" x2="-8.509" y2="-3.556" width="0.127" layer="21" curve="90"/>
<wire x1="-9.017" y1="3.048" x2="-8.509" y2="3.556" width="0.127" layer="21" curve="-90"/>
<pad name="1" x="-7.493" y="0" drill="1.016" diameter="2.159" shape="octagon"/>
<pad name="2" x="7.493" y="0" drill="1.016" diameter="2.159" shape="octagon"/>
<text x="-3.429" y="0.889" size="1.397" layer="25" ratio="10">&gt;NAME</text>
<text x="-3.429" y="-2.286" size="1.397" layer="27" ratio="10">&gt;VALUE</text>
</package>
<package name="C15B8">
<description>Capacitor&lt;p&gt;
MKS4 outline 18 x 8 mm / RM 15 mm</description>
<wire x1="-5.08" y1="1.27" x2="-5.08" y2="0" width="0.4064" layer="21"/>
<wire x1="-5.08" y1="0" x2="-5.08" y2="-1.27" width="0.4064" layer="21"/>
<wire x1="-4.191" y1="1.27" x2="-4.191" y2="0" width="0.4064" layer="21"/>
<wire x1="-4.191" y1="0" x2="-4.191" y2="-1.27" width="0.4064" layer="21"/>
<wire x1="-4.191" y1="0" x2="6.096" y2="0" width="0.127" layer="21"/>
<wire x1="-5.08" y1="0" x2="-6.096" y2="0" width="0.127" layer="21"/>
<wire x1="9.017" y1="3.556" x2="9.017" y2="-3.556" width="0.127" layer="21"/>
<wire x1="8.509" y1="-4.064" x2="-8.509" y2="-4.064" width="0.127" layer="21"/>
<wire x1="-9.017" y1="-3.556" x2="-9.017" y2="3.556" width="0.127" layer="21"/>
<wire x1="-8.509" y1="4.064" x2="8.509" y2="4.064" width="0.127" layer="21"/>
<wire x1="8.509" y1="4.064" x2="9.017" y2="3.556" width="0.127" layer="21" curve="-90"/>
<wire x1="8.509" y1="-4.064" x2="9.017" y2="-3.556" width="0.127" layer="21" curve="90"/>
<wire x1="-9.017" y1="-3.556" x2="-8.509" y2="-4.064" width="0.127" layer="21" curve="90"/>
<wire x1="-9.017" y1="3.556" x2="-8.509" y2="4.064" width="0.127" layer="21" curve="-90"/>
<pad name="1" x="-7.493" y="0" drill="1.016" diameter="2.159" shape="octagon"/>
<pad name="2" x="7.493" y="0" drill="1.016" diameter="2.159" shape="octagon"/>
<text x="-3.429" y="1.143" size="1.397" layer="25" ratio="10">&gt;NAME</text>
<text x="-3.429" y="-2.54" size="1.397" layer="27" ratio="10">&gt;VALUE</text>
</package>
<package name="C15B9">
<description>Capacitor&lt;p&gt;
MKS4 outline 18 x 9 mm / RM 15 mm</description>
<wire x1="-5.08" y1="1.27" x2="-5.08" y2="0" width="0.4064" layer="21"/>
<wire x1="-5.08" y1="0" x2="-5.08" y2="-1.27" width="0.4064" layer="21"/>
<wire x1="-4.191" y1="1.27" x2="-4.191" y2="0" width="0.4064" layer="21"/>
<wire x1="-4.191" y1="0" x2="-4.191" y2="-1.27" width="0.4064" layer="21"/>
<wire x1="-4.191" y1="0" x2="6.096" y2="0" width="0.127" layer="21"/>
<wire x1="-5.08" y1="0" x2="-6.096" y2="0" width="0.127" layer="21"/>
<wire x1="9.017" y1="3.937" x2="9.017" y2="-3.937" width="0.127" layer="21"/>
<wire x1="8.509" y1="-4.445" x2="-8.509" y2="-4.445" width="0.127" layer="21"/>
<wire x1="-9.017" y1="-3.937" x2="-9.017" y2="3.937" width="0.127" layer="21"/>
<wire x1="-8.509" y1="4.445" x2="8.509" y2="4.445" width="0.127" layer="21"/>
<wire x1="8.509" y1="4.445" x2="9.017" y2="3.937" width="0.127" layer="21" curve="-90"/>
<wire x1="8.509" y1="-4.445" x2="9.017" y2="-3.937" width="0.127" layer="21" curve="90"/>
<wire x1="-9.017" y1="-3.937" x2="-8.509" y2="-4.445" width="0.127" layer="21" curve="90"/>
<wire x1="-9.017" y1="3.937" x2="-8.509" y2="4.445" width="0.127" layer="21" curve="-90"/>
<pad name="1" x="-7.493" y="0" drill="1.016" diameter="2.159" shape="octagon"/>
<pad name="2" x="7.493" y="0" drill="1.016" diameter="2.159" shape="octagon"/>
<text x="-3.429" y="1.143" size="1.397" layer="25" ratio="10">&gt;NAME</text>
<text x="-3.429" y="-2.54" size="1.397" layer="27" ratio="10">&gt;VALUE</text>
</package>
<package name="C2,5-2">
<description>Capacitor&lt;p&gt;
MKS2 outline 5 x 2.5 mm / RM2.54 mm</description>
<wire x1="-2.159" y1="1.27" x2="2.159" y2="1.27" width="0.127" layer="21"/>
<wire x1="2.159" y1="-1.27" x2="-2.159" y2="-1.27" width="0.127" layer="21"/>
<wire x1="2.413" y1="1.016" x2="2.413" y2="-1.016" width="0.127" layer="21"/>
<wire x1="-2.413" y1="1.016" x2="-2.413" y2="-1.016" width="0.127" layer="21"/>
<wire x1="2.159" y1="1.27" x2="2.413" y2="1.016" width="0.127" layer="21" curve="-90"/>
<wire x1="-2.413" y1="1.016" x2="-2.159" y2="1.27" width="0.127" layer="21" curve="-90"/>
<wire x1="2.159" y1="-1.27" x2="2.413" y2="-1.016" width="0.127" layer="21" curve="90"/>
<wire x1="-2.413" y1="-1.016" x2="-2.159" y2="-1.27" width="0.127" layer="21" curve="90"/>
<wire x1="1.27" y1="0" x2="0.381" y2="0" width="0.127" layer="51"/>
<wire x1="0.381" y1="0" x2="0.254" y2="0" width="0.127" layer="21"/>
<wire x1="0.254" y1="0" x2="0.254" y2="0.762" width="0.254" layer="21"/>
<wire x1="0.254" y1="0" x2="0.254" y2="-0.762" width="0.254" layer="21"/>
<wire x1="-0.254" y1="0.762" x2="-0.254" y2="0" width="0.254" layer="21"/>
<wire x1="-0.254" y1="0" x2="-0.254" y2="-0.762" width="0.254" layer="21"/>
<wire x1="-0.254" y1="0" x2="-0.381" y2="0" width="0.127" layer="21"/>
<wire x1="-0.381" y1="0" x2="-1.27" y2="0" width="0.127" layer="51"/>
<pad name="1" x="-1.27" y="0" drill="0.8128" diameter="1.6002" shape="octagon"/>
<pad name="2" x="1.27" y="0" drill="0.8128" diameter="1.6002" shape="octagon"/>
<text x="2.921" y="0.254" size="1.27" layer="25" ratio="10">&gt;NAME</text>
<text x="2.921" y="-1.27" size="1.27" layer="27" ratio="10">&gt;VALUE</text>
</package>
<package name="C2,5-4">
<description>Capacitor&lt;p&gt;
MKS2 outline 5 x 4 mm / RM2.54 mm</description>
<wire x1="-2.159" y1="1.905" x2="2.159" y2="1.905" width="0.127" layer="21"/>
<wire x1="2.159" y1="-1.905" x2="-2.159" y2="-1.905" width="0.127" layer="21"/>
<wire x1="2.413" y1="1.651" x2="2.413" y2="-1.651" width="0.127" layer="21"/>
<wire x1="-2.413" y1="1.651" x2="-2.413" y2="-1.651" width="0.127" layer="21"/>
<wire x1="2.159" y1="1.905" x2="2.413" y2="1.651" width="0.127" layer="21" curve="-90"/>
<wire x1="-2.413" y1="1.651" x2="-2.159" y2="1.905" width="0.127" layer="21" curve="-90"/>
<wire x1="2.159" y1="-1.905" x2="2.413" y2="-1.651" width="0.127" layer="21" curve="90"/>
<wire x1="-2.413" y1="-1.651" x2="-2.159" y2="-1.905" width="0.127" layer="21" curve="90"/>
<wire x1="1.27" y1="0" x2="0.381" y2="0" width="0.127" layer="51"/>
<wire x1="0.381" y1="0" x2="0.254" y2="0" width="0.127" layer="21"/>
<wire x1="0.254" y1="0" x2="0.254" y2="0.762" width="0.254" layer="21"/>
<wire x1="0.254" y1="0" x2="0.254" y2="-0.762" width="0.254" layer="21"/>
<wire x1="-0.254" y1="0.762" x2="-0.254" y2="0" width="0.254" layer="21"/>
<wire x1="-0.254" y1="0" x2="-0.254" y2="-0.762" width="0.254" layer="21"/>
<wire x1="-0.254" y1="0" x2="-0.381" y2="0" width="0.127" layer="21"/>
<wire x1="-0.381" y1="0" x2="-1.27" y2="0" width="0.127" layer="51"/>
<pad name="1" x="-1.27" y="0" drill="0.8128" diameter="1.6002" shape="octagon"/>
<pad name="2" x="1.27" y="0" drill="0.8128" diameter="1.6002" shape="octagon"/>
<text x="2.921" y="0.254" size="1.27" layer="25" ratio="10">&gt;NAME</text>
<text x="2.921" y="-1.524" size="1.27" layer="27" ratio="10">&gt;VALUE</text>
</package>
<package name="C2,5-5">
<description>Capacitor&lt;p&gt;
MKS2 outline 5 x 5 mm / RM2.54 mm</description>
<wire x1="-2.159" y1="2.286" x2="2.159" y2="2.286" width="0.127" layer="21"/>
<wire x1="2.159" y1="-2.286" x2="-2.159" y2="-2.286" width="0.127" layer="21"/>
<wire x1="2.413" y1="2.032" x2="2.413" y2="-2.032" width="0.127" layer="21"/>
<wire x1="-2.413" y1="2.032" x2="-2.413" y2="-2.032" width="0.127" layer="21"/>
<wire x1="2.159" y1="2.286" x2="2.413" y2="2.032" width="0.127" layer="21" curve="-90"/>
<wire x1="-2.413" y1="2.032" x2="-2.159" y2="2.286" width="0.127" layer="21" curve="-90"/>
<wire x1="2.159" y1="-2.286" x2="2.413" y2="-2.032" width="0.127" layer="21" curve="90"/>
<wire x1="-2.413" y1="-2.032" x2="-2.159" y2="-2.286" width="0.127" layer="21" curve="90"/>
<wire x1="1.27" y1="0" x2="0.381" y2="0" width="0.127" layer="51"/>
<wire x1="0.381" y1="0" x2="0.254" y2="0" width="0.127" layer="21"/>
<wire x1="0.254" y1="0" x2="0.254" y2="0.762" width="0.254" layer="21"/>
<wire x1="0.254" y1="0" x2="0.254" y2="-0.762" width="0.254" layer="21"/>
<wire x1="-0.254" y1="0.762" x2="-0.254" y2="0" width="0.254" layer="21"/>
<wire x1="-0.254" y1="0" x2="-0.254" y2="-0.762" width="0.254" layer="21"/>
<wire x1="-0.254" y1="0" x2="-0.381" y2="0" width="0.127" layer="21"/>
<wire x1="-0.381" y1="0" x2="-1.27" y2="0" width="0.127" layer="51"/>
<pad name="1" x="-1.27" y="0" drill="0.8128" diameter="1.6002" shape="octagon"/>
<pad name="2" x="1.27" y="0" drill="0.8128" diameter="1.6002" shape="octagon"/>
<text x="2.921" y="0.254" size="1.27" layer="25" ratio="10">&gt;NAME</text>
<text x="2.921" y="-1.524" size="1.27" layer="27" ratio="10">&gt;VALUE</text>
</package>
<package name="C2,5-6">
<description>Capacitor&lt;p&gt;
MKS2 outline 5 x 6 mm / RM2.54 mm</description>
<wire x1="-2.159" y1="2.794" x2="2.159" y2="2.794" width="0.127" layer="21"/>
<wire x1="2.159" y1="-2.794" x2="-2.159" y2="-2.794" width="0.127" layer="21"/>
<wire x1="2.413" y1="2.54" x2="2.413" y2="-2.54" width="0.127" layer="21"/>
<wire x1="-2.413" y1="2.54" x2="-2.413" y2="-2.54" width="0.127" layer="21"/>
<wire x1="2.159" y1="2.794" x2="2.413" y2="2.54" width="0.127" layer="21" curve="-90"/>
<wire x1="-2.413" y1="2.54" x2="-2.159" y2="2.794" width="0.127" layer="21" curve="-90"/>
<wire x1="2.159" y1="-2.794" x2="2.413" y2="-2.54" width="0.127" layer="21" curve="90"/>
<wire x1="-2.413" y1="-2.54" x2="-2.159" y2="-2.794" width="0.127" layer="21" curve="90"/>
<wire x1="1.27" y1="0" x2="0.381" y2="0" width="0.127" layer="51"/>
<wire x1="0.381" y1="0" x2="0.254" y2="0" width="0.127" layer="21"/>
<wire x1="0.254" y1="0" x2="0.254" y2="0.762" width="0.254" layer="21"/>
<wire x1="0.254" y1="0" x2="0.254" y2="-0.762" width="0.254" layer="21"/>
<wire x1="-0.254" y1="0.762" x2="-0.254" y2="0" width="0.254" layer="21"/>
<wire x1="-0.254" y1="0" x2="-0.254" y2="-0.762" width="0.254" layer="21"/>
<wire x1="-0.254" y1="0" x2="-0.381" y2="0" width="0.127" layer="21"/>
<wire x1="-0.381" y1="0" x2="-1.27" y2="0" width="0.127" layer="51"/>
<pad name="1" x="-1.27" y="0" drill="0.8128" diameter="1.6002" shape="octagon"/>
<pad name="2" x="1.27" y="0" drill="0.8128" diameter="1.6002" shape="octagon"/>
<text x="-2.032" y="1.143" size="1.27" layer="25" ratio="10">&gt;NAME</text>
<text x="-2.032" y="-2.413" size="1.27" layer="27" ratio="10">&gt;VALUE</text>
</package>
<package name="C22,5B10">
<description>Capacitor&lt;p&gt;
MKS4 outline 27 x 10 mm / RM 22.5 mm</description>
<wire x1="-12.827" y1="5.334" x2="12.827" y2="5.334" width="0.127" layer="21"/>
<wire x1="13.335" y1="4.826" x2="13.335" y2="-4.826" width="0.127" layer="21"/>
<wire x1="12.827" y1="-5.334" x2="-12.827" y2="-5.334" width="0.127" layer="21"/>
<wire x1="-13.335" y1="-4.826" x2="-13.335" y2="4.826" width="0.127" layer="21"/>
<wire x1="-6.731" y1="1.905" x2="-6.731" y2="0" width="0.4064" layer="21"/>
<wire x1="-6.731" y1="0" x2="-6.731" y2="-1.905" width="0.4064" layer="21"/>
<wire x1="-7.62" y1="1.905" x2="-7.62" y2="0" width="0.4064" layer="21"/>
<wire x1="-7.62" y1="0" x2="-7.62" y2="-1.905" width="0.4064" layer="21"/>
<wire x1="12.827" y1="5.334" x2="13.335" y2="4.826" width="0.127" layer="21" curve="-90"/>
<wire x1="12.827" y1="-5.334" x2="13.335" y2="-4.826" width="0.127" layer="21" curve="90"/>
<wire x1="-13.335" y1="-4.826" x2="-12.827" y2="-5.334" width="0.127" layer="21" curve="90"/>
<wire x1="-13.335" y1="4.826" x2="-12.827" y2="5.334" width="0.127" layer="21" curve="-90"/>
<wire x1="-9.652" y1="0" x2="-7.62" y2="0" width="0.127" layer="21"/>
<wire x1="-6.731" y1="0" x2="9.652" y2="0" width="0.127" layer="21"/>
<pad name="1" x="-11.303" y="0" drill="1.016" diameter="2.54" shape="octagon"/>
<pad name="2" x="11.303" y="0" drill="1.016" diameter="2.54" shape="octagon"/>
<text x="-5.08" y="0.762" size="1.778" layer="25" ratio="10">&gt;NAME</text>
<text x="-5.08" y="-2.54" size="1.778" layer="27" ratio="10">&gt;VALUE</text>
</package>
<package name="C22,5B11">
<description>Capacitor&lt;p&gt;
MKS4 outline 27 x 11 mm / RM 22.5 mm</description>
<wire x1="-12.827" y1="5.588" x2="12.827" y2="5.588" width="0.127" layer="21"/>
<wire x1="13.335" y1="5.08" x2="13.335" y2="-5.08" width="0.127" layer="21"/>
<wire x1="12.827" y1="-5.588" x2="-12.827" y2="-5.588" width="0.127" layer="21"/>
<wire x1="-13.335" y1="-5.08" x2="-13.335" y2="5.08" width="0.127" layer="21"/>
<wire x1="-6.731" y1="1.905" x2="-6.731" y2="0" width="0.4064" layer="21"/>
<wire x1="-6.731" y1="0" x2="-6.731" y2="-1.905" width="0.4064" layer="21"/>
<wire x1="-7.62" y1="1.905" x2="-7.62" y2="0" width="0.4064" layer="21"/>
<wire x1="-7.62" y1="0" x2="-7.62" y2="-1.905" width="0.4064" layer="21"/>
<wire x1="12.827" y1="5.588" x2="13.335" y2="5.08" width="0.127" layer="21" curve="-90"/>
<wire x1="12.827" y1="-5.588" x2="13.335" y2="-5.08" width="0.127" layer="21" curve="90"/>
<wire x1="-13.335" y1="-5.08" x2="-12.827" y2="-5.588" width="0.127" layer="21" curve="90"/>
<wire x1="-13.335" y1="5.08" x2="-12.827" y2="5.588" width="0.127" layer="21" curve="-90"/>
<wire x1="-9.652" y1="0" x2="-7.62" y2="0" width="0.127" layer="21"/>
<wire x1="-6.731" y1="0" x2="9.652" y2="0" width="0.127" layer="21"/>
<pad name="1" x="-11.303" y="0" drill="1.016" diameter="2.54" shape="octagon"/>
<pad name="2" x="11.303" y="0" drill="1.016" diameter="2.54" shape="octagon"/>
<text x="-5.08" y="0.762" size="1.778" layer="25" ratio="10">&gt;NAME</text>
<text x="-5.08" y="-2.54" size="1.778" layer="27" ratio="10">&gt;VALUE</text>
</package>
<package name="C22,5B6">
<description>Capacitor&lt;p&gt;
MKS4 outline 27 x 6 mm / RM 22.5 mm</description>
<wire x1="-12.827" y1="3.048" x2="12.827" y2="3.048" width="0.127" layer="21"/>
<wire x1="13.335" y1="2.54" x2="13.335" y2="-2.54" width="0.127" layer="21"/>
<wire x1="12.827" y1="-3.048" x2="-12.827" y2="-3.048" width="0.127" layer="21"/>
<wire x1="-13.335" y1="-2.54" x2="-13.335" y2="2.54" width="0.127" layer="21"/>
<wire x1="-6.731" y1="1.905" x2="-6.731" y2="0" width="0.4064" layer="21"/>
<wire x1="-6.731" y1="0" x2="-6.731" y2="-1.905" width="0.4064" layer="21"/>
<wire x1="-7.62" y1="1.905" x2="-7.62" y2="0" width="0.4064" layer="21"/>
<wire x1="-7.62" y1="0" x2="-7.62" y2="-1.905" width="0.4064" layer="21"/>
<wire x1="12.827" y1="3.048" x2="13.335" y2="2.54" width="0.127" layer="21" curve="-90"/>
<wire x1="12.827" y1="-3.048" x2="13.335" y2="-2.54" width="0.127" layer="21" curve="90"/>
<wire x1="-13.335" y1="-2.54" x2="-12.827" y2="-3.048" width="0.127" layer="21" curve="90"/>
<wire x1="-13.335" y1="2.54" x2="-12.827" y2="3.048" width="0.127" layer="21" curve="-90"/>
<wire x1="-9.652" y1="0" x2="-7.62" y2="0" width="0.127" layer="21"/>
<wire x1="-6.731" y1="0" x2="9.652" y2="0" width="0.127" layer="21"/>
<pad name="1" x="-11.303" y="0" drill="1.016" diameter="2.54" shape="octagon"/>
<pad name="2" x="11.303" y="0" drill="1.016" diameter="2.54" shape="octagon"/>
<text x="-5.08" y="0.762" size="1.778" layer="25" ratio="10">&gt;NAME</text>
<text x="-5.08" y="-2.54" size="1.778" layer="27" ratio="10">&gt;VALUE</text>
</package>
<package name="C22,5B7">
<description>Capacitor&lt;p&gt;
MKS4 outline 27 x 7 mm / RM 22.5 mm</description>
<wire x1="-12.827" y1="3.556" x2="12.827" y2="3.556" width="0.127" layer="21"/>
<wire x1="13.335" y1="3.048" x2="13.335" y2="-3.048" width="0.127" layer="21"/>
<wire x1="12.827" y1="-3.556" x2="-12.827" y2="-3.556" width="0.127" layer="21"/>
<wire x1="-13.335" y1="-3.048" x2="-13.335" y2="3.048" width="0.127" layer="21"/>
<wire x1="-6.731" y1="1.905" x2="-6.731" y2="0" width="0.4064" layer="21"/>
<wire x1="-6.731" y1="0" x2="-6.731" y2="-1.905" width="0.4064" layer="21"/>
<wire x1="-7.62" y1="1.905" x2="-7.62" y2="0" width="0.4064" layer="21"/>
<wire x1="-7.62" y1="0" x2="-7.62" y2="-1.905" width="0.4064" layer="21"/>
<wire x1="12.827" y1="3.556" x2="13.335" y2="3.048" width="0.127" layer="21" curve="-90"/>
<wire x1="12.827" y1="-3.556" x2="13.335" y2="-3.048" width="0.127" layer="21" curve="90"/>
<wire x1="-13.335" y1="-3.048" x2="-12.827" y2="-3.556" width="0.127" layer="21" curve="90"/>
<wire x1="-13.335" y1="3.048" x2="-12.827" y2="3.556" width="0.127" layer="21" curve="-90"/>
<wire x1="-9.652" y1="0" x2="-7.62" y2="0" width="0.127" layer="21"/>
<wire x1="-6.731" y1="0" x2="9.652" y2="0" width="0.127" layer="21"/>
<pad name="1" x="-11.303" y="0" drill="1.016" diameter="2.54" shape="octagon"/>
<pad name="2" x="11.303" y="0" drill="1.016" diameter="2.54" shape="octagon"/>
<text x="-5.08" y="0.762" size="1.778" layer="25" ratio="10">&gt;NAME</text>
<text x="-5.08" y="-2.54" size="1.778" layer="27" ratio="10">&gt;VALUE</text>
</package>
<package name="C22,5B8">
<description>Capacitor&lt;p&gt;
MKS4 outline 27 x 8 mm / RM 22.5 mm</description>
<wire x1="-12.827" y1="4.318" x2="12.827" y2="4.318" width="0.127" layer="21"/>
<wire x1="13.335" y1="3.81" x2="13.335" y2="-3.81" width="0.127" layer="21"/>
<wire x1="12.827" y1="-4.318" x2="-12.827" y2="-4.318" width="0.127" layer="21"/>
<wire x1="-13.335" y1="-3.81" x2="-13.335" y2="3.81" width="0.127" layer="21"/>
<wire x1="-6.731" y1="1.905" x2="-6.731" y2="0" width="0.4064" layer="21"/>
<wire x1="-6.731" y1="0" x2="-6.731" y2="-1.905" width="0.4064" layer="21"/>
<wire x1="-7.62" y1="1.905" x2="-7.62" y2="0" width="0.4064" layer="21"/>
<wire x1="-7.62" y1="0" x2="-7.62" y2="-1.905" width="0.4064" layer="21"/>
<wire x1="12.827" y1="4.318" x2="13.335" y2="3.81" width="0.127" layer="21" curve="-90"/>
<wire x1="12.827" y1="-4.318" x2="13.335" y2="-3.81" width="0.127" layer="21" curve="90"/>
<wire x1="-13.335" y1="-3.81" x2="-12.827" y2="-4.318" width="0.127" layer="21" curve="90"/>
<wire x1="-13.335" y1="3.81" x2="-12.827" y2="4.318" width="0.127" layer="21" curve="-90"/>
<wire x1="-9.652" y1="0" x2="-7.62" y2="0" width="0.127" layer="21"/>
<wire x1="-6.731" y1="0" x2="9.652" y2="0" width="0.127" layer="21"/>
<pad name="1" x="-11.303" y="0" drill="1.016" diameter="2.54" shape="octagon"/>
<pad name="2" x="11.303" y="0" drill="1.016" diameter="2.54" shape="octagon"/>
<text x="-5.08" y="0.762" size="1.778" layer="25" ratio="10">&gt;NAME</text>
<text x="-5.08" y="-2.54" size="1.778" layer="27" ratio="10">&gt;VALUE</text>
</package>
<package name="C27,5B11">
<description>Capacitor&lt;p&gt;
MKS4 outline 31.6 x 11 mm / RM 27.5 mm</description>
<wire x1="-15.24" y1="5.588" x2="15.24" y2="5.588" width="0.127" layer="21"/>
<wire x1="15.748" y1="5.08" x2="15.748" y2="-5.08" width="0.127" layer="21"/>
<wire x1="15.24" y1="-5.588" x2="-15.24" y2="-5.588" width="0.127" layer="21"/>
<wire x1="-15.748" y1="-5.08" x2="-15.748" y2="5.08" width="0.127" layer="21"/>
<wire x1="-6.731" y1="1.905" x2="-6.731" y2="0" width="0.4064" layer="21"/>
<wire x1="-6.731" y1="0" x2="-6.731" y2="-1.905" width="0.4064" layer="21"/>
<wire x1="-7.62" y1="1.905" x2="-7.62" y2="0" width="0.4064" layer="21"/>
<wire x1="-7.62" y1="0" x2="-7.62" y2="-1.905" width="0.4064" layer="21"/>
<wire x1="15.24" y1="5.588" x2="15.748" y2="5.08" width="0.127" layer="21" curve="-90"/>
<wire x1="15.24" y1="-5.588" x2="15.748" y2="-5.08" width="0.127" layer="21" curve="90"/>
<wire x1="-15.748" y1="-5.08" x2="-15.24" y2="-5.588" width="0.127" layer="21" curve="90"/>
<wire x1="-15.748" y1="5.08" x2="-15.24" y2="5.588" width="0.127" layer="21" curve="-90"/>
<wire x1="-11.557" y1="0" x2="-7.62" y2="0" width="0.127" layer="21"/>
<wire x1="-6.731" y1="0" x2="11.557" y2="0" width="0.127" layer="21"/>
<pad name="1" x="-13.716" y="0" drill="1.1938" diameter="3.1496" shape="octagon"/>
<pad name="2" x="13.716" y="0" drill="1.1938" diameter="3.1496" shape="octagon"/>
<text x="-5.08" y="0.762" size="1.778" layer="25" ratio="10">&gt;NAME</text>
<text x="-5.08" y="-2.54" size="1.778" layer="27" ratio="10">&gt;VALUE</text>
</package>
<package name="C27,5B13">
<description>Capacitor&lt;p&gt;
MKS4 outline 31.6 x 13 mm / RM 27.5 mm</description>
<wire x1="-15.24" y1="6.604" x2="15.24" y2="6.604" width="0.127" layer="21"/>
<wire x1="15.748" y1="6.096" x2="15.748" y2="-6.096" width="0.127" layer="21"/>
<wire x1="15.24" y1="-6.604" x2="-15.24" y2="-6.604" width="0.127" layer="21"/>
<wire x1="-15.748" y1="-6.096" x2="-15.748" y2="6.096" width="0.127" layer="21"/>
<wire x1="-6.731" y1="1.905" x2="-6.731" y2="0" width="0.4064" layer="21"/>
<wire x1="-6.731" y1="0" x2="-6.731" y2="-1.905" width="0.4064" layer="21"/>
<wire x1="-7.62" y1="1.905" x2="-7.62" y2="0" width="0.4064" layer="21"/>
<wire x1="-7.62" y1="0" x2="-7.62" y2="-1.905" width="0.4064" layer="21"/>
<wire x1="15.24" y1="6.604" x2="15.748" y2="6.096" width="0.127" layer="21" curve="-90"/>
<wire x1="15.24" y1="-6.604" x2="15.748" y2="-6.096" width="0.127" layer="21" curve="90"/>
<wire x1="-15.748" y1="-6.096" x2="-15.24" y2="-6.604" width="0.127" layer="21" curve="90"/>
<wire x1="-15.748" y1="6.096" x2="-15.24" y2="6.604" width="0.127" layer="21" curve="-90"/>
<wire x1="-11.557" y1="0" x2="-7.62" y2="0" width="0.127" layer="21"/>
<wire x1="-6.731" y1="0" x2="11.557" y2="0" width="0.127" layer="21"/>
<pad name="1" x="-13.716" y="0" drill="1.1938" diameter="3.1496" shape="octagon"/>
<pad name="2" x="13.716" y="0" drill="1.1938" diameter="3.1496" shape="octagon"/>
<text x="-5.08" y="0.762" size="1.778" layer="25" ratio="10">&gt;NAME</text>
<text x="-5.08" y="-2.54" size="1.778" layer="27" ratio="10">&gt;VALUE</text>
</package>
<package name="C27,5B15">
<description>Capacitor&lt;p&gt;
MKS4 outline 31.6 x 15 mm / RM 27.5 mm</description>
<wire x1="-15.24" y1="7.62" x2="15.24" y2="7.62" width="0.127" layer="21"/>
<wire x1="15.748" y1="7.112" x2="15.748" y2="-7.112" width="0.127" layer="21"/>
<wire x1="15.24" y1="-7.62" x2="-15.24" y2="-7.62" width="0.127" layer="21"/>
<wire x1="-15.748" y1="-7.112" x2="-15.748" y2="7.112" width="0.127" layer="21"/>
<wire x1="-6.731" y1="1.905" x2="-6.731" y2="0" width="0.4064" layer="21"/>
<wire x1="-6.731" y1="0" x2="-6.731" y2="-1.905" width="0.4064" layer="21"/>
<wire x1="-7.62" y1="1.905" x2="-7.62" y2="0" width="0.4064" layer="21"/>
<wire x1="-7.62" y1="0" x2="-7.62" y2="-1.905" width="0.4064" layer="21"/>
<wire x1="15.24" y1="7.62" x2="15.748" y2="7.112" width="0.127" layer="21" curve="-90"/>
<wire x1="15.24" y1="-7.62" x2="15.748" y2="-7.112" width="0.127" layer="21" curve="90"/>
<wire x1="-15.748" y1="-7.112" x2="-15.24" y2="-7.62" width="0.127" layer="21" curve="90"/>
<wire x1="-15.748" y1="7.112" x2="-15.24" y2="7.62" width="0.127" layer="21" curve="-90"/>
<wire x1="-11.557" y1="0" x2="-7.62" y2="0" width="0.127" layer="21"/>
<wire x1="-6.731" y1="0" x2="11.557" y2="0" width="0.127" layer="21"/>
<pad name="1" x="-13.716" y="0" drill="1.1938" diameter="3.1496" shape="octagon"/>
<pad name="2" x="13.716" y="0" drill="1.1938" diameter="3.1496" shape="octagon"/>
<text x="-5.08" y="0.762" size="1.778" layer="25" ratio="10">&gt;NAME</text>
<text x="-5.08" y="-2.54" size="1.778" layer="27" ratio="10">&gt;VALUE</text>
</package>
<package name="C27,5B17">
<description>Capacitor&lt;p&gt;
MKS4 outline 31.6 x 17 mm / RM 27.5 mm</description>
<wire x1="-15.24" y1="8.509" x2="15.24" y2="8.509" width="0.127" layer="21"/>
<wire x1="15.748" y1="8.001" x2="15.748" y2="-8.001" width="0.127" layer="21"/>
<wire x1="15.24" y1="-8.509" x2="-15.24" y2="-8.509" width="0.127" layer="21"/>
<wire x1="-15.748" y1="-8.001" x2="-15.748" y2="8.001" width="0.127" layer="21"/>
<wire x1="-6.731" y1="1.905" x2="-6.731" y2="0" width="0.4064" layer="21"/>
<wire x1="-6.731" y1="0" x2="-6.731" y2="-1.905" width="0.4064" layer="21"/>
<wire x1="-7.62" y1="1.905" x2="-7.62" y2="0" width="0.4064" layer="21"/>
<wire x1="-7.62" y1="0" x2="-7.62" y2="-1.905" width="0.4064" layer="21"/>
<wire x1="15.24" y1="8.509" x2="15.748" y2="8.001" width="0.127" layer="21" curve="-90"/>
<wire x1="15.24" y1="-8.509" x2="15.748" y2="-8.001" width="0.127" layer="21" curve="90"/>
<wire x1="-15.748" y1="-8.001" x2="-15.24" y2="-8.509" width="0.127" layer="21" curve="90"/>
<wire x1="-15.748" y1="8.001" x2="-15.24" y2="8.509" width="0.127" layer="21" curve="-90"/>
<wire x1="-11.557" y1="0" x2="-7.62" y2="0" width="0.127" layer="21"/>
<wire x1="-6.731" y1="0" x2="11.557" y2="0" width="0.127" layer="21"/>
<pad name="1" x="-13.716" y="0" drill="1.1938" diameter="3.1496" shape="octagon"/>
<pad name="2" x="13.716" y="0" drill="1.1938" diameter="3.1496" shape="octagon"/>
<text x="-5.08" y="0.762" size="1.778" layer="25" ratio="10">&gt;NAME</text>
<text x="-5.08" y="-2.54" size="1.778" layer="27" ratio="10">&gt;VALUE</text>
</package>
<package name="C27,5B20">
<description>Capacitor&lt;p&gt;
MKS4 outline 31.6 x 20 mm / RM 27.5 mm</description>
<wire x1="-15.24" y1="10.16" x2="15.24" y2="10.16" width="0.127" layer="21"/>
<wire x1="15.748" y1="9.652" x2="15.748" y2="-9.652" width="0.127" layer="21"/>
<wire x1="15.24" y1="-10.16" x2="-15.24" y2="-10.16" width="0.127" layer="21"/>
<wire x1="-15.748" y1="-9.652" x2="-15.748" y2="9.652" width="0.127" layer="21"/>
<wire x1="-6.731" y1="1.905" x2="-6.731" y2="0" width="0.4064" layer="21"/>
<wire x1="-6.731" y1="0" x2="-6.731" y2="-1.905" width="0.4064" layer="21"/>
<wire x1="-7.62" y1="1.905" x2="-7.62" y2="0" width="0.4064" layer="21"/>
<wire x1="-7.62" y1="0" x2="-7.62" y2="-1.905" width="0.4064" layer="21"/>
<wire x1="15.24" y1="10.16" x2="15.748" y2="9.652" width="0.127" layer="21" curve="-90"/>
<wire x1="15.24" y1="-10.16" x2="15.748" y2="-9.652" width="0.127" layer="21" curve="90"/>
<wire x1="-15.748" y1="-9.652" x2="-15.24" y2="-10.16" width="0.127" layer="21" curve="90"/>
<wire x1="-15.748" y1="9.652" x2="-15.24" y2="10.16" width="0.127" layer="21" curve="-90"/>
<wire x1="-11.557" y1="0" x2="-7.62" y2="0" width="0.127" layer="21"/>
<wire x1="-6.731" y1="0" x2="11.557" y2="0" width="0.127" layer="21"/>
<pad name="1" x="-13.716" y="0" drill="1.1938" diameter="3.1496" shape="octagon"/>
<pad name="2" x="13.716" y="0" drill="1.1938" diameter="3.1496" shape="octagon"/>
<text x="-5.08" y="2.54" size="1.778" layer="25" ratio="10">&gt;NAME</text>
<text x="-5.08" y="-4.318" size="1.778" layer="27" ratio="10">&gt;VALUE</text>
</package>
<package name="C27,5B9">
<description>Capacitor&lt;p&gt;
MKS4 outline 31.6 x 9 mm / RM 27.5 mm</description>
<wire x1="-15.24" y1="4.572" x2="15.24" y2="4.572" width="0.127" layer="21"/>
<wire x1="15.748" y1="4.064" x2="15.748" y2="-4.064" width="0.127" layer="21"/>
<wire x1="15.24" y1="-4.572" x2="-15.24" y2="-4.572" width="0.127" layer="21"/>
<wire x1="-15.748" y1="-4.064" x2="-15.748" y2="4.064" width="0.127" layer="21"/>
<wire x1="-6.731" y1="1.905" x2="-6.731" y2="0" width="0.4064" layer="21"/>
<wire x1="-6.731" y1="0" x2="-6.731" y2="-1.905" width="0.4064" layer="21"/>
<wire x1="-7.62" y1="1.905" x2="-7.62" y2="0" width="0.4064" layer="21"/>
<wire x1="-7.62" y1="0" x2="-7.62" y2="-1.905" width="0.4064" layer="21"/>
<wire x1="15.24" y1="4.572" x2="15.748" y2="4.064" width="0.127" layer="21" curve="-90"/>
<wire x1="15.24" y1="-4.572" x2="15.748" y2="-4.064" width="0.127" layer="21" curve="90"/>
<wire x1="-15.748" y1="-4.064" x2="-15.24" y2="-4.572" width="0.127" layer="21" curve="90"/>
<wire x1="-15.748" y1="4.064" x2="-15.24" y2="4.572" width="0.127" layer="21" curve="-90"/>
<wire x1="-11.557" y1="0" x2="-7.62" y2="0" width="0.127" layer="21"/>
<wire x1="-6.731" y1="0" x2="11.557" y2="0" width="0.127" layer="21"/>
<pad name="1" x="-13.716" y="0" drill="1.1938" diameter="3.1496" shape="octagon"/>
<pad name="2" x="13.716" y="0" drill="1.1938" diameter="3.1496" shape="octagon"/>
<text x="-5.08" y="0.762" size="1.778" layer="25" ratio="10">&gt;NAME</text>
<text x="-5.08" y="-2.54" size="1.778" layer="27" ratio="10">&gt;VALUE</text>
</package>
<package name="C37,5B15">
<description>Capacitor&lt;p&gt;
MKP4 outline 42 x 15 mm / RM 37.5 mm</description>
<wire x1="-20.32" y1="7.62" x2="20.32" y2="7.62" width="0.127" layer="21"/>
<wire x1="20.828" y1="7.112" x2="20.828" y2="-7.112" width="0.127" layer="21"/>
<wire x1="20.32" y1="-7.62" x2="-20.32" y2="-7.62" width="0.127" layer="21"/>
<wire x1="-20.828" y1="-7.112" x2="-20.828" y2="7.112" width="0.127" layer="21"/>
<wire x1="-6.731" y1="1.905" x2="-6.731" y2="0" width="0.4064" layer="21"/>
<wire x1="-6.731" y1="0" x2="-6.731" y2="-1.905" width="0.4064" layer="21"/>
<wire x1="-7.62" y1="1.905" x2="-7.62" y2="0" width="0.4064" layer="21"/>
<wire x1="-7.62" y1="0" x2="-7.62" y2="-1.905" width="0.4064" layer="21"/>
<wire x1="20.32" y1="7.62" x2="20.828" y2="7.112" width="0.127" layer="21" curve="-90"/>
<wire x1="20.32" y1="-7.62" x2="20.828" y2="-7.112" width="0.127" layer="21" curve="90"/>
<wire x1="-20.828" y1="-7.112" x2="-20.32" y2="-7.62" width="0.127" layer="21" curve="90"/>
<wire x1="-20.828" y1="7.112" x2="-20.32" y2="7.62" width="0.127" layer="21" curve="-90"/>
<wire x1="-16.002" y1="0" x2="-7.62" y2="0" width="0.127" layer="21"/>
<wire x1="-6.731" y1="0" x2="16.002" y2="0" width="0.127" layer="21"/>
<pad name="1" x="-18.796" y="0" drill="1.3208" diameter="3.1496" shape="octagon"/>
<pad name="2" x="18.796" y="0" drill="1.3208" diameter="3.1496" shape="octagon"/>
<text x="-5.08" y="0.762" size="1.778" layer="25" ratio="10">&gt;NAME</text>
<text x="-5.08" y="-2.54" size="1.778" layer="27" ratio="10">&gt;VALUE</text>
</package>
<package name="C37,5B19">
<description>Capacitor&lt;p&gt;
MKP4 outline 42 x 19 mm / RM 37.5 mm</description>
<wire x1="-20.32" y1="8.509" x2="20.32" y2="8.509" width="0.127" layer="21"/>
<wire x1="20.828" y1="8.001" x2="20.828" y2="-8.001" width="0.127" layer="21"/>
<wire x1="20.32" y1="-8.509" x2="-20.32" y2="-8.509" width="0.127" layer="21"/>
<wire x1="-20.828" y1="-8.001" x2="-20.828" y2="8.001" width="0.127" layer="21"/>
<wire x1="-6.731" y1="1.905" x2="-6.731" y2="0" width="0.4064" layer="21"/>
<wire x1="-6.731" y1="0" x2="-6.731" y2="-1.905" width="0.4064" layer="21"/>
<wire x1="-7.62" y1="1.905" x2="-7.62" y2="0" width="0.4064" layer="21"/>
<wire x1="-7.62" y1="0" x2="-7.62" y2="-1.905" width="0.4064" layer="21"/>
<wire x1="20.32" y1="8.509" x2="20.828" y2="8.001" width="0.127" layer="21" curve="-90"/>
<wire x1="20.32" y1="-8.509" x2="20.828" y2="-8.001" width="0.127" layer="21" curve="90"/>
<wire x1="-20.828" y1="-8.001" x2="-20.32" y2="-8.509" width="0.127" layer="21" curve="90"/>
<wire x1="-20.828" y1="8.001" x2="-20.32" y2="8.509" width="0.127" layer="21" curve="-90"/>
<wire x1="-16.002" y1="0" x2="-7.62" y2="0" width="0.127" layer="21"/>
<wire x1="-6.731" y1="0" x2="16.002" y2="0" width="0.127" layer="21"/>
<pad name="1" x="-18.796" y="0" drill="1.3208" diameter="3.1496" shape="octagon"/>
<pad name="2" x="18.796" y="0" drill="1.3208" diameter="3.1496" shape="octagon"/>
<text x="-5.08" y="0.762" size="1.778" layer="25" ratio="10">&gt;NAME</text>
<text x="-5.08" y="-2.54" size="1.778" layer="27" ratio="10">&gt;VALUE</text>
</package>
<package name="C37,5B20">
<description>Capacitor&lt;p&gt;
MKP4 outline 42 x 20 mm / RM 37.5 mm</description>
<wire x1="-20.32" y1="10.16" x2="20.32" y2="10.16" width="0.127" layer="21"/>
<wire x1="20.828" y1="9.652" x2="20.828" y2="-9.652" width="0.127" layer="21"/>
<wire x1="20.32" y1="-10.16" x2="-20.32" y2="-10.16" width="0.127" layer="21"/>
<wire x1="-20.828" y1="-9.652" x2="-20.828" y2="9.652" width="0.127" layer="21"/>
<wire x1="-6.731" y1="1.905" x2="-6.731" y2="0" width="0.4064" layer="21"/>
<wire x1="-6.731" y1="0" x2="-6.731" y2="-1.905" width="0.4064" layer="21"/>
<wire x1="-7.62" y1="1.905" x2="-7.62" y2="0" width="0.4064" layer="21"/>
<wire x1="-7.62" y1="0" x2="-7.62" y2="-1.905" width="0.4064" layer="21"/>
<wire x1="20.32" y1="10.16" x2="20.828" y2="9.652" width="0.127" layer="21" curve="-90"/>
<wire x1="20.32" y1="-10.16" x2="20.828" y2="-9.652" width="0.127" layer="21" curve="90"/>
<wire x1="-20.828" y1="-9.652" x2="-20.32" y2="-10.16" width="0.127" layer="21" curve="90"/>
<wire x1="-20.828" y1="9.652" x2="-20.32" y2="10.16" width="0.127" layer="21" curve="-90"/>
<wire x1="-16.002" y1="0" x2="-7.62" y2="0" width="0.127" layer="21"/>
<wire x1="-6.731" y1="0" x2="16.002" y2="0" width="0.127" layer="21"/>
<pad name="1" x="-18.796" y="0" drill="1.3208" diameter="3.1496" shape="octagon"/>
<pad name="2" x="18.796" y="0" drill="1.3208" diameter="3.1496" shape="octagon"/>
<text x="-5.08" y="0.762" size="1.778" layer="25" ratio="10">&gt;NAME</text>
<text x="-5.08" y="-2.54" size="1.778" layer="27" ratio="10">&gt;VALUE</text>
</package>
<package name="C5B2,5">
<description>Capacitor&lt;p&gt;
MKS2 outline 7.5 x 2.5 mm / RM 5.08 mm</description>
<wire x1="-0.3048" y1="0.635" x2="-0.3048" y2="0" width="0.3048" layer="21"/>
<wire x1="-0.3048" y1="0" x2="-0.3048" y2="-0.635" width="0.3048" layer="21"/>
<wire x1="-0.3048" y1="0" x2="-1.524" y2="0" width="0.127" layer="21"/>
<wire x1="0.3302" y1="0.635" x2="0.3302" y2="0" width="0.3048" layer="21"/>
<wire x1="0.3302" y1="0" x2="0.3302" y2="-0.635" width="0.3048" layer="21"/>
<wire x1="0.3302" y1="0" x2="1.524" y2="0" width="0.127" layer="21"/>
<wire x1="-3.683" y1="1.016" x2="-3.683" y2="-1.016" width="0.127" layer="21"/>
<wire x1="-3.429" y1="-1.27" x2="3.429" y2="-1.27" width="0.127" layer="21"/>
<wire x1="3.683" y1="-1.016" x2="3.683" y2="1.016" width="0.127" layer="21"/>
<wire x1="3.429" y1="1.27" x2="-3.429" y2="1.27" width="0.127" layer="21"/>
<wire x1="3.429" y1="1.27" x2="3.683" y2="1.016" width="0.127" layer="21" curve="-90"/>
<wire x1="3.429" y1="-1.27" x2="3.683" y2="-1.016" width="0.127" layer="21" curve="90"/>
<wire x1="-3.683" y1="-1.016" x2="-3.429" y2="-1.27" width="0.127" layer="21" curve="90"/>
<wire x1="-3.683" y1="1.016" x2="-3.429" y2="1.27" width="0.127" layer="21" curve="-90"/>
<pad name="1" x="-2.54" y="0" drill="0.8128" diameter="1.6002" shape="octagon"/>
<pad name="2" x="2.54" y="0" drill="0.8128" diameter="1.6002" shape="octagon"/>
<text x="4.191" y="0" size="1.27" layer="25" ratio="10">&gt;NAME</text>
<text x="4.191" y="-1.524" size="1.27" layer="27" ratio="10">&gt;VALUE</text>
</package>
<package name="C5B3">
<description>Capacitor&lt;p&gt;
MKS2 outline 7.5 x 3 mm / RM 5.08 mm</description>
<wire x1="-0.3048" y1="0.635" x2="-0.3048" y2="0" width="0.3048" layer="21"/>
<wire x1="-0.3048" y1="0" x2="-0.3048" y2="-0.635" width="0.3048" layer="21"/>
<wire x1="-0.3048" y1="0" x2="-1.524" y2="0" width="0.127" layer="21"/>
<wire x1="0.3302" y1="0.635" x2="0.3302" y2="0" width="0.3048" layer="21"/>
<wire x1="0.3302" y1="0" x2="0.3302" y2="-0.635" width="0.3048" layer="21"/>
<wire x1="0.3302" y1="0" x2="1.524" y2="0" width="0.127" layer="21"/>
<wire x1="-3.683" y1="1.27" x2="-3.683" y2="-1.27" width="0.127" layer="21"/>
<wire x1="-3.429" y1="-1.524" x2="3.429" y2="-1.524" width="0.127" layer="21"/>
<wire x1="3.683" y1="-1.27" x2="3.683" y2="1.27" width="0.127" layer="21"/>
<wire x1="3.429" y1="1.524" x2="-3.429" y2="1.524" width="0.127" layer="21"/>
<wire x1="3.429" y1="1.524" x2="3.683" y2="1.27" width="0.127" layer="21" curve="-90"/>
<wire x1="3.429" y1="-1.524" x2="3.683" y2="-1.27" width="0.127" layer="21" curve="90"/>
<wire x1="-3.683" y1="-1.27" x2="-3.429" y2="-1.524" width="0.127" layer="21" curve="90"/>
<wire x1="-3.683" y1="1.27" x2="-3.429" y2="1.524" width="0.127" layer="21" curve="-90"/>
<pad name="1" x="-2.54" y="0" drill="0.8128" diameter="1.6002" shape="octagon"/>
<pad name="2" x="2.54" y="0" drill="0.8128" diameter="1.6002" shape="octagon"/>
<text x="4.191" y="0" size="1.27" layer="25" ratio="10">&gt;NAME</text>
<text x="4.191" y="-1.524" size="1.27" layer="27" ratio="10">&gt;VALUE</text>
</package>
<package name="C5B3,5">
<description>Capacitor&lt;p&gt;
MKS2 outline 7.5 x 4 mm / RM 5.08 mm</description>
<wire x1="-0.3048" y1="0.635" x2="-0.3048" y2="0" width="0.3048" layer="21"/>
<wire x1="-0.3048" y1="0" x2="-0.3048" y2="-0.635" width="0.3048" layer="21"/>
<wire x1="-0.3048" y1="0" x2="-1.524" y2="0" width="0.127" layer="21"/>
<wire x1="0.3302" y1="0.635" x2="0.3302" y2="0" width="0.3048" layer="21"/>
<wire x1="0.3302" y1="0" x2="0.3302" y2="-0.635" width="0.3048" layer="21"/>
<wire x1="0.3302" y1="0" x2="1.524" y2="0" width="0.127" layer="21"/>
<wire x1="-3.683" y1="1.524" x2="-3.683" y2="-1.524" width="0.127" layer="21"/>
<wire x1="-3.429" y1="-1.778" x2="3.429" y2="-1.778" width="0.127" layer="21"/>
<wire x1="3.683" y1="-1.524" x2="3.683" y2="1.524" width="0.127" layer="21"/>
<wire x1="3.429" y1="1.778" x2="-3.429" y2="1.778" width="0.127" layer="21"/>
<wire x1="3.429" y1="1.778" x2="3.683" y2="1.524" width="0.127" layer="21" curve="-90"/>
<wire x1="3.429" y1="-1.778" x2="3.683" y2="-1.524" width="0.127" layer="21" curve="90"/>
<wire x1="-3.683" y1="-1.524" x2="-3.429" y2="-1.778" width="0.127" layer="21" curve="90"/>
<wire x1="-3.683" y1="1.524" x2="-3.429" y2="1.778" width="0.127" layer="21" curve="-90"/>
<pad name="1" x="-2.54" y="0" drill="0.8128" diameter="1.6002" shape="octagon"/>
<pad name="2" x="2.54" y="0" drill="0.8128" diameter="1.6002" shape="octagon"/>
<text x="4.318" y="0.254" size="1.27" layer="25" ratio="10">&gt;NAME</text>
<text x="4.318" y="-1.524" size="1.27" layer="27" ratio="10">&gt;VALUE</text>
</package>
<package name="C5B4,5">
<description>Capacitor&lt;p&gt;
MKS2 outline 7.5 x 4.5 mm / RM 5.08 mm</description>
<wire x1="-0.3048" y1="0.635" x2="-0.3048" y2="0" width="0.3048" layer="21"/>
<wire x1="-0.3048" y1="0" x2="-0.3048" y2="-0.635" width="0.3048" layer="21"/>
<wire x1="-0.3048" y1="0" x2="-1.524" y2="0" width="0.127" layer="21"/>
<wire x1="0.3302" y1="0.635" x2="0.3302" y2="0" width="0.3048" layer="21"/>
<wire x1="0.3302" y1="0" x2="0.3302" y2="-0.635" width="0.3048" layer="21"/>
<wire x1="0.3302" y1="0" x2="1.524" y2="0" width="0.127" layer="21"/>
<wire x1="-3.683" y1="2.032" x2="-3.683" y2="-2.032" width="0.127" layer="21"/>
<wire x1="-3.429" y1="-2.286" x2="3.429" y2="-2.286" width="0.127" layer="21"/>
<wire x1="3.683" y1="-2.032" x2="3.683" y2="2.032" width="0.127" layer="21"/>
<wire x1="3.429" y1="2.286" x2="-3.429" y2="2.286" width="0.127" layer="21"/>
<wire x1="3.429" y1="2.286" x2="3.683" y2="2.032" width="0.127" layer="21" curve="-90"/>
<wire x1="3.429" y1="-2.286" x2="3.683" y2="-2.032" width="0.127" layer="21" curve="90"/>
<wire x1="-3.683" y1="-2.032" x2="-3.429" y2="-2.286" width="0.127" layer="21" curve="90"/>
<wire x1="-3.683" y1="2.032" x2="-3.429" y2="2.286" width="0.127" layer="21" curve="-90"/>
<pad name="1" x="-2.54" y="0" drill="0.8128" diameter="1.6002" shape="octagon"/>
<pad name="2" x="2.54" y="0" drill="0.8128" diameter="1.6002" shape="octagon"/>
<text x="4.318" y="0.254" size="1.27" layer="25" ratio="10">&gt;NAME</text>
<text x="4.318" y="-1.524" size="1.27" layer="27" ratio="10">&gt;VALUE</text>
</package>
<package name="C5B5">
<description>Capacitor&lt;p&gt;
MKS2 outline 7.5 x 5 mm / RM 5.08 mm</description>
<wire x1="-0.3048" y1="0.635" x2="-0.3048" y2="0" width="0.3048" layer="21"/>
<wire x1="-0.3048" y1="0" x2="-0.3048" y2="-0.635" width="0.3048" layer="21"/>
<wire x1="-0.3048" y1="0" x2="-1.524" y2="0" width="0.127" layer="21"/>
<wire x1="0.3302" y1="0.635" x2="0.3302" y2="0" width="0.3048" layer="21"/>
<wire x1="0.3302" y1="0" x2="0.3302" y2="-0.635" width="0.3048" layer="21"/>
<wire x1="0.3302" y1="0" x2="1.524" y2="0" width="0.127" layer="21"/>
<wire x1="-3.683" y1="2.286" x2="-3.683" y2="-2.286" width="0.127" layer="21"/>
<wire x1="-3.429" y1="-2.54" x2="3.429" y2="-2.54" width="0.127" layer="21"/>
<wire x1="3.683" y1="-2.286" x2="3.683" y2="2.286" width="0.127" layer="21"/>
<wire x1="3.429" y1="2.54" x2="-3.429" y2="2.54" width="0.127" layer="21"/>
<wire x1="3.429" y1="2.54" x2="3.683" y2="2.286" width="0.127" layer="21" curve="-90"/>
<wire x1="3.429" y1="-2.54" x2="3.683" y2="-2.286" width="0.127" layer="21" curve="90"/>
<wire x1="-3.683" y1="-2.286" x2="-3.429" y2="-2.54" width="0.127" layer="21" curve="90"/>
<wire x1="-3.683" y1="2.286" x2="-3.429" y2="2.54" width="0.127" layer="21" curve="-90"/>
<pad name="1" x="-2.54" y="0" drill="0.8128" diameter="1.6002" shape="octagon"/>
<pad name="2" x="2.54" y="0" drill="0.8128" diameter="1.6002" shape="octagon"/>
<text x="-2.54" y="1.016" size="1.27" layer="25" ratio="10">&gt;NAME</text>
<text x="-2.54" y="-2.286" size="1.27" layer="27" ratio="10">&gt;VALUE</text>
</package>
<package name="C5B5,5">
<description>Capacitor&lt;p&gt;
MKS2 outline 7.5 x 5.5 mm / RM 5.08 mm</description>
<wire x1="-0.3048" y1="0.635" x2="-0.3048" y2="0" width="0.3048" layer="21"/>
<wire x1="-0.3048" y1="0" x2="-0.3048" y2="-0.635" width="0.3048" layer="21"/>
<wire x1="-0.3048" y1="0" x2="-1.524" y2="0" width="0.127" layer="21"/>
<wire x1="0.3302" y1="0.635" x2="0.3302" y2="0" width="0.3048" layer="21"/>
<wire x1="0.3302" y1="0" x2="0.3302" y2="-0.635" width="0.3048" layer="21"/>
<wire x1="0.3302" y1="0" x2="1.524" y2="0" width="0.127" layer="21"/>
<wire x1="-3.683" y1="2.54" x2="-3.683" y2="-2.54" width="0.127" layer="21"/>
<wire x1="-3.429" y1="-2.794" x2="3.429" y2="-2.794" width="0.127" layer="21"/>
<wire x1="3.683" y1="-2.54" x2="3.683" y2="2.54" width="0.127" layer="21"/>
<wire x1="3.429" y1="2.794" x2="-3.429" y2="2.794" width="0.127" layer="21"/>
<wire x1="3.429" y1="2.794" x2="3.683" y2="2.54" width="0.127" layer="21" curve="-90"/>
<wire x1="3.429" y1="-2.794" x2="3.683" y2="-2.54" width="0.127" layer="21" curve="90"/>
<wire x1="-3.683" y1="-2.54" x2="-3.429" y2="-2.794" width="0.127" layer="21" curve="90"/>
<wire x1="-3.683" y1="2.54" x2="-3.429" y2="2.794" width="0.127" layer="21" curve="-90"/>
<pad name="1" x="-2.54" y="0" drill="0.8128" diameter="1.6002" shape="octagon"/>
<pad name="2" x="2.54" y="0" drill="0.8128" diameter="1.6002" shape="octagon"/>
<text x="-2.54" y="1.016" size="1.27" layer="25" ratio="10">&gt;NAME</text>
<text x="-2.54" y="-2.286" size="1.27" layer="27" ratio="10">&gt;VALUE</text>
</package>
<package name="C5B7,2">
<description>Capacitor&lt;p&gt;
MKS2 outline 7.5 x 7.2 mm / RM 5.08 mm</description>
<wire x1="-1.524" y1="0" x2="-0.4572" y2="0" width="0.127" layer="21"/>
<wire x1="-0.4572" y1="0" x2="-0.4572" y2="0.762" width="0.4064" layer="21"/>
<wire x1="-0.4572" y1="0" x2="-0.4572" y2="-0.762" width="0.4064" layer="21"/>
<wire x1="0.4318" y1="0.762" x2="0.4318" y2="0" width="0.4064" layer="21"/>
<wire x1="0.4318" y1="0" x2="1.524" y2="0" width="0.127" layer="21"/>
<wire x1="0.4318" y1="0" x2="0.4318" y2="-0.762" width="0.4064" layer="21"/>
<wire x1="-3.683" y1="3.429" x2="-3.683" y2="-3.429" width="0.127" layer="21"/>
<wire x1="-3.429" y1="-3.683" x2="3.429" y2="-3.683" width="0.127" layer="21"/>
<wire x1="3.683" y1="-3.429" x2="3.683" y2="3.429" width="0.127" layer="21"/>
<wire x1="3.429" y1="3.683" x2="-3.429" y2="3.683" width="0.127" layer="21"/>
<wire x1="3.429" y1="3.683" x2="3.683" y2="3.429" width="0.127" layer="21" curve="-90"/>
<wire x1="3.429" y1="-3.683" x2="3.683" y2="-3.429" width="0.127" layer="21" curve="90"/>
<wire x1="-3.683" y1="-3.429" x2="-3.429" y2="-3.683" width="0.127" layer="21" curve="90"/>
<wire x1="-3.683" y1="3.429" x2="-3.429" y2="3.683" width="0.127" layer="21" curve="-90"/>
<pad name="1" x="-2.54" y="0" drill="0.8128" diameter="1.6002" shape="octagon"/>
<pad name="2" x="2.54" y="0" drill="0.8128" diameter="1.6002" shape="octagon"/>
<text x="-2.54" y="1.651" size="1.27" layer="25" ratio="10">&gt;NAME</text>
<text x="-3.175" y="-2.921" size="1.27" layer="27" ratio="10">&gt;VALUE</text>
</package>
<package name="C7,5B3">
<description>Capacitor&lt;p&gt;
MKS3 outline 10 x 3 mm / RM 7.62 mm</description>
<wire x1="4.826" y1="1.524" x2="-4.826" y2="1.524" width="0.127" layer="21"/>
<wire x1="-5.08" y1="1.27" x2="-5.08" y2="-1.27" width="0.127" layer="21"/>
<wire x1="-4.826" y1="-1.524" x2="4.826" y2="-1.524" width="0.127" layer="21"/>
<wire x1="5.08" y1="-1.27" x2="5.08" y2="1.27" width="0.127" layer="21"/>
<wire x1="4.826" y1="1.524" x2="5.08" y2="1.27" width="0.127" layer="21" curve="-90"/>
<wire x1="4.826" y1="-1.524" x2="5.08" y2="-1.27" width="0.127" layer="21" curve="90"/>
<wire x1="-5.08" y1="-1.27" x2="-4.826" y2="-1.524" width="0.127" layer="21" curve="90"/>
<wire x1="-5.08" y1="1.27" x2="-4.826" y2="1.524" width="0.127" layer="21" curve="-90"/>
<wire x1="0.508" y1="0" x2="2.54" y2="0" width="0.127" layer="21"/>
<wire x1="-2.54" y1="0" x2="-0.508" y2="0" width="0.127" layer="21"/>
<wire x1="-0.508" y1="0.889" x2="-0.508" y2="0" width="0.4064" layer="21"/>
<wire x1="-0.508" y1="0" x2="-0.508" y2="-0.889" width="0.4064" layer="21"/>
<wire x1="0.508" y1="0.889" x2="0.508" y2="0" width="0.4064" layer="21"/>
<wire x1="0.508" y1="0" x2="0.508" y2="-0.889" width="0.4064" layer="21"/>
<pad name="1" x="-3.81" y="0" drill="0.9144" diameter="1.905" shape="octagon"/>
<pad name="2" x="3.81" y="0" drill="0.9144" diameter="1.905" shape="octagon"/>
<text x="5.588" y="0.254" size="1.27" layer="25" ratio="10">&gt;NAME</text>
<text x="5.588" y="-1.397" size="1.27" layer="27" ratio="10">&gt;VALUE</text>
</package>
<package name="C7,5B4">
<description>Capacitor&lt;p&gt;
MKS3 outline 10 x 4 mm / RM 7.62 mm</description>
<wire x1="4.826" y1="2.032" x2="-4.826" y2="2.032" width="0.127" layer="21"/>
<wire x1="-5.08" y1="1.778" x2="-5.08" y2="-1.778" width="0.127" layer="21"/>
<wire x1="-4.826" y1="-2.032" x2="4.826" y2="-2.032" width="0.127" layer="21"/>
<wire x1="5.08" y1="-1.778" x2="5.08" y2="1.778" width="0.127" layer="21"/>
<wire x1="4.826" y1="2.032" x2="5.08" y2="1.778" width="0.127" layer="21" curve="-90"/>
<wire x1="4.826" y1="-2.032" x2="5.08" y2="-1.778" width="0.127" layer="21" curve="90"/>
<wire x1="-5.08" y1="-1.778" x2="-4.826" y2="-2.032" width="0.127" layer="21" curve="90"/>
<wire x1="-5.08" y1="1.778" x2="-4.826" y2="2.032" width="0.127" layer="21" curve="-90"/>
<wire x1="-1.27" y1="0" x2="2.667" y2="0" width="0.127" layer="21"/>
<wire x1="-2.667" y1="0" x2="-2.159" y2="0" width="0.127" layer="21"/>
<wire x1="-2.159" y1="1.27" x2="-2.159" y2="0" width="0.4064" layer="21"/>
<wire x1="-2.159" y1="0" x2="-2.159" y2="-1.27" width="0.4064" layer="21"/>
<wire x1="-1.27" y1="1.27" x2="-1.27" y2="0" width="0.4064" layer="21"/>
<wire x1="-1.27" y1="0" x2="-1.27" y2="-1.27" width="0.4064" layer="21"/>
<pad name="1" x="-3.81" y="0" drill="0.9144" diameter="1.905" shape="octagon"/>
<pad name="2" x="3.81" y="0" drill="0.9144" diameter="1.905" shape="octagon"/>
<text x="-0.635" y="0.381" size="1.27" layer="25" ratio="10">&gt;NAME</text>
<text x="-4.699" y="-3.683" size="1.27" layer="27" ratio="10">&gt;VALUE</text>
</package>
<package name="C7,5B5">
<description>Capacitor&lt;p&gt;
MKS3 outline 10 x 5 mm / RM 7.62 mm</description>
<wire x1="4.953" y1="2.54" x2="-4.953" y2="2.54" width="0.127" layer="21"/>
<wire x1="-5.207" y1="2.286" x2="-5.207" y2="-2.286" width="0.127" layer="21"/>
<wire x1="-4.953" y1="-2.54" x2="4.953" y2="-2.54" width="0.127" layer="21"/>
<wire x1="5.207" y1="-2.286" x2="5.207" y2="2.286" width="0.127" layer="21"/>
<wire x1="4.953" y1="2.54" x2="5.207" y2="2.286" width="0.127" layer="21" curve="-90"/>
<wire x1="4.953" y1="-2.54" x2="5.207" y2="-2.286" width="0.127" layer="21" curve="90"/>
<wire x1="-5.207" y1="-2.286" x2="-4.953" y2="-2.54" width="0.127" layer="21" curve="90"/>
<wire x1="-5.207" y1="2.286" x2="-4.953" y2="2.54" width="0.127" layer="21" curve="-90"/>
<wire x1="-1.27" y1="0" x2="2.667" y2="0" width="0.127" layer="21"/>
<wire x1="-2.667" y1="0" x2="-2.159" y2="0" width="0.127" layer="21"/>
<wire x1="-2.159" y1="1.27" x2="-2.159" y2="0" width="0.4064" layer="21"/>
<wire x1="-2.159" y1="0" x2="-2.159" y2="-1.27" width="0.4064" layer="21"/>
<wire x1="-1.27" y1="1.27" x2="-1.27" y2="0" width="0.4064" layer="21"/>
<wire x1="-1.27" y1="0" x2="-1.27" y2="-1.27" width="0.4064" layer="21"/>
<pad name="1" x="-3.81" y="0" drill="0.9144" diameter="1.905" shape="octagon"/>
<pad name="2" x="3.81" y="0" drill="0.9144" diameter="1.905" shape="octagon"/>
<text x="-0.635" y="0.762" size="1.27" layer="25" ratio="10">&gt;NAME</text>
<text x="-4.699" y="-4.064" size="1.27" layer="27" ratio="10">&gt;VALUE</text>
</package>
<package name="C7,5B6">
<description>Capacitor&lt;p&gt;
MKS3 outline 10 x 6 mm / RM 7.62 mm</description>
<wire x1="4.953" y1="3.048" x2="-4.953" y2="3.048" width="0.127" layer="21"/>
<wire x1="-5.207" y1="2.794" x2="-5.207" y2="-2.794" width="0.127" layer="21"/>
<wire x1="-4.953" y1="-3.048" x2="4.953" y2="-3.048" width="0.127" layer="21"/>
<wire x1="5.207" y1="-2.794" x2="5.207" y2="2.794" width="0.127" layer="21"/>
<wire x1="4.953" y1="3.048" x2="5.207" y2="2.794" width="0.127" layer="21" curve="-90"/>
<wire x1="4.953" y1="-3.048" x2="5.207" y2="-2.794" width="0.127" layer="21" curve="90"/>
<wire x1="-5.207" y1="-2.794" x2="-4.953" y2="-3.048" width="0.127" layer="21" curve="90"/>
<wire x1="-5.207" y1="2.794" x2="-4.953" y2="3.048" width="0.127" layer="21" curve="-90"/>
<wire x1="-1.27" y1="0" x2="2.667" y2="0" width="0.127" layer="21"/>
<wire x1="-2.667" y1="0" x2="-2.159" y2="0" width="0.127" layer="21"/>
<wire x1="-2.159" y1="1.27" x2="-2.159" y2="0" width="0.4064" layer="21"/>
<wire x1="-2.159" y1="0" x2="-2.159" y2="-1.27" width="0.4064" layer="21"/>
<wire x1="-1.27" y1="1.27" x2="-1.27" y2="0" width="0.4064" layer="21"/>
<wire x1="-1.27" y1="0" x2="-1.27" y2="-1.27" width="0.4064" layer="21"/>
<pad name="1" x="-3.81" y="0" drill="0.9144" diameter="1.905" shape="octagon"/>
<pad name="2" x="3.81" y="0" drill="0.9144" diameter="1.905" shape="octagon"/>
<text x="-0.635" y="1.27" size="1.27" layer="25" ratio="10">&gt;NAME</text>
<text x="-0.635" y="-2.54" size="1.27" layer="27" ratio="10">&gt;VALUE</text>
</package>
</packages>
<symbols>
<symbol name="C">
<wire x1="-2.54" y1="0" x2="-0.508" y2="0" width="0.1524" layer="94"/>
<wire x1="-0.508" y1="1.524" x2="-0.508" y2="-1.524" width="0.254" layer="94"/>
<wire x1="2.54" y1="0" x2="0.508" y2="0" width="0.1524" layer="94"/>
<wire x1="0.508" y1="1.524" x2="0.508" y2="0" width="0.254" layer="94"/>
<wire x1="-0.508" y1="1.524" x2="-0.762" y2="1.524" width="0.254" layer="94"/>
<wire x1="-1.016" y1="1.524" x2="-1.016" y2="-1.524" width="0.254" layer="94"/>
<wire x1="-1.016" y1="-1.524" x2="-0.762" y2="-1.524" width="0.254" layer="94"/>
<wire x1="-0.762" y1="-1.524" x2="-0.762" y2="1.524" width="0.254" layer="94"/>
<wire x1="-0.762" y1="1.524" x2="-1.016" y2="1.524" width="0.254" layer="94"/>
<wire x1="-0.762" y1="-1.524" x2="-0.508" y2="-1.524" width="0.254" layer="94"/>
<wire x1="0.508" y1="-1.524" x2="0.762" y2="-1.524" width="0.254" layer="94"/>
<wire x1="1.016" y1="-1.524" x2="1.016" y2="1.524" width="0.254" layer="94"/>
<wire x1="1.016" y1="1.524" x2="0.762" y2="1.524" width="0.254" layer="94"/>
<wire x1="0.762" y1="1.524" x2="0.762" y2="-1.524" width="0.254" layer="94"/>
<wire x1="0.762" y1="1.524" x2="0.508" y2="1.524" width="0.254" layer="94"/>
<wire x1="0.762" y1="-1.524" x2="1.016" y2="-1.524" width="0.254" layer="94"/>
<wire x1="0.508" y1="0" x2="0.508" y2="-1.524" width="0.254" layer="94"/>
<text x="2.54" y="0.635" size="1.778" layer="95">&gt;NAME</text>
<text x="2.54" y="-2.159" size="1.778" layer="96">&gt;VALUE</text>
<text x="-2.794" y="-1.27" size="0.8636" layer="93">1</text>
<text x="2.286" y="-1.27" size="0.8636" layer="93">2</text>
<pin name="1" x="-2.54" y="0" visible="off" length="point" direction="pas" swaplevel="1"/>
<pin name="2" x="2.54" y="0" visible="off" length="point" direction="pas" swaplevel="1" rot="R180"/>
</symbol>
</symbols>
<devicesets>
<deviceset name="C">
<description>Capacitor&lt;p&gt;
Grid / Package width</description>
<gates>
<gate name="G$1" symbol="C" x="0" y="0"/>
</gates>
<devices>
<device name="10/4" package="C10B4">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="10/5" package="C10B5">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="10/6" package="C10B6">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="15/5" package="C15B5">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="15/6" package="C15B6">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="15/7" package="C15B7">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="15/8" package="C15B8">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="15/9" package="C15B9">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="2.5/3" package="C2,5-2">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="2.5/2" package="C2,5-2">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="2.5/4" package="C2,5-4">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="2.5/5" package="C2,5-5">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="2.5/6" package="C2,5-6">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="22/10" package="C22,5B10">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="22/11" package="C22,5B11">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="22/6" package="C22,5B6">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="22/7" package="C22,5B7">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="22/8" package="C22,5B8">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="27/11" package="C27,5B11">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="27/13" package="C27,5B13">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="27/15" package="C27,5B15">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="27/17" package="C27,5B17">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="27/20" package="C27,5B20">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="27/9" package="C27,5B9">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="37/15" package="C37,5B15">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="37/19" package="C37,5B19">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="37/20" package="C37,5B20">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="5/2.5" package="C5B2,5">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="5/3" package="C5B3">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="5/3.5" package="C5B3,5">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="5/4.5" package="C5B4,5">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="5/5" package="C5B5">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="5/5.5" package="C5B5,5">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="5/7.2" package="C5B7,2">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="7.5/3" package="C7,5B3">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="7.5/4" package="C7,5B4">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="7.5/5" package="C7,5B5">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="7.5/6" package="C7,5B6">
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
<library name="special">
<packages>
<package name="QS">
<description>Quarz&lt;p&gt;
Vertical</description>
<wire x1="-3.429" y1="-2.286" x2="3.429" y2="-2.286" width="0.127" layer="21"/>
<wire x1="3.429" y1="2.286" x2="-3.429" y2="2.286" width="0.127" layer="21"/>
<wire x1="-3.429" y1="-1.778" x2="3.429" y2="-1.778" width="0.0508" layer="21"/>
<wire x1="3.429" y1="1.778" x2="-3.429" y2="1.778" width="0.0508" layer="21"/>
<wire x1="3.429" y1="1.778" x2="3.429" y2="-1.778" width="0.0508" layer="21" curve="-180"/>
<wire x1="3.429" y1="2.286" x2="3.429" y2="-2.286" width="0.127" layer="21" curve="-180"/>
<wire x1="-3.429" y1="2.286" x2="-3.429" y2="-2.286" width="0.127" layer="21" curve="180"/>
<wire x1="-3.429" y1="1.778" x2="-3.429" y2="-1.778" width="0.0508" layer="21" curve="180"/>
<pad name="1" x="-2.54" y="0" drill="0.6096" diameter="1.6002" shape="octagon"/>
<pad name="2" x="2.54" y="0" drill="0.6096" diameter="1.6002" shape="octagon"/>
<text x="-5.08" y="-3.937" size="1.27" layer="27" ratio="10">&gt;VALUE</text>
<text x="-5.08" y="2.667" size="1.27" layer="25" ratio="10">&gt;NAME</text>
</package>
</packages>
<symbols>
<symbol name="XTAL">
<wire x1="-1.27" y1="2.54" x2="1.397" y2="2.54" width="0.4064" layer="94"/>
<wire x1="1.397" y1="2.54" x2="1.397" y2="-2.54" width="0.4064" layer="94"/>
<wire x1="1.397" y1="-2.54" x2="-1.27" y2="-2.54" width="0.4064" layer="94"/>
<wire x1="-1.27" y1="2.54" x2="-1.27" y2="-2.54" width="0.4064" layer="94"/>
<wire x1="2.3368" y1="2.54" x2="2.3368" y2="-2.54" width="0.4064" layer="94"/>
<wire x1="-2.286" y1="2.54" x2="-2.286" y2="-2.54" width="0.4064" layer="94"/>
<text x="-5.08" y="3.81" size="1.778" layer="95">&gt;NAME</text>
<text x="-5.08" y="-5.08" size="1.778" layer="96">&gt;VALUE</text>
<pin name="2" x="5.08" y="0" visible="pad" length="short" direction="pas" swaplevel="1" rot="R180"/>
<pin name="1" x="-5.08" y="0" visible="pad" length="short" direction="pas" swaplevel="1"/>
</symbol>
</symbols>
<devicesets>
<deviceset name="XTAL/S" prefix="Q" uservalue="yes">
<description>Quarz</description>
<gates>
<gate name="G$1" symbol="XTAL" x="0" y="0"/>
</gates>
<devices>
<device name="" package="QS">
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
<library name="rcl">
<packages>
<package name="R0402">
<description>Resistor&lt;p&gt;
chip</description>
<wire x1="-0.2451" y1="0.2238" x2="0.2451" y2="0.2238" width="0.127" layer="51"/>
<wire x1="0.2451" y1="-0.2238" x2="-0.2451" y2="-0.2238" width="0.127" layer="51"/>
<wire x1="-1.4732" y1="0.4826" x2="1.4732" y2="0.4826" width="0.0508" layer="39"/>
<wire x1="1.4732" y1="0.4826" x2="1.4732" y2="-0.4826" width="0.0508" layer="39"/>
<wire x1="1.4732" y1="-0.4826" x2="-1.4732" y2="-0.4826" width="0.0508" layer="39"/>
<wire x1="-1.4732" y1="-0.4826" x2="-1.4732" y2="0.4826" width="0.0508" layer="39"/>
<smd name="1" x="-0.65" y="0" dx="0.7" dy="0.8998" layer="1"/>
<smd name="2" x="0.65" y="0" dx="0.7" dy="0.8998" layer="1"/>
<text x="-0.635" y="0.635" size="1.27" layer="25">&gt;NAME</text>
<text x="-0.635" y="-1.905" size="1.27" layer="27">&gt;VALUE</text>
<rectangle x1="-0.554" y1="-0.3048" x2="-0.254" y2="0.2951" layer="51"/>
<rectangle x1="0.2588" y1="-0.3048" x2="0.5588" y2="0.2951" layer="51"/>
<rectangle x1="-0.1999" y1="-0.4001" x2="0.1999" y2="0.4001" layer="35"/>
</package>
<package name="R0603">
<description>Resistor&lt;p&gt;
chip</description>
<wire x1="-0.4318" y1="-0.3556" x2="0.4318" y2="-0.3556" width="0.127" layer="51"/>
<wire x1="0.4318" y1="0.3556" x2="-0.4318" y2="0.3556" width="0.127" layer="51"/>
<wire x1="-1.4732" y1="0.9827" x2="1.4732" y2="0.9827" width="0.0508" layer="39"/>
<wire x1="1.4732" y1="0.9827" x2="1.4732" y2="-0.9827" width="0.0508" layer="39"/>
<wire x1="1.4732" y1="-0.9827" x2="-1.4732" y2="-0.9827" width="0.0508" layer="39"/>
<wire x1="-1.4732" y1="-0.9827" x2="-1.4732" y2="0.9827" width="0.0508" layer="39"/>
<smd name="1" x="-0.8499" y="0" dx="1" dy="1.1" layer="1"/>
<smd name="2" x="0.8499" y="0" dx="1" dy="1.1" layer="1"/>
<text x="-0.635" y="0.635" size="1.27" layer="25">&gt;NAME</text>
<text x="-0.635" y="-1.905" size="1.27" layer="27">&gt;VALUE</text>
<rectangle x1="0.4318" y1="-0.4318" x2="0.8382" y2="0.4318" layer="51"/>
<rectangle x1="-0.8382" y1="-0.4318" x2="-0.4318" y2="0.4318" layer="51"/>
<rectangle x1="-0.1999" y1="-0.4001" x2="0.1999" y2="0.4001" layer="35"/>
</package>
<package name="R0805">
<description>Resistor&lt;p&gt;
chip</description>
<wire x1="-0.4097" y1="0.635" x2="0.4097" y2="0.635" width="0.127" layer="51"/>
<wire x1="-0.4097" y1="-0.635" x2="0.4097" y2="-0.635" width="0.127" layer="51"/>
<wire x1="-1.9733" y1="0.9827" x2="1.9733" y2="0.9827" width="0.0508" layer="39"/>
<wire x1="1.9733" y1="0.9827" x2="1.9733" y2="-0.9827" width="0.0508" layer="39"/>
<wire x1="1.9733" y1="-0.9827" x2="-1.9733" y2="-0.9827" width="0.0508" layer="39"/>
<wire x1="-1.9733" y1="-0.9827" x2="-1.9733" y2="0.9827" width="0.0508" layer="39"/>
<smd name="1" x="-0.8499" y="0" dx="1.3" dy="1.5" layer="1"/>
<smd name="2" x="0.8499" y="0" dx="1.3" dy="1.5" layer="1"/>
<text x="-0.635" y="1.27" size="1.27" layer="25">&gt;NAME</text>
<text x="-0.635" y="-2.54" size="1.27" layer="27">&gt;VALUE</text>
<rectangle x1="0.4064" y1="-0.6985" x2="1.0564" y2="0.7015" layer="51"/>
<rectangle x1="-1.0668" y1="-0.6985" x2="-0.4168" y2="0.7015" layer="51"/>
<rectangle x1="-0.1999" y1="-0.5001" x2="0.1999" y2="0.5001" layer="35"/>
</package>
<package name="R0805W">
<description>Resistor&lt;p&gt;
chip / Wave soldering</description>
<wire x1="-0.4097" y1="0.635" x2="0.4097" y2="0.635" width="0.127" layer="51"/>
<wire x1="-0.4097" y1="-0.635" x2="0.4097" y2="-0.635" width="0.127" layer="51"/>
<wire x1="-1.9733" y1="0.9827" x2="1.9733" y2="0.9827" width="0.0508" layer="39"/>
<wire x1="1.9733" y1="0.9827" x2="1.9733" y2="-0.9827" width="0.0508" layer="39"/>
<wire x1="1.9733" y1="-0.9827" x2="-1.9733" y2="-0.9827" width="0.0508" layer="39"/>
<wire x1="-1.9733" y1="-0.9827" x2="-1.9733" y2="0.9827" width="0.0508" layer="39"/>
<smd name="1" x="-0.9398" y="0" dx="1.5" dy="1" layer="1"/>
<smd name="2" x="0.9398" y="0" dx="1.5" dy="1" layer="1"/>
<text x="-0.635" y="1.27" size="1.27" layer="25">&gt;NAME</text>
<text x="-0.635" y="-2.54" size="1.27" layer="27">&gt;VALUE</text>
<rectangle x1="0.4064" y1="-0.6985" x2="1.0564" y2="0.7015" layer="51"/>
<rectangle x1="-1.0668" y1="-0.6985" x2="-0.4168" y2="0.7015" layer="51"/>
<rectangle x1="-0.1999" y1="-0.5001" x2="0.1999" y2="0.5001" layer="35"/>
</package>
<package name="R1005">
<description>Resistor&lt;p&gt;
chip</description>
<wire x1="-0.2451" y1="0.2238" x2="0.2451" y2="0.2238" width="0.127" layer="51"/>
<wire x1="0.2451" y1="-0.2238" x2="-0.2451" y2="-0.2238" width="0.127" layer="51"/>
<wire x1="-1.4732" y1="0.4826" x2="1.4732" y2="0.4826" width="0.0508" layer="39"/>
<wire x1="1.4732" y1="0.4826" x2="1.4732" y2="-0.4826" width="0.0508" layer="39"/>
<wire x1="1.4732" y1="-0.4826" x2="-1.4732" y2="-0.4826" width="0.0508" layer="39"/>
<wire x1="-1.4732" y1="-0.4826" x2="-1.4732" y2="0.4826" width="0.0508" layer="39"/>
<smd name="1" x="-0.65" y="0" dx="0.7" dy="0.8998" layer="1"/>
<smd name="2" x="0.65" y="0" dx="0.7" dy="0.8998" layer="1"/>
<text x="-0.635" y="0.635" size="1.27" layer="25">&gt;NAME</text>
<text x="-0.635" y="-1.905" size="1.27" layer="27">&gt;VALUE</text>
<rectangle x1="-0.554" y1="-0.3048" x2="-0.254" y2="0.2951" layer="51"/>
<rectangle x1="0.2588" y1="-0.3048" x2="0.5588" y2="0.2951" layer="51"/>
<rectangle x1="-0.1999" y1="-0.3" x2="0.1999" y2="0.3" layer="35"/>
</package>
<package name="R1206">
<description>Resistor&lt;p&gt;
chip</description>
<wire x1="0.9525" y1="-0.8128" x2="-0.9652" y2="-0.8128" width="0.127" layer="51"/>
<wire x1="0.9525" y1="0.8128" x2="-0.9652" y2="0.8128" width="0.127" layer="51"/>
<wire x1="-2.4732" y1="0.9827" x2="2.4732" y2="0.9827" width="0.0508" layer="39"/>
<wire x1="2.4732" y1="0.9827" x2="2.4732" y2="-0.9827" width="0.0508" layer="39"/>
<wire x1="2.4732" y1="-0.9827" x2="-2.4732" y2="-0.9827" width="0.0508" layer="39"/>
<wire x1="-2.4732" y1="-0.9827" x2="-2.4732" y2="0.9827" width="0.0508" layer="39"/>
<smd name="2" x="1.4224" y="0" dx="1.6002" dy="1.8034" layer="1"/>
<smd name="1" x="-1.4224" y="0" dx="1.6002" dy="1.8034" layer="1"/>
<text x="-1.27" y="1.27" size="1.27" layer="25">&gt;NAME</text>
<text x="-1.27" y="-2.54" size="1.27" layer="27">&gt;VALUE</text>
<rectangle x1="-1.6891" y1="-0.8763" x2="-0.9525" y2="0.8763" layer="51"/>
<rectangle x1="0.9525" y1="-0.8763" x2="1.6891" y2="0.8763" layer="51"/>
<rectangle x1="-0.3" y1="-0.7" x2="0.3" y2="0.7" layer="35"/>
</package>
<package name="R1206W">
<description>Resistor&lt;p&gt;
chip / Wave soldering</description>
<wire x1="-0.9134" y1="0.8001" x2="0.888" y2="0.8001" width="0.127" layer="51"/>
<wire x1="-0.9134" y1="-0.8001" x2="0.888" y2="-0.8001" width="0.127" layer="51"/>
<wire x1="-2.4732" y1="0.9827" x2="2.4732" y2="0.9827" width="0.0508" layer="39"/>
<wire x1="2.4732" y1="0.9827" x2="2.4732" y2="-0.9827" width="0.0508" layer="39"/>
<wire x1="2.4732" y1="-0.9827" x2="-2.4732" y2="-0.9827" width="0.0508" layer="39"/>
<wire x1="-2.4732" y1="-0.9827" x2="-2.4732" y2="0.9827" width="0.0508" layer="39"/>
<smd name="1" x="-1.4986" y="0" dx="1.8" dy="1.1998" layer="1"/>
<smd name="2" x="1.4986" y="0" dx="1.8" dy="1.1998" layer="1"/>
<text x="-1.905" y="1.27" size="1.27" layer="25">&gt;NAME</text>
<text x="-1.905" y="-2.54" size="1.27" layer="27">&gt;VALUE</text>
<rectangle x1="-1.651" y1="-0.8763" x2="-0.9009" y2="0.8738" layer="51"/>
<rectangle x1="0.889" y1="-0.8763" x2="1.6391" y2="0.8738" layer="51"/>
<rectangle x1="-0.3" y1="-0.7" x2="0.3" y2="0.7" layer="35"/>
</package>
<package name="R1210">
<description>Resistor&lt;p&gt;
chip</description>
<wire x1="-0.9134" y1="1.2192" x2="0.9388" y2="1.2192" width="0.127" layer="51"/>
<wire x1="-0.9134" y1="-1.2192" x2="0.9388" y2="-1.2192" width="0.127" layer="51"/>
<wire x1="-2.4732" y1="1.4826" x2="2.4732" y2="1.4826" width="0.0508" layer="39"/>
<wire x1="2.4732" y1="1.4826" x2="2.4732" y2="-1.4826" width="0.0508" layer="39"/>
<wire x1="2.4732" y1="-1.4826" x2="-2.4732" y2="-1.4826" width="0.0508" layer="39"/>
<wire x1="-2.4732" y1="-1.4826" x2="-2.4732" y2="1.4826" width="0.0508" layer="39"/>
<smd name="1" x="-1.4" y="0" dx="1.5996" dy="2.7" layer="1"/>
<smd name="2" x="1.4" y="0" dx="1.5996" dy="2.7" layer="1"/>
<text x="-2.54" y="1.905" size="1.27" layer="25">&gt;NAME</text>
<text x="-2.54" y="-3.175" size="1.27" layer="27">&gt;VALUE</text>
<rectangle x1="-1.651" y1="-1.3081" x2="-0.9009" y2="1.2918" layer="51"/>
<rectangle x1="0.9144" y1="-1.3081" x2="1.6645" y2="1.2918" layer="51"/>
<rectangle x1="-0.3" y1="-0.8999" x2="0.3" y2="0.8999" layer="35"/>
</package>
<package name="R1210W">
<description>Resistor&lt;p&gt;
chip / Wave soldering</description>
<wire x1="-0.9134" y1="1.2192" x2="0.9388" y2="1.2192" width="0.127" layer="51"/>
<wire x1="-0.9134" y1="-1.2192" x2="0.9388" y2="-1.2192" width="0.127" layer="51"/>
<wire x1="-2.4732" y1="1.4826" x2="2.4732" y2="1.4826" width="0.0508" layer="39"/>
<wire x1="2.4732" y1="1.4826" x2="2.4732" y2="-1.4826" width="0.0508" layer="39"/>
<wire x1="2.4732" y1="-1.4826" x2="-2.4732" y2="-1.4826" width="0.0508" layer="39"/>
<wire x1="-2.4732" y1="-1.4826" x2="-2.4732" y2="1.4826" width="0.0508" layer="39"/>
<smd name="1" x="-1.4986" y="0" dx="1.8" dy="1.8" layer="1"/>
<smd name="2" x="1.4986" y="0" dx="1.8" dy="1.8" layer="1"/>
<text x="-2.54" y="1.905" size="1.27" layer="25">&gt;NAME</text>
<text x="-2.54" y="-3.175" size="1.27" layer="27">&gt;VALUE</text>
<rectangle x1="-1.651" y1="-1.3081" x2="-0.9009" y2="1.2918" layer="51"/>
<rectangle x1="0.9144" y1="-1.3081" x2="1.6645" y2="1.2918" layer="51"/>
<rectangle x1="-0.3" y1="-0.8001" x2="0.3" y2="0.8001" layer="35"/>
</package>
<package name="R2010">
<description>Resistor&lt;p&gt;
chip</description>
<wire x1="-1.6619" y1="1.2446" x2="1.6619" y2="1.2446" width="0.127" layer="51"/>
<wire x1="-1.6365" y1="-1.2446" x2="1.6873" y2="-1.2446" width="0.127" layer="51"/>
<wire x1="-3.4732" y1="1.4826" x2="3.4732" y2="1.4826" width="0.0508" layer="39"/>
<wire x1="3.4732" y1="1.4826" x2="3.4732" y2="-1.4826" width="0.0508" layer="39"/>
<wire x1="3.4732" y1="-1.4826" x2="-3.4732" y2="-1.4826" width="0.0508" layer="39"/>
<wire x1="-3.4732" y1="-1.4826" x2="-3.4732" y2="1.4826" width="0.0508" layer="39"/>
<smd name="1" x="-2.1999" y="0" dx="1.8" dy="2.7" layer="1"/>
<smd name="2" x="2.1999" y="0" dx="1.8" dy="2.7" layer="1"/>
<text x="-3.175" y="1.905" size="1.27" layer="25">&gt;NAME</text>
<text x="-3.175" y="-3.175" size="1.27" layer="27">&gt;VALUE</text>
<rectangle x1="-2.4892" y1="-1.3208" x2="-1.6393" y2="1.3292" layer="51"/>
<rectangle x1="1.651" y1="-1.3208" x2="2.5009" y2="1.3292" layer="51"/>
</package>
<package name="R2010W">
<description>Resistor&lt;p&gt;
chip / Wave soldering</description>
<wire x1="-1.6619" y1="1.2446" x2="1.6619" y2="1.2446" width="0.127" layer="51"/>
<wire x1="-1.6365" y1="-1.2446" x2="1.6873" y2="-1.2446" width="0.127" layer="51"/>
<wire x1="-3.4732" y1="1.4826" x2="3.4732" y2="1.4826" width="0.0508" layer="39"/>
<wire x1="3.4732" y1="1.4826" x2="3.4732" y2="-1.4826" width="0.0508" layer="39"/>
<wire x1="3.4732" y1="-1.4826" x2="-3.4732" y2="-1.4826" width="0.0508" layer="39"/>
<wire x1="-3.4732" y1="-1.4826" x2="-3.4732" y2="1.4826" width="0.0508" layer="39"/>
<smd name="1" x="-2.3114" y="0" dx="2" dy="1.8" layer="1"/>
<smd name="2" x="2.3114" y="0" dx="2" dy="1.8" layer="1"/>
<text x="-2.54" y="1.905" size="1.27" layer="25">&gt;NAME</text>
<text x="-2.54" y="-3.175" size="1.27" layer="27">&gt;VALUE</text>
<rectangle x1="-2.4892" y1="-1.3208" x2="-1.6393" y2="1.3292" layer="51"/>
<rectangle x1="1.651" y1="-1.3208" x2="2.5009" y2="1.3292" layer="51"/>
</package>
<package name="R2012">
<description>Resistor&lt;p&gt;
chip</description>
<wire x1="-0.4097" y1="0.635" x2="0.4097" y2="0.635" width="0.127" layer="51"/>
<wire x1="-0.4097" y1="-0.635" x2="0.4097" y2="-0.635" width="0.127" layer="51"/>
<wire x1="-1.9733" y1="0.9827" x2="1.9733" y2="0.9827" width="0.0508" layer="39"/>
<wire x1="1.9733" y1="0.9827" x2="1.9733" y2="-0.9827" width="0.0508" layer="39"/>
<wire x1="1.9733" y1="-0.9827" x2="-1.9733" y2="-0.9827" width="0.0508" layer="39"/>
<wire x1="-1.9733" y1="-0.9827" x2="-1.9733" y2="0.9827" width="0.0508" layer="39"/>
<smd name="1" x="-0.8499" y="0" dx="1.3" dy="1.5" layer="1"/>
<smd name="2" x="0.8499" y="0" dx="1.3" dy="1.5" layer="1"/>
<text x="-0.635" y="1.27" size="1.27" layer="25">&gt;NAME</text>
<text x="-0.635" y="-2.54" size="1.27" layer="27">&gt;VALUE</text>
<rectangle x1="0.4064" y1="-0.6985" x2="1.0564" y2="0.7015" layer="51"/>
<rectangle x1="-1.0668" y1="-0.6985" x2="-0.4168" y2="0.7015" layer="51"/>
<rectangle x1="-0.1001" y1="-0.5999" x2="0.1001" y2="0.5999" layer="35"/>
</package>
<package name="R2012W">
<description>Resistor&lt;p&gt;
chip / Wave soldering</description>
<wire x1="-0.4097" y1="0.635" x2="0.4097" y2="0.635" width="0.127" layer="51"/>
<wire x1="-0.4097" y1="-0.635" x2="0.4097" y2="-0.635" width="0.127" layer="51"/>
<wire x1="-1.9733" y1="0.9827" x2="1.9733" y2="0.9827" width="0.0508" layer="39"/>
<wire x1="1.9733" y1="0.9827" x2="1.9733" y2="-0.9827" width="0.0508" layer="39"/>
<wire x1="1.9733" y1="-0.9827" x2="-1.9733" y2="-0.9827" width="0.0508" layer="39"/>
<wire x1="-1.9733" y1="-0.9827" x2="-1.9733" y2="0.9827" width="0.0508" layer="39"/>
<smd name="1" x="-0.9398" y="0" dx="1.5" dy="1" layer="1"/>
<smd name="2" x="0.9398" y="0" dx="1.5" dy="1" layer="1"/>
<text x="-0.635" y="1.27" size="1.27" layer="25">&gt;NAME</text>
<text x="-0.635" y="-2.54" size="1.27" layer="27">&gt;VALUE</text>
<rectangle x1="0.4064" y1="-0.6985" x2="1.0564" y2="0.7015" layer="51"/>
<rectangle x1="-1.0668" y1="-0.6985" x2="-0.4168" y2="0.7015" layer="51"/>
<rectangle x1="-0.1001" y1="-0.5999" x2="0.1001" y2="0.5999" layer="35"/>
</package>
<package name="R2512">
<description>Resistor&lt;p&gt;
chip</description>
<wire x1="-2.3617" y1="1.4732" x2="2.3871" y2="1.4732" width="0.127" layer="51"/>
<wire x1="-2.3617" y1="-1.4732" x2="2.3871" y2="-1.4732" width="0.127" layer="51"/>
<wire x1="-3.9733" y1="1.9827" x2="3.9733" y2="1.9827" width="0.0508" layer="39"/>
<wire x1="3.9733" y1="1.9827" x2="3.9733" y2="-1.9827" width="0.0508" layer="39"/>
<wire x1="3.9733" y1="-1.9827" x2="-3.9733" y2="-1.9827" width="0.0508" layer="39"/>
<wire x1="-3.9733" y1="-1.9827" x2="-3.9733" y2="1.9827" width="0.0508" layer="39"/>
<smd name="1" x="-2.8001" y="0" dx="1.8" dy="3.1998" layer="1"/>
<smd name="2" x="2.8001" y="0" dx="1.8" dy="3.1998" layer="1"/>
<text x="-2.54" y="1.905" size="1.27" layer="25">&gt;NAME</text>
<text x="-2.54" y="-3.175" size="1.27" layer="27">&gt;VALUE</text>
<rectangle x1="-3.2004" y1="-1.5494" x2="-2.3505" y2="1.5507" layer="51"/>
<rectangle x1="2.3622" y1="-1.5494" x2="3.2121" y2="1.5507" layer="51"/>
<rectangle x1="-0.5001" y1="-1" x2="0.5001" y2="1" layer="35"/>
</package>
<package name="R2512W">
<description>Resistor&lt;p&gt;
chip / Wave soldering</description>
<wire x1="-2.3617" y1="1.4732" x2="2.3871" y2="1.4732" width="0.127" layer="51"/>
<wire x1="-2.3617" y1="-1.4732" x2="2.3871" y2="-1.4732" width="0.127" layer="51"/>
<wire x1="-3.9733" y1="1.9827" x2="3.9733" y2="1.9827" width="0.0508" layer="39"/>
<wire x1="3.9733" y1="1.9827" x2="3.9733" y2="-1.9827" width="0.0508" layer="39"/>
<wire x1="3.9733" y1="-1.9827" x2="-3.9733" y2="-1.9827" width="0.0508" layer="39"/>
<wire x1="-3.9733" y1="-1.9827" x2="-3.9733" y2="1.9827" width="0.0508" layer="39"/>
<smd name="1" x="-2.8956" y="0" dx="2" dy="2.1" layer="1"/>
<smd name="2" x="2.8956" y="0" dx="2" dy="2.1" layer="1"/>
<text x="-1.905" y="1.905" size="1.27" layer="25">&gt;NAME</text>
<text x="-1.905" y="-3.175" size="1.27" layer="27">&gt;VALUE</text>
<rectangle x1="-3.2004" y1="-1.5494" x2="-2.3505" y2="1.5507" layer="51"/>
<rectangle x1="2.3622" y1="-1.5494" x2="3.2121" y2="1.5507" layer="51"/>
<rectangle x1="-0.5001" y1="-1" x2="0.5001" y2="1" layer="35"/>
</package>
<package name="R3216">
<description>Resistor&lt;p&gt;
chip</description>
<wire x1="-0.9134" y1="0.8001" x2="0.888" y2="0.8001" width="0.127" layer="51"/>
<wire x1="-0.9134" y1="-0.8001" x2="0.888" y2="-0.8001" width="0.127" layer="51"/>
<wire x1="-2.4732" y1="0.9827" x2="2.4732" y2="0.9827" width="0.0508" layer="39"/>
<wire x1="2.4732" y1="0.9827" x2="2.4732" y2="-0.9827" width="0.0508" layer="39"/>
<wire x1="2.4732" y1="-0.9827" x2="-2.4732" y2="-0.9827" width="0.0508" layer="39"/>
<wire x1="-2.4732" y1="-0.9827" x2="-2.4732" y2="0.9827" width="0.0508" layer="39"/>
<smd name="1" x="-1.4" y="0" dx="1.5996" dy="1.8" layer="1"/>
<smd name="2" x="1.4" y="0" dx="1.5996" dy="1.8" layer="1"/>
<text x="-1.905" y="1.27" size="1.27" layer="25">&gt;NAME</text>
<text x="-1.905" y="-2.54" size="1.27" layer="27">&gt;VALUE</text>
<rectangle x1="-1.651" y1="-0.8763" x2="-0.9009" y2="0.8738" layer="51"/>
<rectangle x1="0.889" y1="-0.8763" x2="1.6391" y2="0.8738" layer="51"/>
<rectangle x1="-0.3" y1="-0.7" x2="0.3" y2="0.7" layer="35"/>
</package>
<package name="R3216W">
<description>Resistor&lt;p&gt;
chip / Wave soldering</description>
<wire x1="-0.9134" y1="0.8001" x2="0.888" y2="0.8001" width="0.127" layer="51"/>
<wire x1="-0.9134" y1="-0.8001" x2="0.888" y2="-0.8001" width="0.127" layer="51"/>
<wire x1="-2.4732" y1="0.9827" x2="2.4732" y2="0.9827" width="0.0508" layer="39"/>
<wire x1="2.4732" y1="0.9827" x2="2.4732" y2="-0.9827" width="0.0508" layer="39"/>
<wire x1="2.4732" y1="-0.9827" x2="-2.4732" y2="-0.9827" width="0.0508" layer="39"/>
<wire x1="-2.4732" y1="-0.9827" x2="-2.4732" y2="0.9827" width="0.0508" layer="39"/>
<smd name="1" x="-1.4986" y="0" dx="1.8" dy="1.1998" layer="1"/>
<smd name="2" x="1.4986" y="0" dx="1.8" dy="1.1998" layer="1"/>
<text x="-1.905" y="1.27" size="1.27" layer="25">&gt;NAME</text>
<text x="-1.905" y="-2.54" size="1.27" layer="27">&gt;VALUE</text>
<rectangle x1="-1.651" y1="-0.8763" x2="-0.9009" y2="0.8738" layer="51"/>
<rectangle x1="0.889" y1="-0.8763" x2="1.6391" y2="0.8738" layer="51"/>
<rectangle x1="-0.3" y1="-0.7" x2="0.3" y2="0.7" layer="35"/>
</package>
<package name="R3225">
<description>Resistor&lt;p&gt;
chip</description>
<wire x1="-0.9134" y1="1.2192" x2="0.9388" y2="1.2192" width="0.127" layer="51"/>
<wire x1="-0.9134" y1="-1.2192" x2="0.9388" y2="-1.2192" width="0.127" layer="51"/>
<wire x1="-2.4732" y1="1.4826" x2="2.4732" y2="1.4826" width="0.0508" layer="39"/>
<wire x1="2.4732" y1="1.4826" x2="2.4732" y2="-1.4826" width="0.0508" layer="39"/>
<wire x1="2.4732" y1="-1.4826" x2="-2.4732" y2="-1.4826" width="0.0508" layer="39"/>
<wire x1="-2.4732" y1="-1.4826" x2="-2.4732" y2="1.4826" width="0.0508" layer="39"/>
<smd name="1" x="-1.4" y="0" dx="1.5996" dy="2.7" layer="1"/>
<smd name="2" x="1.4" y="0" dx="1.5996" dy="2.7" layer="1"/>
<text x="-2.54" y="1.905" size="1.27" layer="25">&gt;NAME</text>
<text x="-2.54" y="-3.175" size="1.27" layer="27">&gt;VALUE</text>
<rectangle x1="-1.651" y1="-1.3081" x2="-0.9009" y2="1.2918" layer="51"/>
<rectangle x1="0.9144" y1="-1.3081" x2="1.6645" y2="1.2918" layer="51"/>
<rectangle x1="-0.3" y1="-1" x2="0.3" y2="1" layer="35"/>
</package>
<package name="R3225W">
<description>Resistor&lt;p&gt;
chip / Wave soldering</description>
<wire x1="-0.9134" y1="1.2192" x2="0.9388" y2="1.2192" width="0.127" layer="51"/>
<wire x1="-0.9134" y1="-1.2192" x2="0.9388" y2="-1.2192" width="0.127" layer="51"/>
<wire x1="-2.4732" y1="1.4826" x2="2.4732" y2="1.4826" width="0.0508" layer="39"/>
<wire x1="2.4732" y1="1.4826" x2="2.4732" y2="-1.4826" width="0.0508" layer="39"/>
<wire x1="2.4732" y1="-1.4826" x2="-2.4732" y2="-1.4826" width="0.0508" layer="39"/>
<wire x1="-2.4732" y1="-1.4826" x2="-2.4732" y2="1.4826" width="0.0508" layer="39"/>
<smd name="1" x="-1.4986" y="0" dx="1.8" dy="1.8" layer="1"/>
<smd name="2" x="1.4986" y="0" dx="1.8" dy="1.8" layer="1"/>
<text x="-1.905" y="1.905" size="1.27" layer="25">&gt;NAME</text>
<text x="-1.905" y="-3.175" size="1.27" layer="27">&gt;VALUE</text>
<rectangle x1="-1.651" y1="-1.3081" x2="-0.9009" y2="1.2918" layer="51"/>
<rectangle x1="0.9144" y1="-1.3081" x2="1.6645" y2="1.2918" layer="51"/>
<rectangle x1="-0.3" y1="-1" x2="0.3" y2="1" layer="35"/>
</package>
<package name="R5025">
<description>Resistor&lt;p&gt;
chip</description>
<wire x1="-1.6619" y1="1.2446" x2="1.6619" y2="1.2446" width="0.127" layer="51"/>
<wire x1="-1.6365" y1="-1.2446" x2="1.6873" y2="-1.2446" width="0.127" layer="51"/>
<wire x1="-3.4732" y1="1.4826" x2="3.4732" y2="1.4826" width="0.0508" layer="39"/>
<wire x1="3.4732" y1="1.4826" x2="3.4732" y2="-1.4826" width="0.0508" layer="39"/>
<wire x1="3.4732" y1="-1.4826" x2="-3.4732" y2="-1.4826" width="0.0508" layer="39"/>
<wire x1="-3.4732" y1="-1.4826" x2="-3.4732" y2="1.4826" width="0.0508" layer="39"/>
<smd name="1" x="-2.1999" y="0" dx="1.8" dy="2.7" layer="1"/>
<smd name="2" x="2.1999" y="0" dx="1.8" dy="2.7" layer="1"/>
<text x="-3.175" y="1.905" size="1.27" layer="25">&gt;NAME</text>
<text x="-3.175" y="-3.175" size="1.27" layer="27">&gt;VALUE</text>
<rectangle x1="-2.4892" y1="-1.3208" x2="-1.6393" y2="1.3292" layer="51"/>
<rectangle x1="1.651" y1="-1.3208" x2="2.5009" y2="1.3292" layer="51"/>
<rectangle x1="-0.5001" y1="-1" x2="0.5001" y2="1" layer="35"/>
</package>
<package name="R5025W">
<description>Resistor&lt;p&gt;
chip / Wave soldering</description>
<wire x1="-1.6619" y1="1.2446" x2="1.6619" y2="1.2446" width="0.127" layer="51"/>
<wire x1="-1.6365" y1="-1.2446" x2="1.6873" y2="-1.2446" width="0.127" layer="51"/>
<wire x1="-3.4732" y1="1.4826" x2="3.4732" y2="1.4826" width="0.0508" layer="39"/>
<wire x1="3.4732" y1="1.4826" x2="3.4732" y2="-1.4826" width="0.0508" layer="39"/>
<wire x1="3.4732" y1="-1.4826" x2="-3.4732" y2="-1.4826" width="0.0508" layer="39"/>
<wire x1="-3.4732" y1="-1.4826" x2="-3.4732" y2="1.4826" width="0.0508" layer="39"/>
<smd name="1" x="-2.3114" y="0" dx="2" dy="1.8" layer="1"/>
<smd name="2" x="2.3114" y="0" dx="2" dy="1.8" layer="1"/>
<text x="-3.175" y="1.905" size="1.27" layer="25">&gt;NAME</text>
<text x="-3.175" y="-3.175" size="1.27" layer="27">&gt;VALUE</text>
<rectangle x1="-2.4892" y1="-1.3208" x2="-1.6393" y2="1.3292" layer="51"/>
<rectangle x1="1.651" y1="-1.3208" x2="2.5009" y2="1.3292" layer="51"/>
<rectangle x1="-0.5001" y1="-1" x2="0.5001" y2="1" layer="35"/>
</package>
<package name="R6332">
<description>Resistor&lt;p&gt;
chip</description>
<wire x1="-2.3617" y1="1.4732" x2="2.3871" y2="1.4732" width="0.127" layer="51"/>
<wire x1="-2.3617" y1="-1.4732" x2="2.3871" y2="-1.4732" width="0.127" layer="51"/>
<wire x1="-3.9733" y1="1.9827" x2="3.9733" y2="1.9827" width="0.0508" layer="39"/>
<wire x1="3.9733" y1="1.9827" x2="3.9733" y2="-1.9827" width="0.0508" layer="39"/>
<wire x1="3.9733" y1="-1.9827" x2="-3.9733" y2="-1.9827" width="0.0508" layer="39"/>
<wire x1="-3.9733" y1="-1.9827" x2="-3.9733" y2="1.9827" width="0.0508" layer="39"/>
<smd name="1" x="-2.8001" y="0" dx="1.8" dy="3.1998" layer="1"/>
<smd name="2" x="2.8001" y="0" dx="1.8" dy="3.1998" layer="1"/>
<text x="-2.54" y="1.905" size="1.27" layer="25">&gt;NAME</text>
<text x="-2.54" y="-3.175" size="1.27" layer="27">&gt;VALUE</text>
<rectangle x1="-3.2004" y1="-1.5494" x2="-2.3505" y2="1.5507" layer="51"/>
<rectangle x1="2.3622" y1="-1.5494" x2="3.2121" y2="1.5507" layer="51"/>
<rectangle x1="-0.5001" y1="-1" x2="0.5001" y2="1" layer="35"/>
</package>
<package name="R6332W">
<description>Resistor&lt;p&gt;
chip / Wave soldering</description>
<wire x1="-2.3617" y1="1.4732" x2="2.3871" y2="1.4732" width="0.127" layer="51"/>
<wire x1="-2.3617" y1="-1.4732" x2="2.3871" y2="-1.4732" width="0.127" layer="51"/>
<wire x1="-3.9733" y1="1.9827" x2="3.9733" y2="1.9827" width="0.0508" layer="39"/>
<wire x1="3.9733" y1="1.9827" x2="3.9733" y2="-1.9827" width="0.0508" layer="39"/>
<wire x1="3.9733" y1="-1.9827" x2="-3.9733" y2="-1.9827" width="0.0508" layer="39"/>
<wire x1="-3.9733" y1="-1.9827" x2="-3.9733" y2="1.9827" width="0.0508" layer="39"/>
<smd name="1" x="-2.8956" y="0" dx="2" dy="2.1" layer="1"/>
<smd name="2" x="2.8956" y="0" dx="2" dy="2.1" layer="1"/>
<text x="-2.54" y="1.905" size="1.27" layer="25">&gt;NAME</text>
<text x="-2.54" y="-3.175" size="1.27" layer="27">&gt;VALUE</text>
<rectangle x1="-3.2004" y1="-1.5494" x2="-2.3505" y2="1.5507" layer="51"/>
<rectangle x1="2.3622" y1="-1.5494" x2="3.2121" y2="1.5507" layer="51"/>
<rectangle x1="-0.5001" y1="-1" x2="0.5001" y2="1" layer="35"/>
</package>
<package name="M0805">
<description>Resistor&lt;p&gt;
melf 0.10 W</description>
<wire x1="-1.9733" y1="0.9827" x2="1.9733" y2="0.9827" width="0.0508" layer="39"/>
<wire x1="1.9733" y1="-0.9827" x2="-1.9733" y2="-0.9827" width="0.0508" layer="39"/>
<wire x1="-1.9733" y1="-0.9827" x2="-1.9733" y2="0.9827" width="0.0508" layer="39"/>
<wire x1="1.9733" y1="0.9827" x2="1.9733" y2="-0.9827" width="0.0508" layer="39"/>
<wire x1="0.7112" y1="0.635" x2="-0.7112" y2="0.635" width="0.127" layer="51"/>
<wire x1="0.7112" y1="-0.635" x2="-0.7112" y2="-0.635" width="0.127" layer="51"/>
<smd name="1" x="-0.95" y="0" dx="1.3" dy="1.5996" layer="1"/>
<smd name="2" x="0.95" y="0" dx="1.3" dy="1.5996" layer="1"/>
<text x="-1.27" y="1.27" size="1.27" layer="25">&gt;NAME</text>
<text x="-1.27" y="-2.54" size="1.27" layer="27">&gt;VALUE</text>
<rectangle x1="-1.0414" y1="-0.7112" x2="-0.6858" y2="0.7112" layer="51"/>
<rectangle x1="0.6858" y1="-0.7112" x2="1.0414" y2="0.7112" layer="51"/>
<rectangle x1="-0.1999" y1="-0.5999" x2="0.1999" y2="0.5999" layer="35"/>
</package>
<package name="M1206">
<description>Resistor&lt;p&gt;
melf 0.25 W</description>
<wire x1="-2.4732" y1="1.4826" x2="2.4732" y2="1.4826" width="0.0508" layer="39"/>
<wire x1="2.4732" y1="-1.4826" x2="-2.4732" y2="-1.4826" width="0.0508" layer="39"/>
<wire x1="-2.4732" y1="-1.4826" x2="-2.4732" y2="1.4826" width="0.0508" layer="39"/>
<wire x1="2.4732" y1="1.4826" x2="2.4732" y2="-1.4826" width="0.0508" layer="39"/>
<wire x1="1.143" y1="0.8382" x2="-1.143" y2="0.8382" width="0.127" layer="51"/>
<wire x1="1.143" y1="-0.8382" x2="-1.143" y2="-0.8382" width="0.127" layer="51"/>
<smd name="1" x="-1.4" y="0" dx="1.5996" dy="2" layer="1"/>
<smd name="2" x="1.4" y="0" dx="1.5996" dy="2" layer="1"/>
<text x="-1.27" y="1.27" size="1.27" layer="25">&gt;NAME</text>
<text x="-1.27" y="-2.54" size="1.27" layer="27">&gt;VALUE</text>
<rectangle x1="-1.7018" y1="-0.9144" x2="-1.1176" y2="0.9144" layer="51"/>
<rectangle x1="1.1176" y1="-0.9144" x2="1.7018" y2="0.9144" layer="51"/>
<rectangle x1="-0.3" y1="-0.8001" x2="0.3" y2="0.8001" layer="35"/>
</package>
<package name="M1406">
<description>Resistor&lt;p&gt;
melf 0.12 W</description>
<wire x1="-2.9733" y1="0.9827" x2="2.9733" y2="0.9827" width="0.0508" layer="39"/>
<wire x1="2.9733" y1="-0.9827" x2="-2.9733" y2="-0.9827" width="0.0508" layer="39"/>
<wire x1="-2.9733" y1="-0.9827" x2="-2.9733" y2="0.9827" width="0.0508" layer="39"/>
<wire x1="2.9733" y1="0.9827" x2="2.9733" y2="-0.9827" width="0.0508" layer="39"/>
<wire x1="1.3208" y1="0.762" x2="-1.3208" y2="0.762" width="0.127" layer="51"/>
<wire x1="1.3208" y1="-0.762" x2="-1.3208" y2="-0.762" width="0.127" layer="51"/>
<smd name="1" x="-1.7" y="0" dx="1.4" dy="1.8" layer="1"/>
<smd name="2" x="1.7" y="0" dx="1.4" dy="1.8" layer="1"/>
<text x="-1.27" y="1.27" size="1.27" layer="25">&gt;NAME</text>
<text x="-1.27" y="-2.54" size="1.27" layer="27">&gt;VALUE</text>
<rectangle x1="-1.8542" y1="-0.8382" x2="-1.2954" y2="0.8382" layer="51"/>
<rectangle x1="1.2954" y1="-0.8382" x2="1.8542" y2="0.8382" layer="51"/>
<rectangle x1="-0.3" y1="-0.7" x2="0.3" y2="0.7" layer="35"/>
</package>
<package name="M2012">
<description>Resistor&lt;p&gt;
melf 0.10 W</description>
<wire x1="-1.9733" y1="0.9827" x2="1.9733" y2="0.9827" width="0.0508" layer="39"/>
<wire x1="1.9733" y1="-0.9827" x2="-1.9733" y2="-0.9827" width="0.0508" layer="39"/>
<wire x1="-1.9733" y1="-0.9827" x2="-1.9733" y2="0.9827" width="0.0508" layer="39"/>
<wire x1="1.9733" y1="0.9827" x2="1.9733" y2="-0.9827" width="0.0508" layer="39"/>
<wire x1="0.7112" y1="0.635" x2="-0.7112" y2="0.635" width="0.127" layer="51"/>
<wire x1="0.7112" y1="-0.635" x2="-0.7112" y2="-0.635" width="0.127" layer="51"/>
<smd name="1" x="-0.95" y="0" dx="1.3" dy="1.5996" layer="1"/>
<smd name="2" x="0.95" y="0" dx="1.3" dy="1.5996" layer="1"/>
<text x="-1.27" y="1.27" size="1.27" layer="25">&gt;NAME</text>
<text x="-1.27" y="-2.54" size="1.27" layer="27">&gt;VALUE</text>
<rectangle x1="-1.0414" y1="-0.7112" x2="-0.6858" y2="0.7112" layer="51"/>
<rectangle x1="0.6858" y1="-0.7112" x2="1.0414" y2="0.7112" layer="51"/>
<rectangle x1="-0.1999" y1="-0.5999" x2="0.1999" y2="0.5999" layer="35"/>
</package>
<package name="M2309">
<description>Resistor&lt;p&gt;
melf 0.25 W</description>
<wire x1="-4.4732" y1="1.4826" x2="4.4732" y2="1.4826" width="0.0508" layer="39"/>
<wire x1="4.4732" y1="-1.4826" x2="-4.4732" y2="-1.4826" width="0.0508" layer="39"/>
<wire x1="-4.4732" y1="-1.4826" x2="-4.4732" y2="1.4826" width="0.0508" layer="39"/>
<wire x1="4.4732" y1="1.4826" x2="4.4732" y2="-1.4826" width="0.0508" layer="39"/>
<wire x1="2.413" y1="1.1684" x2="-2.4384" y2="1.1684" width="0.127" layer="51"/>
<wire x1="2.413" y1="-1.1684" x2="-2.413" y2="-1.1684" width="0.127" layer="51"/>
<smd name="1" x="-2.8499" y="0" dx="1.5" dy="2.5996" layer="1"/>
<smd name="2" x="2.8499" y="0" dx="1.5" dy="2.5996" layer="1"/>
<text x="-1.905" y="1.905" size="1.27" layer="25">&gt;NAME</text>
<text x="-2.54" y="-2.54" size="1.27" layer="27">&gt;VALUE</text>
<rectangle x1="-3.048" y1="-1.2446" x2="-2.3876" y2="1.2446" layer="51"/>
<rectangle x1="2.3876" y1="-1.2446" x2="3.048" y2="1.2446" layer="51"/>
<rectangle x1="-0.5001" y1="-1" x2="0.5001" y2="1" layer="35"/>
</package>
<package name="M3216">
<description>Resistor&lt;p&gt;
melf 0.25 W</description>
<wire x1="-2.4732" y1="1.4826" x2="2.4732" y2="1.4826" width="0.0508" layer="39"/>
<wire x1="2.4732" y1="-1.4826" x2="-2.4732" y2="-1.4826" width="0.0508" layer="39"/>
<wire x1="-2.4732" y1="-1.4826" x2="-2.4732" y2="1.4826" width="0.0508" layer="39"/>
<wire x1="2.4732" y1="1.4826" x2="2.4732" y2="-1.4826" width="0.0508" layer="39"/>
<wire x1="1.143" y1="0.8382" x2="-1.143" y2="0.8382" width="0.127" layer="51"/>
<wire x1="1.143" y1="-0.8382" x2="-1.143" y2="-0.8382" width="0.127" layer="51"/>
<smd name="1" x="-1.4" y="0" dx="1.5996" dy="2" layer="1"/>
<smd name="2" x="1.4" y="0" dx="1.5996" dy="2" layer="1"/>
<text x="-1.27" y="1.27" size="1.27" layer="25">&gt;NAME</text>
<text x="-1.27" y="-2.54" size="1.27" layer="27">&gt;VALUE</text>
<rectangle x1="-1.7018" y1="-0.9144" x2="-1.1176" y2="0.9144" layer="51"/>
<rectangle x1="1.1176" y1="-0.9144" x2="1.7018" y2="0.9144" layer="51"/>
<rectangle x1="-0.3" y1="-0.8001" x2="0.3" y2="0.8001" layer="35"/>
</package>
<package name="M3516">
<description>Resistor&lt;p&gt;
melf 0.12 W</description>
<wire x1="-2.9733" y1="0.9827" x2="2.9733" y2="0.9827" width="0.0508" layer="39"/>
<wire x1="2.9733" y1="-0.9827" x2="-2.9733" y2="-0.9827" width="0.0508" layer="39"/>
<wire x1="-2.9733" y1="-0.9827" x2="-2.9733" y2="0.9827" width="0.0508" layer="39"/>
<wire x1="2.9733" y1="0.9827" x2="2.9733" y2="-0.9827" width="0.0508" layer="39"/>
<wire x1="1.3208" y1="0.762" x2="-1.3208" y2="0.762" width="0.127" layer="51"/>
<wire x1="1.3208" y1="-0.762" x2="-1.3208" y2="-0.762" width="0.127" layer="51"/>
<smd name="1" x="-1.7" y="0" dx="1.4" dy="1.8" layer="1"/>
<smd name="2" x="1.7" y="0" dx="1.4" dy="1.8" layer="1"/>
<text x="-1.27" y="1.27" size="1.27" layer="25">&gt;NAME</text>
<text x="-1.27" y="-2.54" size="1.27" layer="27">&gt;VALUE</text>
<rectangle x1="-1.8542" y1="-0.8382" x2="-1.2954" y2="0.8382" layer="51"/>
<rectangle x1="1.2954" y1="-0.8382" x2="1.8542" y2="0.8382" layer="51"/>
<rectangle x1="-0.4001" y1="-0.7" x2="0.4001" y2="0.7" layer="35"/>
</package>
<package name="M5923">
<description>Resistor&lt;p&gt;
melf 0.25 W</description>
<wire x1="-4.4732" y1="1.4826" x2="4.4732" y2="1.4826" width="0.0508" layer="39"/>
<wire x1="4.4732" y1="-1.4826" x2="-4.4732" y2="-1.4826" width="0.0508" layer="39"/>
<wire x1="-4.4732" y1="-1.4826" x2="-4.4732" y2="1.4826" width="0.0508" layer="39"/>
<wire x1="4.4732" y1="1.4826" x2="4.4732" y2="-1.4826" width="0.0508" layer="39"/>
<wire x1="2.413" y1="1.1684" x2="-2.4384" y2="1.1684" width="0.127" layer="51"/>
<wire x1="2.413" y1="-1.1684" x2="-2.413" y2="-1.1684" width="0.127" layer="51"/>
<smd name="1" x="-2.8499" y="0" dx="1.5" dy="2.5996" layer="1"/>
<smd name="2" x="2.8499" y="0" dx="1.5" dy="2.5996" layer="1"/>
<text x="-1.905" y="1.905" size="1.27" layer="25">&gt;NAME</text>
<text x="-2.54" y="-2.54" size="1.27" layer="27">&gt;VALUE</text>
<rectangle x1="-3.048" y1="-1.2446" x2="-2.3876" y2="1.2446" layer="51"/>
<rectangle x1="2.3876" y1="-1.2446" x2="3.048" y2="1.2446" layer="51"/>
<rectangle x1="-0.5001" y1="-1" x2="0.5001" y2="1" layer="35"/>
</package>
<package name="0204/5">
<description>Resistor&lt;p&gt;
Type 0204 Grid  5 mm</description>
<wire x1="2.54" y1="0" x2="2.032" y2="0" width="0.508" layer="51"/>
<wire x1="-2.54" y1="0" x2="-2.032" y2="0" width="0.508" layer="51"/>
<wire x1="-1.778" y1="0.635" x2="-1.524" y2="0.889" width="0.127" layer="21" curve="-90" cap="flat"/>
<wire x1="-1.778" y1="-0.635" x2="-1.524" y2="-0.889" width="0.127" layer="21" curve="90" cap="flat"/>
<wire x1="1.524" y1="-0.889" x2="1.778" y2="-0.635" width="0.127" layer="21" curve="90" cap="flat"/>
<wire x1="1.524" y1="0.889" x2="1.778" y2="0.635" width="0.127" layer="21" curve="-90" cap="flat"/>
<wire x1="-1.778" y1="-0.635" x2="-1.778" y2="0.635" width="0.127" layer="51"/>
<wire x1="-1.524" y1="0.889" x2="-1.27" y2="0.889" width="0.127" layer="21"/>
<wire x1="-1.143" y1="0.762" x2="-1.27" y2="0.889" width="0.127" layer="21"/>
<wire x1="-1.524" y1="-0.889" x2="-1.27" y2="-0.889" width="0.127" layer="21"/>
<wire x1="-1.143" y1="-0.762" x2="-1.27" y2="-0.889" width="0.127" layer="21"/>
<wire x1="1.143" y1="0.762" x2="1.27" y2="0.889" width="0.127" layer="21"/>
<wire x1="1.143" y1="0.762" x2="-1.143" y2="0.762" width="0.127" layer="21"/>
<wire x1="1.143" y1="-0.762" x2="1.27" y2="-0.889" width="0.127" layer="21"/>
<wire x1="1.143" y1="-0.762" x2="-1.143" y2="-0.762" width="0.127" layer="21"/>
<wire x1="1.524" y1="0.889" x2="1.27" y2="0.889" width="0.127" layer="21"/>
<wire x1="1.524" y1="-0.889" x2="1.27" y2="-0.889" width="0.127" layer="21"/>
<wire x1="1.778" y1="-0.635" x2="1.778" y2="0.635" width="0.127" layer="51"/>
<pad name="1" x="-2.54" y="0" drill="0.8128" diameter="1.397" shape="octagon"/>
<pad name="2" x="2.54" y="0" drill="0.8128" shape="octagon"/>
<text x="-2.0066" y="1.1684" size="0.9906" layer="25" ratio="12">&gt;NAME</text>
<text x="-2.1336" y="-2.3114" size="0.9906" layer="27" ratio="12">&gt;VALUE</text>
<rectangle x1="-2.032" y1="-0.254" x2="-1.778" y2="0.254" layer="51"/>
<rectangle x1="1.778" y1="-0.254" x2="2.032" y2="0.254" layer="51"/>
</package>
<package name="0204/7">
<description>Resistor&lt;p&gt;
Type 0204 Grid  7.5 mm</description>
<wire x1="3.81" y1="0" x2="2.921" y2="0" width="0.508" layer="51"/>
<wire x1="-3.81" y1="0" x2="-2.921" y2="0" width="0.508" layer="51"/>
<wire x1="-2.54" y1="0.762" x2="-2.286" y2="1.016" width="0.127" layer="21" curve="-90"/>
<wire x1="-2.54" y1="-0.762" x2="-2.286" y2="-1.016" width="0.127" layer="21" curve="90"/>
<wire x1="2.286" y1="-1.016" x2="2.54" y2="-0.762" width="0.127" layer="21" curve="90"/>
<wire x1="2.286" y1="1.016" x2="2.54" y2="0.762" width="0.127" layer="21" curve="-90"/>
<wire x1="-2.54" y1="-0.762" x2="-2.54" y2="0.762" width="0.127" layer="21"/>
<wire x1="-2.286" y1="1.016" x2="-1.905" y2="1.016" width="0.127" layer="21"/>
<wire x1="-1.778" y1="0.889" x2="-1.905" y2="1.016" width="0.127" layer="21"/>
<wire x1="-2.286" y1="-1.016" x2="-1.905" y2="-1.016" width="0.127" layer="21"/>
<wire x1="-1.778" y1="-0.889" x2="-1.905" y2="-1.016" width="0.127" layer="21"/>
<wire x1="1.778" y1="0.889" x2="1.905" y2="1.016" width="0.127" layer="21"/>
<wire x1="1.778" y1="0.889" x2="-1.778" y2="0.889" width="0.127" layer="21"/>
<wire x1="1.778" y1="-0.889" x2="1.905" y2="-1.016" width="0.127" layer="21"/>
<wire x1="1.778" y1="-0.889" x2="-1.778" y2="-0.889" width="0.127" layer="21"/>
<wire x1="2.286" y1="1.016" x2="1.905" y2="1.016" width="0.127" layer="21"/>
<wire x1="2.286" y1="-1.016" x2="1.905" y2="-1.016" width="0.127" layer="21"/>
<wire x1="2.54" y1="-0.762" x2="2.54" y2="0.762" width="0.127" layer="21"/>
<pad name="1" x="-3.81" y="0" drill="0.8128" shape="octagon"/>
<pad name="2" x="3.81" y="0" drill="0.8128" shape="octagon"/>
<text x="-2.54" y="1.5494" size="0.9906" layer="25" ratio="12">&gt;NAME</text>
<text x="-1.6256" y="-0.4826" size="0.9906" layer="27" ratio="12">&gt;VALUE</text>
<rectangle x1="2.54" y1="-0.254" x2="2.921" y2="0.254" layer="21"/>
<rectangle x1="-2.921" y1="-0.254" x2="-2.54" y2="0.254" layer="21"/>
</package>
<package name="0204V">
<description>Resistor&lt;p&gt;
Type 0204 Vertical Grid  2.5 mm</description>
<wire x1="-1.27" y1="0" x2="1.27" y2="0" width="0.508" layer="51"/>
<wire x1="-0.127" y1="0" x2="0.127" y2="0" width="0.508" layer="21"/>
<circle x="-1.27" y="0" radius="0.889" width="0.127" layer="51"/>
<circle x="-1.27" y="0" radius="0.635" width="0.0508" layer="51"/>
<pad name="1" x="-1.27" y="0" drill="0.8128" shape="octagon"/>
<pad name="2" x="1.27" y="0" drill="0.8128" shape="octagon"/>
<text x="-2.1336" y="1.1684" size="0.9906" layer="25" ratio="12">&gt;NAME</text>
<text x="-2.1336" y="-2.3114" size="0.9906" layer="27" ratio="12">&gt;VALUE</text>
</package>
<package name="0207/10">
<description>Resistor&lt;p&gt;
Type 0204 Grid  10 mm</description>
<wire x1="5.08" y1="0" x2="4.064" y2="0" width="0.6096" layer="51"/>
<wire x1="-5.08" y1="0" x2="-4.064" y2="0" width="0.6096" layer="51"/>
<wire x1="-3.175" y1="0.889" x2="-2.921" y2="1.143" width="0.127" layer="21" curve="-90"/>
<wire x1="-3.175" y1="-0.889" x2="-2.921" y2="-1.143" width="0.127" layer="21" curve="90"/>
<wire x1="2.921" y1="-1.143" x2="3.175" y2="-0.889" width="0.127" layer="21" curve="90"/>
<wire x1="2.921" y1="1.143" x2="3.175" y2="0.889" width="0.127" layer="21" curve="-90"/>
<wire x1="-3.175" y1="-0.889" x2="-3.175" y2="0.889" width="0.127" layer="21"/>
<wire x1="-2.921" y1="1.143" x2="-2.54" y2="1.143" width="0.127" layer="21"/>
<wire x1="-2.413" y1="1.016" x2="-2.54" y2="1.143" width="0.127" layer="21"/>
<wire x1="-2.921" y1="-1.143" x2="-2.54" y2="-1.143" width="0.127" layer="21"/>
<wire x1="-2.413" y1="-1.016" x2="-2.54" y2="-1.143" width="0.127" layer="21"/>
<wire x1="2.413" y1="1.016" x2="2.54" y2="1.143" width="0.127" layer="21"/>
<wire x1="2.413" y1="1.016" x2="-2.413" y2="1.016" width="0.127" layer="21"/>
<wire x1="2.413" y1="-1.016" x2="2.54" y2="-1.143" width="0.127" layer="21"/>
<wire x1="2.413" y1="-1.016" x2="-2.413" y2="-1.016" width="0.127" layer="21"/>
<wire x1="2.921" y1="1.143" x2="2.54" y2="1.143" width="0.127" layer="21"/>
<wire x1="2.921" y1="-1.143" x2="2.54" y2="-1.143" width="0.127" layer="21"/>
<wire x1="3.175" y1="-0.889" x2="3.175" y2="0.889" width="0.127" layer="21"/>
<pad name="1" x="-5.08" y="0" drill="0.8128" shape="octagon"/>
<pad name="2" x="5.08" y="0" drill="0.8128" shape="octagon"/>
<text x="-3.048" y="1.524" size="1.27" layer="25" ratio="10">&gt;NAME</text>
<text x="-2.2606" y="-0.635" size="1.27" layer="27" ratio="10">&gt;VALUE</text>
<rectangle x1="3.175" y1="-0.3048" x2="4.0386" y2="0.3048" layer="21"/>
<rectangle x1="-4.0386" y1="-0.3048" x2="-3.175" y2="0.3048" layer="21"/>
</package>
<package name="0207/12">
<description>Resistor&lt;p&gt;
Type 0207 Grid  12 mm</description>
<wire x1="6.35" y1="0" x2="5.334" y2="0" width="0.6096" layer="51"/>
<wire x1="-6.35" y1="0" x2="-5.334" y2="0" width="0.6096" layer="51"/>
<wire x1="-3.175" y1="0.889" x2="-2.921" y2="1.143" width="0.127" layer="21" curve="-90"/>
<wire x1="-3.175" y1="-0.889" x2="-2.921" y2="-1.143" width="0.127" layer="21" curve="90"/>
<wire x1="2.921" y1="-1.143" x2="3.175" y2="-0.889" width="0.127" layer="21" curve="90"/>
<wire x1="2.921" y1="1.143" x2="3.175" y2="0.889" width="0.127" layer="21" curve="-90"/>
<wire x1="-3.175" y1="-0.889" x2="-3.175" y2="0.889" width="0.127" layer="21"/>
<wire x1="-2.921" y1="1.143" x2="-2.54" y2="1.143" width="0.127" layer="21"/>
<wire x1="-2.413" y1="1.016" x2="-2.54" y2="1.143" width="0.127" layer="21"/>
<wire x1="-2.921" y1="-1.143" x2="-2.54" y2="-1.143" width="0.127" layer="21"/>
<wire x1="-2.413" y1="-1.016" x2="-2.54" y2="-1.143" width="0.127" layer="21"/>
<wire x1="2.413" y1="1.016" x2="2.54" y2="1.143" width="0.127" layer="21"/>
<wire x1="2.413" y1="1.016" x2="-2.413" y2="1.016" width="0.127" layer="21"/>
<wire x1="2.413" y1="-1.016" x2="2.54" y2="-1.143" width="0.127" layer="21"/>
<wire x1="2.413" y1="-1.016" x2="-2.413" y2="-1.016" width="0.127" layer="21"/>
<wire x1="2.921" y1="1.143" x2="2.54" y2="1.143" width="0.127" layer="21"/>
<wire x1="2.921" y1="-1.143" x2="2.54" y2="-1.143" width="0.127" layer="21"/>
<wire x1="3.175" y1="-0.889" x2="3.175" y2="0.889" width="0.127" layer="21"/>
<wire x1="4.445" y1="0" x2="4.064" y2="0" width="0.6096" layer="21"/>
<wire x1="-4.445" y1="0" x2="-4.064" y2="0" width="0.6096" layer="21"/>
<pad name="1" x="-6.35" y="0" drill="0.8128" shape="octagon"/>
<pad name="2" x="6.35" y="0" drill="0.8128" shape="octagon"/>
<text x="-3.175" y="1.397" size="1.27" layer="25" ratio="10">&gt;NAME</text>
<text x="-2.286" y="-0.6858" size="1.27" layer="27" ratio="10">&gt;VALUE</text>
<rectangle x1="3.175" y1="-0.3048" x2="4.0386" y2="0.3048" layer="21"/>
<rectangle x1="-4.0386" y1="-0.3048" x2="-3.175" y2="0.3048" layer="21"/>
<rectangle x1="4.445" y1="-0.3048" x2="5.3086" y2="0.3048" layer="21"/>
<rectangle x1="-5.3086" y1="-0.3048" x2="-4.445" y2="0.3048" layer="21"/>
</package>
<package name="0207/15">
<description>Resistor&lt;p&gt;
Type 0207 Grid  15mm</description>
<wire x1="7.62" y1="0" x2="6.604" y2="0" width="0.6096" layer="51"/>
<wire x1="-7.62" y1="0" x2="-6.604" y2="0" width="0.6096" layer="51"/>
<wire x1="-3.175" y1="0.889" x2="-2.921" y2="1.143" width="0.127" layer="21" curve="-90"/>
<wire x1="-3.175" y1="-0.889" x2="-2.921" y2="-1.143" width="0.127" layer="21" curve="90"/>
<wire x1="2.921" y1="-1.143" x2="3.175" y2="-0.889" width="0.127" layer="21" curve="90"/>
<wire x1="2.921" y1="1.143" x2="3.175" y2="0.889" width="0.127" layer="21" curve="-90"/>
<wire x1="-3.175" y1="-0.889" x2="-3.175" y2="0.889" width="0.127" layer="21"/>
<wire x1="-2.921" y1="1.143" x2="-2.54" y2="1.143" width="0.127" layer="21"/>
<wire x1="-2.413" y1="1.016" x2="-2.54" y2="1.143" width="0.127" layer="21"/>
<wire x1="-2.921" y1="-1.143" x2="-2.54" y2="-1.143" width="0.127" layer="21"/>
<wire x1="-2.413" y1="-1.016" x2="-2.54" y2="-1.143" width="0.127" layer="21"/>
<wire x1="2.413" y1="1.016" x2="2.54" y2="1.143" width="0.127" layer="21"/>
<wire x1="2.413" y1="1.016" x2="-2.413" y2="1.016" width="0.127" layer="21"/>
<wire x1="2.413" y1="-1.016" x2="2.54" y2="-1.143" width="0.127" layer="21"/>
<wire x1="2.413" y1="-1.016" x2="-2.413" y2="-1.016" width="0.127" layer="21"/>
<wire x1="2.921" y1="1.143" x2="2.54" y2="1.143" width="0.127" layer="21"/>
<wire x1="2.921" y1="-1.143" x2="2.54" y2="-1.143" width="0.127" layer="21"/>
<wire x1="3.175" y1="-0.889" x2="3.175" y2="0.889" width="0.127" layer="21"/>
<wire x1="5.715" y1="0" x2="4.064" y2="0" width="0.6096" layer="21"/>
<wire x1="-5.715" y1="0" x2="-4.064" y2="0" width="0.6096" layer="21"/>
<pad name="1" x="-7.62" y="0" drill="0.8128" shape="octagon"/>
<pad name="2" x="7.62" y="0" drill="0.8128" shape="octagon"/>
<text x="-3.175" y="1.397" size="1.27" layer="25" ratio="10">&gt;NAME</text>
<text x="-2.286" y="-0.6858" size="1.27" layer="27" ratio="10">&gt;VALUE</text>
<rectangle x1="3.175" y1="-0.3048" x2="4.0386" y2="0.3048" layer="21"/>
<rectangle x1="-4.0386" y1="-0.3048" x2="-3.175" y2="0.3048" layer="21"/>
<rectangle x1="5.715" y1="-0.3048" x2="6.5786" y2="0.3048" layer="21"/>
<rectangle x1="-6.5786" y1="-0.3048" x2="-5.715" y2="0.3048" layer="21"/>
</package>
<package name="0207/2V">
<description>Resistor&lt;p&gt;
Type 0207 Vertical Grid  2.5 mm</description>
<wire x1="-1.27" y1="0" x2="-0.381" y2="0" width="0.6096" layer="51"/>
<wire x1="-0.254" y1="0" x2="0.254" y2="0" width="0.6096" layer="21"/>
<wire x1="0.381" y1="0" x2="1.27" y2="0" width="0.6096" layer="51"/>
<circle x="-1.27" y="0" radius="1.27" width="0.127" layer="21"/>
<circle x="-1.27" y="0" radius="1.016" width="0.127" layer="51"/>
<pad name="1" x="-1.27" y="0" drill="0.8128" shape="octagon"/>
<pad name="2" x="1.27" y="0" drill="0.8128" shape="octagon"/>
<text x="0.2032" y="1.143" size="1.27" layer="25" ratio="10">&gt;NAME</text>
<text x="0.2032" y="-2.4892" size="1.27" layer="27" ratio="10">&gt;VALUE</text>
</package>
<package name="0207/5V">
<description>Resistor&lt;p&gt;
Type 0207 Vertical Grid  5 mm</description>
<wire x1="-2.54" y1="0" x2="-0.889" y2="0" width="0.6096" layer="51"/>
<wire x1="-0.762" y1="0" x2="0.762" y2="0" width="0.6096" layer="21"/>
<wire x1="0.889" y1="0" x2="2.54" y2="0" width="0.6096" layer="51"/>
<circle x="-2.54" y="0" radius="1.27" width="0.127" layer="21"/>
<circle x="-2.54" y="0" radius="1.016" width="0.127" layer="51"/>
<pad name="1" x="-2.54" y="0" drill="0.8128" shape="octagon"/>
<pad name="2" x="2.54" y="0" drill="0.8128" shape="octagon"/>
<text x="-1.143" y="0.889" size="1.27" layer="25" ratio="10">&gt;NAME</text>
<text x="-1.143" y="-2.159" size="1.27" layer="27" ratio="10">&gt;VALUE</text>
</package>
<package name="0207/7">
<description>Resistor&lt;p&gt;
Type 0204 Grid  7.5 mm</description>
<wire x1="-3.81" y1="0" x2="-3.429" y2="0" width="0.6096" layer="51"/>
<wire x1="-3.175" y1="0.889" x2="-2.921" y2="1.143" width="0.127" layer="21" curve="-90" cap="flat"/>
<wire x1="-3.175" y1="-0.889" x2="-2.921" y2="-1.143" width="0.127" layer="21" curve="90" cap="flat"/>
<wire x1="2.921" y1="-1.143" x2="3.175" y2="-0.889" width="0.127" layer="21" curve="90" cap="flat"/>
<wire x1="2.921" y1="1.143" x2="3.175" y2="0.889" width="0.127" layer="21" curve="-90" cap="flat"/>
<wire x1="-3.175" y1="-0.889" x2="-3.175" y2="0.889" width="0.127" layer="51"/>
<wire x1="-2.921" y1="1.143" x2="-2.54" y2="1.143" width="0.127" layer="21"/>
<wire x1="-2.413" y1="1.016" x2="-2.54" y2="1.143" width="0.127" layer="21"/>
<wire x1="-2.921" y1="-1.143" x2="-2.54" y2="-1.143" width="0.127" layer="21"/>
<wire x1="-2.413" y1="-1.016" x2="-2.54" y2="-1.143" width="0.127" layer="21"/>
<wire x1="2.413" y1="1.016" x2="2.54" y2="1.143" width="0.127" layer="21"/>
<wire x1="2.413" y1="1.016" x2="-2.413" y2="1.016" width="0.127" layer="21"/>
<wire x1="2.413" y1="-1.016" x2="2.54" y2="-1.143" width="0.127" layer="21"/>
<wire x1="2.413" y1="-1.016" x2="-2.413" y2="-1.016" width="0.127" layer="21"/>
<wire x1="2.921" y1="1.143" x2="2.54" y2="1.143" width="0.127" layer="21"/>
<wire x1="2.921" y1="-1.143" x2="2.54" y2="-1.143" width="0.127" layer="21"/>
<wire x1="3.175" y1="-0.889" x2="3.175" y2="0.889" width="0.127" layer="51"/>
<wire x1="3.429" y1="0" x2="3.81" y2="0" width="0.6096" layer="51"/>
<pad name="1" x="-3.81" y="0" drill="0.8128" shape="octagon"/>
<pad name="2" x="3.81" y="0" drill="0.8128" shape="octagon"/>
<text x="-2.54" y="1.397" size="1.27" layer="25" ratio="10">&gt;NAME</text>
<text x="-2.286" y="-0.5588" size="1.27" layer="27" ratio="10">&gt;VALUE</text>
<rectangle x1="-3.429" y1="-0.3048" x2="-3.175" y2="0.3048" layer="51"/>
<rectangle x1="3.175" y1="-0.3048" x2="3.429" y2="0.3048" layer="51"/>
</package>
<package name="0309/10">
<description>Resistor&lt;p&gt;
Type 0309 Grid  10mm</description>
<wire x1="-4.699" y1="0" x2="-5.08" y2="0" width="0.6096" layer="51"/>
<wire x1="-4.318" y1="1.27" x2="-4.064" y2="1.524" width="0.127" layer="21" curve="-90" cap="flat"/>
<wire x1="-4.318" y1="-1.27" x2="-4.064" y2="-1.524" width="0.127" layer="21" curve="90" cap="flat"/>
<wire x1="4.064" y1="-1.524" x2="4.318" y2="-1.27" width="0.127" layer="21" curve="90" cap="flat"/>
<wire x1="4.064" y1="1.524" x2="4.318" y2="1.27" width="0.127" layer="21" curve="-90" cap="flat"/>
<wire x1="-4.318" y1="-1.27" x2="-4.318" y2="1.27" width="0.127" layer="51"/>
<wire x1="-4.064" y1="1.524" x2="-3.429" y2="1.524" width="0.127" layer="21"/>
<wire x1="-3.302" y1="1.397" x2="-3.429" y2="1.524" width="0.127" layer="21"/>
<wire x1="-4.064" y1="-1.524" x2="-3.429" y2="-1.524" width="0.127" layer="21"/>
<wire x1="-3.302" y1="-1.397" x2="-3.429" y2="-1.524" width="0.127" layer="21"/>
<wire x1="3.302" y1="1.397" x2="3.429" y2="1.524" width="0.127" layer="21"/>
<wire x1="3.302" y1="1.397" x2="-3.302" y2="1.397" width="0.127" layer="21"/>
<wire x1="3.302" y1="-1.397" x2="3.429" y2="-1.524" width="0.127" layer="21"/>
<wire x1="3.302" y1="-1.397" x2="-3.302" y2="-1.397" width="0.127" layer="21"/>
<wire x1="4.064" y1="1.524" x2="3.429" y2="1.524" width="0.127" layer="21"/>
<wire x1="4.064" y1="-1.524" x2="3.429" y2="-1.524" width="0.127" layer="21"/>
<wire x1="4.318" y1="-1.27" x2="4.318" y2="1.27" width="0.127" layer="51"/>
<wire x1="5.08" y1="0" x2="4.699" y2="0" width="0.6096" layer="51"/>
<pad name="1" x="-5.08" y="0" drill="0.8128" shape="octagon"/>
<pad name="2" x="5.08" y="0" drill="0.8128" shape="octagon"/>
<text x="-4.191" y="1.905" size="1.27" layer="25" ratio="10">&gt;NAME</text>
<text x="-2.54" y="-0.6858" size="1.27" layer="27" ratio="10">&gt;VALUE</text>
<rectangle x1="-4.6228" y1="-0.3048" x2="-4.318" y2="0.3048" layer="51"/>
<rectangle x1="4.318" y1="-0.3048" x2="4.6228" y2="0.3048" layer="51"/>
</package>
<package name="0309/12">
<description>Resistor&lt;p&gt;
Type 0309 Grid  12.5 mm</description>
<wire x1="6.35" y1="0" x2="5.08" y2="0" width="0.6096" layer="51"/>
<wire x1="-6.35" y1="0" x2="-5.08" y2="0" width="0.6096" layer="51"/>
<wire x1="-4.318" y1="1.27" x2="-4.064" y2="1.524" width="0.127" layer="21" curve="-90"/>
<wire x1="-4.318" y1="-1.27" x2="-4.064" y2="-1.524" width="0.127" layer="21" curve="90"/>
<wire x1="4.064" y1="-1.524" x2="4.318" y2="-1.27" width="0.127" layer="21" curve="90"/>
<wire x1="4.064" y1="1.524" x2="4.318" y2="1.27" width="0.127" layer="21" curve="-90"/>
<wire x1="-4.318" y1="-1.27" x2="-4.318" y2="1.27" width="0.127" layer="21"/>
<wire x1="-4.064" y1="1.524" x2="-3.429" y2="1.524" width="0.127" layer="21"/>
<wire x1="-3.302" y1="1.397" x2="-3.429" y2="1.524" width="0.127" layer="21"/>
<wire x1="-4.064" y1="-1.524" x2="-3.429" y2="-1.524" width="0.127" layer="21"/>
<wire x1="-3.302" y1="-1.397" x2="-3.429" y2="-1.524" width="0.127" layer="21"/>
<wire x1="3.302" y1="1.397" x2="3.429" y2="1.524" width="0.127" layer="21"/>
<wire x1="3.302" y1="1.397" x2="-3.302" y2="1.397" width="0.127" layer="21"/>
<wire x1="3.302" y1="-1.397" x2="3.429" y2="-1.524" width="0.127" layer="21"/>
<wire x1="3.302" y1="-1.397" x2="-3.302" y2="-1.397" width="0.127" layer="21"/>
<wire x1="4.064" y1="1.524" x2="3.429" y2="1.524" width="0.127" layer="21"/>
<wire x1="4.064" y1="-1.524" x2="3.429" y2="-1.524" width="0.127" layer="21"/>
<wire x1="4.318" y1="-1.27" x2="4.318" y2="1.27" width="0.127" layer="21"/>
<pad name="1" x="-6.35" y="0" drill="0.8128" shape="octagon"/>
<pad name="2" x="6.35" y="0" drill="0.8128" shape="octagon"/>
<text x="-4.191" y="1.905" size="1.27" layer="25" ratio="10">&gt;NAME</text>
<text x="-2.54" y="-0.6858" size="1.27" layer="27" ratio="10">&gt;VALUE</text>
<rectangle x1="4.318" y1="-0.3048" x2="5.1816" y2="0.3048" layer="21"/>
<rectangle x1="-5.1816" y1="-0.3048" x2="-4.318" y2="0.3048" layer="21"/>
</package>
<package name="0309V">
<description>Resistor&lt;p&gt;
Type 0309 Vertical Grid  2.5 mm</description>
<wire x1="1.27" y1="0" x2="0.635" y2="0" width="0.6096" layer="51"/>
<wire x1="-0.635" y1="0" x2="-1.27" y2="0" width="0.6096" layer="51"/>
<circle x="-1.27" y="0" radius="1.524" width="0.127" layer="21"/>
<circle x="-1.27" y="0" radius="0.762" width="0.127" layer="51"/>
<pad name="1" x="-1.27" y="0" drill="0.8128" shape="octagon"/>
<pad name="2" x="1.27" y="0" drill="0.8128" shape="octagon"/>
<text x="0.508" y="1.143" size="1.27" layer="25" ratio="10">&gt;NAME</text>
<text x="0.381" y="-2.4638" size="1.27" layer="27" ratio="10">&gt;VALUE</text>
<rectangle x1="0.254" y1="-0.3048" x2="0.5588" y2="0.3048" layer="51"/>
<rectangle x1="-0.635" y1="-0.3048" x2="-0.3302" y2="0.3048" layer="51"/>
<rectangle x1="-0.3302" y1="-0.3048" x2="0.254" y2="0.3048" layer="21"/>
</package>
<package name="0411/12">
<description>Resistor&lt;p&gt;
Type 0411 Grid  12.5 mm</description>
<wire x1="6.35" y1="0" x2="5.461" y2="0" width="0.762" layer="51"/>
<wire x1="-6.35" y1="0" x2="-5.461" y2="0" width="0.762" layer="51"/>
<wire x1="5.08" y1="-1.651" x2="5.08" y2="1.651" width="0.127" layer="21"/>
<wire x1="4.699" y1="2.032" x2="5.08" y2="1.651" width="0.127" layer="21" curve="-90"/>
<wire x1="-5.08" y1="-1.651" x2="-4.699" y2="-2.032" width="0.127" layer="21" curve="90"/>
<wire x1="4.699" y1="-2.032" x2="5.08" y2="-1.651" width="0.127" layer="21" curve="90"/>
<wire x1="-5.08" y1="1.651" x2="-4.699" y2="2.032" width="0.127" layer="21" curve="-90"/>
<wire x1="4.699" y1="2.032" x2="4.064" y2="2.032" width="0.127" layer="21"/>
<wire x1="3.937" y1="1.905" x2="4.064" y2="2.032" width="0.127" layer="21"/>
<wire x1="4.699" y1="-2.032" x2="4.064" y2="-2.032" width="0.127" layer="21"/>
<wire x1="3.937" y1="-1.905" x2="4.064" y2="-2.032" width="0.127" layer="21"/>
<wire x1="-3.937" y1="1.905" x2="-4.064" y2="2.032" width="0.127" layer="21"/>
<wire x1="-3.937" y1="1.905" x2="3.937" y2="1.905" width="0.127" layer="21"/>
<wire x1="-3.937" y1="-1.905" x2="-4.064" y2="-2.032" width="0.127" layer="21"/>
<wire x1="-3.937" y1="-1.905" x2="3.937" y2="-1.905" width="0.127" layer="21"/>
<wire x1="-5.08" y1="1.651" x2="-5.08" y2="-1.651" width="0.127" layer="21"/>
<wire x1="-4.699" y1="2.032" x2="-4.064" y2="2.032" width="0.127" layer="21"/>
<wire x1="-4.699" y1="-2.032" x2="-4.064" y2="-2.032" width="0.127" layer="21"/>
<pad name="1" x="-6.35" y="0" drill="0.9144" shape="octagon"/>
<pad name="2" x="6.35" y="0" drill="0.9144" shape="octagon"/>
<text x="-5.08" y="2.413" size="1.27" layer="25" ratio="10">&gt;NAME</text>
<text x="-3.5814" y="-0.635" size="1.27" layer="27" ratio="10">&gt;VALUE</text>
<rectangle x1="-5.3594" y1="-0.381" x2="-5.08" y2="0.381" layer="21"/>
<rectangle x1="5.08" y1="-0.381" x2="5.3594" y2="0.381" layer="21"/>
</package>
<package name="0411/15">
<description>Resistor&lt;p&gt;
Type 0411 Grid  15 mm</description>
<wire x1="5.08" y1="-1.651" x2="5.08" y2="1.651" width="0.127" layer="21"/>
<wire x1="4.699" y1="2.032" x2="5.08" y2="1.651" width="0.127" layer="21" curve="-90"/>
<wire x1="-5.08" y1="-1.651" x2="-4.699" y2="-2.032" width="0.127" layer="21" curve="90"/>
<wire x1="4.699" y1="-2.032" x2="5.08" y2="-1.651" width="0.127" layer="21" curve="90"/>
<wire x1="-5.08" y1="1.651" x2="-4.699" y2="2.032" width="0.127" layer="21" curve="-90"/>
<wire x1="4.699" y1="2.032" x2="4.064" y2="2.032" width="0.127" layer="21"/>
<wire x1="3.937" y1="1.905" x2="4.064" y2="2.032" width="0.127" layer="21"/>
<wire x1="4.699" y1="-2.032" x2="4.064" y2="-2.032" width="0.127" layer="21"/>
<wire x1="3.937" y1="-1.905" x2="4.064" y2="-2.032" width="0.127" layer="21"/>
<wire x1="-3.937" y1="1.905" x2="-4.064" y2="2.032" width="0.127" layer="21"/>
<wire x1="-3.937" y1="1.905" x2="3.937" y2="1.905" width="0.127" layer="21"/>
<wire x1="-3.937" y1="-1.905" x2="-4.064" y2="-2.032" width="0.127" layer="21"/>
<wire x1="-3.937" y1="-1.905" x2="3.937" y2="-1.905" width="0.127" layer="21"/>
<wire x1="-5.08" y1="1.651" x2="-5.08" y2="-1.651" width="0.127" layer="21"/>
<wire x1="-4.699" y1="2.032" x2="-4.064" y2="2.032" width="0.127" layer="21"/>
<wire x1="-4.699" y1="-2.032" x2="-4.064" y2="-2.032" width="0.127" layer="21"/>
<wire x1="-7.62" y1="0" x2="-6.35" y2="0" width="0.762" layer="51"/>
<wire x1="6.35" y1="0" x2="7.62" y2="0" width="0.762" layer="51"/>
<pad name="1" x="-7.62" y="0" drill="0.9144" shape="octagon"/>
<pad name="2" x="7.62" y="0" drill="0.9144" shape="octagon"/>
<text x="-5.08" y="2.413" size="1.27" layer="25" ratio="10">&gt;NAME</text>
<text x="-3.5814" y="-0.635" size="1.27" layer="27" ratio="10">&gt;VALUE</text>
<rectangle x1="5.08" y1="-0.381" x2="6.477" y2="0.381" layer="21"/>
<rectangle x1="-6.477" y1="-0.381" x2="-5.08" y2="0.381" layer="21"/>
</package>
<package name="0411V">
<description>Resistor&lt;p&gt;
Type 0411 Vertical Grid  3.81 mm</description>
<wire x1="1.27" y1="0" x2="0.3048" y2="0" width="0.762" layer="51"/>
<wire x1="-1.5748" y1="0" x2="-2.54" y2="0" width="0.762" layer="51"/>
<circle x="-2.54" y="0" radius="2.032" width="0.127" layer="21"/>
<circle x="-2.54" y="0" radius="1.016" width="0.127" layer="51"/>
<pad name="1" x="-2.54" y="0" drill="0.9144" shape="octagon"/>
<pad name="2" x="1.27" y="0" drill="0.9144" shape="octagon"/>
<text x="-0.508" y="1.143" size="1.27" layer="25" ratio="10">&gt;NAME</text>
<text x="-0.5334" y="-2.413" size="1.27" layer="27" ratio="10">&gt;VALUE</text>
<rectangle x1="-1.4732" y1="-0.381" x2="0.2032" y2="0.381" layer="21"/>
</package>
<package name="0414/15">
<description>Resistor&lt;p&gt;
Type 0414 Grid  15 mm</description>
<wire x1="7.62" y1="0" x2="6.604" y2="0" width="0.8128" layer="51"/>
<wire x1="-7.62" y1="0" x2="-6.604" y2="0" width="0.8128" layer="51"/>
<wire x1="-6.096" y1="1.905" x2="-5.842" y2="2.159" width="0.127" layer="21" curve="-90"/>
<wire x1="-6.096" y1="-1.905" x2="-5.842" y2="-2.159" width="0.127" layer="21" curve="90"/>
<wire x1="5.842" y1="-2.159" x2="6.096" y2="-1.905" width="0.127" layer="21" curve="90"/>
<wire x1="5.842" y1="2.159" x2="6.096" y2="1.905" width="0.127" layer="21" curve="-90"/>
<wire x1="-6.096" y1="-1.905" x2="-6.096" y2="1.905" width="0.127" layer="21"/>
<wire x1="-5.842" y1="2.159" x2="-4.953" y2="2.159" width="0.127" layer="21"/>
<wire x1="-4.826" y1="2.032" x2="-4.953" y2="2.159" width="0.127" layer="21"/>
<wire x1="-5.842" y1="-2.159" x2="-4.953" y2="-2.159" width="0.127" layer="21"/>
<wire x1="-4.826" y1="-2.032" x2="-4.953" y2="-2.159" width="0.127" layer="21"/>
<wire x1="4.826" y1="2.032" x2="4.953" y2="2.159" width="0.127" layer="21"/>
<wire x1="4.826" y1="2.032" x2="-4.826" y2="2.032" width="0.127" layer="21"/>
<wire x1="4.826" y1="-2.032" x2="4.953" y2="-2.159" width="0.127" layer="21"/>
<wire x1="4.826" y1="-2.032" x2="-4.826" y2="-2.032" width="0.127" layer="21"/>
<wire x1="5.842" y1="2.159" x2="4.953" y2="2.159" width="0.127" layer="21"/>
<wire x1="5.842" y1="-2.159" x2="4.953" y2="-2.159" width="0.127" layer="21"/>
<wire x1="6.096" y1="-1.905" x2="6.096" y2="1.905" width="0.127" layer="21"/>
<pad name="1" x="-7.62" y="0" drill="1.016" shape="octagon"/>
<pad name="2" x="7.62" y="0" drill="1.016" shape="octagon"/>
<text x="-6.096" y="2.5654" size="1.27" layer="25" ratio="10">&gt;NAME</text>
<text x="-4.318" y="-0.5842" size="1.27" layer="27" ratio="10">&gt;VALUE</text>
<rectangle x1="6.096" y1="-0.4064" x2="6.5024" y2="0.4064" layer="21"/>
<rectangle x1="-6.5024" y1="-0.4064" x2="-6.096" y2="0.4064" layer="21"/>
</package>
<package name="0414V">
<description>Resistor&lt;p&gt;
Type 0414 Vertical Grid  5 mm</description>
<wire x1="2.54" y1="0" x2="1.397" y2="0" width="0.8128" layer="51"/>
<wire x1="-2.54" y1="0" x2="-1.397" y2="0" width="0.8128" layer="51"/>
<circle x="-2.54" y="0" radius="2.159" width="0.127" layer="21"/>
<circle x="-2.54" y="0" radius="1.143" width="0.127" layer="51"/>
<pad name="1" x="-2.54" y="0" drill="1.016" shape="octagon"/>
<pad name="2" x="2.54" y="0" drill="1.016" shape="octagon"/>
<text x="0" y="1.4224" size="1.27" layer="25" ratio="10">&gt;NAME</text>
<text x="0" y="-2.7432" size="1.27" layer="27" ratio="10">&gt;VALUE</text>
<rectangle x1="-1.2954" y1="-0.4064" x2="1.2954" y2="0.4064" layer="21"/>
</package>
<package name="0617/17">
<description>Resistor&lt;p&gt;
Type 0617  Grid  17.5 mm</description>
<wire x1="-8.89" y1="0" x2="-8.636" y2="0" width="0.8128" layer="51"/>
<wire x1="-7.874" y1="3.048" x2="-6.985" y2="3.048" width="0.127" layer="21"/>
<wire x1="-6.731" y1="2.794" x2="-6.985" y2="3.048" width="0.127" layer="21"/>
<wire x1="-7.874" y1="-3.048" x2="-6.985" y2="-3.048" width="0.127" layer="21"/>
<wire x1="-6.731" y1="-2.794" x2="-6.985" y2="-3.048" width="0.127" layer="21"/>
<wire x1="6.731" y1="2.794" x2="6.985" y2="3.048" width="0.127" layer="21"/>
<wire x1="6.731" y1="2.794" x2="-6.731" y2="2.794" width="0.127" layer="21"/>
<wire x1="6.731" y1="-2.794" x2="6.985" y2="-3.048" width="0.127" layer="21"/>
<wire x1="6.731" y1="-2.794" x2="-6.731" y2="-2.794" width="0.127" layer="21"/>
<wire x1="7.874" y1="3.048" x2="6.985" y2="3.048" width="0.127" layer="21"/>
<wire x1="7.874" y1="-3.048" x2="6.985" y2="-3.048" width="0.127" layer="21"/>
<wire x1="-8.255" y1="-2.667" x2="-8.255" y2="-1.016" width="0.127" layer="21"/>
<wire x1="-8.255" y1="1.016" x2="-8.255" y2="-1.016" width="0.127" layer="51"/>
<wire x1="-8.255" y1="1.016" x2="-8.255" y2="2.667" width="0.127" layer="21"/>
<wire x1="8.255" y1="-2.667" x2="8.255" y2="-1.016" width="0.127" layer="21"/>
<wire x1="8.255" y1="1.016" x2="8.255" y2="-1.016" width="0.127" layer="51"/>
<wire x1="8.255" y1="1.016" x2="8.255" y2="2.667" width="0.127" layer="21"/>
<wire x1="8.636" y1="0" x2="8.89" y2="0" width="0.8128" layer="51"/>
<wire x1="-8.255" y1="2.667" x2="-7.874" y2="3.048" width="0.127" layer="21" curve="-90"/>
<wire x1="7.874" y1="3.048" x2="8.255" y2="2.667" width="0.127" layer="21" curve="-90"/>
<wire x1="-8.255" y1="-2.667" x2="-7.874" y2="-3.048" width="0.127" layer="21" curve="90"/>
<wire x1="7.874" y1="-3.048" x2="8.255" y2="-2.667" width="0.127" layer="21" curve="90"/>
<pad name="1" x="-8.89" y="0" drill="1.016" shape="octagon"/>
<pad name="2" x="8.89" y="0" drill="1.016" shape="octagon"/>
<text x="-8.128" y="3.4544" size="1.27" layer="25" ratio="10">&gt;NAME</text>
<text x="-6.096" y="-0.7112" size="1.27" layer="27" ratio="10">&gt;VALUE</text>
<rectangle x1="-8.5344" y1="-0.4064" x2="-8.2296" y2="0.4064" layer="51"/>
<rectangle x1="8.2296" y1="-0.4064" x2="8.5344" y2="0.4064" layer="51"/>
</package>
<package name="0617/22">
<description>Resistor&lt;p&gt;
Type 0617  Grid  22.5 mm</description>
<wire x1="-10.287" y1="0" x2="-11.43" y2="0" width="0.8128" layer="51"/>
<wire x1="-8.255" y1="-2.667" x2="-8.255" y2="2.667" width="0.127" layer="21"/>
<wire x1="-7.874" y1="3.048" x2="-6.985" y2="3.048" width="0.127" layer="21"/>
<wire x1="-6.731" y1="2.794" x2="-6.985" y2="3.048" width="0.127" layer="21"/>
<wire x1="-7.874" y1="-3.048" x2="-6.985" y2="-3.048" width="0.127" layer="21"/>
<wire x1="-6.731" y1="-2.794" x2="-6.985" y2="-3.048" width="0.127" layer="21"/>
<wire x1="6.731" y1="2.794" x2="6.985" y2="3.048" width="0.127" layer="21"/>
<wire x1="6.731" y1="2.794" x2="-6.731" y2="2.794" width="0.127" layer="21"/>
<wire x1="6.731" y1="-2.794" x2="6.985" y2="-3.048" width="0.127" layer="21"/>
<wire x1="6.731" y1="-2.794" x2="-6.731" y2="-2.794" width="0.127" layer="21"/>
<wire x1="7.874" y1="3.048" x2="6.985" y2="3.048" width="0.127" layer="21"/>
<wire x1="7.874" y1="-3.048" x2="6.985" y2="-3.048" width="0.127" layer="21"/>
<wire x1="8.255" y1="-2.667" x2="8.255" y2="2.667" width="0.127" layer="21"/>
<wire x1="11.43" y1="0" x2="10.287" y2="0" width="0.8128" layer="51"/>
<wire x1="-8.255" y1="2.667" x2="-7.874" y2="3.048" width="0.127" layer="21" curve="-90"/>
<wire x1="-8.255" y1="-2.667" x2="-7.874" y2="-3.048" width="0.127" layer="21" curve="90"/>
<wire x1="7.874" y1="3.048" x2="8.255" y2="2.667" width="0.127" layer="21" curve="-90"/>
<wire x1="7.874" y1="-3.048" x2="8.255" y2="-2.667" width="0.127" layer="21" curve="90"/>
<pad name="1" x="-11.43" y="0" drill="1.016" shape="octagon"/>
<pad name="2" x="11.43" y="0" drill="1.016" shape="octagon"/>
<text x="-8.255" y="3.4544" size="1.27" layer="25" ratio="10">&gt;NAME</text>
<text x="-6.477" y="-0.5842" size="1.27" layer="27" ratio="10">&gt;VALUE</text>
<rectangle x1="-10.1854" y1="-0.4064" x2="-8.255" y2="0.4064" layer="21"/>
<rectangle x1="8.255" y1="-0.4064" x2="10.1854" y2="0.4064" layer="21"/>
</package>
<package name="0617V">
<description>Resistor&lt;p&gt;
Type 0617  Vertical Grid  5 mm</description>
<wire x1="-2.54" y1="0" x2="-1.27" y2="0" width="0.8128" layer="51"/>
<wire x1="1.27" y1="0" x2="2.54" y2="0" width="0.8128" layer="51"/>
<circle x="-2.54" y="0" radius="3.048" width="0.127" layer="21"/>
<circle x="-2.54" y="0" radius="1.143" width="0.127" layer="51"/>
<pad name="1" x="-2.54" y="0" drill="1.016" shape="octagon"/>
<pad name="2" x="2.54" y="0" drill="1.016" shape="octagon"/>
<text x="0.635" y="1.4224" size="1.27" layer="25" ratio="10">&gt;NAME</text>
<text x="0.635" y="-2.6162" size="1.27" layer="27" ratio="10">&gt;VALUE</text>
<rectangle x1="-1.3208" y1="-0.4064" x2="1.3208" y2="0.4064" layer="21"/>
</package>
<package name="0922/22">
<description>Resistor&lt;p&gt;
Type 0922  Grid  22.5 mm</description>
<wire x1="11.43" y1="0" x2="10.795" y2="0" width="0.8128" layer="51"/>
<wire x1="-11.43" y1="0" x2="-10.795" y2="0" width="0.8128" layer="51"/>
<wire x1="-10.16" y1="-4.191" x2="-10.16" y2="4.191" width="0.127" layer="21"/>
<wire x1="-9.779" y1="4.572" x2="-8.89" y2="4.572" width="0.127" layer="21"/>
<wire x1="-8.636" y1="4.318" x2="-8.89" y2="4.572" width="0.127" layer="21"/>
<wire x1="-9.779" y1="-4.572" x2="-8.89" y2="-4.572" width="0.127" layer="21"/>
<wire x1="-8.636" y1="-4.318" x2="-8.89" y2="-4.572" width="0.127" layer="21"/>
<wire x1="8.636" y1="4.318" x2="8.89" y2="4.572" width="0.127" layer="21"/>
<wire x1="8.636" y1="4.318" x2="-8.636" y2="4.318" width="0.127" layer="21"/>
<wire x1="8.636" y1="-4.318" x2="8.89" y2="-4.572" width="0.127" layer="21"/>
<wire x1="8.636" y1="-4.318" x2="-8.636" y2="-4.318" width="0.127" layer="21"/>
<wire x1="9.779" y1="4.572" x2="8.89" y2="4.572" width="0.127" layer="21"/>
<wire x1="9.779" y1="-4.572" x2="8.89" y2="-4.572" width="0.127" layer="21"/>
<wire x1="10.16" y1="-4.191" x2="10.16" y2="4.191" width="0.127" layer="21"/>
<wire x1="-10.16" y1="-4.191" x2="-9.779" y2="-4.572" width="0.127" layer="21" curve="90"/>
<wire x1="-10.16" y1="4.191" x2="-9.779" y2="4.572" width="0.127" layer="21" curve="-90"/>
<wire x1="9.779" y1="-4.572" x2="10.16" y2="-4.191" width="0.127" layer="21" curve="90"/>
<wire x1="9.779" y1="4.572" x2="10.16" y2="4.191" width="0.127" layer="21" curve="-90"/>
<pad name="1" x="-11.43" y="0" drill="1.016" shape="octagon"/>
<pad name="2" x="11.43" y="0" drill="1.016" shape="octagon"/>
<text x="-10.16" y="5.1054" size="1.27" layer="25" ratio="10">&gt;NAME</text>
<text x="-6.477" y="-0.5842" size="1.27" layer="27" ratio="10">&gt;VALUE</text>
<rectangle x1="-10.7188" y1="-0.4064" x2="-10.16" y2="0.4064" layer="51"/>
<rectangle x1="10.16" y1="-0.4064" x2="10.3124" y2="0.4064" layer="21"/>
<rectangle x1="-10.3124" y1="-0.4064" x2="-10.16" y2="0.4064" layer="21"/>
<rectangle x1="10.16" y1="-0.4064" x2="10.7188" y2="0.4064" layer="51"/>
</package>
<package name="P0613V">
<description>Resistor&lt;p&gt;
Type 0613 Vertical Grid  5 mm</description>
<wire x1="2.54" y1="0" x2="1.397" y2="0" width="0.8128" layer="51"/>
<wire x1="-2.54" y1="0" x2="-1.397" y2="0" width="0.8128" layer="51"/>
<circle x="-2.54" y="0" radius="2.286" width="0.127" layer="21"/>
<circle x="-2.54" y="0" radius="1.143" width="0.127" layer="51"/>
<pad name="1" x="-2.54" y="0" drill="1.016" shape="octagon"/>
<pad name="2" x="2.54" y="0" drill="1.016" shape="octagon"/>
<text x="0" y="1.524" size="1.27" layer="25" ratio="10">&gt;NAME</text>
<text x="0" y="-2.794" size="1.27" layer="27" ratio="10">&gt;VALUE</text>
<rectangle x1="-1.2954" y1="-0.4064" x2="1.3208" y2="0.4064" layer="21"/>
</package>
<package name="P0613/15">
<description>Resistor&lt;p&gt;
Type 0613 Grid  15 mm</description>
<wire x1="7.62" y1="0" x2="6.985" y2="0" width="0.8128" layer="51"/>
<wire x1="-7.62" y1="0" x2="-6.985" y2="0" width="0.8128" layer="51"/>
<wire x1="-6.477" y1="2.032" x2="-6.223" y2="2.286" width="0.127" layer="21" curve="-90"/>
<wire x1="-6.477" y1="-2.032" x2="-6.223" y2="-2.286" width="0.127" layer="21" curve="90"/>
<wire x1="6.223" y1="-2.286" x2="6.477" y2="-2.032" width="0.127" layer="21" curve="90"/>
<wire x1="6.223" y1="2.286" x2="6.477" y2="2.032" width="0.127" layer="21" curve="-90"/>
<wire x1="-6.223" y1="2.286" x2="-5.334" y2="2.286" width="0.127" layer="21"/>
<wire x1="-5.207" y1="2.159" x2="-5.334" y2="2.286" width="0.127" layer="21"/>
<wire x1="-6.223" y1="-2.286" x2="-5.334" y2="-2.286" width="0.127" layer="21"/>
<wire x1="-5.207" y1="-2.159" x2="-5.334" y2="-2.286" width="0.127" layer="21"/>
<wire x1="5.207" y1="2.159" x2="5.334" y2="2.286" width="0.127" layer="21"/>
<wire x1="5.207" y1="2.159" x2="-5.207" y2="2.159" width="0.127" layer="21"/>
<wire x1="5.207" y1="-2.159" x2="5.334" y2="-2.286" width="0.127" layer="21"/>
<wire x1="5.207" y1="-2.159" x2="-5.207" y2="-2.159" width="0.127" layer="21"/>
<wire x1="6.223" y1="2.286" x2="5.334" y2="2.286" width="0.127" layer="21"/>
<wire x1="6.223" y1="-2.286" x2="5.334" y2="-2.286" width="0.127" layer="21"/>
<wire x1="-5.334" y1="1.905" x2="-5.334" y2="-1.905" width="0.0508" layer="21"/>
<wire x1="-6.223" y1="1.905" x2="-6.223" y2="-1.905" width="0.0508" layer="21"/>
<wire x1="6.223" y1="1.905" x2="6.223" y2="-1.905" width="0.0508" layer="21"/>
<wire x1="5.334" y1="1.905" x2="5.334" y2="-1.905" width="0.0508" layer="21"/>
<wire x1="6.477" y1="-0.635" x2="6.477" y2="-2.032" width="0.127" layer="21"/>
<wire x1="6.477" y1="-0.635" x2="6.477" y2="0.635" width="0.127" layer="51"/>
<wire x1="6.477" y1="2.032" x2="6.477" y2="0.635" width="0.127" layer="21"/>
<wire x1="-6.477" y1="-2.032" x2="-6.477" y2="-0.635" width="0.127" layer="21"/>
<wire x1="-6.477" y1="0.635" x2="-6.477" y2="-0.635" width="0.127" layer="51"/>
<wire x1="-6.477" y1="0.635" x2="-6.477" y2="2.032" width="0.127" layer="21"/>
<pad name="1" x="-7.62" y="0" drill="1.016" shape="octagon"/>
<pad name="2" x="7.62" y="0" drill="1.016" shape="octagon"/>
<text x="-6.477" y="2.6924" size="1.27" layer="25" ratio="10">&gt;NAME</text>
<text x="-4.318" y="-0.7112" size="1.27" layer="27" ratio="10">&gt;VALUE</text>
<rectangle x1="-7.0358" y1="-0.4064" x2="-6.477" y2="0.4064" layer="51"/>
<rectangle x1="6.477" y1="-0.4064" x2="7.0358" y2="0.4064" layer="51"/>
</package>
<package name="P0817/22">
<description>Resistor&lt;p&gt;
Type 0817 Grid  22.5 mm</description>
<wire x1="-10.414" y1="0" x2="-11.43" y2="0" width="0.8128" layer="51"/>
<wire x1="-8.509" y1="-3.429" x2="-8.509" y2="3.429" width="0.127" layer="21"/>
<wire x1="-8.128" y1="3.81" x2="-7.239" y2="3.81" width="0.127" layer="21"/>
<wire x1="-6.985" y1="3.556" x2="-7.239" y2="3.81" width="0.127" layer="21"/>
<wire x1="-8.128" y1="-3.81" x2="-7.239" y2="-3.81" width="0.127" layer="21"/>
<wire x1="-6.985" y1="-3.556" x2="-7.239" y2="-3.81" width="0.127" layer="21"/>
<wire x1="6.985" y1="3.556" x2="7.239" y2="3.81" width="0.127" layer="21"/>
<wire x1="6.985" y1="3.556" x2="-6.985" y2="3.556" width="0.127" layer="21"/>
<wire x1="6.985" y1="-3.556" x2="7.239" y2="-3.81" width="0.127" layer="21"/>
<wire x1="6.985" y1="-3.556" x2="-6.985" y2="-3.556" width="0.127" layer="21"/>
<wire x1="8.128" y1="3.81" x2="7.239" y2="3.81" width="0.127" layer="21"/>
<wire x1="8.128" y1="-3.81" x2="7.239" y2="-3.81" width="0.127" layer="21"/>
<wire x1="8.509" y1="-3.429" x2="8.509" y2="3.429" width="0.127" layer="21"/>
<wire x1="-7.239" y1="3.429" x2="-7.239" y2="-3.429" width="0.0508" layer="21"/>
<wire x1="-8.128" y1="3.429" x2="-8.128" y2="-3.429" width="0.0508" layer="21"/>
<wire x1="8.128" y1="3.429" x2="8.128" y2="-3.429" width="0.0508" layer="21"/>
<wire x1="7.239" y1="3.429" x2="7.239" y2="-3.429" width="0.0508" layer="21"/>
<wire x1="11.43" y1="0" x2="10.414" y2="0" width="0.8128" layer="51"/>
<wire x1="-8.509" y1="3.429" x2="-8.128" y2="3.81" width="0.127" layer="21" curve="-90"/>
<wire x1="-8.509" y1="-3.429" x2="-8.128" y2="-3.81" width="0.127" layer="21" curve="90"/>
<wire x1="8.128" y1="3.81" x2="8.509" y2="3.429" width="0.127" layer="21" curve="-90"/>
<wire x1="8.128" y1="-3.81" x2="8.509" y2="-3.429" width="0.127" layer="21" curve="90"/>
<pad name="1" x="-11.43" y="0" drill="1.016" shape="octagon"/>
<pad name="2" x="11.43" y="0" drill="1.016" shape="octagon"/>
<text x="-8.382" y="4.2164" size="1.27" layer="25" ratio="10">&gt;NAME</text>
<text x="-6.223" y="-0.5842" size="1.27" layer="27" ratio="10">&gt;VALUE</text>
<text x="6.604" y="-2.2606" size="1.27" layer="51" ratio="10" rot="R90">0817</text>
<rectangle x1="8.509" y1="-0.4064" x2="10.3124" y2="0.4064" layer="21"/>
<rectangle x1="-10.3124" y1="-0.4064" x2="-8.509" y2="0.4064" layer="21"/>
</package>
<package name="P0817V">
<description>Resistor&lt;p&gt;
Type 0817 Grid  6.35 mm</description>
<wire x1="-3.81" y1="0" x2="-5.08" y2="0" width="0.8128" layer="51"/>
<wire x1="1.27" y1="0" x2="0" y2="0" width="0.8128" layer="51"/>
<circle x="-5.08" y="0" radius="3.81" width="0.127" layer="21"/>
<circle x="-5.08" y="0" radius="1.27" width="0.127" layer="51"/>
<pad name="1" x="-5.08" y="0" drill="1.016" shape="octagon"/>
<pad name="2" x="1.27" y="0" drill="1.016" shape="octagon"/>
<text x="-1.016" y="1.27" size="1.27" layer="25" ratio="10">&gt;NAME</text>
<text x="-1.016" y="-2.54" size="1.27" layer="27" ratio="10">&gt;VALUE</text>
<text x="-6.858" y="2.032" size="1.016" layer="21" ratio="12">0817</text>
<rectangle x1="-3.81" y1="-0.4064" x2="0" y2="0.4064" layer="21"/>
</package>
<package name="V234/12">
<description>Resistor&lt;p&gt;
Type V234 Grid  12.5 mm</description>
<wire x1="-4.953" y1="1.524" x2="-4.699" y2="1.778" width="0.127" layer="21" curve="-90"/>
<wire x1="4.699" y1="1.778" x2="4.953" y2="1.524" width="0.127" layer="21" curve="-90"/>
<wire x1="4.699" y1="-1.778" x2="4.953" y2="-1.524" width="0.127" layer="21" curve="90"/>
<wire x1="-4.953" y1="-1.524" x2="-4.699" y2="-1.778" width="0.127" layer="21" curve="90"/>
<wire x1="-4.699" y1="1.778" x2="4.699" y2="1.778" width="0.127" layer="21"/>
<wire x1="-4.953" y1="1.524" x2="-4.953" y2="-1.524" width="0.127" layer="21"/>
<wire x1="4.699" y1="-1.778" x2="-4.699" y2="-1.778" width="0.127" layer="21"/>
<wire x1="4.953" y1="1.524" x2="4.953" y2="-1.524" width="0.127" layer="21"/>
<wire x1="6.35" y1="0" x2="5.461" y2="0" width="0.8128" layer="51"/>
<wire x1="-6.35" y1="0" x2="-5.461" y2="0" width="0.8128" layer="51"/>
<pad name="1" x="-6.35" y="0" drill="1.016" shape="octagon"/>
<pad name="2" x="6.35" y="0" drill="1.016" shape="octagon"/>
<text x="-4.953" y="2.032" size="1.27" layer="25" ratio="10">&gt;NAME</text>
<text x="-3.81" y="-0.635" size="1.27" layer="27" ratio="10">&gt;VALUE</text>
<rectangle x1="4.953" y1="-0.4064" x2="5.4102" y2="0.4064" layer="21"/>
<rectangle x1="-5.4102" y1="-0.4064" x2="-4.953" y2="0.4064" layer="21"/>
</package>
<package name="V235/17">
<description>Resistor&lt;p&gt;
Type V235 Grid  17.78 mm</description>
<wire x1="-6.731" y1="2.921" x2="6.731" y2="2.921" width="0.127" layer="21"/>
<wire x1="-7.112" y1="2.54" x2="-7.112" y2="-2.54" width="0.127" layer="21"/>
<wire x1="6.731" y1="-2.921" x2="-6.731" y2="-2.921" width="0.127" layer="21"/>
<wire x1="7.112" y1="2.54" x2="7.112" y2="-2.54" width="0.127" layer="21"/>
<wire x1="8.89" y1="0" x2="7.874" y2="0" width="1.016" layer="51"/>
<wire x1="-7.874" y1="0" x2="-8.89" y2="0" width="1.016" layer="51"/>
<wire x1="-7.112" y1="-2.54" x2="-6.731" y2="-2.921" width="0.127" layer="21" curve="90"/>
<wire x1="6.731" y1="2.921" x2="7.112" y2="2.54" width="0.127" layer="21" curve="-90"/>
<wire x1="6.731" y1="-2.921" x2="7.112" y2="-2.54" width="0.127" layer="21" curve="90"/>
<wire x1="-7.112" y1="2.54" x2="-6.731" y2="2.921" width="0.127" layer="21" curve="-90"/>
<pad name="1" x="-8.89" y="0" drill="1.1938" shape="octagon"/>
<pad name="2" x="8.89" y="0" drill="1.1938" shape="octagon"/>
<text x="-6.858" y="3.302" size="1.27" layer="25" ratio="10">&gt;NAME</text>
<text x="-5.842" y="-0.635" size="1.27" layer="27" ratio="10">&gt;VALUE</text>
<rectangle x1="7.112" y1="-0.508" x2="7.747" y2="0.508" layer="21"/>
<rectangle x1="-7.747" y1="-0.508" x2="-7.112" y2="0.508" layer="21"/>
</package>
<package name="V526-0">
<description>Resistor&lt;p&gt;
Type V526-0 Grid  2.5 mm</description>
<wire x1="-2.54" y1="1.016" x2="-2.286" y2="1.27" width="0.127" layer="21" curve="-90"/>
<wire x1="2.286" y1="1.27" x2="2.54" y2="1.016" width="0.127" layer="21" curve="-90"/>
<wire x1="2.286" y1="-1.27" x2="2.54" y2="-1.016" width="0.127" layer="21" curve="90"/>
<wire x1="-2.54" y1="-1.016" x2="-2.286" y2="-1.27" width="0.127" layer="21" curve="90"/>
<wire x1="2.286" y1="1.27" x2="-2.286" y2="1.27" width="0.127" layer="21"/>
<wire x1="2.54" y1="-1.016" x2="2.54" y2="1.016" width="0.127" layer="21"/>
<wire x1="-2.286" y1="-1.27" x2="2.286" y2="-1.27" width="0.127" layer="21"/>
<wire x1="-2.54" y1="1.016" x2="-2.54" y2="-1.016" width="0.127" layer="21"/>
<pad name="1" x="-1.27" y="0" drill="0.8128" shape="octagon"/>
<pad name="2" x="1.27" y="0" drill="0.8128" shape="octagon"/>
<text x="3.048" y="-0.635" size="1.27" layer="25" ratio="10">&gt;NAME</text>
<text x="-2.159" y="-0.635" size="1.27" layer="27" ratio="10">&gt;VALUE</text>
</package>
<package name="C0402">
<description>Capacitor&lt;p&gt;
chip</description>
<wire x1="-0.2451" y1="0.2238" x2="0.2451" y2="0.2238" width="0.127" layer="51"/>
<wire x1="0.2451" y1="-0.2238" x2="-0.2451" y2="-0.2238" width="0.127" layer="51"/>
<wire x1="-1.4732" y1="0.4826" x2="1.4732" y2="0.4826" width="0.0508" layer="39"/>
<wire x1="1.4732" y1="0.4826" x2="1.4732" y2="-0.4826" width="0.0508" layer="39"/>
<wire x1="1.4732" y1="-0.4826" x2="-1.4732" y2="-0.4826" width="0.0508" layer="39"/>
<wire x1="-1.4732" y1="-0.4826" x2="-1.4732" y2="0.4826" width="0.0508" layer="39"/>
<smd name="1" x="-0.65" y="0" dx="0.7" dy="0.8998" layer="1"/>
<smd name="2" x="0.65" y="0" dx="0.7" dy="0.8998" layer="1"/>
<text x="-0.635" y="0.635" size="1.27" layer="25">&gt;NAME</text>
<text x="-0.635" y="-1.905" size="1.27" layer="27">&gt;VALUE</text>
<rectangle x1="-0.554" y1="-0.3048" x2="-0.254" y2="0.2951" layer="51"/>
<rectangle x1="0.2588" y1="-0.3048" x2="0.5588" y2="0.2951" layer="51"/>
<rectangle x1="-0.1999" y1="-0.3" x2="0.1999" y2="0.3" layer="35"/>
</package>
<package name="C0504">
<description>Capacitor&lt;p&gt;
chip</description>
<wire x1="-1.4732" y1="0.9827" x2="1.4732" y2="0.9827" width="0.0508" layer="39"/>
<wire x1="1.4732" y1="0.9827" x2="1.4732" y2="-0.9827" width="0.0508" layer="39"/>
<wire x1="1.4732" y1="-0.9827" x2="-1.4732" y2="-0.9827" width="0.0508" layer="39"/>
<wire x1="-1.4732" y1="-0.9827" x2="-1.4732" y2="0.9827" width="0.0508" layer="39"/>
<wire x1="-0.2944" y1="0.5588" x2="0.2944" y2="0.5588" width="0.1" layer="51"/>
<wire x1="-0.2944" y1="-0.5588" x2="0.2944" y2="-0.5588" width="0.1" layer="51"/>
<smd name="1" x="-0.7" y="0" dx="1" dy="1.3" layer="1"/>
<smd name="2" x="0.7" y="0" dx="1" dy="1.3" layer="1"/>
<text x="-0.635" y="1.27" size="1.27" layer="25">&gt;NAME</text>
<text x="-0.635" y="-2.54" size="1.27" layer="27">&gt;VALUE</text>
<rectangle x1="-0.6604" y1="-0.6223" x2="-0.2804" y2="0.6276" layer="51"/>
<rectangle x1="0.2794" y1="-0.6223" x2="0.6594" y2="0.6276" layer="51"/>
<rectangle x1="-0.1001" y1="-0.4001" x2="0.1001" y2="0.4001" layer="35"/>
</package>
<package name="C0603">
<description>Capacitor&lt;p&gt;
chip</description>
<wire x1="-1.4732" y1="0.9827" x2="1.4732" y2="0.9827" width="0.0508" layer="39"/>
<wire x1="1.4732" y1="0.9827" x2="1.4732" y2="-0.9827" width="0.0508" layer="39"/>
<wire x1="1.4732" y1="-0.9827" x2="-1.4732" y2="-0.9827" width="0.0508" layer="39"/>
<wire x1="-1.4732" y1="-0.9827" x2="-1.4732" y2="0.9827" width="0.0508" layer="39"/>
<wire x1="-0.3556" y1="0.4318" x2="0.3556" y2="0.4318" width="0.1" layer="51"/>
<wire x1="-0.3556" y1="-0.4191" x2="0.3556" y2="-0.4191" width="0.1" layer="51"/>
<smd name="1" x="-0.8499" y="0" dx="1.1" dy="1" layer="1"/>
<smd name="2" x="0.8499" y="0" dx="1.1" dy="1" layer="1"/>
<text x="-0.635" y="0.635" size="1.27" layer="25">&gt;NAME</text>
<text x="-0.635" y="-1.905" size="1.27" layer="27">&gt;VALUE</text>
<rectangle x1="-0.8382" y1="-0.4699" x2="-0.3381" y2="0.4801" layer="51"/>
<rectangle x1="0.3302" y1="-0.4699" x2="0.8303" y2="0.4801" layer="51"/>
<rectangle x1="-0.1999" y1="-0.3" x2="0.1999" y2="0.3" layer="35"/>
</package>
<package name="C0805">
<description>Capacitor&lt;p&gt;
chip</description>
<wire x1="-1.9733" y1="0.9827" x2="1.9733" y2="0.9827" width="0.0508" layer="39"/>
<wire x1="1.9733" y1="-0.9827" x2="-1.9733" y2="-0.9827" width="0.0508" layer="39"/>
<wire x1="-1.9733" y1="-0.9827" x2="-1.9733" y2="0.9827" width="0.0508" layer="39"/>
<wire x1="-0.381" y1="0.6604" x2="0.381" y2="0.6604" width="0.1" layer="51"/>
<wire x1="-0.3556" y1="-0.6604" x2="0.381" y2="-0.6604" width="0.1" layer="51"/>
<wire x1="1.9733" y1="0.9827" x2="1.9733" y2="-0.9827" width="0.0508" layer="39"/>
<smd name="1" x="-0.8499" y="0" dx="1.3" dy="1.5" layer="1"/>
<smd name="2" x="0.8499" y="0" dx="1.3" dy="1.5" layer="1"/>
<text x="-1.27" y="1.27" size="1.27" layer="25">&gt;NAME</text>
<text x="-1.27" y="-2.54" size="1.27" layer="27">&gt;VALUE</text>
<rectangle x1="-1.0922" y1="-0.7239" x2="-0.3421" y2="0.7262" layer="51"/>
<rectangle x1="0.3556" y1="-0.7239" x2="1.1057" y2="0.7262" layer="51"/>
<rectangle x1="-0.1001" y1="-0.4001" x2="0.1001" y2="0.4001" layer="35"/>
</package>
<package name="C1005">
<description>Capacitor&lt;p&gt;
chip</description>
<wire x1="-0.2451" y1="0.2238" x2="0.2451" y2="0.2238" width="0.127" layer="51"/>
<wire x1="0.2451" y1="-0.2238" x2="-0.2451" y2="-0.2238" width="0.127" layer="51"/>
<wire x1="-1.4732" y1="0.4826" x2="1.4732" y2="0.4826" width="0.0508" layer="39"/>
<wire x1="1.4732" y1="0.4826" x2="1.4732" y2="-0.4826" width="0.0508" layer="39"/>
<wire x1="1.4732" y1="-0.4826" x2="-1.4732" y2="-0.4826" width="0.0508" layer="39"/>
<wire x1="-1.4732" y1="-0.4826" x2="-1.4732" y2="0.4826" width="0.0508" layer="39"/>
<smd name="1" x="-0.65" y="0" dx="0.7" dy="0.8998" layer="1"/>
<smd name="2" x="0.65" y="0" dx="0.7" dy="0.8998" layer="1"/>
<text x="-0.635" y="0.635" size="1.27" layer="25">&gt;NAME</text>
<text x="-0.635" y="-1.905" size="1.27" layer="27">&gt;VALUE</text>
<rectangle x1="-0.554" y1="-0.3048" x2="-0.254" y2="0.2951" layer="51"/>
<rectangle x1="0.2588" y1="-0.3048" x2="0.5588" y2="0.2951" layer="51"/>
<rectangle x1="-0.1999" y1="-0.3" x2="0.1999" y2="0.3" layer="35"/>
</package>
<package name="C1206">
<description>Capacitor&lt;p&gt;
chip</description>
<wire x1="-2.4732" y1="0.9827" x2="2.4732" y2="0.9827" width="0.0508" layer="39"/>
<wire x1="2.4732" y1="-0.9827" x2="-2.4732" y2="-0.9827" width="0.0508" layer="39"/>
<wire x1="-2.4732" y1="-0.9827" x2="-2.4732" y2="0.9827" width="0.0508" layer="39"/>
<wire x1="2.4732" y1="0.9827" x2="2.4732" y2="-0.9827" width="0.0508" layer="39"/>
<wire x1="-0.9652" y1="0.7874" x2="0.9652" y2="0.7874" width="0.1" layer="51"/>
<wire x1="-0.9652" y1="-0.7874" x2="0.9652" y2="-0.7874" width="0.1" layer="51"/>
<smd name="1" x="-1.4" y="0" dx="1.5996" dy="1.8" layer="1"/>
<smd name="2" x="1.4" y="0" dx="1.5996" dy="1.8" layer="1"/>
<text x="-1.27" y="1.27" size="1.27" layer="25">&gt;NAME</text>
<text x="-1.27" y="-2.54" size="1.27" layer="27">&gt;VALUE</text>
<rectangle x1="-1.7018" y1="-0.8509" x2="-0.9517" y2="0.8491" layer="51"/>
<rectangle x1="0.9517" y1="-0.8491" x2="1.7018" y2="0.8509" layer="51"/>
<rectangle x1="-0.1999" y1="-0.4001" x2="0.1999" y2="0.4001" layer="35"/>
</package>
<package name="C1210">
<description>Capacitor&lt;p&gt;
chip</description>
<wire x1="-2.4732" y1="1.4826" x2="2.4732" y2="1.4826" width="0.0508" layer="39"/>
<wire x1="2.4732" y1="-1.4826" x2="-2.4732" y2="-1.4826" width="0.0508" layer="39"/>
<wire x1="-2.4732" y1="-1.4826" x2="-2.4732" y2="1.4826" width="0.0508" layer="39"/>
<wire x1="-0.9652" y1="1.2446" x2="0.9652" y2="1.2446" width="0.1" layer="51"/>
<wire x1="-0.9652" y1="-1.2446" x2="0.9652" y2="-1.2446" width="0.1" layer="51"/>
<wire x1="2.4732" y1="1.4826" x2="2.4732" y2="-1.4826" width="0.0508" layer="39"/>
<smd name="1" x="-1.4" y="0" dx="1.5996" dy="2.7" layer="1"/>
<smd name="2" x="1.4" y="0" dx="1.5996" dy="2.7" layer="1"/>
<text x="-1.905" y="1.905" size="1.27" layer="25">&gt;NAME</text>
<text x="-1.905" y="-3.175" size="1.27" layer="27">&gt;VALUE</text>
<rectangle x1="-1.7018" y1="-1.2954" x2="-0.9517" y2="1.3045" layer="51"/>
<rectangle x1="0.9517" y1="-1.3045" x2="1.7018" y2="1.2954" layer="51"/>
<rectangle x1="-0.1999" y1="-0.4001" x2="0.1999" y2="0.4001" layer="35"/>
</package>
<package name="C1310">
<description>Capacitor&lt;p&gt;
chip</description>
<wire x1="-1.4732" y1="0.9827" x2="1.4732" y2="0.9827" width="0.0508" layer="39"/>
<wire x1="1.4732" y1="0.9827" x2="1.4732" y2="-0.9827" width="0.0508" layer="39"/>
<wire x1="1.4732" y1="-0.9827" x2="-1.4732" y2="-0.9827" width="0.0508" layer="39"/>
<wire x1="-1.4732" y1="-0.9827" x2="-1.4732" y2="0.9827" width="0.0508" layer="39"/>
<wire x1="-0.2944" y1="0.5588" x2="0.2944" y2="0.5588" width="0.1" layer="51"/>
<wire x1="-0.2944" y1="-0.5588" x2="0.2944" y2="-0.5588" width="0.1" layer="51"/>
<smd name="1" x="-0.7" y="0" dx="1" dy="1.3" layer="1"/>
<smd name="2" x="0.7" y="0" dx="1" dy="1.3" layer="1"/>
<text x="-0.635" y="1.27" size="1.27" layer="25">&gt;NAME</text>
<text x="-0.635" y="-2.54" size="1.27" layer="27">&gt;VALUE</text>
<rectangle x1="-0.6604" y1="-0.6223" x2="-0.2804" y2="0.6276" layer="51"/>
<rectangle x1="0.2794" y1="-0.6223" x2="0.6594" y2="0.6276" layer="51"/>
<rectangle x1="-0.1001" y1="-0.3" x2="0.1001" y2="0.3" layer="35"/>
</package>
<package name="C1608">
<description>Capacitor&lt;p&gt;
chip</description>
<wire x1="-1.4732" y1="0.9827" x2="1.4732" y2="0.9827" width="0.0508" layer="39"/>
<wire x1="1.4732" y1="0.9827" x2="1.4732" y2="-0.9827" width="0.0508" layer="39"/>
<wire x1="1.4732" y1="-0.9827" x2="-1.4732" y2="-0.9827" width="0.0508" layer="39"/>
<wire x1="-1.4732" y1="-0.9827" x2="-1.4732" y2="0.9827" width="0.0508" layer="39"/>
<wire x1="-0.3556" y1="0.4318" x2="0.3556" y2="0.4318" width="0.1" layer="51"/>
<wire x1="-0.3556" y1="-0.4191" x2="0.3556" y2="-0.4191" width="0.1" layer="51"/>
<smd name="1" x="-0.8499" y="0" dx="1.1" dy="1" layer="1"/>
<smd name="2" x="0.8499" y="0" dx="1.1" dy="1" layer="1"/>
<text x="-0.635" y="0.635" size="1.27" layer="25">&gt;NAME</text>
<text x="-0.635" y="-1.905" size="1.27" layer="27">&gt;VALUE</text>
<rectangle x1="-0.8382" y1="-0.4699" x2="-0.3381" y2="0.4801" layer="51"/>
<rectangle x1="0.3302" y1="-0.4699" x2="0.8303" y2="0.4801" layer="51"/>
<rectangle x1="-0.1999" y1="-0.3" x2="0.1999" y2="0.3" layer="35"/>
</package>
<package name="C1812">
<description>Capacitor&lt;p&gt;
chip</description>
<wire x1="-2.9733" y1="1.9827" x2="2.9733" y2="1.9827" width="0.0508" layer="39"/>
<wire x1="2.9733" y1="-1.9827" x2="-2.9733" y2="-1.9827" width="0.0508" layer="39"/>
<wire x1="-2.9733" y1="-1.9827" x2="-2.9733" y2="1.9827" width="0.0508" layer="39"/>
<wire x1="-1.4732" y1="1.6002" x2="1.4732" y2="1.6002" width="0.1" layer="51"/>
<wire x1="-1.4478" y1="-1.6002" x2="1.4732" y2="-1.6002" width="0.1" layer="51"/>
<wire x1="2.9733" y1="1.9827" x2="2.9733" y2="-1.9827" width="0.0508" layer="39"/>
<smd name="1" x="-1.95" y="0" dx="1.8998" dy="3.4" layer="1"/>
<smd name="2" x="1.95" y="0" dx="1.8998" dy="3.4" layer="1"/>
<text x="-1.905" y="2.54" size="1.27" layer="25">&gt;NAME</text>
<text x="-1.905" y="-3.81" size="1.27" layer="27">&gt;VALUE</text>
<rectangle x1="-2.3876" y1="-1.651" x2="-1.4376" y2="1.649" layer="51"/>
<rectangle x1="1.4478" y1="-1.651" x2="2.3978" y2="1.649" layer="51"/>
<rectangle x1="-0.3" y1="-0.4001" x2="0.3" y2="0.4001" layer="35"/>
</package>
<package name="C1825">
<description>Capacitor&lt;p&gt;
chip</description>
<wire x1="-2.9733" y1="3.4826" x2="2.9733" y2="3.4826" width="0.0508" layer="39"/>
<wire x1="2.9733" y1="-3.4826" x2="-2.9733" y2="-3.4826" width="0.0508" layer="39"/>
<wire x1="-2.9733" y1="-3.4826" x2="-2.9733" y2="3.4826" width="0.0508" layer="39"/>
<wire x1="-1.4986" y1="3.2766" x2="1.4732" y2="3.2766" width="0.1" layer="51"/>
<wire x1="-1.4732" y1="-3.2766" x2="1.4986" y2="-3.2766" width="0.1" layer="51"/>
<wire x1="2.9733" y1="3.4826" x2="2.9733" y2="-3.4826" width="0.0508" layer="39"/>
<smd name="1" x="-1.95" y="0" dx="1.8998" dy="6.8" layer="1"/>
<smd name="2" x="1.95" y="0" dx="1.8998" dy="6.8" layer="1"/>
<text x="-1.905" y="3.81" size="1.27" layer="25">&gt;NAME</text>
<text x="-1.905" y="-5.08" size="1.27" layer="27">&gt;VALUE</text>
<rectangle x1="-2.413" y1="-3.3528" x2="-1.463" y2="3.3472" layer="51"/>
<rectangle x1="1.4478" y1="-3.3528" x2="2.3978" y2="3.3472" layer="51"/>
<rectangle x1="-0.7" y1="-0.7" x2="0.7" y2="0.7" layer="35"/>
</package>
<package name="C2012">
<description>Capacitor&lt;p&gt;
chip</description>
<wire x1="-1.9733" y1="0.9827" x2="1.9733" y2="0.9827" width="0.0508" layer="39"/>
<wire x1="1.9733" y1="0.9827" x2="1.9733" y2="-0.9827" width="0.0508" layer="39"/>
<wire x1="1.9733" y1="-0.9827" x2="-1.9733" y2="-0.9827" width="0.0508" layer="39"/>
<wire x1="-1.9733" y1="-0.9827" x2="-1.9733" y2="0.9827" width="0.0508" layer="39"/>
<wire x1="-0.381" y1="0.6604" x2="0.381" y2="0.6604" width="0.1" layer="51"/>
<wire x1="-0.3556" y1="-0.6604" x2="0.381" y2="-0.6604" width="0.1" layer="51"/>
<smd name="1" x="-0.8499" y="0" dx="1.3" dy="1.5" layer="1"/>
<smd name="2" x="0.8499" y="0" dx="1.3" dy="1.5" layer="1"/>
<text x="-1.27" y="1.27" size="1.27" layer="25">&gt;NAME</text>
<text x="-1.27" y="-2.54" size="1.27" layer="27">&gt;VALUE</text>
<rectangle x1="-1.0922" y1="-0.7239" x2="-0.3421" y2="0.7262" layer="51"/>
<rectangle x1="0.3556" y1="-0.7239" x2="1.1057" y2="0.7262" layer="51"/>
<rectangle x1="-0.1001" y1="-0.4001" x2="0.1001" y2="0.4001" layer="35"/>
</package>
<package name="C3216">
<description>Capacitor&lt;p&gt;
chip</description>
<wire x1="-2.4732" y1="0.9827" x2="2.4732" y2="0.9827" width="0.0508" layer="39"/>
<wire x1="2.4732" y1="-0.9827" x2="-2.4732" y2="-0.9827" width="0.0508" layer="39"/>
<wire x1="-2.4732" y1="-0.9827" x2="-2.4732" y2="0.9827" width="0.0508" layer="39"/>
<wire x1="2.4732" y1="0.9827" x2="2.4732" y2="-0.9827" width="0.0508" layer="39"/>
<wire x1="-0.9652" y1="0.7874" x2="0.9652" y2="0.7874" width="0.1" layer="51"/>
<wire x1="-0.9652" y1="-0.7874" x2="0.9652" y2="-0.7874" width="0.1" layer="51"/>
<smd name="1" x="-1.4" y="0" dx="1.5996" dy="1.8" layer="1"/>
<smd name="2" x="1.4" y="0" dx="1.5996" dy="1.8" layer="1"/>
<text x="-1.27" y="1.27" size="1.27" layer="25">&gt;NAME</text>
<text x="-1.27" y="-2.54" size="1.27" layer="27">&gt;VALUE</text>
<rectangle x1="-1.7018" y1="-0.8509" x2="-0.9517" y2="0.8491" layer="51"/>
<rectangle x1="0.9517" y1="-0.8491" x2="1.7018" y2="0.8509" layer="51"/>
<rectangle x1="-0.3" y1="-0.5001" x2="0.3" y2="0.5001" layer="35"/>
</package>
<package name="C3225">
<description>Capacitor&lt;p&gt;
chip</description>
<wire x1="-2.4732" y1="1.4826" x2="2.4732" y2="1.4826" width="0.0508" layer="39"/>
<wire x1="2.4732" y1="-1.4826" x2="-2.4732" y2="-1.4826" width="0.0508" layer="39"/>
<wire x1="-2.4732" y1="-1.4826" x2="-2.4732" y2="1.4826" width="0.0508" layer="39"/>
<wire x1="-0.9652" y1="1.2446" x2="0.9652" y2="1.2446" width="0.1" layer="51"/>
<wire x1="-0.9652" y1="-1.2446" x2="0.9652" y2="-1.2446" width="0.1" layer="51"/>
<wire x1="2.4732" y1="1.4826" x2="2.4732" y2="-1.4826" width="0.0508" layer="39"/>
<smd name="1" x="-1.4" y="0" dx="1.5996" dy="2.7" layer="1"/>
<smd name="2" x="1.4" y="0" dx="1.5996" dy="2.7" layer="1"/>
<text x="-1.905" y="1.905" size="1.27" layer="25">&gt;NAME</text>
<text x="-1.905" y="-3.175" size="1.27" layer="27">&gt;VALUE</text>
<rectangle x1="-1.7018" y1="-1.2954" x2="-0.9517" y2="1.3045" layer="51"/>
<rectangle x1="0.9517" y1="-1.3045" x2="1.7018" y2="1.2954" layer="51"/>
<rectangle x1="-0.1999" y1="-0.5001" x2="0.1999" y2="0.5001" layer="35"/>
</package>
<package name="C4532">
<description>Capacitor&lt;p&gt;
chip</description>
<wire x1="-2.9733" y1="1.9827" x2="2.9733" y2="1.9827" width="0.0508" layer="39"/>
<wire x1="2.9733" y1="-1.9827" x2="-2.9733" y2="-1.9827" width="0.0508" layer="39"/>
<wire x1="-2.9733" y1="-1.9827" x2="-2.9733" y2="1.9827" width="0.0508" layer="39"/>
<wire x1="-1.4732" y1="1.6002" x2="1.4732" y2="1.6002" width="0.1" layer="51"/>
<wire x1="-1.4478" y1="-1.6002" x2="1.4732" y2="-1.6002" width="0.1" layer="51"/>
<wire x1="2.9733" y1="1.9827" x2="2.9733" y2="-1.9827" width="0.0508" layer="39"/>
<smd name="1" x="-1.95" y="0" dx="1.8998" dy="3.4" layer="1"/>
<smd name="2" x="1.95" y="0" dx="1.8998" dy="3.4" layer="1"/>
<text x="-1.905" y="2.54" size="1.27" layer="25">&gt;NAME</text>
<text x="-1.905" y="-3.81" size="1.27" layer="27">&gt;VALUE</text>
<rectangle x1="-2.3876" y1="-1.651" x2="-1.4376" y2="1.649" layer="51"/>
<rectangle x1="1.4478" y1="-1.651" x2="2.3978" y2="1.649" layer="51"/>
<rectangle x1="-0.4001" y1="-0.7" x2="0.4001" y2="0.7" layer="35"/>
</package>
<package name="C4564">
<description>Capacitor&lt;p&gt;
chip</description>
<wire x1="-2.9733" y1="3.4826" x2="2.9733" y2="3.4826" width="0.0508" layer="39"/>
<wire x1="2.9733" y1="-3.4826" x2="-2.9733" y2="-3.4826" width="0.0508" layer="39"/>
<wire x1="-2.9733" y1="-3.4826" x2="-2.9733" y2="3.4826" width="0.0508" layer="39"/>
<wire x1="-1.4986" y1="3.2766" x2="1.4732" y2="3.2766" width="0.1" layer="51"/>
<wire x1="-1.4732" y1="-3.2766" x2="1.4986" y2="-3.2766" width="0.1" layer="51"/>
<wire x1="2.9733" y1="3.4826" x2="2.9733" y2="-3.4826" width="0.0508" layer="39"/>
<smd name="1" x="-1.95" y="0" dx="1.8998" dy="6.8" layer="1"/>
<smd name="2" x="1.95" y="0" dx="1.8998" dy="6.8" layer="1"/>
<text x="-1.905" y="3.81" size="1.27" layer="25">&gt;NAME</text>
<text x="-1.905" y="-5.08" size="1.27" layer="27">&gt;VALUE</text>
<rectangle x1="-2.413" y1="-3.3528" x2="-1.463" y2="3.3472" layer="51"/>
<rectangle x1="1.4478" y1="-3.3528" x2="2.3978" y2="3.3472" layer="51"/>
<rectangle x1="-0.5001" y1="-1" x2="0.5001" y2="1" layer="35"/>
</package>
<package name="C025-024X044">
<description>Capacitor&lt;p&gt;
Grid  2.5 mm Outline 2.4 x 4.4 mm</description>
<wire x1="-2.159" y1="-0.635" x2="-2.159" y2="0.635" width="0.127" layer="21"/>
<wire x1="-2.159" y1="0.635" x2="-1.651" y2="1.143" width="0.127" layer="21" curve="-90"/>
<wire x1="-2.159" y1="-0.635" x2="-1.651" y2="-1.143" width="0.127" layer="21" curve="90"/>
<wire x1="1.651" y1="1.143" x2="-1.651" y2="1.143" width="0.127" layer="21"/>
<wire x1="2.159" y1="-0.635" x2="2.159" y2="0.635" width="0.127" layer="21"/>
<wire x1="1.651" y1="-1.143" x2="-1.651" y2="-1.143" width="0.127" layer="21"/>
<wire x1="1.651" y1="1.143" x2="2.159" y2="0.635" width="0.127" layer="21" curve="-90"/>
<wire x1="1.651" y1="-1.143" x2="2.159" y2="-0.635" width="0.127" layer="21" curve="90"/>
<wire x1="-0.3048" y1="0.762" x2="-0.3048" y2="0" width="0.3048" layer="51"/>
<wire x1="-0.3048" y1="0" x2="-0.3048" y2="-0.762" width="0.3048" layer="51"/>
<wire x1="0.3302" y1="0.762" x2="0.3302" y2="0" width="0.3048" layer="51"/>
<wire x1="0.3302" y1="0" x2="0.3302" y2="-0.762" width="0.3048" layer="51"/>
<wire x1="1.27" y1="0" x2="0.3302" y2="0" width="0.127" layer="51"/>
<wire x1="-1.27" y1="0" x2="-0.3048" y2="0" width="0.127" layer="51"/>
<pad name="1" x="-1.27" y="0" drill="0.8128" shape="octagon"/>
<pad name="2" x="1.27" y="0" drill="0.8128" shape="octagon"/>
<text x="2.54" y="-0.635" size="1.27" layer="25" ratio="10">&gt;NAME</text>
<text x="-2.159" y="-2.794" size="1.27" layer="27" ratio="10">&gt;VALUE</text>
</package>
<package name="C025-025X050">
<description>Capacitor&lt;p&gt;
Grid  2.5 mm Outline 2.5 x 5 mm</description>
<wire x1="-2.159" y1="1.27" x2="2.159" y2="1.27" width="0.127" layer="21"/>
<wire x1="2.159" y1="-1.27" x2="-2.159" y2="-1.27" width="0.127" layer="21"/>
<wire x1="2.413" y1="1.016" x2="2.413" y2="-1.016" width="0.127" layer="21"/>
<wire x1="-2.413" y1="1.016" x2="-2.413" y2="-1.016" width="0.127" layer="21"/>
<wire x1="2.159" y1="1.27" x2="2.413" y2="1.016" width="0.127" layer="21" curve="-90"/>
<wire x1="-2.413" y1="1.016" x2="-2.159" y2="1.27" width="0.127" layer="21" curve="-90"/>
<wire x1="2.159" y1="-1.27" x2="2.413" y2="-1.016" width="0.127" layer="21" curve="90"/>
<wire x1="-2.413" y1="-1.016" x2="-2.159" y2="-1.27" width="0.127" layer="21" curve="90"/>
<wire x1="0.762" y1="0" x2="0.381" y2="0" width="0.127" layer="51"/>
<wire x1="0.381" y1="0" x2="0.254" y2="0" width="0.127" layer="21"/>
<wire x1="0.254" y1="0" x2="0.254" y2="0.762" width="0.254" layer="21"/>
<wire x1="0.254" y1="0" x2="0.254" y2="-0.762" width="0.254" layer="21"/>
<wire x1="-0.254" y1="0.762" x2="-0.254" y2="0" width="0.254" layer="21"/>
<wire x1="-0.254" y1="0" x2="-0.254" y2="-0.762" width="0.254" layer="21"/>
<wire x1="-0.254" y1="0" x2="-0.381" y2="0" width="0.127" layer="21"/>
<wire x1="-0.381" y1="0" x2="-0.762" y2="0" width="0.127" layer="51"/>
<pad name="1" x="-1.27" y="0" drill="0.8128" shape="octagon"/>
<pad name="2" x="1.27" y="0" drill="0.8128" shape="octagon"/>
<text x="2.921" y="0.254" size="1.27" layer="25" ratio="10">&gt;NAME</text>
<text x="2.921" y="-1.27" size="1.27" layer="27" ratio="10">&gt;VALUE</text>
</package>
<package name="C025-030X050">
<description>Capacitor&lt;p&gt;
Grid  2.5 mm Outline 3 x 5 mm</description>
<wire x1="-2.159" y1="1.524" x2="2.159" y2="1.524" width="0.127" layer="21"/>
<wire x1="2.159" y1="-1.524" x2="-2.159" y2="-1.524" width="0.127" layer="21"/>
<wire x1="2.413" y1="1.27" x2="2.413" y2="-1.27" width="0.127" layer="21"/>
<wire x1="-2.413" y1="1.27" x2="-2.413" y2="-1.27" width="0.127" layer="21"/>
<wire x1="2.159" y1="1.524" x2="2.413" y2="1.27" width="0.127" layer="21" curve="-90"/>
<wire x1="-2.413" y1="1.27" x2="-2.159" y2="1.524" width="0.127" layer="21" curve="-90"/>
<wire x1="2.159" y1="-1.524" x2="2.413" y2="-1.27" width="0.127" layer="21" curve="90"/>
<wire x1="-2.413" y1="-1.27" x2="-2.159" y2="-1.524" width="0.127" layer="21" curve="90"/>
<wire x1="0.762" y1="0" x2="0.381" y2="0" width="0.127" layer="51"/>
<wire x1="0.381" y1="0" x2="0.254" y2="0" width="0.127" layer="21"/>
<wire x1="0.254" y1="0" x2="0.254" y2="0.762" width="0.254" layer="21"/>
<wire x1="0.254" y1="0" x2="0.254" y2="-0.762" width="0.254" layer="21"/>
<wire x1="-0.254" y1="0.762" x2="-0.254" y2="0" width="0.254" layer="21"/>
<wire x1="-0.254" y1="0" x2="-0.254" y2="-0.762" width="0.254" layer="21"/>
<wire x1="-0.254" y1="0" x2="-0.381" y2="0" width="0.127" layer="21"/>
<wire x1="-0.381" y1="0" x2="-0.762" y2="0" width="0.127" layer="51"/>
<pad name="1" x="-1.27" y="0" drill="0.8128" shape="octagon"/>
<pad name="2" x="1.27" y="0" drill="0.8128" shape="octagon"/>
<text x="2.921" y="0.127" size="1.27" layer="25" ratio="10">&gt;NAME</text>
<text x="2.921" y="-1.397" size="1.27" layer="27" ratio="10">&gt;VALUE</text>
</package>
<package name="C025-040X050">
<description>Capacitor&lt;p&gt;
Grid  2.5 mm Outline 4 x 5 mm</description>
<wire x1="-2.159" y1="1.905" x2="2.159" y2="1.905" width="0.127" layer="21"/>
<wire x1="2.159" y1="-1.905" x2="-2.159" y2="-1.905" width="0.127" layer="21"/>
<wire x1="2.413" y1="1.651" x2="2.413" y2="-1.651" width="0.127" layer="21"/>
<wire x1="-2.413" y1="1.651" x2="-2.413" y2="-1.651" width="0.127" layer="21"/>
<wire x1="2.159" y1="1.905" x2="2.413" y2="1.651" width="0.127" layer="21" curve="-90"/>
<wire x1="-2.413" y1="1.651" x2="-2.159" y2="1.905" width="0.127" layer="21" curve="-90"/>
<wire x1="2.159" y1="-1.905" x2="2.413" y2="-1.651" width="0.127" layer="21" curve="90"/>
<wire x1="-2.413" y1="-1.651" x2="-2.159" y2="-1.905" width="0.127" layer="21" curve="90"/>
<wire x1="0.762" y1="0" x2="0.381" y2="0" width="0.127" layer="51"/>
<wire x1="0.381" y1="0" x2="0.254" y2="0" width="0.127" layer="21"/>
<wire x1="0.254" y1="0" x2="0.254" y2="0.762" width="0.254" layer="21"/>
<wire x1="0.254" y1="0" x2="0.254" y2="-0.762" width="0.254" layer="21"/>
<wire x1="-0.254" y1="0.762" x2="-0.254" y2="0" width="0.254" layer="21"/>
<wire x1="-0.254" y1="0" x2="-0.254" y2="-0.762" width="0.254" layer="21"/>
<wire x1="-0.254" y1="0" x2="-0.381" y2="0" width="0.127" layer="21"/>
<wire x1="-0.381" y1="0" x2="-0.762" y2="0" width="0.127" layer="51"/>
<pad name="1" x="-1.27" y="0" drill="0.8128" shape="octagon"/>
<pad name="2" x="1.27" y="0" drill="0.8128" shape="octagon"/>
<text x="2.921" y="0.254" size="1.27" layer="25" ratio="10">&gt;NAME</text>
<text x="2.921" y="-1.524" size="1.27" layer="27" ratio="10">&gt;VALUE</text>
</package>
<package name="C025-050X050">
<description>Capacitor&lt;p&gt;
Grid  2.5 mm Outline 5 x 5 mm</description>
<wire x1="-2.159" y1="2.286" x2="2.159" y2="2.286" width="0.127" layer="21"/>
<wire x1="2.159" y1="-2.286" x2="-2.159" y2="-2.286" width="0.127" layer="21"/>
<wire x1="2.413" y1="2.032" x2="2.413" y2="-2.032" width="0.127" layer="21"/>
<wire x1="-2.413" y1="2.032" x2="-2.413" y2="-2.032" width="0.127" layer="21"/>
<wire x1="2.159" y1="2.286" x2="2.413" y2="2.032" width="0.127" layer="21" curve="-90"/>
<wire x1="-2.413" y1="2.032" x2="-2.159" y2="2.286" width="0.127" layer="21" curve="-90"/>
<wire x1="2.159" y1="-2.286" x2="2.413" y2="-2.032" width="0.127" layer="21" curve="90"/>
<wire x1="-2.413" y1="-2.032" x2="-2.159" y2="-2.286" width="0.127" layer="21" curve="90"/>
<wire x1="0.762" y1="0" x2="0.381" y2="0" width="0.127" layer="51"/>
<wire x1="0.381" y1="0" x2="0.254" y2="0" width="0.127" layer="21"/>
<wire x1="0.254" y1="0" x2="0.254" y2="0.762" width="0.254" layer="21"/>
<wire x1="0.254" y1="0" x2="0.254" y2="-0.762" width="0.254" layer="21"/>
<wire x1="-0.254" y1="0.762" x2="-0.254" y2="0" width="0.254" layer="21"/>
<wire x1="-0.254" y1="0" x2="-0.254" y2="-0.762" width="0.254" layer="21"/>
<wire x1="-0.254" y1="0" x2="-0.381" y2="0" width="0.127" layer="21"/>
<wire x1="-0.381" y1="0" x2="-0.762" y2="0" width="0.127" layer="51"/>
<pad name="1" x="-1.27" y="0" drill="0.8128" shape="octagon"/>
<pad name="2" x="1.27" y="0" drill="0.8128" shape="octagon"/>
<text x="2.921" y="0.254" size="1.27" layer="25" ratio="10">&gt;NAME</text>
<text x="2.921" y="-1.524" size="1.27" layer="27" ratio="10">&gt;VALUE</text>
</package>
<package name="C025-060X050">
<description>Capacitor&lt;p&gt;
Grid  2.5 mm Outline 6 x 5 mm</description>
<wire x1="-2.159" y1="2.794" x2="2.159" y2="2.794" width="0.127" layer="21"/>
<wire x1="2.159" y1="-2.794" x2="-2.159" y2="-2.794" width="0.127" layer="21"/>
<wire x1="2.413" y1="2.54" x2="2.413" y2="-2.54" width="0.127" layer="21"/>
<wire x1="-2.413" y1="2.54" x2="-2.413" y2="-2.54" width="0.127" layer="21"/>
<wire x1="2.159" y1="2.794" x2="2.413" y2="2.54" width="0.127" layer="21" curve="-90"/>
<wire x1="-2.413" y1="2.54" x2="-2.159" y2="2.794" width="0.127" layer="21" curve="-90"/>
<wire x1="2.159" y1="-2.794" x2="2.413" y2="-2.54" width="0.127" layer="21" curve="90"/>
<wire x1="-2.413" y1="-2.54" x2="-2.159" y2="-2.794" width="0.127" layer="21" curve="90"/>
<wire x1="0.762" y1="0" x2="0.381" y2="0" width="0.127" layer="51"/>
<wire x1="0.381" y1="0" x2="0.254" y2="0" width="0.127" layer="21"/>
<wire x1="0.254" y1="0" x2="0.254" y2="0.762" width="0.254" layer="21"/>
<wire x1="0.254" y1="0" x2="0.254" y2="-0.762" width="0.254" layer="21"/>
<wire x1="-0.254" y1="0.762" x2="-0.254" y2="0" width="0.254" layer="21"/>
<wire x1="-0.254" y1="0" x2="-0.254" y2="-0.762" width="0.254" layer="21"/>
<wire x1="-0.254" y1="0" x2="-0.381" y2="0" width="0.127" layer="21"/>
<wire x1="-0.381" y1="0" x2="-0.762" y2="0" width="0.127" layer="51"/>
<pad name="1" x="-1.27" y="0" drill="0.8128" shape="octagon"/>
<pad name="2" x="1.27" y="0" drill="0.8128" shape="octagon"/>
<text x="-2.032" y="1.143" size="1.27" layer="25" ratio="10">&gt;NAME</text>
<text x="-2.032" y="-2.413" size="1.27" layer="27" ratio="10">&gt;VALUE</text>
</package>
<package name="C025_050-024X070">
<description>Capacitor&lt;p&gt;
Grid  2.5 mm + 5 mm Outline 2.4 x 7 mm</description>
<wire x1="-2.159" y1="-0.635" x2="-2.159" y2="0.635" width="0.127" layer="51"/>
<wire x1="-2.159" y1="0.635" x2="-1.651" y2="1.143" width="0.127" layer="21" curve="-90" cap="flat"/>
<wire x1="-2.159" y1="-0.635" x2="-1.651" y2="-1.143" width="0.127" layer="21" curve="90" cap="flat"/>
<wire x1="1.651" y1="1.143" x2="-1.651" y2="1.143" width="0.127" layer="21"/>
<wire x1="2.159" y1="-0.635" x2="2.159" y2="0.635" width="0.127" layer="51"/>
<wire x1="1.651" y1="-1.143" x2="-1.651" y2="-1.143" width="0.127" layer="21"/>
<wire x1="1.651" y1="1.143" x2="2.159" y2="0.635" width="0.127" layer="21" curve="-90" cap="flat"/>
<wire x1="-4.191" y1="-1.143" x2="-3.9624" y2="-1.143" width="0.127" layer="21"/>
<wire x1="-4.191" y1="1.143" x2="-3.9624" y2="1.143" width="0.127" layer="21"/>
<wire x1="-4.699" y1="-0.635" x2="-4.191" y2="-1.143" width="0.127" layer="21" curve="90"/>
<wire x1="1.651" y1="-1.143" x2="2.159" y2="-0.635" width="0.127" layer="21" curve="90" cap="flat"/>
<wire x1="-4.699" y1="0.635" x2="-4.191" y2="1.143" width="0.127" layer="21" curve="-90"/>
<wire x1="-4.699" y1="-0.635" x2="-4.699" y2="0.635" width="0.127" layer="21"/>
<wire x1="-3.429" y1="1.143" x2="-2.5654" y2="1.143" width="0.127" layer="21"/>
<wire x1="-3.429" y1="-1.143" x2="-2.5654" y2="-1.143" width="0.127" layer="21"/>
<wire x1="-0.3048" y1="0.762" x2="-0.3048" y2="0" width="0.3048" layer="51"/>
<wire x1="-0.3048" y1="0" x2="-0.3048" y2="-0.762" width="0.3048" layer="51"/>
<wire x1="0.3302" y1="0.762" x2="0.3302" y2="0" width="0.3048" layer="51"/>
<wire x1="0.3302" y1="0" x2="0.3302" y2="-0.762" width="0.3048" layer="51"/>
<wire x1="1.27" y1="0" x2="0.3302" y2="0" width="0.127" layer="51"/>
<wire x1="-1.27" y1="0" x2="-0.3048" y2="0" width="0.127" layer="51"/>
<pad name="1" x="-3.81" y="0" drill="0.8128" shape="octagon"/>
<pad name="2" x="-1.27" y="0" drill="0.8128" shape="octagon"/>
<pad name="3" x="1.27" y="0" drill="0.8128" shape="octagon"/>
<text x="2.54" y="-0.635" size="1.27" layer="25" ratio="10">&gt;NAME</text>
<text x="-4.699" y="-2.921" size="1.27" layer="27" ratio="10">&gt;VALUE</text>
</package>
<package name="C025_050-025X075">
<description>Capacitor&lt;p&gt;
Grid  2.5 + 5 mm Outline 2.5 x 7.5 mm</description>
<wire x1="-2.159" y1="1.27" x2="2.159" y2="1.27" width="0.127" layer="21"/>
<wire x1="2.159" y1="-1.27" x2="-2.159" y2="-1.27" width="0.127" layer="21"/>
<wire x1="-2.413" y1="1.016" x2="-2.413" y2="-1.016" width="0.127" layer="21"/>
<wire x1="2.159" y1="1.27" x2="2.413" y2="1.016" width="0.127" layer="21" curve="-90"/>
<wire x1="-2.413" y1="1.016" x2="-2.159" y2="1.27" width="0.127" layer="21" curve="-90"/>
<wire x1="2.159" y1="-1.27" x2="2.413" y2="-1.016" width="0.127" layer="21" curve="90"/>
<wire x1="-2.413" y1="-1.016" x2="-2.159" y2="-1.27" width="0.127" layer="21" curve="90"/>
<wire x1="0.381" y1="0" x2="0.254" y2="0" width="0.127" layer="21"/>
<wire x1="0.254" y1="0" x2="0.254" y2="0.762" width="0.254" layer="21"/>
<wire x1="0.254" y1="0" x2="0.254" y2="-0.762" width="0.254" layer="21"/>
<wire x1="-0.254" y1="0.762" x2="-0.254" y2="0" width="0.254" layer="21"/>
<wire x1="-0.254" y1="0" x2="-0.254" y2="-0.762" width="0.254" layer="21"/>
<wire x1="-0.254" y1="0" x2="-0.381" y2="0" width="0.127" layer="21"/>
<wire x1="-0.381" y1="0" x2="-0.762" y2="0" width="0.127" layer="51"/>
<wire x1="4.953" y1="1.016" x2="4.953" y2="-1.016" width="0.127" layer="21"/>
<wire x1="4.699" y1="1.27" x2="4.953" y2="1.016" width="0.127" layer="21" curve="-90"/>
<wire x1="4.699" y1="-1.27" x2="4.953" y2="-1.016" width="0.127" layer="21" curve="90"/>
<wire x1="2.794" y1="1.27" x2="4.699" y2="1.27" width="0.127" layer="21"/>
<wire x1="4.699" y1="-1.27" x2="2.794" y2="-1.27" width="0.127" layer="21"/>
<wire x1="2.413" y1="1.016" x2="2.413" y2="0.762" width="0.127" layer="21"/>
<wire x1="2.413" y1="-0.762" x2="2.413" y2="-1.016" width="0.127" layer="21"/>
<wire x1="2.413" y1="0.254" x2="2.413" y2="-0.254" width="0.127" layer="21"/>
<wire x1="1.778" y1="0" x2="2.286" y2="0" width="0.127" layer="51"/>
<wire x1="2.286" y1="0" x2="2.794" y2="0" width="0.127" layer="21"/>
<wire x1="2.794" y1="0" x2="3.302" y2="0" width="0.127" layer="51"/>
<wire x1="0.762" y1="0" x2="0.381" y2="0" width="0.127" layer="51"/>
<pad name="1" x="-1.27" y="0" drill="0.8128" shape="octagon"/>
<pad name="3" x="3.81" y="0" drill="0.8128" shape="octagon"/>
<pad name="2" x="1.27" y="0" drill="0.8128" shape="octagon"/>
<text x="5.461" y="0.127" size="1.27" layer="25" ratio="10">&gt;NAME</text>
<text x="5.461" y="-1.397" size="1.27" layer="27" ratio="10">&gt;VALUE</text>
</package>
<package name="C025_050-035X075">
<description>Capacitor&lt;p&gt;
Grid  2.5 + 5 mm Outline 3.5 x 7.5 mm</description>
<wire x1="-2.159" y1="1.778" x2="2.159" y2="1.778" width="0.127" layer="21"/>
<wire x1="2.159" y1="-1.778" x2="-2.159" y2="-1.778" width="0.127" layer="21"/>
<wire x1="-2.413" y1="1.524" x2="-2.413" y2="-1.524" width="0.127" layer="21"/>
<wire x1="2.159" y1="1.778" x2="2.413" y2="1.524" width="0.127" layer="21" curve="-90"/>
<wire x1="-2.413" y1="1.524" x2="-2.159" y2="1.778" width="0.127" layer="21" curve="-90"/>
<wire x1="2.159" y1="-1.778" x2="2.413" y2="-1.524" width="0.127" layer="21" curve="90"/>
<wire x1="-2.413" y1="-1.524" x2="-2.159" y2="-1.778" width="0.127" layer="21" curve="90"/>
<wire x1="0.381" y1="0" x2="0.254" y2="0" width="0.127" layer="21"/>
<wire x1="0.254" y1="0" x2="0.254" y2="0.762" width="0.254" layer="21"/>
<wire x1="0.254" y1="0" x2="0.254" y2="-0.762" width="0.254" layer="21"/>
<wire x1="-0.254" y1="0.762" x2="-0.254" y2="0" width="0.254" layer="21"/>
<wire x1="-0.254" y1="0" x2="-0.254" y2="-0.762" width="0.254" layer="21"/>
<wire x1="-0.254" y1="0" x2="-0.381" y2="0" width="0.127" layer="21"/>
<wire x1="-0.381" y1="0" x2="-0.762" y2="0" width="0.127" layer="51"/>
<wire x1="4.953" y1="1.524" x2="4.953" y2="-1.524" width="0.127" layer="21"/>
<wire x1="4.699" y1="1.778" x2="4.953" y2="1.524" width="0.127" layer="21" curve="-90"/>
<wire x1="4.699" y1="-1.778" x2="4.953" y2="-1.524" width="0.127" layer="21" curve="90"/>
<wire x1="2.794" y1="1.778" x2="4.699" y2="1.778" width="0.127" layer="21"/>
<wire x1="4.699" y1="-1.778" x2="2.794" y2="-1.778" width="0.127" layer="21"/>
<wire x1="2.413" y1="1.524" x2="2.413" y2="1.016" width="0.127" layer="21"/>
<wire x1="2.413" y1="-1.016" x2="2.413" y2="-1.524" width="0.127" layer="21"/>
<wire x1="2.413" y1="0.508" x2="2.413" y2="-0.508" width="0.127" layer="21"/>
<wire x1="0.381" y1="0" x2="0.762" y2="0" width="0.127" layer="51"/>
<wire x1="2.286" y1="0" x2="2.794" y2="0" width="0.127" layer="21"/>
<wire x1="2.794" y1="0" x2="3.302" y2="0" width="0.127" layer="51"/>
<wire x1="2.286" y1="0" x2="1.778" y2="0" width="0.127" layer="51"/>
<pad name="1" x="-1.27" y="0" drill="0.8128" shape="octagon"/>
<pad name="3" x="3.81" y="0" drill="0.8128" shape="octagon"/>
<pad name="2" x="1.27" y="0" drill="0.8128" shape="octagon"/>
<text x="5.461" y="0.254" size="1.27" layer="25" ratio="10">&gt;NAME</text>
<text x="5.461" y="-1.524" size="1.27" layer="27" ratio="10">&gt;VALUE</text>
</package>
<package name="C025_050-045X075">
<description>Capacitor&lt;p&gt;
Grid  2.5 + 5 mm Outline 4.5 x 7.5 mm</description>
<wire x1="-2.159" y1="2.286" x2="2.159" y2="2.286" width="0.127" layer="21"/>
<wire x1="2.159" y1="-2.286" x2="-2.159" y2="-2.286" width="0.127" layer="21"/>
<wire x1="-2.413" y1="2.032" x2="-2.413" y2="-2.032" width="0.127" layer="21"/>
<wire x1="2.159" y1="2.286" x2="2.413" y2="2.032" width="0.127" layer="21" curve="-90"/>
<wire x1="-2.413" y1="2.032" x2="-2.159" y2="2.286" width="0.127" layer="21" curve="-90"/>
<wire x1="2.159" y1="-2.286" x2="2.413" y2="-2.032" width="0.127" layer="21" curve="90"/>
<wire x1="-2.413" y1="-2.032" x2="-2.159" y2="-2.286" width="0.127" layer="21" curve="90"/>
<wire x1="0.381" y1="0" x2="0.254" y2="0" width="0.127" layer="21"/>
<wire x1="0.254" y1="0" x2="0.254" y2="0.762" width="0.254" layer="21"/>
<wire x1="0.254" y1="0" x2="0.254" y2="-0.762" width="0.254" layer="21"/>
<wire x1="-0.254" y1="0.762" x2="-0.254" y2="0" width="0.254" layer="21"/>
<wire x1="-0.254" y1="0" x2="-0.254" y2="-0.762" width="0.254" layer="21"/>
<wire x1="-0.254" y1="0" x2="-0.381" y2="0" width="0.127" layer="21"/>
<wire x1="-0.381" y1="0" x2="-0.762" y2="0" width="0.127" layer="51"/>
<wire x1="4.953" y1="2.032" x2="4.953" y2="-2.032" width="0.127" layer="21"/>
<wire x1="4.699" y1="2.286" x2="4.953" y2="2.032" width="0.127" layer="21" curve="-90"/>
<wire x1="4.699" y1="-2.286" x2="4.953" y2="-2.032" width="0.127" layer="21" curve="90"/>
<wire x1="2.794" y1="2.286" x2="4.699" y2="2.286" width="0.127" layer="21"/>
<wire x1="4.699" y1="-2.286" x2="2.794" y2="-2.286" width="0.127" layer="21"/>
<wire x1="2.413" y1="2.032" x2="2.413" y2="1.397" width="0.127" layer="21"/>
<wire x1="2.413" y1="-1.397" x2="2.413" y2="-2.032" width="0.127" layer="21"/>
<wire x1="2.413" y1="0.762" x2="2.413" y2="-0.762" width="0.127" layer="21"/>
<wire x1="2.286" y1="0" x2="2.794" y2="0" width="0.127" layer="21"/>
<wire x1="2.794" y1="0" x2="3.302" y2="0" width="0.127" layer="51"/>
<wire x1="0.381" y1="0" x2="0.762" y2="0" width="0.127" layer="51"/>
<wire x1="2.286" y1="0" x2="1.778" y2="0" width="0.127" layer="51"/>
<pad name="1" x="-1.27" y="0" drill="0.8128" shape="octagon"/>
<pad name="3" x="3.81" y="0" drill="0.8128" shape="octagon"/>
<pad name="2" x="1.27" y="0" drill="0.8128" shape="octagon"/>
<text x="5.461" y="0.381" size="1.27" layer="25" ratio="10">&gt;NAME</text>
<text x="5.461" y="-1.651" size="1.27" layer="27" ratio="10">&gt;VALUE</text>
</package>
<package name="C025_050-055X075">
<description>Capacitor&lt;p&gt;
Grid  2.5 + 5 mm Outline 5.5 x 7.5 mm</description>
<wire x1="-2.159" y1="2.794" x2="2.159" y2="2.794" width="0.127" layer="21"/>
<wire x1="2.159" y1="-2.794" x2="-2.159" y2="-2.794" width="0.127" layer="21"/>
<wire x1="-2.413" y1="2.54" x2="-2.413" y2="-2.54" width="0.127" layer="21"/>
<wire x1="2.159" y1="2.794" x2="2.413" y2="2.54" width="0.127" layer="21" curve="-90"/>
<wire x1="-2.413" y1="2.54" x2="-2.159" y2="2.794" width="0.127" layer="21" curve="-90"/>
<wire x1="2.159" y1="-2.794" x2="2.413" y2="-2.54" width="0.127" layer="21" curve="90"/>
<wire x1="-2.413" y1="-2.54" x2="-2.159" y2="-2.794" width="0.127" layer="21" curve="90"/>
<wire x1="0.381" y1="0" x2="0.254" y2="0" width="0.127" layer="21"/>
<wire x1="0.254" y1="0" x2="0.254" y2="0.762" width="0.254" layer="21"/>
<wire x1="0.254" y1="0" x2="0.254" y2="-0.762" width="0.254" layer="21"/>
<wire x1="-0.254" y1="0.762" x2="-0.254" y2="0" width="0.254" layer="21"/>
<wire x1="-0.254" y1="0" x2="-0.254" y2="-0.762" width="0.254" layer="21"/>
<wire x1="-0.254" y1="0" x2="-0.381" y2="0" width="0.127" layer="21"/>
<wire x1="-0.381" y1="0" x2="-0.762" y2="0" width="0.127" layer="51"/>
<wire x1="4.953" y1="2.54" x2="4.953" y2="-2.54" width="0.127" layer="21"/>
<wire x1="4.699" y1="2.794" x2="4.953" y2="2.54" width="0.127" layer="21" curve="-90"/>
<wire x1="4.699" y1="-2.794" x2="4.953" y2="-2.54" width="0.127" layer="21" curve="90"/>
<wire x1="2.794" y1="2.794" x2="4.699" y2="2.794" width="0.127" layer="21"/>
<wire x1="4.699" y1="-2.794" x2="2.794" y2="-2.794" width="0.127" layer="21"/>
<wire x1="2.413" y1="2.54" x2="2.413" y2="2.032" width="0.127" layer="21"/>
<wire x1="2.413" y1="-2.032" x2="2.413" y2="-2.54" width="0.127" layer="21"/>
<wire x1="2.413" y1="0.762" x2="2.413" y2="-0.762" width="0.127" layer="21"/>
<wire x1="1.778" y1="0" x2="2.286" y2="0" width="0.127" layer="51"/>
<wire x1="2.286" y1="0" x2="2.794" y2="0" width="0.127" layer="21"/>
<wire x1="2.794" y1="0" x2="3.302" y2="0" width="0.127" layer="51"/>
<wire x1="0.381" y1="0" x2="0.762" y2="0" width="0.127" layer="51"/>
<pad name="1" x="-1.27" y="0" drill="0.8128" shape="octagon"/>
<pad name="3" x="3.81" y="0" drill="0.8128" shape="octagon"/>
<pad name="2" x="1.27" y="0" drill="0.8128" shape="octagon"/>
<text x="-2.032" y="1.143" size="1.27" layer="25" ratio="10">&gt;NAME</text>
<text x="-2.032" y="-2.286" size="1.27" layer="27" ratio="10">&gt;VALUE</text>
</package>
<package name="C050-024X044">
<description>Capacitor&lt;p&gt;
Grid  5 mm Outline 2.4 x  4.4 mm</description>
<wire x1="-2.159" y1="-0.635" x2="-2.159" y2="0.635" width="0.127" layer="51"/>
<wire x1="-2.159" y1="0.635" x2="-1.651" y2="1.143" width="0.127" layer="21" curve="-90" cap="flat"/>
<wire x1="-2.159" y1="-0.635" x2="-1.651" y2="-1.143" width="0.127" layer="21" curve="90" cap="flat"/>
<wire x1="1.651" y1="1.143" x2="-1.651" y2="1.143" width="0.127" layer="21"/>
<wire x1="2.159" y1="-0.635" x2="2.159" y2="0.635" width="0.127" layer="51"/>
<wire x1="1.651" y1="-1.143" x2="-1.651" y2="-1.143" width="0.127" layer="21"/>
<wire x1="1.651" y1="1.143" x2="2.159" y2="0.635" width="0.127" layer="21" curve="-90" cap="flat"/>
<wire x1="1.651" y1="-1.143" x2="2.159" y2="-0.635" width="0.127" layer="21" curve="90" cap="flat"/>
<wire x1="-0.3048" y1="0.762" x2="-0.3048" y2="0" width="0.3048" layer="21"/>
<wire x1="-0.3048" y1="0" x2="-0.3048" y2="-0.762" width="0.3048" layer="21"/>
<wire x1="0.3302" y1="0.762" x2="0.3302" y2="0" width="0.3048" layer="21"/>
<wire x1="0.3302" y1="0" x2="0.3302" y2="-0.762" width="0.3048" layer="21"/>
<wire x1="1.27" y1="0" x2="0.3302" y2="0" width="0.127" layer="21"/>
<wire x1="-1.27" y1="0" x2="-0.3048" y2="0" width="0.127" layer="21"/>
<pad name="1" x="-2.54" y="0" drill="0.8128" shape="octagon"/>
<pad name="2" x="2.54" y="0" drill="0.8128" shape="octagon"/>
<text x="3.683" y="-0.635" size="1.27" layer="25" ratio="10">&gt;NAME</text>
<text x="-2.413" y="-2.667" size="1.27" layer="27" ratio="10">&gt;VALUE</text>
<rectangle x1="2.159" y1="-0.381" x2="2.54" y2="0.381" layer="51"/>
<rectangle x1="-2.54" y1="-0.381" x2="-2.159" y2="0.381" layer="51"/>
</package>
<package name="C050-025X075">
<description>Capacitor&lt;p&gt;
Grid  5 mm Outline 2.5 x 7.5 mm</description>
<wire x1="-0.3048" y1="0.635" x2="-0.3048" y2="0" width="0.3048" layer="21"/>
<wire x1="-0.3048" y1="0" x2="-0.3048" y2="-0.635" width="0.3048" layer="21"/>
<wire x1="-0.3048" y1="0" x2="-1.524" y2="0" width="0.127" layer="21"/>
<wire x1="0.3302" y1="0.635" x2="0.3302" y2="0" width="0.3048" layer="21"/>
<wire x1="0.3302" y1="0" x2="0.3302" y2="-0.635" width="0.3048" layer="21"/>
<wire x1="0.3302" y1="0" x2="1.524" y2="0" width="0.127" layer="21"/>
<wire x1="-3.683" y1="1.016" x2="-3.683" y2="-1.016" width="0.127" layer="21"/>
<wire x1="-3.429" y1="-1.27" x2="3.429" y2="-1.27" width="0.127" layer="21"/>
<wire x1="3.683" y1="-1.016" x2="3.683" y2="1.016" width="0.127" layer="21"/>
<wire x1="3.429" y1="1.27" x2="-3.429" y2="1.27" width="0.127" layer="21"/>
<wire x1="3.429" y1="1.27" x2="3.683" y2="1.016" width="0.127" layer="21" curve="-90"/>
<wire x1="3.429" y1="-1.27" x2="3.683" y2="-1.016" width="0.127" layer="21" curve="90"/>
<wire x1="-3.683" y1="-1.016" x2="-3.429" y2="-1.27" width="0.127" layer="21" curve="90"/>
<wire x1="-3.683" y1="1.016" x2="-3.429" y2="1.27" width="0.127" layer="21" curve="-90"/>
<pad name="1" x="-2.54" y="0" drill="0.8128" shape="octagon"/>
<pad name="2" x="2.54" y="0" drill="0.8128" shape="octagon"/>
<text x="4.191" y="0" size="1.27" layer="25" ratio="10">&gt;NAME</text>
<text x="4.191" y="-1.524" size="1.27" layer="27" ratio="10">&gt;VALUE</text>
</package>
<package name="C050-045X075">
<description>Capacitor&lt;p&gt;
Grid  5 mm Outline 4.5 x 7.5 mm</description>
<wire x1="-0.3048" y1="0.635" x2="-0.3048" y2="0" width="0.3048" layer="21"/>
<wire x1="-0.3048" y1="0" x2="-0.3048" y2="-0.635" width="0.3048" layer="21"/>
<wire x1="-0.3048" y1="0" x2="-1.524" y2="0" width="0.127" layer="21"/>
<wire x1="0.3302" y1="0.635" x2="0.3302" y2="0" width="0.3048" layer="21"/>
<wire x1="0.3302" y1="0" x2="0.3302" y2="-0.635" width="0.3048" layer="21"/>
<wire x1="0.3302" y1="0" x2="1.524" y2="0" width="0.127" layer="21"/>
<wire x1="-3.683" y1="2.032" x2="-3.683" y2="-2.032" width="0.127" layer="21"/>
<wire x1="-3.429" y1="-2.286" x2="3.429" y2="-2.286" width="0.127" layer="21"/>
<wire x1="3.683" y1="-2.032" x2="3.683" y2="2.032" width="0.127" layer="21"/>
<wire x1="3.429" y1="2.286" x2="-3.429" y2="2.286" width="0.127" layer="21"/>
<wire x1="3.429" y1="2.286" x2="3.683" y2="2.032" width="0.127" layer="21" curve="-90"/>
<wire x1="3.429" y1="-2.286" x2="3.683" y2="-2.032" width="0.127" layer="21" curve="90"/>
<wire x1="-3.683" y1="-2.032" x2="-3.429" y2="-2.286" width="0.127" layer="21" curve="90"/>
<wire x1="-3.683" y1="2.032" x2="-3.429" y2="2.286" width="0.127" layer="21" curve="-90"/>
<pad name="1" x="-2.54" y="0" drill="0.8128" shape="octagon"/>
<pad name="2" x="2.54" y="0" drill="0.8128" shape="octagon"/>
<text x="4.318" y="0.254" size="1.27" layer="25" ratio="10">&gt;NAME</text>
<text x="4.318" y="-1.524" size="1.27" layer="27" ratio="10">&gt;VALUE</text>
</package>
<package name="C050-030X075">
<description>Capacitor&lt;p&gt;
Grid  5 mm Outline 3 x 7.5 mm</description>
<wire x1="-0.3048" y1="0.635" x2="-0.3048" y2="0" width="0.3048" layer="21"/>
<wire x1="-0.3048" y1="0" x2="-0.3048" y2="-0.635" width="0.3048" layer="21"/>
<wire x1="-0.3048" y1="0" x2="-1.524" y2="0" width="0.127" layer="21"/>
<wire x1="0.3302" y1="0.635" x2="0.3302" y2="0" width="0.3048" layer="21"/>
<wire x1="0.3302" y1="0" x2="0.3302" y2="-0.635" width="0.3048" layer="21"/>
<wire x1="0.3302" y1="0" x2="1.524" y2="0" width="0.127" layer="21"/>
<wire x1="-3.683" y1="1.27" x2="-3.683" y2="-1.27" width="0.127" layer="21"/>
<wire x1="-3.429" y1="-1.524" x2="3.429" y2="-1.524" width="0.127" layer="21"/>
<wire x1="3.683" y1="-1.27" x2="3.683" y2="1.27" width="0.127" layer="21"/>
<wire x1="3.429" y1="1.524" x2="-3.429" y2="1.524" width="0.127" layer="21"/>
<wire x1="3.429" y1="1.524" x2="3.683" y2="1.27" width="0.127" layer="21" curve="-90"/>
<wire x1="3.429" y1="-1.524" x2="3.683" y2="-1.27" width="0.127" layer="21" curve="90"/>
<wire x1="-3.683" y1="-1.27" x2="-3.429" y2="-1.524" width="0.127" layer="21" curve="90"/>
<wire x1="-3.683" y1="1.27" x2="-3.429" y2="1.524" width="0.127" layer="21" curve="-90"/>
<pad name="1" x="-2.54" y="0" drill="0.8128" shape="octagon"/>
<pad name="2" x="2.54" y="0" drill="0.8128" shape="octagon"/>
<text x="4.191" y="0" size="1.27" layer="25" ratio="10">&gt;NAME</text>
<text x="4.191" y="-1.524" size="1.27" layer="27" ratio="10">&gt;VALUE</text>
</package>
<package name="C050-050X075">
<description>Capacitor&lt;p&gt;
Grid  5 mm Outline 5 x 7.5 mm</description>
<wire x1="-0.3048" y1="0.635" x2="-0.3048" y2="0" width="0.3048" layer="21"/>
<wire x1="-0.3048" y1="0" x2="-0.3048" y2="-0.635" width="0.3048" layer="21"/>
<wire x1="-0.3048" y1="0" x2="-1.524" y2="0" width="0.127" layer="21"/>
<wire x1="0.3302" y1="0.635" x2="0.3302" y2="0" width="0.3048" layer="21"/>
<wire x1="0.3302" y1="0" x2="0.3302" y2="-0.635" width="0.3048" layer="21"/>
<wire x1="0.3302" y1="0" x2="1.524" y2="0" width="0.127" layer="21"/>
<wire x1="-3.683" y1="2.286" x2="-3.683" y2="-2.286" width="0.127" layer="21"/>
<wire x1="-3.429" y1="-2.54" x2="3.429" y2="-2.54" width="0.127" layer="21"/>
<wire x1="3.683" y1="-2.286" x2="3.683" y2="2.286" width="0.127" layer="21"/>
<wire x1="3.429" y1="2.54" x2="-3.429" y2="2.54" width="0.127" layer="21"/>
<wire x1="3.429" y1="2.54" x2="3.683" y2="2.286" width="0.127" layer="21" curve="-90"/>
<wire x1="3.429" y1="-2.54" x2="3.683" y2="-2.286" width="0.127" layer="21" curve="90"/>
<wire x1="-3.683" y1="-2.286" x2="-3.429" y2="-2.54" width="0.127" layer="21" curve="90"/>
<wire x1="-3.683" y1="2.286" x2="-3.429" y2="2.54" width="0.127" layer="21" curve="-90"/>
<pad name="1" x="-2.54" y="0" drill="0.8128" shape="octagon"/>
<pad name="2" x="2.54" y="0" drill="0.8128" shape="octagon"/>
<text x="-2.54" y="1.016" size="1.27" layer="25" ratio="10">&gt;NAME</text>
<text x="-2.54" y="-2.286" size="1.27" layer="27" ratio="10">&gt;VALUE</text>
</package>
<package name="C050-055X075">
<description>Capacitor&lt;p&gt;
Grid  5 mm Outline 5.5 x 7.5 mm</description>
<wire x1="-0.3048" y1="0.635" x2="-0.3048" y2="0" width="0.3048" layer="21"/>
<wire x1="-0.3048" y1="0" x2="-0.3048" y2="-0.635" width="0.3048" layer="21"/>
<wire x1="-0.3048" y1="0" x2="-1.524" y2="0" width="0.127" layer="21"/>
<wire x1="0.3302" y1="0.635" x2="0.3302" y2="0" width="0.3048" layer="21"/>
<wire x1="0.3302" y1="0" x2="0.3302" y2="-0.635" width="0.3048" layer="21"/>
<wire x1="0.3302" y1="0" x2="1.524" y2="0" width="0.127" layer="21"/>
<wire x1="-3.683" y1="2.54" x2="-3.683" y2="-2.54" width="0.127" layer="21"/>
<wire x1="-3.429" y1="-2.794" x2="3.429" y2="-2.794" width="0.127" layer="21"/>
<wire x1="3.683" y1="-2.54" x2="3.683" y2="2.54" width="0.127" layer="21"/>
<wire x1="3.429" y1="2.794" x2="-3.429" y2="2.794" width="0.127" layer="21"/>
<wire x1="3.429" y1="2.794" x2="3.683" y2="2.54" width="0.127" layer="21" curve="-90"/>
<wire x1="3.429" y1="-2.794" x2="3.683" y2="-2.54" width="0.127" layer="21" curve="90"/>
<wire x1="-3.683" y1="-2.54" x2="-3.429" y2="-2.794" width="0.127" layer="21" curve="90"/>
<wire x1="-3.683" y1="2.54" x2="-3.429" y2="2.794" width="0.127" layer="21" curve="-90"/>
<pad name="1" x="-2.54" y="0" drill="0.8128" shape="octagon"/>
<pad name="2" x="2.54" y="0" drill="0.8128" shape="octagon"/>
<text x="-2.54" y="1.016" size="1.27" layer="25" ratio="10">&gt;NAME</text>
<text x="-2.54" y="-2.286" size="1.27" layer="27" ratio="10">&gt;VALUE</text>
</package>
<package name="C050-075X075">
<description>Capacitor&lt;p&gt;
Grid  5 mm Outline 7.5 x 7.5 mm</description>
<wire x1="-1.524" y1="0" x2="-0.4572" y2="0" width="0.127" layer="21"/>
<wire x1="-0.4572" y1="0" x2="-0.4572" y2="0.762" width="0.4064" layer="21"/>
<wire x1="-0.4572" y1="0" x2="-0.4572" y2="-0.762" width="0.4064" layer="21"/>
<wire x1="0.4318" y1="0.762" x2="0.4318" y2="0" width="0.4064" layer="21"/>
<wire x1="0.4318" y1="0" x2="1.524" y2="0" width="0.127" layer="21"/>
<wire x1="0.4318" y1="0" x2="0.4318" y2="-0.762" width="0.4064" layer="21"/>
<wire x1="-3.683" y1="3.429" x2="-3.683" y2="-3.429" width="0.127" layer="21"/>
<wire x1="-3.429" y1="-3.683" x2="3.429" y2="-3.683" width="0.127" layer="21"/>
<wire x1="3.683" y1="-3.429" x2="3.683" y2="3.429" width="0.127" layer="21"/>
<wire x1="3.429" y1="3.683" x2="-3.429" y2="3.683" width="0.127" layer="21"/>
<wire x1="3.429" y1="3.683" x2="3.683" y2="3.429" width="0.127" layer="21" curve="-90"/>
<wire x1="3.429" y1="-3.683" x2="3.683" y2="-3.429" width="0.127" layer="21" curve="90"/>
<wire x1="-3.683" y1="-3.429" x2="-3.429" y2="-3.683" width="0.127" layer="21" curve="90"/>
<wire x1="-3.683" y1="3.429" x2="-3.429" y2="3.683" width="0.127" layer="21" curve="-90"/>
<pad name="1" x="-2.54" y="0" drill="0.8128" shape="octagon"/>
<pad name="2" x="2.54" y="0" drill="0.8128" shape="octagon"/>
<text x="-2.54" y="1.651" size="1.27" layer="25" ratio="10">&gt;NAME</text>
<text x="-3.175" y="-2.921" size="1.27" layer="27" ratio="10">&gt;VALUE</text>
</package>
<package name="C050H075X075">
<description>Capacitor&lt;p&gt;
Horizontal Grid  5 mm Outline 7.5 x 7.5 mm</description>
<wire x1="-3.683" y1="7.112" x2="-3.683" y2="0.508" width="0.127" layer="21"/>
<wire x1="-3.683" y1="0.508" x2="-3.302" y2="0.508" width="0.127" layer="21"/>
<wire x1="-3.302" y1="0.508" x2="-1.778" y2="0.508" width="0.127" layer="51"/>
<wire x1="-1.778" y1="0.508" x2="1.778" y2="0.508" width="0.127" layer="21"/>
<wire x1="1.778" y1="0.508" x2="3.302" y2="0.508" width="0.127" layer="51"/>
<wire x1="3.302" y1="0.508" x2="3.683" y2="0.508" width="0.127" layer="21"/>
<wire x1="3.683" y1="0.508" x2="3.683" y2="7.112" width="0.127" layer="21"/>
<wire x1="3.175" y1="7.62" x2="-3.175" y2="7.62" width="0.127" layer="21"/>
<wire x1="-0.3048" y1="2.413" x2="-0.3048" y2="1.778" width="0.3048" layer="21"/>
<wire x1="-0.3048" y1="1.778" x2="-0.3048" y2="1.143" width="0.3048" layer="21"/>
<wire x1="-0.3048" y1="1.778" x2="-1.651" y2="1.778" width="0.127" layer="21"/>
<wire x1="0.3302" y1="2.413" x2="0.3302" y2="1.778" width="0.3048" layer="21"/>
<wire x1="0.3302" y1="1.778" x2="0.3302" y2="1.143" width="0.3048" layer="21"/>
<wire x1="0.3302" y1="1.778" x2="1.651" y2="1.778" width="0.127" layer="21"/>
<wire x1="-3.683" y1="7.112" x2="-3.175" y2="7.62" width="0.127" layer="21" curve="-90"/>
<wire x1="3.175" y1="7.62" x2="3.683" y2="7.112" width="0.127" layer="21" curve="-90"/>
<wire x1="-2.54" y1="0" x2="-2.54" y2="0.254" width="0.508" layer="51"/>
<wire x1="2.54" y1="0" x2="2.54" y2="0.254" width="0.508" layer="51"/>
<pad name="1" x="-2.54" y="0" drill="0.8128" shape="octagon"/>
<pad name="2" x="2.54" y="0" drill="0.8128" shape="octagon"/>
<text x="-2.54" y="5.08" size="1.27" layer="25" ratio="10">&gt;NAME</text>
<text x="-3.175" y="3.175" size="1.27" layer="27" ratio="10">&gt;VALUE</text>
<rectangle x1="-2.794" y1="0.127" x2="-2.286" y2="0.508" layer="51"/>
<rectangle x1="2.286" y1="0.127" x2="2.794" y2="0.508" layer="51"/>
</package>
<package name="C075-032X103">
<description>Capacitor&lt;p&gt;
Grid  7.5 mm Outline 3.2 x 10.3 mm</description>
<wire x1="4.826" y1="1.524" x2="-4.826" y2="1.524" width="0.127" layer="21"/>
<wire x1="-5.08" y1="1.27" x2="-5.08" y2="-1.27" width="0.127" layer="21"/>
<wire x1="-4.826" y1="-1.524" x2="4.826" y2="-1.524" width="0.127" layer="21"/>
<wire x1="5.08" y1="-1.27" x2="5.08" y2="1.27" width="0.127" layer="21"/>
<wire x1="4.826" y1="1.524" x2="5.08" y2="1.27" width="0.127" layer="21" curve="-90"/>
<wire x1="4.826" y1="-1.524" x2="5.08" y2="-1.27" width="0.127" layer="21" curve="90"/>
<wire x1="-5.08" y1="-1.27" x2="-4.826" y2="-1.524" width="0.127" layer="21" curve="90"/>
<wire x1="-5.08" y1="1.27" x2="-4.826" y2="1.524" width="0.127" layer="21" curve="-90"/>
<wire x1="0.508" y1="0" x2="2.54" y2="0" width="0.127" layer="21"/>
<wire x1="-2.54" y1="0" x2="-0.508" y2="0" width="0.127" layer="21"/>
<wire x1="-0.508" y1="0.889" x2="-0.508" y2="0" width="0.4064" layer="21"/>
<wire x1="-0.508" y1="0" x2="-0.508" y2="-0.889" width="0.4064" layer="21"/>
<wire x1="0.508" y1="0.889" x2="0.508" y2="0" width="0.4064" layer="21"/>
<wire x1="0.508" y1="0" x2="0.508" y2="-0.889" width="0.4064" layer="21"/>
<pad name="1" x="-3.81" y="0" drill="0.9144" shape="octagon"/>
<pad name="2" x="3.81" y="0" drill="0.9144" shape="octagon"/>
<text x="5.588" y="0.254" size="1.27" layer="25" ratio="10">&gt;NAME</text>
<text x="5.588" y="-1.397" size="1.27" layer="27" ratio="10">&gt;VALUE</text>
</package>
<package name="C075-042X103">
<description>Capacitor&lt;p&gt;
Grid  7.5 mm Outline 4.2 x 10.3 mm</description>
<wire x1="4.826" y1="2.032" x2="-4.826" y2="2.032" width="0.127" layer="21"/>
<wire x1="-5.08" y1="1.778" x2="-5.08" y2="-1.778" width="0.127" layer="21"/>
<wire x1="-4.826" y1="-2.032" x2="4.826" y2="-2.032" width="0.127" layer="21"/>
<wire x1="5.08" y1="-1.778" x2="5.08" y2="1.778" width="0.127" layer="21"/>
<wire x1="4.826" y1="2.032" x2="5.08" y2="1.778" width="0.127" layer="21" curve="-90"/>
<wire x1="4.826" y1="-2.032" x2="5.08" y2="-1.778" width="0.127" layer="21" curve="90"/>
<wire x1="-5.08" y1="-1.778" x2="-4.826" y2="-2.032" width="0.127" layer="21" curve="90"/>
<wire x1="-5.08" y1="1.778" x2="-4.826" y2="2.032" width="0.127" layer="21" curve="-90"/>
<wire x1="-1.27" y1="0" x2="2.667" y2="0" width="0.127" layer="21"/>
<wire x1="-2.667" y1="0" x2="-2.159" y2="0" width="0.127" layer="21"/>
<wire x1="-2.159" y1="1.27" x2="-2.159" y2="0" width="0.4064" layer="21"/>
<wire x1="-2.159" y1="0" x2="-2.159" y2="-1.27" width="0.4064" layer="21"/>
<wire x1="-1.27" y1="1.27" x2="-1.27" y2="0" width="0.4064" layer="21"/>
<wire x1="-1.27" y1="0" x2="-1.27" y2="-1.27" width="0.4064" layer="21"/>
<pad name="1" x="-3.81" y="0" drill="0.9144" shape="octagon"/>
<pad name="2" x="3.81" y="0" drill="0.9144" shape="octagon"/>
<text x="-0.635" y="0.381" size="1.27" layer="25" ratio="10">&gt;NAME</text>
<text x="-0.635" y="-1.651" size="1.27" layer="27" ratio="10">&gt;VALUE</text>
</package>
<package name="C075-052X106">
<description>Capacitor&lt;p&gt;
Grid  7.5 mm Outline 5.2 x 10.6 mm</description>
<wire x1="4.953" y1="2.54" x2="-4.953" y2="2.54" width="0.127" layer="21"/>
<wire x1="-5.207" y1="2.286" x2="-5.207" y2="-2.286" width="0.127" layer="21"/>
<wire x1="-4.953" y1="-2.54" x2="4.953" y2="-2.54" width="0.127" layer="21"/>
<wire x1="5.207" y1="-2.286" x2="5.207" y2="2.286" width="0.127" layer="21"/>
<wire x1="4.953" y1="2.54" x2="5.207" y2="2.286" width="0.127" layer="21" curve="-90"/>
<wire x1="4.953" y1="-2.54" x2="5.207" y2="-2.286" width="0.127" layer="21" curve="90"/>
<wire x1="-5.207" y1="-2.286" x2="-4.953" y2="-2.54" width="0.127" layer="21" curve="90"/>
<wire x1="-5.207" y1="2.286" x2="-4.953" y2="2.54" width="0.127" layer="21" curve="-90"/>
<wire x1="-1.27" y1="0" x2="2.667" y2="0" width="0.127" layer="21"/>
<wire x1="-2.667" y1="0" x2="-2.159" y2="0" width="0.127" layer="21"/>
<wire x1="-2.159" y1="1.27" x2="-2.159" y2="0" width="0.4064" layer="21"/>
<wire x1="-2.159" y1="0" x2="-2.159" y2="-1.27" width="0.4064" layer="21"/>
<wire x1="-1.27" y1="1.27" x2="-1.27" y2="0" width="0.4064" layer="21"/>
<wire x1="-1.27" y1="0" x2="-1.27" y2="-1.27" width="0.4064" layer="21"/>
<pad name="1" x="-3.81" y="0" drill="0.9144" shape="octagon"/>
<pad name="2" x="3.81" y="0" drill="0.9144" shape="octagon"/>
<text x="-0.635" y="0.762" size="1.27" layer="25" ratio="10">&gt;NAME</text>
<text x="-0.635" y="-2.032" size="1.27" layer="27" ratio="10">&gt;VALUE</text>
</package>
<package name="C102-043X133">
<description>Capacitor&lt;p&gt;
Grid  10.2 mm Outline 4.3 x 13.3 mm</description>
<wire x1="-3.175" y1="1.27" x2="-3.175" y2="0" width="0.4064" layer="21"/>
<wire x1="-2.286" y1="1.27" x2="-2.286" y2="0" width="0.4064" layer="21"/>
<wire x1="3.81" y1="0" x2="-2.286" y2="0" width="0.127" layer="21"/>
<wire x1="-2.286" y1="0" x2="-2.286" y2="-1.27" width="0.4064" layer="21"/>
<wire x1="-3.81" y1="0" x2="-3.175" y2="0" width="0.127" layer="21"/>
<wire x1="-3.175" y1="0" x2="-3.175" y2="-1.27" width="0.4064" layer="21"/>
<wire x1="-6.096" y1="2.032" x2="6.096" y2="2.032" width="0.127" layer="21"/>
<wire x1="6.604" y1="1.524" x2="6.604" y2="-1.524" width="0.127" layer="21"/>
<wire x1="6.096" y1="-2.032" x2="-6.096" y2="-2.032" width="0.127" layer="21"/>
<wire x1="-6.604" y1="-1.524" x2="-6.604" y2="1.524" width="0.127" layer="21"/>
<wire x1="6.096" y1="2.032" x2="6.604" y2="1.524" width="0.127" layer="21" curve="-90"/>
<wire x1="6.096" y1="-2.032" x2="6.604" y2="-1.524" width="0.127" layer="21" curve="90"/>
<wire x1="-6.604" y1="-1.524" x2="-6.096" y2="-2.032" width="0.127" layer="21" curve="90"/>
<wire x1="-6.604" y1="1.524" x2="-6.096" y2="2.032" width="0.127" layer="21" curve="-90"/>
<pad name="1" x="-5.08" y="0" drill="1.016" shape="octagon"/>
<pad name="2" x="5.08" y="0" drill="1.016" shape="octagon"/>
<text x="-1.524" y="0.381" size="1.27" layer="25" ratio="10">&gt;NAME</text>
<text x="-1.524" y="-1.651" size="1.27" layer="27" ratio="10">&gt;VALUE</text>
</package>
<package name="C102-054X133">
<description>Capacitor&lt;p&gt;
Grid  10.2 mm Outline 5.4 x 13.3 mm</description>
<wire x1="-3.175" y1="1.27" x2="-3.175" y2="0" width="0.4064" layer="21"/>
<wire x1="-2.286" y1="1.27" x2="-2.286" y2="0" width="0.4064" layer="21"/>
<wire x1="3.81" y1="0" x2="-2.286" y2="0" width="0.127" layer="21"/>
<wire x1="-2.286" y1="0" x2="-2.286" y2="-1.27" width="0.4064" layer="21"/>
<wire x1="-3.81" y1="0" x2="-3.175" y2="0" width="0.127" layer="21"/>
<wire x1="-3.175" y1="0" x2="-3.175" y2="-1.27" width="0.4064" layer="21"/>
<wire x1="-6.096" y1="2.54" x2="6.096" y2="2.54" width="0.127" layer="21"/>
<wire x1="6.604" y1="2.032" x2="6.604" y2="-2.032" width="0.127" layer="21"/>
<wire x1="6.096" y1="-2.54" x2="-6.096" y2="-2.54" width="0.127" layer="21"/>
<wire x1="-6.604" y1="-2.032" x2="-6.604" y2="2.032" width="0.127" layer="21"/>
<wire x1="6.096" y1="2.54" x2="6.604" y2="2.032" width="0.127" layer="21" curve="-90"/>
<wire x1="6.096" y1="-2.54" x2="6.604" y2="-2.032" width="0.127" layer="21" curve="90"/>
<wire x1="-6.604" y1="-2.032" x2="-6.096" y2="-2.54" width="0.127" layer="21" curve="90"/>
<wire x1="-6.604" y1="2.032" x2="-6.096" y2="2.54" width="0.127" layer="21" curve="-90"/>
<pad name="1" x="-5.08" y="0" drill="1.016" shape="octagon"/>
<pad name="2" x="5.08" y="0" drill="1.016" shape="octagon"/>
<text x="-1.524" y="0.635" size="1.27" layer="25" ratio="10">&gt;NAME</text>
<text x="-1.524" y="-1.905" size="1.27" layer="27" ratio="10">&gt;VALUE</text>
</package>
<package name="C102-064X133">
<description>Capacitor&lt;p&gt;
Grid  10.2 mm Outline 6.4 x 13.3 mm</description>
<wire x1="-3.175" y1="1.27" x2="-3.175" y2="0" width="0.4064" layer="21"/>
<wire x1="-2.286" y1="1.27" x2="-2.286" y2="0" width="0.4064" layer="21"/>
<wire x1="3.81" y1="0" x2="-2.286" y2="0" width="0.127" layer="21"/>
<wire x1="-2.286" y1="0" x2="-2.286" y2="-1.27" width="0.4064" layer="21"/>
<wire x1="-3.81" y1="0" x2="-3.175" y2="0" width="0.127" layer="21"/>
<wire x1="-3.175" y1="0" x2="-3.175" y2="-1.27" width="0.4064" layer="21"/>
<wire x1="-6.096" y1="3.048" x2="6.096" y2="3.048" width="0.127" layer="21"/>
<wire x1="6.604" y1="2.54" x2="6.604" y2="-2.54" width="0.127" layer="21"/>
<wire x1="6.096" y1="-3.048" x2="-6.096" y2="-3.048" width="0.127" layer="21"/>
<wire x1="-6.604" y1="-2.54" x2="-6.604" y2="2.54" width="0.127" layer="21"/>
<wire x1="6.096" y1="3.048" x2="6.604" y2="2.54" width="0.127" layer="21" curve="-90"/>
<wire x1="6.096" y1="-3.048" x2="6.604" y2="-2.54" width="0.127" layer="21" curve="90"/>
<wire x1="-6.604" y1="-2.54" x2="-6.096" y2="-3.048" width="0.127" layer="21" curve="90"/>
<wire x1="-6.604" y1="2.54" x2="-6.096" y2="3.048" width="0.127" layer="21" curve="-90"/>
<pad name="1" x="-5.08" y="0" drill="1.016" shape="octagon"/>
<pad name="2" x="5.08" y="0" drill="1.016" shape="octagon"/>
<text x="-1.524" y="0.762" size="1.27" layer="25" ratio="10">&gt;NAME</text>
<text x="-1.524" y="-2.032" size="1.27" layer="27" ratio="10">&gt;VALUE</text>
</package>
<package name="C102_152-062X184">
<description>Capacitor&lt;p&gt;
Grid  10.2 mm + 15.2 mm Outline 6.2 x 18.4 mm</description>
<wire x1="-2.286" y1="1.27" x2="-2.286" y2="0" width="0.4064" layer="21"/>
<wire x1="-2.286" y1="0" x2="-2.286" y2="-1.27" width="0.4064" layer="21"/>
<wire x1="-3.175" y1="1.27" x2="-3.175" y2="0" width="0.4064" layer="21"/>
<wire x1="-3.175" y1="0" x2="-3.175" y2="-1.27" width="0.4064" layer="21"/>
<wire x1="-3.683" y1="0" x2="-3.175" y2="0" width="0.127" layer="21"/>
<wire x1="-2.286" y1="0" x2="3.683" y2="0" width="0.127" layer="21"/>
<wire x1="6.477" y1="0" x2="8.636" y2="0" width="0.127" layer="21"/>
<wire x1="-6.096" y1="3.048" x2="6.223" y2="3.048" width="0.127" layer="21"/>
<wire x1="6.223" y1="-3.048" x2="-6.096" y2="-3.048" width="0.127" layer="21"/>
<wire x1="-6.604" y1="-2.54" x2="-6.604" y2="2.54" width="0.127" layer="21"/>
<wire x1="6.223" y1="3.048" x2="6.731" y2="2.54" width="0.127" layer="21" curve="-90"/>
<wire x1="6.223" y1="-3.048" x2="6.731" y2="-2.54" width="0.127" layer="21" curve="90"/>
<wire x1="-6.604" y1="-2.54" x2="-6.096" y2="-3.048" width="0.127" layer="21" curve="90"/>
<wire x1="-6.604" y1="2.54" x2="-6.096" y2="3.048" width="0.127" layer="21" curve="-90"/>
<wire x1="6.731" y1="2.54" x2="6.731" y2="-2.54" width="0.127" layer="21"/>
<wire x1="11.176" y1="3.048" x2="11.684" y2="2.54" width="0.127" layer="21" curve="-90"/>
<wire x1="11.176" y1="-3.048" x2="11.684" y2="-2.54" width="0.127" layer="21" curve="90"/>
<wire x1="11.176" y1="-3.048" x2="7.112" y2="-3.048" width="0.127" layer="21"/>
<wire x1="7.112" y1="3.048" x2="11.176" y2="3.048" width="0.127" layer="21"/>
<wire x1="11.684" y1="2.54" x2="11.684" y2="-2.54" width="0.127" layer="21"/>
<pad name="1" x="-5.08" y="0" drill="1.016" shape="octagon"/>
<pad name="2" x="5.08" y="0" drill="1.016" shape="octagon"/>
<pad name="3" x="10.033" y="0" drill="1.016" shape="octagon"/>
<text x="-1.524" y="1.016" size="1.27" layer="25" ratio="10">&gt;NAME</text>
<text x="-1.524" y="-2.286" size="1.27" layer="27" ratio="10">&gt;VALUE</text>
</package>
<package name="C150-054X183">
<description>Capacitor&lt;p&gt;
Grid  15 mm Outline 5.4 x 18.3 mm</description>
<wire x1="-5.08" y1="1.27" x2="-5.08" y2="0" width="0.4064" layer="21"/>
<wire x1="-5.08" y1="0" x2="-5.08" y2="-1.27" width="0.4064" layer="21"/>
<wire x1="-4.191" y1="1.27" x2="-4.191" y2="0" width="0.4064" layer="21"/>
<wire x1="-4.191" y1="0" x2="-4.191" y2="-1.27" width="0.4064" layer="21"/>
<wire x1="-4.191" y1="0" x2="6.096" y2="0" width="0.127" layer="21"/>
<wire x1="-5.08" y1="0" x2="-6.096" y2="0" width="0.127" layer="21"/>
<wire x1="9.017" y1="2.032" x2="9.017" y2="-2.032" width="0.127" layer="21"/>
<wire x1="8.509" y1="-2.54" x2="-8.509" y2="-2.54" width="0.127" layer="21"/>
<wire x1="-9.017" y1="-2.032" x2="-9.017" y2="2.032" width="0.127" layer="21"/>
<wire x1="-8.509" y1="2.54" x2="8.509" y2="2.54" width="0.127" layer="21"/>
<wire x1="8.509" y1="2.54" x2="9.017" y2="2.032" width="0.127" layer="21" curve="-90"/>
<wire x1="8.509" y1="-2.54" x2="9.017" y2="-2.032" width="0.127" layer="21" curve="90"/>
<wire x1="-9.017" y1="-2.032" x2="-8.509" y2="-2.54" width="0.127" layer="21" curve="90"/>
<wire x1="-9.017" y1="2.032" x2="-8.509" y2="2.54" width="0.127" layer="21" curve="-90"/>
<pad name="1" x="-7.493" y="0" drill="1.016" shape="octagon"/>
<pad name="2" x="7.493" y="0" drill="1.016" shape="octagon"/>
<text x="-3.429" y="0.635" size="1.27" layer="25" ratio="10">&gt;NAME</text>
<text x="-3.429" y="-2.032" size="1.27" layer="27" ratio="10">&gt;VALUE</text>
</package>
<package name="C150-064X183">
<description>Capacitor&lt;p&gt;
Grid  15 mm Outline 6.4 x 18.3 mm</description>
<wire x1="-5.08" y1="1.27" x2="-5.08" y2="0" width="0.4064" layer="21"/>
<wire x1="-5.08" y1="0" x2="-5.08" y2="-1.27" width="0.4064" layer="21"/>
<wire x1="-4.191" y1="1.27" x2="-4.191" y2="0" width="0.4064" layer="21"/>
<wire x1="-4.191" y1="0" x2="-4.191" y2="-1.27" width="0.4064" layer="21"/>
<wire x1="-4.191" y1="0" x2="6.096" y2="0" width="0.127" layer="21"/>
<wire x1="-5.08" y1="0" x2="-6.096" y2="0" width="0.127" layer="21"/>
<wire x1="9.017" y1="2.54" x2="9.017" y2="-2.54" width="0.127" layer="21"/>
<wire x1="8.509" y1="-3.048" x2="-8.509" y2="-3.048" width="0.127" layer="21"/>
<wire x1="-9.017" y1="-2.54" x2="-9.017" y2="2.54" width="0.127" layer="21"/>
<wire x1="-8.509" y1="3.048" x2="8.509" y2="3.048" width="0.127" layer="21"/>
<wire x1="8.509" y1="3.048" x2="9.017" y2="2.54" width="0.127" layer="21" curve="-90"/>
<wire x1="8.509" y1="-3.048" x2="9.017" y2="-2.54" width="0.127" layer="21" curve="90"/>
<wire x1="-9.017" y1="-2.54" x2="-8.509" y2="-3.048" width="0.127" layer="21" curve="90"/>
<wire x1="-9.017" y1="2.54" x2="-8.509" y2="3.048" width="0.127" layer="21" curve="-90"/>
<pad name="1" x="-7.493" y="0" drill="1.016" shape="octagon"/>
<pad name="2" x="7.493" y="0" drill="1.016" shape="octagon"/>
<text x="-3.429" y="0.635" size="1.27" layer="25" ratio="10">&gt;NAME</text>
<text x="-3.429" y="-2.032" size="1.27" layer="27" ratio="10">&gt;VALUE</text>
</package>
<package name="C150-072X183">
<description>Capacitor&lt;p&gt;
Grid  15 mm Outline 7.2 x 18.3 mm</description>
<wire x1="-5.08" y1="1.27" x2="-5.08" y2="0" width="0.4064" layer="21"/>
<wire x1="-5.08" y1="0" x2="-5.08" y2="-1.27" width="0.4064" layer="21"/>
<wire x1="-4.191" y1="1.27" x2="-4.191" y2="0" width="0.4064" layer="21"/>
<wire x1="-4.191" y1="0" x2="-4.191" y2="-1.27" width="0.4064" layer="21"/>
<wire x1="-4.191" y1="0" x2="6.096" y2="0" width="0.127" layer="21"/>
<wire x1="-5.08" y1="0" x2="-6.096" y2="0" width="0.127" layer="21"/>
<wire x1="9.017" y1="3.048" x2="9.017" y2="-3.048" width="0.127" layer="21"/>
<wire x1="8.509" y1="-3.556" x2="-8.509" y2="-3.556" width="0.127" layer="21"/>
<wire x1="-9.017" y1="-3.048" x2="-9.017" y2="3.048" width="0.127" layer="21"/>
<wire x1="-8.509" y1="3.556" x2="8.509" y2="3.556" width="0.127" layer="21"/>
<wire x1="8.509" y1="3.556" x2="9.017" y2="3.048" width="0.127" layer="21" curve="-90"/>
<wire x1="8.509" y1="-3.556" x2="9.017" y2="-3.048" width="0.127" layer="21" curve="90"/>
<wire x1="-9.017" y1="-3.048" x2="-8.509" y2="-3.556" width="0.127" layer="21" curve="90"/>
<wire x1="-9.017" y1="3.048" x2="-8.509" y2="3.556" width="0.127" layer="21" curve="-90"/>
<pad name="1" x="-7.493" y="0" drill="1.016" shape="octagon"/>
<pad name="2" x="7.493" y="0" drill="1.016" shape="octagon"/>
<text x="-3.429" y="0.889" size="1.27" layer="25" ratio="10">&gt;NAME</text>
<text x="-3.429" y="-2.286" size="1.27" layer="27" ratio="10">&gt;VALUE</text>
</package>
<package name="C150-084X183">
<description>Capacitor&lt;p&gt;
Grid  15 mm Outline 8.4 x 18.3 mm</description>
<wire x1="-5.08" y1="1.27" x2="-5.08" y2="0" width="0.4064" layer="21"/>
<wire x1="-5.08" y1="0" x2="-5.08" y2="-1.27" width="0.4064" layer="21"/>
<wire x1="-4.191" y1="1.27" x2="-4.191" y2="0" width="0.4064" layer="21"/>
<wire x1="-4.191" y1="0" x2="-4.191" y2="-1.27" width="0.4064" layer="21"/>
<wire x1="-4.191" y1="0" x2="6.096" y2="0" width="0.127" layer="21"/>
<wire x1="-5.08" y1="0" x2="-6.096" y2="0" width="0.127" layer="21"/>
<wire x1="9.017" y1="3.556" x2="9.017" y2="-3.556" width="0.127" layer="21"/>
<wire x1="8.509" y1="-4.064" x2="-8.509" y2="-4.064" width="0.127" layer="21"/>
<wire x1="-9.017" y1="-3.556" x2="-9.017" y2="3.556" width="0.127" layer="21"/>
<wire x1="-8.509" y1="4.064" x2="8.509" y2="4.064" width="0.127" layer="21"/>
<wire x1="8.509" y1="4.064" x2="9.017" y2="3.556" width="0.127" layer="21" curve="-90"/>
<wire x1="8.509" y1="-4.064" x2="9.017" y2="-3.556" width="0.127" layer="21" curve="90"/>
<wire x1="-9.017" y1="-3.556" x2="-8.509" y2="-4.064" width="0.127" layer="21" curve="90"/>
<wire x1="-9.017" y1="3.556" x2="-8.509" y2="4.064" width="0.127" layer="21" curve="-90"/>
<pad name="1" x="-7.493" y="0" drill="1.016" shape="octagon"/>
<pad name="2" x="7.493" y="0" drill="1.016" shape="octagon"/>
<text x="-3.429" y="1.143" size="1.27" layer="25" ratio="10">&gt;NAME</text>
<text x="-3.429" y="-2.54" size="1.27" layer="27" ratio="10">&gt;VALUE</text>
</package>
<package name="C150-091X182">
<description>Capacitor&lt;p&gt;
Grid  15 mm Outline 9.1 x 18.2 mm</description>
<wire x1="-5.08" y1="1.27" x2="-5.08" y2="0" width="0.4064" layer="21"/>
<wire x1="-5.08" y1="0" x2="-5.08" y2="-1.27" width="0.4064" layer="21"/>
<wire x1="-4.191" y1="1.27" x2="-4.191" y2="0" width="0.4064" layer="21"/>
<wire x1="-4.191" y1="0" x2="-4.191" y2="-1.27" width="0.4064" layer="21"/>
<wire x1="-4.191" y1="0" x2="6.096" y2="0" width="0.127" layer="21"/>
<wire x1="-5.08" y1="0" x2="-6.096" y2="0" width="0.127" layer="21"/>
<wire x1="9.017" y1="3.937" x2="9.017" y2="-3.937" width="0.127" layer="21"/>
<wire x1="8.509" y1="-4.445" x2="-8.509" y2="-4.445" width="0.127" layer="21"/>
<wire x1="-9.017" y1="-3.937" x2="-9.017" y2="3.937" width="0.127" layer="21"/>
<wire x1="-8.509" y1="4.445" x2="8.509" y2="4.445" width="0.127" layer="21"/>
<wire x1="8.509" y1="4.445" x2="9.017" y2="3.937" width="0.127" layer="21" curve="-90"/>
<wire x1="8.509" y1="-4.445" x2="9.017" y2="-3.937" width="0.127" layer="21" curve="90"/>
<wire x1="-9.017" y1="-3.937" x2="-8.509" y2="-4.445" width="0.127" layer="21" curve="90"/>
<wire x1="-9.017" y1="3.937" x2="-8.509" y2="4.445" width="0.127" layer="21" curve="-90"/>
<pad name="1" x="-7.493" y="0" drill="1.016" shape="octagon"/>
<pad name="2" x="7.493" y="0" drill="1.016" shape="octagon"/>
<text x="-3.429" y="1.143" size="1.27" layer="25" ratio="10">&gt;NAME</text>
<text x="-3.429" y="-2.54" size="1.27" layer="27" ratio="10">&gt;VALUE</text>
</package>
<package name="C225-062X268">
<description>Capacitor&lt;p&gt;
Grid  22.5 mm Outline 6.2 x 26.8 mm</description>
<wire x1="-12.827" y1="3.048" x2="12.827" y2="3.048" width="0.127" layer="21"/>
<wire x1="13.335" y1="2.54" x2="13.335" y2="-2.54" width="0.127" layer="21"/>
<wire x1="12.827" y1="-3.048" x2="-12.827" y2="-3.048" width="0.127" layer="21"/>
<wire x1="-13.335" y1="-2.54" x2="-13.335" y2="2.54" width="0.127" layer="21"/>
<wire x1="-6.731" y1="1.905" x2="-6.731" y2="0" width="0.4064" layer="21"/>
<wire x1="-6.731" y1="0" x2="-6.731" y2="-1.905" width="0.4064" layer="21"/>
<wire x1="-7.62" y1="1.905" x2="-7.62" y2="0" width="0.4064" layer="21"/>
<wire x1="-7.62" y1="0" x2="-7.62" y2="-1.905" width="0.4064" layer="21"/>
<wire x1="12.827" y1="3.048" x2="13.335" y2="2.54" width="0.127" layer="21" curve="-90"/>
<wire x1="12.827" y1="-3.048" x2="13.335" y2="-2.54" width="0.127" layer="21" curve="90"/>
<wire x1="-13.335" y1="-2.54" x2="-12.827" y2="-3.048" width="0.127" layer="21" curve="90"/>
<wire x1="-13.335" y1="2.54" x2="-12.827" y2="3.048" width="0.127" layer="21" curve="-90"/>
<wire x1="-9.652" y1="0" x2="-7.62" y2="0" width="0.127" layer="21"/>
<wire x1="-6.731" y1="0" x2="9.652" y2="0" width="0.127" layer="21"/>
<pad name="1" x="-11.303" y="0" drill="1.016" shape="octagon"/>
<pad name="2" x="11.303" y="0" drill="1.016" shape="octagon"/>
<text x="-5.08" y="0.762" size="1.778" layer="25" ratio="10">&gt;NAME</text>
<text x="-5.08" y="-2.54" size="1.778" layer="27" ratio="10">&gt;VALUE</text>
</package>
<package name="C225-074X268">
<description>Capacitor&lt;p&gt;
Grid  22.5 mm Outline 7.4 x 26.8 mm</description>
<wire x1="-12.827" y1="3.556" x2="12.827" y2="3.556" width="0.127" layer="21"/>
<wire x1="13.335" y1="3.048" x2="13.335" y2="-3.048" width="0.127" layer="21"/>
<wire x1="12.827" y1="-3.556" x2="-12.827" y2="-3.556" width="0.127" layer="21"/>
<wire x1="-13.335" y1="-3.048" x2="-13.335" y2="3.048" width="0.127" layer="21"/>
<wire x1="-6.731" y1="1.905" x2="-6.731" y2="0" width="0.4064" layer="21"/>
<wire x1="-6.731" y1="0" x2="-6.731" y2="-1.905" width="0.4064" layer="21"/>
<wire x1="-7.62" y1="1.905" x2="-7.62" y2="0" width="0.4064" layer="21"/>
<wire x1="-7.62" y1="0" x2="-7.62" y2="-1.905" width="0.4064" layer="21"/>
<wire x1="12.827" y1="3.556" x2="13.335" y2="3.048" width="0.127" layer="21" curve="-90"/>
<wire x1="12.827" y1="-3.556" x2="13.335" y2="-3.048" width="0.127" layer="21" curve="90"/>
<wire x1="-13.335" y1="-3.048" x2="-12.827" y2="-3.556" width="0.127" layer="21" curve="90"/>
<wire x1="-13.335" y1="3.048" x2="-12.827" y2="3.556" width="0.127" layer="21" curve="-90"/>
<wire x1="-9.652" y1="0" x2="-7.62" y2="0" width="0.127" layer="21"/>
<wire x1="-6.731" y1="0" x2="9.652" y2="0" width="0.127" layer="21"/>
<pad name="1" x="-11.303" y="0" drill="1.016" shape="octagon"/>
<pad name="2" x="11.303" y="0" drill="1.016" shape="octagon"/>
<text x="-5.08" y="0.762" size="1.778" layer="25" ratio="10">&gt;NAME</text>
<text x="-5.08" y="-2.54" size="1.778" layer="27" ratio="10">&gt;VALUE</text>
</package>
<package name="C225-087X268">
<description>Capacitor&lt;p&gt;
Grid  22.5 mm Outline 8.7 x 26.8 mm</description>
<wire x1="-12.827" y1="4.318" x2="12.827" y2="4.318" width="0.127" layer="21"/>
<wire x1="13.335" y1="3.81" x2="13.335" y2="-3.81" width="0.127" layer="21"/>
<wire x1="12.827" y1="-4.318" x2="-12.827" y2="-4.318" width="0.127" layer="21"/>
<wire x1="-13.335" y1="-3.81" x2="-13.335" y2="3.81" width="0.127" layer="21"/>
<wire x1="-6.731" y1="1.905" x2="-6.731" y2="0" width="0.4064" layer="21"/>
<wire x1="-6.731" y1="0" x2="-6.731" y2="-1.905" width="0.4064" layer="21"/>
<wire x1="-7.62" y1="1.905" x2="-7.62" y2="0" width="0.4064" layer="21"/>
<wire x1="-7.62" y1="0" x2="-7.62" y2="-1.905" width="0.4064" layer="21"/>
<wire x1="12.827" y1="4.318" x2="13.335" y2="3.81" width="0.127" layer="21" curve="-90"/>
<wire x1="12.827" y1="-4.318" x2="13.335" y2="-3.81" width="0.127" layer="21" curve="90"/>
<wire x1="-13.335" y1="-3.81" x2="-12.827" y2="-4.318" width="0.127" layer="21" curve="90"/>
<wire x1="-13.335" y1="3.81" x2="-12.827" y2="4.318" width="0.127" layer="21" curve="-90"/>
<wire x1="-9.652" y1="0" x2="-7.62" y2="0" width="0.127" layer="21"/>
<wire x1="-6.731" y1="0" x2="9.652" y2="0" width="0.127" layer="21"/>
<pad name="1" x="-11.303" y="0" drill="1.016" shape="octagon"/>
<pad name="2" x="11.303" y="0" drill="1.016" shape="octagon"/>
<text x="-5.08" y="0.762" size="1.778" layer="25" ratio="10">&gt;NAME</text>
<text x="-5.08" y="-2.54" size="1.778" layer="27" ratio="10">&gt;VALUE</text>
</package>
<package name="C225-108X268">
<description>Capacitor&lt;p&gt;
Grid  22.5 mm Outline 10.8 x 26.8 mm</description>
<wire x1="-12.827" y1="5.334" x2="12.827" y2="5.334" width="0.127" layer="21"/>
<wire x1="13.335" y1="4.826" x2="13.335" y2="-4.826" width="0.127" layer="21"/>
<wire x1="12.827" y1="-5.334" x2="-12.827" y2="-5.334" width="0.127" layer="21"/>
<wire x1="-13.335" y1="-4.826" x2="-13.335" y2="4.826" width="0.127" layer="21"/>
<wire x1="-6.731" y1="1.905" x2="-6.731" y2="0" width="0.4064" layer="21"/>
<wire x1="-6.731" y1="0" x2="-6.731" y2="-1.905" width="0.4064" layer="21"/>
<wire x1="-7.62" y1="1.905" x2="-7.62" y2="0" width="0.4064" layer="21"/>
<wire x1="-7.62" y1="0" x2="-7.62" y2="-1.905" width="0.4064" layer="21"/>
<wire x1="12.827" y1="5.334" x2="13.335" y2="4.826" width="0.127" layer="21" curve="-90"/>
<wire x1="12.827" y1="-5.334" x2="13.335" y2="-4.826" width="0.127" layer="21" curve="90"/>
<wire x1="-13.335" y1="-4.826" x2="-12.827" y2="-5.334" width="0.127" layer="21" curve="90"/>
<wire x1="-13.335" y1="4.826" x2="-12.827" y2="5.334" width="0.127" layer="21" curve="-90"/>
<wire x1="-9.652" y1="0" x2="-7.62" y2="0" width="0.127" layer="21"/>
<wire x1="-6.731" y1="0" x2="9.652" y2="0" width="0.127" layer="21"/>
<pad name="1" x="-11.303" y="0" drill="1.016" shape="octagon"/>
<pad name="2" x="11.303" y="0" drill="1.016" shape="octagon"/>
<text x="-5.08" y="0.762" size="1.778" layer="25" ratio="10">&gt;NAME</text>
<text x="-5.08" y="-2.54" size="1.778" layer="27" ratio="10">&gt;VALUE</text>
</package>
<package name="C225-113X268">
<description>Capacitor&lt;p&gt;
Grid  22.5 mm Outline 11.3 x 26.8 mm</description>
<wire x1="-12.827" y1="5.588" x2="12.827" y2="5.588" width="0.127" layer="21"/>
<wire x1="13.335" y1="5.08" x2="13.335" y2="-5.08" width="0.127" layer="21"/>
<wire x1="12.827" y1="-5.588" x2="-12.827" y2="-5.588" width="0.127" layer="21"/>
<wire x1="-13.335" y1="-5.08" x2="-13.335" y2="5.08" width="0.127" layer="21"/>
<wire x1="-6.731" y1="1.905" x2="-6.731" y2="0" width="0.4064" layer="21"/>
<wire x1="-6.731" y1="0" x2="-6.731" y2="-1.905" width="0.4064" layer="21"/>
<wire x1="-7.62" y1="1.905" x2="-7.62" y2="0" width="0.4064" layer="21"/>
<wire x1="-7.62" y1="0" x2="-7.62" y2="-1.905" width="0.4064" layer="21"/>
<wire x1="12.827" y1="5.588" x2="13.335" y2="5.08" width="0.127" layer="21" curve="-90"/>
<wire x1="12.827" y1="-5.588" x2="13.335" y2="-5.08" width="0.127" layer="21" curve="90"/>
<wire x1="-13.335" y1="-5.08" x2="-12.827" y2="-5.588" width="0.127" layer="21" curve="90"/>
<wire x1="-13.335" y1="5.08" x2="-12.827" y2="5.588" width="0.127" layer="21" curve="-90"/>
<wire x1="-9.652" y1="0" x2="-7.62" y2="0" width="0.127" layer="21"/>
<wire x1="-6.731" y1="0" x2="9.652" y2="0" width="0.127" layer="21"/>
<pad name="1" x="-11.303" y="0" drill="1.016" shape="octagon"/>
<pad name="2" x="11.303" y="0" drill="1.016" shape="octagon"/>
<text x="-5.08" y="0.762" size="1.778" layer="25" ratio="10">&gt;NAME</text>
<text x="-5.08" y="-2.54" size="1.778" layer="27" ratio="10">&gt;VALUE</text>
</package>
<package name="C275-093X316">
<description>Capacitor&lt;p&gt;
Grid  27.5 mm Outline 9.3 x 31.6 mm</description>
<wire x1="-15.24" y1="4.572" x2="15.24" y2="4.572" width="0.127" layer="21"/>
<wire x1="15.748" y1="4.064" x2="15.748" y2="-4.064" width="0.127" layer="21"/>
<wire x1="15.24" y1="-4.572" x2="-15.24" y2="-4.572" width="0.127" layer="21"/>
<wire x1="-15.748" y1="-4.064" x2="-15.748" y2="4.064" width="0.127" layer="21"/>
<wire x1="-6.731" y1="1.905" x2="-6.731" y2="0" width="0.4064" layer="21"/>
<wire x1="-6.731" y1="0" x2="-6.731" y2="-1.905" width="0.4064" layer="21"/>
<wire x1="-7.62" y1="1.905" x2="-7.62" y2="0" width="0.4064" layer="21"/>
<wire x1="-7.62" y1="0" x2="-7.62" y2="-1.905" width="0.4064" layer="21"/>
<wire x1="15.24" y1="4.572" x2="15.748" y2="4.064" width="0.127" layer="21" curve="-90"/>
<wire x1="15.24" y1="-4.572" x2="15.748" y2="-4.064" width="0.127" layer="21" curve="90"/>
<wire x1="-15.748" y1="-4.064" x2="-15.24" y2="-4.572" width="0.127" layer="21" curve="90"/>
<wire x1="-15.748" y1="4.064" x2="-15.24" y2="4.572" width="0.127" layer="21" curve="-90"/>
<wire x1="-11.557" y1="0" x2="-7.62" y2="0" width="0.127" layer="21"/>
<wire x1="-6.731" y1="0" x2="11.557" y2="0" width="0.127" layer="21"/>
<pad name="1" x="-13.716" y="0" drill="1.1938" shape="octagon"/>
<pad name="2" x="13.716" y="0" drill="1.1938" shape="octagon"/>
<text x="-5.08" y="0.762" size="1.778" layer="25" ratio="10">&gt;NAME</text>
<text x="-5.08" y="-2.54" size="1.778" layer="27" ratio="10">&gt;VALUE</text>
</package>
<package name="C275-113X316">
<description>Capacitor&lt;p&gt;
Grid  27.5 mm Outline 11.3 x 31.6 mm</description>
<wire x1="-15.24" y1="5.588" x2="15.24" y2="5.588" width="0.127" layer="21"/>
<wire x1="15.748" y1="5.08" x2="15.748" y2="-5.08" width="0.127" layer="21"/>
<wire x1="15.24" y1="-5.588" x2="-15.24" y2="-5.588" width="0.127" layer="21"/>
<wire x1="-15.748" y1="-5.08" x2="-15.748" y2="5.08" width="0.127" layer="21"/>
<wire x1="-6.731" y1="1.905" x2="-6.731" y2="0" width="0.4064" layer="21"/>
<wire x1="-6.731" y1="0" x2="-6.731" y2="-1.905" width="0.4064" layer="21"/>
<wire x1="-7.62" y1="1.905" x2="-7.62" y2="0" width="0.4064" layer="21"/>
<wire x1="-7.62" y1="0" x2="-7.62" y2="-1.905" width="0.4064" layer="21"/>
<wire x1="15.24" y1="5.588" x2="15.748" y2="5.08" width="0.127" layer="21" curve="-90"/>
<wire x1="15.24" y1="-5.588" x2="15.748" y2="-5.08" width="0.127" layer="21" curve="90"/>
<wire x1="-15.748" y1="-5.08" x2="-15.24" y2="-5.588" width="0.127" layer="21" curve="90"/>
<wire x1="-15.748" y1="5.08" x2="-15.24" y2="5.588" width="0.127" layer="21" curve="-90"/>
<wire x1="-11.557" y1="0" x2="-7.62" y2="0" width="0.127" layer="21"/>
<wire x1="-6.731" y1="0" x2="11.557" y2="0" width="0.127" layer="21"/>
<pad name="1" x="-13.716" y="0" drill="1.1938" shape="octagon"/>
<pad name="2" x="13.716" y="0" drill="1.1938" shape="octagon"/>
<text x="-5.08" y="0.762" size="1.778" layer="25" ratio="10">&gt;NAME</text>
<text x="-5.08" y="-2.54" size="1.778" layer="27" ratio="10">&gt;VALUE</text>
</package>
<package name="C275-134X316">
<description>Capacitor&lt;p&gt;
Grid  27.5 mm Outline 13.4 x 31.6 mm</description>
<wire x1="-15.24" y1="6.604" x2="15.24" y2="6.604" width="0.127" layer="21"/>
<wire x1="15.748" y1="6.096" x2="15.748" y2="-6.096" width="0.127" layer="21"/>
<wire x1="15.24" y1="-6.604" x2="-15.24" y2="-6.604" width="0.127" layer="21"/>
<wire x1="-15.748" y1="-6.096" x2="-15.748" y2="6.096" width="0.127" layer="21"/>
<wire x1="-6.731" y1="1.905" x2="-6.731" y2="0" width="0.4064" layer="21"/>
<wire x1="-6.731" y1="0" x2="-6.731" y2="-1.905" width="0.4064" layer="21"/>
<wire x1="-7.62" y1="1.905" x2="-7.62" y2="0" width="0.4064" layer="21"/>
<wire x1="-7.62" y1="0" x2="-7.62" y2="-1.905" width="0.4064" layer="21"/>
<wire x1="15.24" y1="6.604" x2="15.748" y2="6.096" width="0.127" layer="21" curve="-90"/>
<wire x1="15.24" y1="-6.604" x2="15.748" y2="-6.096" width="0.127" layer="21" curve="90"/>
<wire x1="-15.748" y1="-6.096" x2="-15.24" y2="-6.604" width="0.127" layer="21" curve="90"/>
<wire x1="-15.748" y1="6.096" x2="-15.24" y2="6.604" width="0.127" layer="21" curve="-90"/>
<wire x1="-11.557" y1="0" x2="-7.62" y2="0" width="0.127" layer="21"/>
<wire x1="-6.731" y1="0" x2="11.557" y2="0" width="0.127" layer="21"/>
<pad name="1" x="-13.716" y="0" drill="1.1938" shape="octagon"/>
<pad name="2" x="13.716" y="0" drill="1.1938" shape="octagon"/>
<text x="-5.08" y="0.762" size="1.778" layer="25" ratio="10">&gt;NAME</text>
<text x="-5.08" y="-2.54" size="1.778" layer="27" ratio="10">&gt;VALUE</text>
</package>
<package name="C275-205X316">
<description>Capacitor&lt;p&gt;
Grid  27.5 mm Outline 20.5 x 31.6 mm</description>
<wire x1="-15.24" y1="10.16" x2="15.24" y2="10.16" width="0.127" layer="21"/>
<wire x1="15.748" y1="9.652" x2="15.748" y2="-9.652" width="0.127" layer="21"/>
<wire x1="15.24" y1="-10.16" x2="-15.24" y2="-10.16" width="0.127" layer="21"/>
<wire x1="-15.748" y1="-9.652" x2="-15.748" y2="9.652" width="0.127" layer="21"/>
<wire x1="-6.731" y1="1.905" x2="-6.731" y2="0" width="0.4064" layer="21"/>
<wire x1="-6.731" y1="0" x2="-6.731" y2="-1.905" width="0.4064" layer="21"/>
<wire x1="-7.62" y1="1.905" x2="-7.62" y2="0" width="0.4064" layer="21"/>
<wire x1="-7.62" y1="0" x2="-7.62" y2="-1.905" width="0.4064" layer="21"/>
<wire x1="15.24" y1="10.16" x2="15.748" y2="9.652" width="0.127" layer="21" curve="-90"/>
<wire x1="15.24" y1="-10.16" x2="15.748" y2="-9.652" width="0.127" layer="21" curve="90"/>
<wire x1="-15.748" y1="-9.652" x2="-15.24" y2="-10.16" width="0.127" layer="21" curve="90"/>
<wire x1="-15.748" y1="9.652" x2="-15.24" y2="10.16" width="0.127" layer="21" curve="-90"/>
<wire x1="-11.557" y1="0" x2="-7.62" y2="0" width="0.127" layer="21"/>
<wire x1="-6.731" y1="0" x2="11.557" y2="0" width="0.127" layer="21"/>
<pad name="1" x="-13.716" y="0" drill="1.1938" shape="octagon"/>
<pad name="2" x="13.716" y="0" drill="1.1938" shape="octagon"/>
<text x="-5.08" y="2.54" size="1.778" layer="25" ratio="10">&gt;NAME</text>
<text x="-5.08" y="-4.318" size="1.778" layer="27" ratio="10">&gt;VALUE</text>
</package>
<package name="C325-137X374">
<description>Capacitor&lt;p&gt;
Grid  32.5 mm Outline 13.7 x 37.4 mm</description>
<wire x1="-14.2748" y1="0" x2="-12.7" y2="0" width="0.127" layer="21"/>
<wire x1="-12.7" y1="1.905" x2="-12.7" y2="0" width="0.4064" layer="21"/>
<wire x1="-11.811" y1="1.905" x2="-11.811" y2="0" width="0.4064" layer="21"/>
<wire x1="-11.811" y1="0" x2="14.2748" y2="0" width="0.127" layer="21"/>
<wire x1="-11.811" y1="0" x2="-11.811" y2="-1.905" width="0.4064" layer="21"/>
<wire x1="-12.7" y1="0" x2="-12.7" y2="-1.905" width="0.4064" layer="21"/>
<wire x1="18.542" y1="6.731" x2="18.542" y2="-6.731" width="0.127" layer="21"/>
<wire x1="-18.542" y1="6.731" x2="-18.542" y2="-6.731" width="0.127" layer="21"/>
<wire x1="-18.542" y1="-6.731" x2="18.542" y2="-6.731" width="0.127" layer="21"/>
<wire x1="18.542" y1="6.731" x2="-18.542" y2="6.731" width="0.127" layer="21"/>
<pad name="1" x="-16.256" y="0" drill="1.1938" shape="octagon"/>
<pad name="2" x="16.256" y="0" drill="1.1938" shape="octagon"/>
<text x="-10.8712" y="0.9652" size="1.778" layer="25" ratio="10">&gt;NAME</text>
<text x="-10.8458" y="-2.8702" size="1.778" layer="27" ratio="10">&gt;VALUE</text>
</package>
<package name="C325-162X374">
<description>Capacitor&lt;p&gt;
Grid  32.5 mm Outline 16.2 x 37.4 mm</description>
<wire x1="-14.2748" y1="0" x2="-12.7" y2="0" width="0.127" layer="21"/>
<wire x1="-12.7" y1="1.905" x2="-12.7" y2="0" width="0.4064" layer="21"/>
<wire x1="-11.811" y1="1.905" x2="-11.811" y2="0" width="0.4064" layer="21"/>
<wire x1="-11.811" y1="0" x2="14.2748" y2="0" width="0.127" layer="21"/>
<wire x1="-11.811" y1="0" x2="-11.811" y2="-1.905" width="0.4064" layer="21"/>
<wire x1="-12.7" y1="0" x2="-12.7" y2="-1.905" width="0.4064" layer="21"/>
<wire x1="18.542" y1="8.001" x2="18.542" y2="-8.001" width="0.127" layer="21"/>
<wire x1="-18.542" y1="8.001" x2="-18.542" y2="-8.001" width="0.127" layer="21"/>
<wire x1="-18.542" y1="-8.001" x2="18.542" y2="-8.001" width="0.127" layer="21"/>
<wire x1="18.542" y1="8.001" x2="-18.542" y2="8.001" width="0.127" layer="21"/>
<pad name="1" x="-16.256" y="0" drill="1.1938" shape="octagon"/>
<pad name="2" x="16.256" y="0" drill="1.1938" shape="octagon"/>
<text x="-10.8712" y="0.9652" size="1.778" layer="25" ratio="10">&gt;NAME</text>
<text x="-10.8458" y="-2.8702" size="1.778" layer="27" ratio="10">&gt;VALUE</text>
</package>
<package name="C325-182X374">
<description>Capacitor&lt;p&gt;
Grid  32.5 mm Outline 18.2 x 37.4 mm</description>
<wire x1="-14.2748" y1="0" x2="-12.7" y2="0" width="0.127" layer="21"/>
<wire x1="-12.7" y1="1.905" x2="-12.7" y2="0" width="0.4064" layer="21"/>
<wire x1="-11.811" y1="1.905" x2="-11.811" y2="0" width="0.4064" layer="21"/>
<wire x1="-11.811" y1="0" x2="14.2748" y2="0" width="0.127" layer="21"/>
<wire x1="-11.811" y1="0" x2="-11.811" y2="-1.905" width="0.4064" layer="21"/>
<wire x1="-12.7" y1="0" x2="-12.7" y2="-1.905" width="0.4064" layer="21"/>
<wire x1="18.542" y1="9.017" x2="18.542" y2="-9.017" width="0.127" layer="21"/>
<wire x1="-18.542" y1="9.017" x2="-18.542" y2="-9.017" width="0.127" layer="21"/>
<wire x1="-18.542" y1="-9.017" x2="18.542" y2="-9.017" width="0.127" layer="21"/>
<wire x1="18.542" y1="9.017" x2="-18.542" y2="9.017" width="0.127" layer="21"/>
<pad name="1" x="-16.256" y="0" drill="1.1938" shape="octagon"/>
<pad name="2" x="16.256" y="0" drill="1.1938" shape="octagon"/>
<text x="-10.8712" y="0.9652" size="1.778" layer="25" ratio="10">&gt;NAME</text>
<text x="-10.8458" y="-2.8702" size="1.778" layer="27" ratio="10">&gt;VALUE</text>
</package>
<package name="C375-192X418">
<description>Capacitor&lt;p&gt;
Grid  37.5 mm Outline 19.2 x 41.8 mm</description>
<wire x1="-20.32" y1="8.509" x2="20.32" y2="8.509" width="0.127" layer="21"/>
<wire x1="20.828" y1="8.001" x2="20.828" y2="-8.001" width="0.127" layer="21"/>
<wire x1="20.32" y1="-8.509" x2="-20.32" y2="-8.509" width="0.127" layer="21"/>
<wire x1="-20.828" y1="-8.001" x2="-20.828" y2="8.001" width="0.127" layer="21"/>
<wire x1="-6.731" y1="1.905" x2="-6.731" y2="0" width="0.4064" layer="21"/>
<wire x1="-6.731" y1="0" x2="-6.731" y2="-1.905" width="0.4064" layer="21"/>
<wire x1="-7.62" y1="1.905" x2="-7.62" y2="0" width="0.4064" layer="21"/>
<wire x1="-7.62" y1="0" x2="-7.62" y2="-1.905" width="0.4064" layer="21"/>
<wire x1="20.32" y1="8.509" x2="20.828" y2="8.001" width="0.127" layer="21" curve="-90"/>
<wire x1="20.32" y1="-8.509" x2="20.828" y2="-8.001" width="0.127" layer="21" curve="90"/>
<wire x1="-20.828" y1="-8.001" x2="-20.32" y2="-8.509" width="0.127" layer="21" curve="90"/>
<wire x1="-20.828" y1="8.001" x2="-20.32" y2="8.509" width="0.127" layer="21" curve="-90"/>
<wire x1="-16.002" y1="0" x2="-7.62" y2="0" width="0.127" layer="21"/>
<wire x1="-6.731" y1="0" x2="16.002" y2="0" width="0.127" layer="21"/>
<pad name="1" x="-18.796" y="0" drill="1.3208" shape="octagon"/>
<pad name="2" x="18.796" y="0" drill="1.3208" shape="octagon"/>
<text x="-5.08" y="0.762" size="1.778" layer="25" ratio="10">&gt;NAME</text>
<text x="-5.08" y="-2.54" size="1.778" layer="27" ratio="10">&gt;VALUE</text>
</package>
<package name="C375-203X418">
<description>Capacitor&lt;p&gt;
Grid  37.5 mm Outline 20.3 x 41.8 mm</description>
<wire x1="-20.32" y1="10.16" x2="20.32" y2="10.16" width="0.127" layer="21"/>
<wire x1="20.828" y1="9.652" x2="20.828" y2="-9.652" width="0.127" layer="21"/>
<wire x1="20.32" y1="-10.16" x2="-20.32" y2="-10.16" width="0.127" layer="21"/>
<wire x1="-20.828" y1="-9.652" x2="-20.828" y2="9.652" width="0.127" layer="21"/>
<wire x1="-6.731" y1="1.905" x2="-6.731" y2="0" width="0.4064" layer="21"/>
<wire x1="-6.731" y1="0" x2="-6.731" y2="-1.905" width="0.4064" layer="21"/>
<wire x1="-7.62" y1="1.905" x2="-7.62" y2="0" width="0.4064" layer="21"/>
<wire x1="-7.62" y1="0" x2="-7.62" y2="-1.905" width="0.4064" layer="21"/>
<wire x1="20.32" y1="10.16" x2="20.828" y2="9.652" width="0.127" layer="21" curve="-90"/>
<wire x1="20.32" y1="-10.16" x2="20.828" y2="-9.652" width="0.127" layer="21" curve="90"/>
<wire x1="-20.828" y1="-9.652" x2="-20.32" y2="-10.16" width="0.127" layer="21" curve="90"/>
<wire x1="-20.828" y1="9.652" x2="-20.32" y2="10.16" width="0.127" layer="21" curve="-90"/>
<wire x1="-16.002" y1="0" x2="-7.62" y2="0" width="0.127" layer="21"/>
<wire x1="-6.731" y1="0" x2="16.002" y2="0" width="0.127" layer="21"/>
<pad name="1" x="-18.796" y="0" drill="1.3208" shape="octagon"/>
<pad name="2" x="18.796" y="0" drill="1.3208" shape="octagon"/>
<text x="-5.08" y="0.762" size="1.778" layer="25" ratio="10">&gt;NAME</text>
<text x="-5.08" y="-2.54" size="1.778" layer="27" ratio="10">&gt;VALUE</text>
</package>
<package name="C050-035X075">
<description>Capacitor&lt;p&gt;
Grid  5 mm Outline 3.5 x 7.5 mm</description>
<wire x1="-0.3048" y1="0.635" x2="-0.3048" y2="0" width="0.3048" layer="21"/>
<wire x1="-0.3048" y1="0" x2="-0.3048" y2="-0.635" width="0.3048" layer="21"/>
<wire x1="-0.3048" y1="0" x2="-1.524" y2="0" width="0.127" layer="21"/>
<wire x1="0.3302" y1="0.635" x2="0.3302" y2="0" width="0.3048" layer="21"/>
<wire x1="0.3302" y1="0" x2="0.3302" y2="-0.635" width="0.3048" layer="21"/>
<wire x1="0.3302" y1="0" x2="1.524" y2="0" width="0.127" layer="21"/>
<wire x1="-3.683" y1="1.524" x2="-3.683" y2="-1.524" width="0.127" layer="21"/>
<wire x1="-3.429" y1="-1.778" x2="3.429" y2="-1.778" width="0.127" layer="21"/>
<wire x1="3.683" y1="-1.524" x2="3.683" y2="1.524" width="0.127" layer="21"/>
<wire x1="3.429" y1="1.778" x2="-3.429" y2="1.778" width="0.127" layer="21"/>
<wire x1="3.429" y1="1.778" x2="3.683" y2="1.524" width="0.127" layer="21" curve="-90"/>
<wire x1="3.429" y1="-1.778" x2="3.683" y2="-1.524" width="0.127" layer="21" curve="90"/>
<wire x1="-3.683" y1="-1.524" x2="-3.429" y2="-1.778" width="0.127" layer="21" curve="90"/>
<wire x1="-3.683" y1="1.524" x2="-3.429" y2="1.778" width="0.127" layer="21" curve="-90"/>
<pad name="1" x="-2.54" y="0" drill="0.8128" shape="octagon"/>
<pad name="2" x="2.54" y="0" drill="0.8128" shape="octagon"/>
<text x="4.318" y="0.254" size="1.27" layer="25" ratio="10">&gt;NAME</text>
<text x="4.318" y="-1.524" size="1.27" layer="27" ratio="10">&gt;VALUE</text>
</package>
<package name="C375-155X418">
<description>Capacitor&lt;p&gt;
Grid  37.5 mm Outline 15.5 x 41.8 mm</description>
<wire x1="-20.32" y1="7.62" x2="20.32" y2="7.62" width="0.127" layer="21"/>
<wire x1="20.828" y1="7.112" x2="20.828" y2="-7.112" width="0.127" layer="21"/>
<wire x1="20.32" y1="-7.62" x2="-20.32" y2="-7.62" width="0.127" layer="21"/>
<wire x1="-20.828" y1="-7.112" x2="-20.828" y2="7.112" width="0.127" layer="21"/>
<wire x1="-6.731" y1="1.905" x2="-6.731" y2="0" width="0.4064" layer="21"/>
<wire x1="-6.731" y1="0" x2="-6.731" y2="-1.905" width="0.4064" layer="21"/>
<wire x1="-7.62" y1="1.905" x2="-7.62" y2="0" width="0.4064" layer="21"/>
<wire x1="-7.62" y1="0" x2="-7.62" y2="-1.905" width="0.4064" layer="21"/>
<wire x1="20.32" y1="7.62" x2="20.828" y2="7.112" width="0.127" layer="21" curve="-90"/>
<wire x1="20.32" y1="-7.62" x2="20.828" y2="-7.112" width="0.127" layer="21" curve="90"/>
<wire x1="-20.828" y1="-7.112" x2="-20.32" y2="-7.62" width="0.127" layer="21" curve="90"/>
<wire x1="-20.828" y1="7.112" x2="-20.32" y2="7.62" width="0.127" layer="21" curve="-90"/>
<wire x1="-16.002" y1="0" x2="-7.62" y2="0" width="0.127" layer="21"/>
<wire x1="-6.731" y1="0" x2="16.002" y2="0" width="0.127" layer="21"/>
<pad name="1" x="-18.796" y="0" drill="1.3208" shape="octagon"/>
<pad name="2" x="18.796" y="0" drill="1.3208" shape="octagon"/>
<text x="-5.08" y="0.762" size="1.778" layer="25" ratio="10">&gt;NAME</text>
<text x="-5.08" y="-2.54" size="1.778" layer="27" ratio="10">&gt;VALUE</text>
</package>
<package name="C075-063X106">
<description>Capacitor&lt;p&gt;
Grid  7.5 mm Outline 6.3 x 10.6 mm</description>
<wire x1="4.953" y1="3.048" x2="-4.953" y2="3.048" width="0.127" layer="21"/>
<wire x1="-5.207" y1="2.794" x2="-5.207" y2="-2.794" width="0.127" layer="21"/>
<wire x1="-4.953" y1="-3.048" x2="4.953" y2="-3.048" width="0.127" layer="21"/>
<wire x1="5.207" y1="-2.794" x2="5.207" y2="2.794" width="0.127" layer="21"/>
<wire x1="4.953" y1="3.048" x2="5.207" y2="2.794" width="0.127" layer="21" curve="-90"/>
<wire x1="4.953" y1="-3.048" x2="5.207" y2="-2.794" width="0.127" layer="21" curve="90"/>
<wire x1="-5.207" y1="-2.794" x2="-4.953" y2="-3.048" width="0.127" layer="21" curve="90"/>
<wire x1="-5.207" y1="2.794" x2="-4.953" y2="3.048" width="0.127" layer="21" curve="-90"/>
<wire x1="-1.27" y1="0" x2="2.667" y2="0" width="0.127" layer="21"/>
<wire x1="-2.667" y1="0" x2="-2.159" y2="0" width="0.127" layer="21"/>
<wire x1="-2.159" y1="1.27" x2="-2.159" y2="0" width="0.4064" layer="21"/>
<wire x1="-2.159" y1="0" x2="-2.159" y2="-1.27" width="0.4064" layer="21"/>
<wire x1="-1.27" y1="1.27" x2="-1.27" y2="0" width="0.4064" layer="21"/>
<wire x1="-1.27" y1="0" x2="-1.27" y2="-1.27" width="0.4064" layer="21"/>
<pad name="1" x="-3.81" y="0" drill="0.9144" shape="octagon"/>
<pad name="2" x="3.81" y="0" drill="0.9144" shape="octagon"/>
<text x="-0.635" y="1.27" size="1.27" layer="25" ratio="10">&gt;NAME</text>
<text x="-0.635" y="-2.54" size="1.27" layer="27" ratio="10">&gt;VALUE</text>
</package>
<package name="C275-154X316">
<description>Capacitor&lt;p&gt;
Grid  27.5 mm Outline 15.4 x 31.6 mm</description>
<wire x1="-15.24" y1="7.62" x2="15.24" y2="7.62" width="0.127" layer="21"/>
<wire x1="15.748" y1="7.112" x2="15.748" y2="-7.112" width="0.127" layer="21"/>
<wire x1="15.24" y1="-7.62" x2="-15.24" y2="-7.62" width="0.127" layer="21"/>
<wire x1="-15.748" y1="-7.112" x2="-15.748" y2="7.112" width="0.127" layer="21"/>
<wire x1="-6.731" y1="1.905" x2="-6.731" y2="0" width="0.4064" layer="21"/>
<wire x1="-6.731" y1="0" x2="-6.731" y2="-1.905" width="0.4064" layer="21"/>
<wire x1="-7.62" y1="1.905" x2="-7.62" y2="0" width="0.4064" layer="21"/>
<wire x1="-7.62" y1="0" x2="-7.62" y2="-1.905" width="0.4064" layer="21"/>
<wire x1="15.24" y1="7.62" x2="15.748" y2="7.112" width="0.127" layer="21" curve="-90"/>
<wire x1="15.24" y1="-7.62" x2="15.748" y2="-7.112" width="0.127" layer="21" curve="90"/>
<wire x1="-15.748" y1="-7.112" x2="-15.24" y2="-7.62" width="0.127" layer="21" curve="90"/>
<wire x1="-15.748" y1="7.112" x2="-15.24" y2="7.62" width="0.127" layer="21" curve="-90"/>
<wire x1="-11.557" y1="0" x2="-7.62" y2="0" width="0.127" layer="21"/>
<wire x1="-6.731" y1="0" x2="11.557" y2="0" width="0.127" layer="21"/>
<pad name="1" x="-13.716" y="0" drill="1.1938" shape="octagon"/>
<pad name="2" x="13.716" y="0" drill="1.1938" shape="octagon"/>
<text x="-5.08" y="0.762" size="1.778" layer="25" ratio="10">&gt;NAME</text>
<text x="-5.08" y="-2.54" size="1.778" layer="27" ratio="10">&gt;VALUE</text>
</package>
<package name="C275-173X316">
<description>Capacitor&lt;p&gt;
Grid  27.5 mm Outline 17.3 x 31.6 mm</description>
<wire x1="-15.24" y1="8.509" x2="15.24" y2="8.509" width="0.127" layer="21"/>
<wire x1="15.748" y1="8.001" x2="15.748" y2="-8.001" width="0.127" layer="21"/>
<wire x1="15.24" y1="-8.509" x2="-15.24" y2="-8.509" width="0.127" layer="21"/>
<wire x1="-15.748" y1="-8.001" x2="-15.748" y2="8.001" width="0.127" layer="21"/>
<wire x1="-6.731" y1="1.905" x2="-6.731" y2="0" width="0.4064" layer="21"/>
<wire x1="-6.731" y1="0" x2="-6.731" y2="-1.905" width="0.4064" layer="21"/>
<wire x1="-7.62" y1="1.905" x2="-7.62" y2="0" width="0.4064" layer="21"/>
<wire x1="-7.62" y1="0" x2="-7.62" y2="-1.905" width="0.4064" layer="21"/>
<wire x1="15.24" y1="8.509" x2="15.748" y2="8.001" width="0.127" layer="21" curve="-90"/>
<wire x1="15.24" y1="-8.509" x2="15.748" y2="-8.001" width="0.127" layer="21" curve="90"/>
<wire x1="-15.748" y1="-8.001" x2="-15.24" y2="-8.509" width="0.127" layer="21" curve="90"/>
<wire x1="-15.748" y1="8.001" x2="-15.24" y2="8.509" width="0.127" layer="21" curve="-90"/>
<wire x1="-11.557" y1="0" x2="-7.62" y2="0" width="0.127" layer="21"/>
<wire x1="-6.731" y1="0" x2="11.557" y2="0" width="0.127" layer="21"/>
<pad name="1" x="-13.716" y="0" drill="1.1938" shape="octagon"/>
<pad name="2" x="13.716" y="0" drill="1.1938" shape="octagon"/>
<text x="-5.08" y="0.762" size="1.778" layer="25" ratio="10">&gt;NAME</text>
<text x="-5.08" y="-2.54" size="1.778" layer="27" ratio="10">&gt;VALUE</text>
</package>
</packages>
<symbols>
<symbol name="R-EU">
<wire x1="-2.54" y1="-0.889" x2="2.54" y2="-0.889" width="0.254" layer="94"/>
<wire x1="2.54" y1="0.889" x2="-2.54" y2="0.889" width="0.254" layer="94"/>
<wire x1="2.54" y1="-0.889" x2="2.54" y2="0.889" width="0.254" layer="94"/>
<wire x1="-2.54" y1="-0.889" x2="-2.54" y2="0.889" width="0.254" layer="94"/>
<text x="-3.81" y="1.4986" size="1.778" layer="95">&gt;NAME</text>
<text x="-3.81" y="-3.302" size="1.778" layer="96">&gt;VALUE</text>
<pin name="2" x="5.08" y="0" visible="off" length="short" direction="pas" swaplevel="1" rot="R180"/>
<pin name="1" x="-5.08" y="0" visible="off" length="short" direction="pas" swaplevel="1"/>
</symbol>
<symbol name="C-EU">
<wire x1="0" y1="-2.54" x2="0" y2="-2.032" width="0.1524" layer="94"/>
<wire x1="0" y1="0" x2="0" y2="-0.508" width="0.1524" layer="94"/>
<text x="1.524" y="0.381" size="1.778" layer="95">&gt;NAME</text>
<text x="1.524" y="-4.699" size="1.778" layer="96">&gt;VALUE</text>
<rectangle x1="-2.032" y1="-1.016" x2="2.032" y2="-0.508" layer="94"/>
<rectangle x1="-2.032" y1="-2.032" x2="2.032" y2="-1.524" layer="94"/>
<pin name="1" x="0" y="-5.08" visible="off" length="short" direction="pas" swaplevel="1" rot="R90"/>
<pin name="2" x="0" y="2.54" visible="off" length="short" direction="pas" swaplevel="1" rot="R270"/>
</symbol>
</symbols>
<devicesets>
<deviceset name="R-EU_" prefix="R" uservalue="yes">
<description>Resistor&lt;p&gt;
&lt;i&gt;&lt;b&gt;EU&lt;/b&gt;rop Symbol&lt;/i&gt;</description>
<gates>
<gate name="G$1" symbol="R-EU" x="0" y="0"/>
</gates>
<devices>
<device name="R0402" package="R0402">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="R0603" package="R0603">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="R0805" package="R0805">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="R0805W" package="R0805W">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="R1005" package="R1005">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="R1206" package="R1206">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="R1206W" package="R1206W">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="R1210" package="R1210">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="R1210W" package="R1210W">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="R2010" package="R2010">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="R2010W" package="R2010W">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="R2012" package="R2012">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="R2012W" package="R2012W">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="R2512" package="R2512">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="R2512W" package="R2512W">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="R3216" package="R3216">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="R3216W" package="R3216W">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="R3225" package="R3225">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="R3225W" package="R3225W">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="R5025" package="R5025">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="R5025W" package="R5025W">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="R6332" package="R6332">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="R6332W" package="R6332W">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="M0805" package="M0805">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="M1206" package="M1206">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="M1406" package="M1406">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="M2012" package="M2012">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="M2309" package="M2309">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="M3216" package="M3216">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="M3516" package="M3516">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="M5923" package="M5923">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="0204/5" package="0204/5">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="0204/7" package="0204/7">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="0204/V2" package="0204V">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="0207/10" package="0207/10">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="0207/12" package="0207/12">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="0207/15" package="0207/15">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="0207/2V" package="0207/2V">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="0207/5V" package="0207/5V">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="0207/7" package="0207/7">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="0309/10" package="0309/10">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="0309/12" package="0309/12">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="0309/2V" package="0309V">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="0411/12" package="0411/12">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="0411/15" package="0411/15">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="0411/3V" package="0411V">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="0414/15" package="0414/15">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="0414/5V" package="0414V">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="0617/17" package="0617/17">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="0617/22" package="0617/22">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="0617/5V" package="0617V">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="0922/22" package="0922/22">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="0613/5V" package="P0613V">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="0613/15" package="P0613/15">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="0817/22" package="P0817/22">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="0817/7V" package="P0817V">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="V234/12" package="V234/12">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="V235/17" package="V235/17">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="V526-0" package="V526-0">
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
<deviceset name="C-EU" prefix="C" uservalue="yes">
<description>Capacitor&lt;p&gt;
&lt;i&gt;&lt;b&gt;EU&lt;/b&gt;rop Symbol&lt;/i&gt;</description>
<gates>
<gate name="G$1" symbol="C-EU" x="0" y="0"/>
</gates>
<devices>
<device name="C0402" package="C0402">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="C0504" package="C0504">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="C0603" package="C0603">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="C0805" package="C0805">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="C1005" package="C1005">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="C1206" package="C1206">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="C1210" package="C1210">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="C1310" package="C1310">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="C1608" package="C1608">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="C1812" package="C1812">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="C1825" package="C1825">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="C2012" package="C2012">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="C3216" package="C3216">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="C3225" package="C3225">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="C4532" package="C4532">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="C4564" package="C4564">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="025-024X044" package="C025-024X044">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="025-025X050" package="C025-025X050">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="025-030X050" package="C025-030X050">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="025-040X050" package="C025-040X050">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="025-050X050" package="C025-050X050">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="025-060X050" package="C025-060X050">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="C025_050-024X070" package="C025_050-024X070">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="025_050-025X075" package="C025_050-025X075">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="025_050-035X075" package="C025_050-035X075">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="025_050-045X075" package="C025_050-045X075">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="025_050-055X075" package="C025_050-055X075">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="050-024X044" package="C050-024X044">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="050-025X075" package="C050-025X075">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="050-045X075" package="C050-045X075">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="050-030X075" package="C050-030X075">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="050-050X075" package="C050-050X075">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="050-055X075" package="C050-055X075">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="050-075X075" package="C050-075X075">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="050H075X075" package="C050H075X075">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="075-032X103" package="C075-032X103">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="075-042X103" package="C075-042X103">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="075-052X106" package="C075-052X106">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="102-043X133" package="C102-043X133">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="102-054X133" package="C102-054X133">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="102-064X133" package="C102-064X133">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="102_152-062X184" package="C102_152-062X184">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="150-054X183" package="C150-054X183">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="150-064X183" package="C150-064X183">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="150-072X183" package="C150-072X183">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="150-084X183" package="C150-084X183">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="150-091X182" package="C150-091X182">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="225-062X268" package="C225-062X268">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="225-074X268" package="C225-074X268">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="225-087X268" package="C225-087X268">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="225-108X268" package="C225-108X268">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="225-113X268" package="C225-113X268">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="275-093X316" package="C275-093X316">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="275-113X316" package="C275-113X316">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="275-134X316" package="C275-134X316">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="275-205X316" package="C275-205X316">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="325-137X374" package="C325-137X374">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="325-162X374" package="C325-162X374">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="325-182X374" package="C325-182X374">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="375-192X418" package="C375-192X418">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="375-203X418" package="C375-203X418">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="050-035X075" package="C050-035X075">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="375-155X418" package="C375-155X418">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="075-063X106" package="C075-063X106">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="275-154X316" package="C275-154X316">
<connects>
<connect gate="G$1" pin="1" pad="1"/>
<connect gate="G$1" pin="2" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="275-173X316" package="C275-173X316">
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
<library name="diode">
<packages>
<package name="DO35-10">
<description>Diode&lt;p&gt;
Diameter 2 mm horizontal Grid 10.16 mm</description>
<wire x1="5.08" y1="0" x2="4.191" y2="0" width="0.508" layer="51"/>
<wire x1="-5.08" y1="0" x2="-4.191" y2="0" width="0.508" layer="51"/>
<wire x1="-0.635" y1="0" x2="0" y2="0" width="0.127" layer="21"/>
<wire x1="1.016" y1="0.635" x2="1.016" y2="-0.635" width="0.127" layer="21"/>
<wire x1="1.016" y1="-0.635" x2="0" y2="0" width="0.127" layer="21"/>
<wire x1="0" y1="0" x2="1.524" y2="0" width="0.127" layer="21"/>
<wire x1="0" y1="0" x2="1.016" y2="0.635" width="0.127" layer="21"/>
<wire x1="0" y1="0.635" x2="0" y2="0" width="0.127" layer="21"/>
<wire x1="0" y1="0" x2="0" y2="-0.635" width="0.127" layer="21"/>
<wire x1="2.032" y1="1.016" x2="2.286" y2="0.762" width="0.127" layer="21" curve="-90"/>
<wire x1="-2.286" y1="0.762" x2="-2.032" y2="1.016" width="0.127" layer="21" curve="-90"/>
<wire x1="-2.286" y1="-0.762" x2="-2.032" y2="-1.016" width="0.127" layer="21" curve="90"/>
<wire x1="2.032" y1="-1.016" x2="2.286" y2="-0.762" width="0.127" layer="21" curve="90"/>
<wire x1="2.286" y1="-0.762" x2="2.286" y2="0.762" width="0.127" layer="21"/>
<wire x1="-2.286" y1="0.762" x2="-2.286" y2="-0.762" width="0.127" layer="21"/>
<wire x1="-2.032" y1="1.016" x2="2.032" y2="1.016" width="0.127" layer="21"/>
<wire x1="-2.032" y1="-1.016" x2="2.032" y2="-1.016" width="0.127" layer="21"/>
<pad name="K" x="-5.08" y="0" drill="0.8128" diameter="1.6002"/>
<pad name="A" x="5.08" y="0" drill="0.8128" diameter="1.6002" shape="octagon"/>
<text x="6.223" y="-0.254" size="1.27" layer="25" ratio="10">&gt;NAME</text>
<text x="6.223" y="-1.905" size="1.27" layer="27" ratio="10">&gt;VALUE</text>
<rectangle x1="-1.905" y1="-1.016" x2="-1.397" y2="1.016" layer="21"/>
<rectangle x1="2.286" y1="-0.254" x2="4.191" y2="0.254" layer="21"/>
<rectangle x1="-4.191" y1="-0.254" x2="-2.286" y2="0.254" layer="21"/>
</package>
<package name="SMB">
<wire x1="-2.2606" y1="1.905" x2="2.2606" y2="1.905" width="0.1" layer="21"/>
<wire x1="-2.2606" y1="-1.905" x2="2.2606" y2="-1.905" width="0.1" layer="21"/>
<wire x1="-2.2606" y1="-1.905" x2="-2.2606" y2="1.905" width="0.1" layer="51"/>
<wire x1="2.2606" y1="-1.905" x2="2.2606" y2="1.905" width="0.1" layer="51"/>
<wire x1="0.6429" y1="1" x2="-0.73" y2="0" width="0.1998" layer="21"/>
<wire x1="-0.73" y1="0" x2="0.6429" y2="-1" width="0.1998" layer="21"/>
<wire x1="0.6429" y1="-1" x2="0.6429" y2="1" width="0.1998" layer="21"/>
<wire x1="-0.73" y1="1" x2="-0.73" y2="-1" width="0.1998" layer="21"/>
<smd name="1" x="-2.1999" y="0" dx="2.4" dy="2.4" layer="1"/>
<smd name="2" x="2.1999" y="0" dx="2.4" dy="2.4" layer="1"/>
<text x="-2.159" y="2.159" size="1.27" layer="25">&gt;NAME</text>
<text x="-1.905" y="-3.429" size="1.27" layer="27">&gt;VALUE</text>
<rectangle x1="-2.794" y1="-1.0922" x2="-2.2606" y2="1.0922" layer="51"/>
<rectangle x1="2.2606" y1="-1.0922" x2="2.794" y2="1.0922" layer="51"/>
</package>
</packages>
<symbols>
<symbol name="D">
<wire x1="-1.27" y1="-1.27" x2="1.27" y2="0" width="0.254" layer="94"/>
<wire x1="1.27" y1="0" x2="-1.27" y2="1.27" width="0.254" layer="94"/>
<wire x1="1.27" y1="1.27" x2="1.27" y2="0" width="0.254" layer="94"/>
<wire x1="-1.27" y1="1.27" x2="-1.27" y2="-1.27" width="0.254" layer="94"/>
<wire x1="1.27" y1="0" x2="1.27" y2="-1.27" width="0.254" layer="94"/>
<text x="2.54" y="0.4826" size="1.778" layer="95">&gt;NAME</text>
<text x="2.54" y="-2.3114" size="1.778" layer="96">&gt;VALUE</text>
<pin name="A" x="-2.54" y="0" visible="off" length="short" direction="pas"/>
<pin name="C" x="2.54" y="0" visible="off" length="short" direction="pas" rot="R180"/>
</symbol>
</symbols>
<devicesets>
<deviceset name="1N4148?" prefix="D">
<description>Diode&lt;p&gt;
High-speed diodes (Philips)</description>
<gates>
<gate name="G$1" symbol="D" x="0" y="0"/>
</gates>
<devices>
<device name="" package="DO35-10">
<connects>
<connect gate="G$1" pin="A" pad="A"/>
<connect gate="G$1" pin="C" pad="K"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
<device name="SMD" package="SMB">
<connects>
<connect gate="G$1" pin="A" pad="2"/>
<connect gate="G$1" pin="C" pad="1"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
</devices>
</deviceset>
</devicesets>
</library>
<library name="polcap">
<packages>
<package name="E2,5-6">
<description>Elco RM 2.54 mm / diameter 6 mm vertical</description>
<wire x1="-2.032" y1="1.27" x2="-1.651" y2="1.27" width="0.127" layer="21"/>
<wire x1="-1.651" y1="0.889" x2="-1.651" y2="1.27" width="0.127" layer="21"/>
<wire x1="-1.651" y1="1.27" x2="-1.27" y2="1.27" width="0.127" layer="21"/>
<wire x1="-1.651" y1="1.27" x2="-1.651" y2="1.651" width="0.127" layer="21"/>
<wire x1="-1.651" y1="0" x2="-0.762" y2="0" width="0.127" layer="51"/>
<wire x1="-0.762" y1="0" x2="-0.762" y2="-1.27" width="0.127" layer="51"/>
<wire x1="-0.762" y1="-1.27" x2="-0.254" y2="-1.27" width="0.127" layer="51"/>
<wire x1="-0.254" y1="-1.27" x2="-0.254" y2="1.27" width="0.127" layer="51"/>
<wire x1="-0.254" y1="1.27" x2="-0.762" y2="1.27" width="0.127" layer="51"/>
<wire x1="-0.762" y1="1.27" x2="-0.762" y2="0" width="0.127" layer="51"/>
<wire x1="0.635" y1="0" x2="1.651" y2="0" width="0.127" layer="51"/>
<circle x="0" y="0" radius="2.794" width="0.127" layer="21"/>
<pad name="-" x="1.27" y="0" drill="0.8128" diameter="1.6002" shape="octagon"/>
<pad name="+" x="-1.27" y="0" drill="0.8128" diameter="1.6002"/>
<text x="3.429" y="0.508" size="1.27" layer="25" ratio="10">&gt;NAME</text>
<text x="3.429" y="-1.27" size="1.27" layer="27" ratio="10">&gt;VALUE</text>
<rectangle x1="0.254" y1="-1.27" x2="0.762" y2="1.27" layer="51"/>
</package>
</packages>
<symbols>
<symbol name="ELKO">
<wire x1="-1.524" y1="1.651" x2="1.524" y2="1.651" width="0.2032" layer="94"/>
<wire x1="1.524" y1="1.651" x2="1.524" y2="2.413" width="0.2032" layer="94"/>
<wire x1="-1.524" y1="2.413" x2="-1.524" y2="1.651" width="0.2032" layer="94"/>
<wire x1="-1.524" y1="2.413" x2="1.524" y2="2.413" width="0.2032" layer="94"/>
<wire x1="-1.8034" y1="3.3274" x2="-0.8636" y2="3.3274" width="0.1524" layer="94"/>
<wire x1="-1.3462" y1="2.8702" x2="-1.3462" y2="3.81" width="0.1524" layer="94"/>
<text x="2.159" y="0.7366" size="1.778" layer="95">&gt;NAME</text>
<text x="0.889" y="-2.0574" size="1.778" layer="96">&gt;VALUE</text>
<rectangle x1="-1.524" y1="0" x2="1.524" y2="0.762" layer="94"/>
<pin name="-" x="0" y="-2.54" visible="off" length="short" direction="pas" rot="R90"/>
<pin name="+" x="0" y="5.08" visible="off" length="short" direction="pas" rot="R270"/>
</symbol>
</symbols>
<devicesets>
<deviceset name="E2,5-6" prefix="C" uservalue="yes">
<gates>
<gate name="1" symbol="ELKO" x="0" y="0"/>
</gates>
<devices>
<device name="" package="E2,5-6">
<connects>
<connect gate="1" pin="+" pad="+"/>
<connect gate="1" pin="-" pad="-"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
</devices>
</deviceset>
</devicesets>
</library>
<library name="PINHEAD">
<packages>
<package name="1X20">
<wire x1="20.955" y1="1.27" x2="22.225" y2="1.27" width="0.127" layer="21"/>
<wire x1="22.225" y1="1.27" x2="22.86" y2="0.635" width="0.127" layer="21"/>
<wire x1="22.86" y1="0.635" x2="22.86" y2="-0.635" width="0.127" layer="21"/>
<wire x1="22.86" y1="-0.635" x2="22.225" y2="-1.27" width="0.127" layer="21"/>
<wire x1="17.78" y1="0.635" x2="18.415" y2="1.27" width="0.127" layer="21"/>
<wire x1="18.415" y1="1.27" x2="19.685" y2="1.27" width="0.127" layer="21"/>
<wire x1="19.685" y1="1.27" x2="20.32" y2="0.635" width="0.127" layer="21"/>
<wire x1="20.32" y1="0.635" x2="20.32" y2="-0.635" width="0.127" layer="21"/>
<wire x1="20.32" y1="-0.635" x2="19.685" y2="-1.27" width="0.127" layer="21"/>
<wire x1="19.685" y1="-1.27" x2="18.415" y2="-1.27" width="0.127" layer="21"/>
<wire x1="18.415" y1="-1.27" x2="17.78" y2="-0.635" width="0.127" layer="21"/>
<wire x1="20.955" y1="1.27" x2="20.32" y2="0.635" width="0.127" layer="21"/>
<wire x1="20.32" y1="-0.635" x2="20.955" y2="-1.27" width="0.127" layer="21"/>
<wire x1="22.225" y1="-1.27" x2="20.955" y2="-1.27" width="0.127" layer="21"/>
<wire x1="13.335" y1="1.27" x2="14.605" y2="1.27" width="0.127" layer="21"/>
<wire x1="14.605" y1="1.27" x2="15.24" y2="0.635" width="0.127" layer="21"/>
<wire x1="15.24" y1="0.635" x2="15.24" y2="-0.635" width="0.127" layer="21"/>
<wire x1="15.24" y1="-0.635" x2="14.605" y2="-1.27" width="0.127" layer="21"/>
<wire x1="15.24" y1="0.635" x2="15.875" y2="1.27" width="0.127" layer="21"/>
<wire x1="15.875" y1="1.27" x2="17.145" y2="1.27" width="0.127" layer="21"/>
<wire x1="17.145" y1="1.27" x2="17.78" y2="0.635" width="0.127" layer="21"/>
<wire x1="17.78" y1="0.635" x2="17.78" y2="-0.635" width="0.127" layer="21"/>
<wire x1="17.78" y1="-0.635" x2="17.145" y2="-1.27" width="0.127" layer="21"/>
<wire x1="17.145" y1="-1.27" x2="15.875" y2="-1.27" width="0.127" layer="21"/>
<wire x1="15.875" y1="-1.27" x2="15.24" y2="-0.635" width="0.127" layer="21"/>
<wire x1="10.16" y1="0.635" x2="10.795" y2="1.27" width="0.127" layer="21"/>
<wire x1="10.795" y1="1.27" x2="12.065" y2="1.27" width="0.127" layer="21"/>
<wire x1="12.065" y1="1.27" x2="12.7" y2="0.635" width="0.127" layer="21"/>
<wire x1="12.7" y1="0.635" x2="12.7" y2="-0.635" width="0.127" layer="21"/>
<wire x1="12.7" y1="-0.635" x2="12.065" y2="-1.27" width="0.127" layer="21"/>
<wire x1="12.065" y1="-1.27" x2="10.795" y2="-1.27" width="0.127" layer="21"/>
<wire x1="10.795" y1="-1.27" x2="10.16" y2="-0.635" width="0.127" layer="21"/>
<wire x1="13.335" y1="1.27" x2="12.7" y2="0.635" width="0.127" layer="21"/>
<wire x1="12.7" y1="-0.635" x2="13.335" y2="-1.27" width="0.127" layer="21"/>
<wire x1="14.605" y1="-1.27" x2="13.335" y2="-1.27" width="0.127" layer="21"/>
<wire x1="5.715" y1="1.27" x2="6.985" y2="1.27" width="0.127" layer="21"/>
<wire x1="6.985" y1="1.27" x2="7.62" y2="0.635" width="0.127" layer="21"/>
<wire x1="7.62" y1="0.635" x2="7.62" y2="-0.635" width="0.127" layer="21"/>
<wire x1="7.62" y1="-0.635" x2="6.985" y2="-1.27" width="0.127" layer="21"/>
<wire x1="7.62" y1="0.635" x2="8.255" y2="1.27" width="0.127" layer="21"/>
<wire x1="8.255" y1="1.27" x2="9.525" y2="1.27" width="0.127" layer="21"/>
<wire x1="9.525" y1="1.27" x2="10.16" y2="0.635" width="0.127" layer="21"/>
<wire x1="10.16" y1="0.635" x2="10.16" y2="-0.635" width="0.127" layer="21"/>
<wire x1="10.16" y1="-0.635" x2="9.525" y2="-1.27" width="0.127" layer="21"/>
<wire x1="9.525" y1="-1.27" x2="8.255" y2="-1.27" width="0.127" layer="21"/>
<wire x1="8.255" y1="-1.27" x2="7.62" y2="-0.635" width="0.127" layer="21"/>
<wire x1="2.54" y1="0.635" x2="3.175" y2="1.27" width="0.127" layer="21"/>
<wire x1="3.175" y1="1.27" x2="4.445" y2="1.27" width="0.127" layer="21"/>
<wire x1="4.445" y1="1.27" x2="5.08" y2="0.635" width="0.127" layer="21"/>
<wire x1="5.08" y1="0.635" x2="5.08" y2="-0.635" width="0.127" layer="21"/>
<wire x1="5.08" y1="-0.635" x2="4.445" y2="-1.27" width="0.127" layer="21"/>
<wire x1="4.445" y1="-1.27" x2="3.175" y2="-1.27" width="0.127" layer="21"/>
<wire x1="3.175" y1="-1.27" x2="2.54" y2="-0.635" width="0.127" layer="21"/>
<wire x1="5.715" y1="1.27" x2="5.08" y2="0.635" width="0.127" layer="21"/>
<wire x1="5.08" y1="-0.635" x2="5.715" y2="-1.27" width="0.127" layer="21"/>
<wire x1="6.985" y1="-1.27" x2="5.715" y2="-1.27" width="0.127" layer="21"/>
<wire x1="-1.905" y1="1.27" x2="-0.635" y2="1.27" width="0.127" layer="21"/>
<wire x1="-0.635" y1="1.27" x2="0" y2="0.635" width="0.127" layer="21"/>
<wire x1="0" y1="0.635" x2="0" y2="-0.635" width="0.127" layer="21"/>
<wire x1="0" y1="-0.635" x2="-0.635" y2="-1.27" width="0.127" layer="21"/>
<wire x1="0" y1="0.635" x2="0.635" y2="1.27" width="0.127" layer="21"/>
<wire x1="0.635" y1="1.27" x2="1.905" y2="1.27" width="0.127" layer="21"/>
<wire x1="1.905" y1="1.27" x2="2.54" y2="0.635" width="0.127" layer="21"/>
<wire x1="2.54" y1="0.635" x2="2.54" y2="-0.635" width="0.127" layer="21"/>
<wire x1="2.54" y1="-0.635" x2="1.905" y2="-1.27" width="0.127" layer="21"/>
<wire x1="1.905" y1="-1.27" x2="0.635" y2="-1.27" width="0.127" layer="21"/>
<wire x1="0.635" y1="-1.27" x2="0" y2="-0.635" width="0.127" layer="21"/>
<wire x1="-5.08" y1="0.635" x2="-4.445" y2="1.27" width="0.127" layer="21"/>
<wire x1="-4.445" y1="1.27" x2="-3.175" y2="1.27" width="0.127" layer="21"/>
<wire x1="-3.175" y1="1.27" x2="-2.54" y2="0.635" width="0.127" layer="21"/>
<wire x1="-2.54" y1="0.635" x2="-2.54" y2="-0.635" width="0.127" layer="21"/>
<wire x1="-2.54" y1="-0.635" x2="-3.175" y2="-1.27" width="0.127" layer="21"/>
<wire x1="-3.175" y1="-1.27" x2="-4.445" y2="-1.27" width="0.127" layer="21"/>
<wire x1="-4.445" y1="-1.27" x2="-5.08" y2="-0.635" width="0.127" layer="21"/>
<wire x1="-1.905" y1="1.27" x2="-2.54" y2="0.635" width="0.127" layer="21"/>
<wire x1="-2.54" y1="-0.635" x2="-1.905" y2="-1.27" width="0.127" layer="21"/>
<wire x1="-0.635" y1="-1.27" x2="-1.905" y2="-1.27" width="0.127" layer="21"/>
<wire x1="-9.525" y1="1.27" x2="-8.255" y2="1.27" width="0.127" layer="21"/>
<wire x1="-8.255" y1="1.27" x2="-7.62" y2="0.635" width="0.127" layer="21"/>
<wire x1="-7.62" y1="0.635" x2="-7.62" y2="-0.635" width="0.127" layer="21"/>
<wire x1="-7.62" y1="-0.635" x2="-8.255" y2="-1.27" width="0.127" layer="21"/>
<wire x1="-7.62" y1="0.635" x2="-6.985" y2="1.27" width="0.127" layer="21"/>
<wire x1="-6.985" y1="1.27" x2="-5.715" y2="1.27" width="0.127" layer="21"/>
<wire x1="-5.715" y1="1.27" x2="-5.08" y2="0.635" width="0.127" layer="21"/>
<wire x1="-5.08" y1="0.635" x2="-5.08" y2="-0.635" width="0.127" layer="21"/>
<wire x1="-5.08" y1="-0.635" x2="-5.715" y2="-1.27" width="0.127" layer="21"/>
<wire x1="-5.715" y1="-1.27" x2="-6.985" y2="-1.27" width="0.127" layer="21"/>
<wire x1="-6.985" y1="-1.27" x2="-7.62" y2="-0.635" width="0.127" layer="21"/>
<wire x1="-12.7" y1="0.635" x2="-12.065" y2="1.27" width="0.127" layer="21"/>
<wire x1="-12.065" y1="1.27" x2="-10.795" y2="1.27" width="0.127" layer="21"/>
<wire x1="-10.795" y1="1.27" x2="-10.16" y2="0.635" width="0.127" layer="21"/>
<wire x1="-10.16" y1="0.635" x2="-10.16" y2="-0.635" width="0.127" layer="21"/>
<wire x1="-10.16" y1="-0.635" x2="-10.795" y2="-1.27" width="0.127" layer="21"/>
<wire x1="-10.795" y1="-1.27" x2="-12.065" y2="-1.27" width="0.127" layer="21"/>
<wire x1="-12.065" y1="-1.27" x2="-12.7" y2="-0.635" width="0.127" layer="21"/>
<wire x1="-9.525" y1="1.27" x2="-10.16" y2="0.635" width="0.127" layer="21"/>
<wire x1="-10.16" y1="-0.635" x2="-9.525" y2="-1.27" width="0.127" layer="21"/>
<wire x1="-8.255" y1="-1.27" x2="-9.525" y2="-1.27" width="0.127" layer="21"/>
<wire x1="-17.145" y1="1.27" x2="-15.875" y2="1.27" width="0.127" layer="21"/>
<wire x1="-15.875" y1="1.27" x2="-15.24" y2="0.635" width="0.127" layer="21"/>
<wire x1="-15.24" y1="0.635" x2="-15.24" y2="-0.635" width="0.127" layer="21"/>
<wire x1="-15.24" y1="-0.635" x2="-15.875" y2="-1.27" width="0.127" layer="21"/>
<wire x1="-15.24" y1="0.635" x2="-14.605" y2="1.27" width="0.127" layer="21"/>
<wire x1="-14.605" y1="1.27" x2="-13.335" y2="1.27" width="0.127" layer="21"/>
<wire x1="-13.335" y1="1.27" x2="-12.7" y2="0.635" width="0.127" layer="21"/>
<wire x1="-12.7" y1="0.635" x2="-12.7" y2="-0.635" width="0.127" layer="21"/>
<wire x1="-12.7" y1="-0.635" x2="-13.335" y2="-1.27" width="0.127" layer="21"/>
<wire x1="-13.335" y1="-1.27" x2="-14.605" y2="-1.27" width="0.127" layer="21"/>
<wire x1="-14.605" y1="-1.27" x2="-15.24" y2="-0.635" width="0.127" layer="21"/>
<wire x1="-20.32" y1="0.635" x2="-19.685" y2="1.27" width="0.127" layer="21"/>
<wire x1="-19.685" y1="1.27" x2="-18.415" y2="1.27" width="0.127" layer="21"/>
<wire x1="-18.415" y1="1.27" x2="-17.78" y2="0.635" width="0.127" layer="21"/>
<wire x1="-17.78" y1="0.635" x2="-17.78" y2="-0.635" width="0.127" layer="21"/>
<wire x1="-17.78" y1="-0.635" x2="-18.415" y2="-1.27" width="0.127" layer="21"/>
<wire x1="-18.415" y1="-1.27" x2="-19.685" y2="-1.27" width="0.127" layer="21"/>
<wire x1="-19.685" y1="-1.27" x2="-20.32" y2="-0.635" width="0.127" layer="21"/>
<wire x1="-17.145" y1="1.27" x2="-17.78" y2="0.635" width="0.127" layer="21"/>
<wire x1="-17.78" y1="-0.635" x2="-17.145" y2="-1.27" width="0.127" layer="21"/>
<wire x1="-15.875" y1="-1.27" x2="-17.145" y2="-1.27" width="0.127" layer="21"/>
<wire x1="-24.765" y1="1.27" x2="-23.495" y2="1.27" width="0.127" layer="21"/>
<wire x1="-23.495" y1="1.27" x2="-22.86" y2="0.635" width="0.127" layer="21"/>
<wire x1="-22.86" y1="0.635" x2="-22.86" y2="-0.635" width="0.127" layer="21"/>
<wire x1="-22.86" y1="-0.635" x2="-23.495" y2="-1.27" width="0.127" layer="21"/>
<wire x1="-22.86" y1="0.635" x2="-22.225" y2="1.27" width="0.127" layer="21"/>
<wire x1="-22.225" y1="1.27" x2="-20.955" y2="1.27" width="0.127" layer="21"/>
<wire x1="-20.955" y1="1.27" x2="-20.32" y2="0.635" width="0.127" layer="21"/>
<wire x1="-20.32" y1="0.635" x2="-20.32" y2="-0.635" width="0.127" layer="21"/>
<wire x1="-20.32" y1="-0.635" x2="-20.955" y2="-1.27" width="0.127" layer="21"/>
<wire x1="-20.955" y1="-1.27" x2="-22.225" y2="-1.27" width="0.127" layer="21"/>
<wire x1="-22.225" y1="-1.27" x2="-22.86" y2="-0.635" width="0.127" layer="21"/>
<wire x1="-25.4" y1="0.635" x2="-25.4" y2="-0.635" width="0.127" layer="21"/>
<wire x1="-24.765" y1="1.27" x2="-25.4" y2="0.635" width="0.127" layer="21"/>
<wire x1="-25.4" y1="-0.635" x2="-24.765" y2="-1.27" width="0.127" layer="21"/>
<wire x1="-23.495" y1="-1.27" x2="-24.765" y2="-1.27" width="0.127" layer="21"/>
<wire x1="23.495" y1="1.27" x2="24.765" y2="1.27" width="0.127" layer="21"/>
<wire x1="24.765" y1="1.27" x2="25.4" y2="0.635" width="0.127" layer="21"/>
<wire x1="25.4" y1="0.635" x2="25.4" y2="-0.635" width="0.127" layer="21"/>
<wire x1="25.4" y1="-0.635" x2="24.765" y2="-1.27" width="0.127" layer="21"/>
<wire x1="23.495" y1="1.27" x2="22.86" y2="0.635" width="0.127" layer="21"/>
<wire x1="22.86" y1="-0.635" x2="23.495" y2="-1.27" width="0.127" layer="21"/>
<wire x1="24.765" y1="-1.27" x2="23.495" y2="-1.27" width="0.127" layer="21"/>
<pad name="1" x="-24.13" y="0" drill="1.016" diameter="1.5748" shape="octagon"/>
<pad name="2" x="-21.59" y="0" drill="1.016" diameter="1.5748" shape="octagon"/>
<pad name="3" x="-19.05" y="0" drill="1.016" diameter="1.5748" shape="octagon"/>
<pad name="4" x="-16.51" y="0" drill="1.016" diameter="1.5748" shape="octagon"/>
<pad name="5" x="-13.97" y="0" drill="1.016" diameter="1.5748" shape="octagon"/>
<pad name="6" x="-11.43" y="0" drill="1.016" diameter="1.5748" shape="octagon"/>
<pad name="7" x="-8.89" y="0" drill="1.016" diameter="1.5748" shape="octagon"/>
<pad name="8" x="-6.35" y="0" drill="1.016" diameter="1.5748" shape="octagon"/>
<pad name="9" x="-3.81" y="0" drill="1.016" diameter="1.5748" shape="octagon"/>
<pad name="10" x="-1.27" y="0" drill="1.016" diameter="1.5748" shape="octagon"/>
<pad name="11" x="1.27" y="0" drill="1.016" diameter="1.5748" shape="octagon"/>
<pad name="12" x="3.81" y="0" drill="1.016" diameter="1.5748" shape="octagon"/>
<pad name="13" x="6.35" y="0" drill="1.016" diameter="1.5748" shape="octagon"/>
<pad name="14" x="8.89" y="0" drill="1.016" diameter="1.5748" shape="octagon"/>
<pad name="15" x="11.43" y="0" drill="1.016" diameter="1.5748" shape="octagon"/>
<pad name="16" x="13.97" y="0" drill="1.016" diameter="1.5748" shape="octagon"/>
<pad name="17" x="16.51" y="0" drill="1.016" diameter="1.5748" shape="octagon"/>
<pad name="18" x="19.05" y="0" drill="1.016" diameter="1.5748" shape="octagon"/>
<pad name="19" x="21.59" y="0" drill="1.016" diameter="1.5748" shape="octagon"/>
<pad name="20" x="24.13" y="0" drill="1.016" diameter="1.5748" shape="octagon"/>
<text x="-25.4762" y="1.8288" size="1.27" layer="25" ratio="10">&gt;NAME</text>
<rectangle x1="21.336" y1="-0.254" x2="21.844" y2="0.254" layer="51"/>
<rectangle x1="18.796" y1="-0.254" x2="19.304" y2="0.254" layer="51"/>
<rectangle x1="16.256" y1="-0.254" x2="16.764" y2="0.254" layer="51"/>
<rectangle x1="13.716" y1="-0.254" x2="14.224" y2="0.254" layer="51"/>
<rectangle x1="11.176" y1="-0.254" x2="11.684" y2="0.254" layer="51"/>
<rectangle x1="8.636" y1="-0.254" x2="9.144" y2="0.254" layer="51"/>
<rectangle x1="6.096" y1="-0.254" x2="6.604" y2="0.254" layer="51"/>
<rectangle x1="3.556" y1="-0.254" x2="4.064" y2="0.254" layer="51"/>
<rectangle x1="1.016" y1="-0.254" x2="1.524" y2="0.254" layer="51"/>
<rectangle x1="-1.524" y1="-0.254" x2="-1.016" y2="0.254" layer="51"/>
<rectangle x1="-4.064" y1="-0.254" x2="-3.556" y2="0.254" layer="51"/>
<rectangle x1="-6.604" y1="-0.254" x2="-6.096" y2="0.254" layer="51"/>
<rectangle x1="-9.144" y1="-0.254" x2="-8.636" y2="0.254" layer="51"/>
<rectangle x1="-11.684" y1="-0.254" x2="-11.176" y2="0.254" layer="51"/>
<rectangle x1="-14.224" y1="-0.254" x2="-13.716" y2="0.254" layer="51"/>
<rectangle x1="-16.764" y1="-0.254" x2="-16.256" y2="0.254" layer="51"/>
<rectangle x1="-19.304" y1="-0.254" x2="-18.796" y2="0.254" layer="51"/>
<rectangle x1="-21.844" y1="-0.254" x2="-21.336" y2="0.254" layer="51"/>
<rectangle x1="-24.384" y1="-0.254" x2="-23.876" y2="0.254" layer="51"/>
<rectangle x1="23.876" y1="-0.254" x2="24.384" y2="0.254" layer="51"/>
</package>
</packages>
<symbols>
<symbol name="PINHD20">
<wire x1="-6.35" y1="-27.94" x2="1.27" y2="-27.94" width="0.4064" layer="94"/>
<wire x1="1.27" y1="-27.94" x2="1.27" y2="25.4" width="0.4064" layer="94"/>
<wire x1="1.27" y1="25.4" x2="-6.35" y2="25.4" width="0.4064" layer="94"/>
<wire x1="-6.35" y1="25.4" x2="-6.35" y2="-27.94" width="0.4064" layer="94"/>
<text x="-6.35" y="26.035" size="1.778" layer="95">&gt;NAME</text>
<text x="-6.35" y="-30.48" size="1.778" layer="96">&gt;VALUE</text>
<pin name="1" x="-2.54" y="22.86" visible="pad" length="short" direction="pas" function="dot"/>
<pin name="2" x="-2.54" y="20.32" visible="pad" length="short" direction="pas" function="dot"/>
<pin name="3" x="-2.54" y="17.78" visible="pad" length="short" direction="pas" function="dot"/>
<pin name="4" x="-2.54" y="15.24" visible="pad" length="short" direction="pas" function="dot"/>
<pin name="5" x="-2.54" y="12.7" visible="pad" length="short" direction="pas" function="dot"/>
<pin name="6" x="-2.54" y="10.16" visible="pad" length="short" direction="pas" function="dot"/>
<pin name="7" x="-2.54" y="7.62" visible="pad" length="short" direction="pas" function="dot"/>
<pin name="8" x="-2.54" y="5.08" visible="pad" length="short" direction="pas" function="dot"/>
<pin name="9" x="-2.54" y="2.54" visible="pad" length="short" direction="pas" function="dot"/>
<pin name="10" x="-2.54" y="0" visible="pad" length="short" direction="pas" function="dot"/>
<pin name="11" x="-2.54" y="-2.54" visible="pad" length="short" direction="pas" function="dot"/>
<pin name="12" x="-2.54" y="-5.08" visible="pad" length="short" direction="pas" function="dot"/>
<pin name="13" x="-2.54" y="-7.62" visible="pad" length="short" direction="pas" function="dot"/>
<pin name="14" x="-2.54" y="-10.16" visible="pad" length="short" direction="pas" function="dot"/>
<pin name="15" x="-2.54" y="-12.7" visible="pad" length="short" direction="pas" function="dot"/>
<pin name="16" x="-2.54" y="-15.24" visible="pad" length="short" direction="pas" function="dot"/>
<pin name="17" x="-2.54" y="-17.78" visible="pad" length="short" direction="pas" function="dot"/>
<pin name="18" x="-2.54" y="-20.32" visible="pad" length="short" direction="pas" function="dot"/>
<pin name="19" x="-2.54" y="-22.86" visible="pad" length="short" direction="pas" function="dot"/>
<pin name="20" x="-2.54" y="-25.4" visible="pad" length="short" direction="pas" function="dot"/>
</symbol>
</symbols>
<devicesets>
<deviceset name="PINHD-1X20" prefix="JP" uservalue="yes">
<gates>
<gate name="A" symbol="PINHD20" x="0" y="0"/>
</gates>
<devices>
<device name="" package="1X20">
<connects>
<connect gate="A" pin="1" pad="1"/>
<connect gate="A" pin="10" pad="10"/>
<connect gate="A" pin="11" pad="11"/>
<connect gate="A" pin="12" pad="12"/>
<connect gate="A" pin="13" pad="13"/>
<connect gate="A" pin="14" pad="14"/>
<connect gate="A" pin="15" pad="15"/>
<connect gate="A" pin="16" pad="16"/>
<connect gate="A" pin="17" pad="17"/>
<connect gate="A" pin="18" pad="18"/>
<connect gate="A" pin="19" pad="19"/>
<connect gate="A" pin="2" pad="2"/>
<connect gate="A" pin="20" pad="20"/>
<connect gate="A" pin="3" pad="3"/>
<connect gate="A" pin="4" pad="4"/>
<connect gate="A" pin="5" pad="5"/>
<connect gate="A" pin="6" pad="6"/>
<connect gate="A" pin="7" pad="7"/>
<connect gate="A" pin="8" pad="8"/>
<connect gate="A" pin="9" pad="9"/>
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
<text x="-2.54" y="-2.54" size="1.778" layer="96">&gt;VALUE</text>
<pin name="GND" x="0" y="2.54" visible="off" length="short" direction="sup" rot="R270"/>
</symbol>
<symbol name="VCC">
<wire x1="1.27" y1="-1.905" x2="0" y2="0" width="0.254" layer="94"/>
<wire x1="0" y1="0" x2="-1.27" y2="-1.905" width="0.254" layer="94"/>
<text x="-2.54" y="-2.54" size="1.778" layer="96" rot="R90">&gt;VALUE</text>
<pin name="VCC" x="0" y="-2.54" visible="off" length="short" direction="sup" rot="R90"/>
</symbol>
<symbol name="+12V">
<wire x1="1.27" y1="-1.905" x2="0" y2="0" width="0.254" layer="94"/>
<wire x1="0" y1="0" x2="-1.27" y2="-1.905" width="0.254" layer="94"/>
<wire x1="1.27" y1="-0.635" x2="0" y2="1.27" width="0.254" layer="94"/>
<wire x1="0" y1="1.27" x2="-1.27" y2="-0.635" width="0.254" layer="94"/>
<text x="-2.54" y="-5.08" size="1.778" layer="96" rot="R90">&gt;VALUE</text>
<pin name="+12V" x="0" y="-2.54" visible="off" length="short" direction="sup" rot="R90"/>
</symbol>
</symbols>
<devicesets>
<deviceset name="GND" prefix="GND" uservalue="yes">
<description>Supply Symbol</description>
<gates>
<gate name="1" symbol="GND" x="0" y="0"/>
</gates>
<devices>
<device name="*">
<technologies>
<technology name=""/>
</technologies>
</device>
</devices>
</deviceset>
<deviceset name="VCC" prefix="P+" uservalue="yes">
<description>Supply Symbol</description>
<gates>
<gate name="VCC" symbol="VCC" x="0" y="0"/>
</gates>
<devices>
<device name="*">
<technologies>
<technology name=""/>
</technologies>
</device>
</devices>
</deviceset>
<deviceset name="+12V" prefix="P+" uservalue="yes">
<description>Supply Symbol</description>
<gates>
<gate name="1" symbol="+12V" x="0" y="0"/>
</gates>
<devices>
<device name="*">
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
<class number="0" name="default" width="0" drill="0">
</class>
</classes>
<parts>
<part name="F1" library="frames" deviceset="DINA4_P" device=""/>
<part name="IC1" library="microchip" deviceset="PIC16F8*" device="P" technology="4A" value="16F84"/>
<part name="U1" library="linear" deviceset="78LXXZ" device="" value="78L05"/>
<part name="C5" library="capacitor-wima" deviceset="C" device="2.5/2" value="27p"/>
<part name="C6" library="capacitor-wima" deviceset="C" device="2.5/2" value="27p"/>
<part name="Q1" library="special" deviceset="XTAL/S" device=""/>
<part name="R1" library="rcl" deviceset="R-EU_" device="0207/10" value="2.2k"/>
<part name="D1" library="diode" deviceset="1N4148?" device=""/>
<part name="C1" library="polcap" deviceset="E2,5-6" device="" value="10u"/>
<part name="C2" library="polcap" deviceset="E2,5-6" device="" value="10u"/>
<part name="C3" library="rcl" deviceset="C-EU" device="025-025X050" value="10n"/>
<part name="C4" library="rcl" deviceset="C-EU" device="025-025X050" value="10n"/>
<part name="J1" library="PINHEAD" deviceset="PINHD-1X20" device=""/>
<part name="GND1" library="supply1" deviceset="GND" device="*"/>
<part name="GND2" library="supply1" deviceset="GND" device="*"/>
<part name="GND3" library="supply1" deviceset="GND" device="*"/>
<part name="GND4" library="supply1" deviceset="GND" device="*"/>
<part name="GND5" library="supply1" deviceset="GND" device="*"/>
<part name="P+1" library="supply1" deviceset="VCC" device="*"/>
<part name="P+2" library="supply1" deviceset="VCC" device="*"/>
<part name="P+3" library="supply1" deviceset="VCC" device="*"/>
<part name="P+4" library="supply1" deviceset="VCC" device="*"/>
<part name="P+5" library="supply1" deviceset="+12V" device="*"/>
<part name="P+6" library="supply1" deviceset="+12V" device="*"/>
<part name="GND6" library="supply1" deviceset="GND" device="*"/>
<part name="GND7" library="supply1" deviceset="GND" device="*"/>
<part name="GND8" library="supply1" deviceset="GND" device="*"/>
<part name="GND9" library="supply1" deviceset="GND" device="*"/>
<part name="GND10" library="supply1" deviceset="GND" device="*"/>
</parts>
<sheets>
<sheet>
<plain>
<text x="81.28" y="27.94" size="2.54" layer="94">PICSTAMP</text>
<text x="170.18" y="7.62" size="2.54" layer="94">1.0</text>
</plain>
<instances>
<instance part="F1" gate="G$1" x="0" y="0"/>
<instance part="F1" gate="G$2" x="78.74" y="0"/>
<instance part="IC1" gate="G$1" x="109.22" y="154.94"/>
<instance part="U1" gate="A1" x="71.12" y="99.06"/>
<instance part="C5" gate="G$1" x="86.36" y="162.56" smashed="yes" rot="R90">
<attribute name="NAME" x="81.28" y="159.385" size="1.778" layer="95"/>
<attribute name="VALUE" x="88.9" y="159.131" size="1.778" layer="96"/>
</instance>
<instance part="C6" gate="G$1" x="68.58" y="162.56" smashed="yes" rot="R90">
<attribute name="NAME" x="60.96" y="163.83" size="1.778" layer="95"/>
<attribute name="VALUE" x="60.325" y="161.036" size="1.778" layer="96"/>
</instance>
<instance part="Q1" gate="G$1" x="78.74" y="165.1" smashed="yes">
<attribute name="NAME" x="78.105" y="168.91" size="1.778" layer="95"/>
<attribute name="VALUE" x="73.66" y="160.02" size="1.778" layer="96"/>
</instance>
<instance part="R1" gate="G$1" x="45.72" y="195.58" smashed="yes" rot="R90">
<attribute name="NAME" x="48.26" y="197.0786" size="1.778" layer="95"/>
<attribute name="VALUE" x="48.26" y="194.183" size="1.778" layer="96"/>
</instance>
<instance part="D1" gate="G$1" x="45.72" y="187.96" smashed="yes" rot="R270">
<attribute name="NAME" x="48.26" y="188.4426" size="1.778" layer="95"/>
<attribute name="VALUE" x="48.26" y="185.6486" size="1.778" layer="96"/>
</instance>
<instance part="C1" gate="1" x="48.26" y="91.44"/>
<instance part="C2" gate="1" x="93.98" y="91.44"/>
<instance part="C3" gate="G$1" x="55.88" y="93.98"/>
<instance part="C4" gate="G$1" x="83.82" y="93.98"/>
<instance part="J1" gate="A" x="149.86" y="152.4" smashed="yes" rot="MR180">
<attribute name="NAME" x="143.51" y="184.15" size="1.778" layer="95" rot="MR180"/>
<attribute name="VALUE" x="143.51" y="182.88" size="1.778" layer="96" rot="MR180"/>
</instance>
<instance part="GND1" gate="1" x="93.98" y="132.08"/>
<instance part="GND2" gate="1" x="68.58" y="157.48"/>
<instance part="GND3" gate="1" x="86.36" y="157.48"/>
<instance part="GND4" gate="1" x="134.62" y="180.34"/>
<instance part="GND5" gate="1" x="139.7" y="127"/>
<instance part="P+1" gate="VCC" x="45.72" y="203.2"/>
<instance part="P+2" gate="VCC" x="93.98" y="175.26"/>
<instance part="P+3" gate="VCC" x="93.98" y="104.14"/>
<instance part="P+4" gate="VCC" x="129.54" y="127" rot="R180"/>
<instance part="P+5" gate="1" x="48.26" y="104.14"/>
<instance part="P+6" gate="1" x="134.62" y="127" rot="R180"/>
<instance part="GND6" gate="1" x="71.12" y="86.36"/>
<instance part="GND7" gate="1" x="48.26" y="86.36"/>
<instance part="GND8" gate="1" x="55.88" y="86.36"/>
<instance part="GND9" gate="1" x="83.82" y="86.36"/>
<instance part="GND10" gate="1" x="93.98" y="86.36"/>
</instances>
<busses>
</busses>
<nets>
<net name="A0" class="0">
<segment>
<wire x1="147.32" y1="137.16" x2="121.92" y2="137.16" width="0.1524" layer="91"/>
<pinref part="IC1" gate="G$1" pin="RA0"/>
<pinref part="J1" gate="A" pin="4"/>
</segment>
</net>
<net name="A1" class="0">
<segment>
<wire x1="147.32" y1="139.7" x2="121.92" y2="139.7" width="0.1524" layer="91"/>
<pinref part="IC1" gate="G$1" pin="RA1"/>
<pinref part="J1" gate="A" pin="5"/>
</segment>
</net>
<net name="A2" class="0">
<segment>
<wire x1="147.32" y1="142.24" x2="121.92" y2="142.24" width="0.1524" layer="91"/>
<pinref part="IC1" gate="G$1" pin="RA2"/>
<pinref part="J1" gate="A" pin="6"/>
</segment>
</net>
<net name="A3" class="0">
<segment>
<wire x1="147.32" y1="144.78" x2="121.92" y2="144.78" width="0.1524" layer="91"/>
<pinref part="IC1" gate="G$1" pin="RA3"/>
<pinref part="J1" gate="A" pin="7"/>
</segment>
</net>
<net name="A4" class="0">
<segment>
<wire x1="147.32" y1="147.32" x2="121.92" y2="147.32" width="0.1524" layer="91"/>
<pinref part="IC1" gate="G$1" pin="T0CKI/RA4"/>
<pinref part="J1" gate="A" pin="8"/>
</segment>
</net>
<net name="B0" class="0">
<segment>
<wire x1="147.32" y1="149.86" x2="124.46" y2="149.86" width="0.1524" layer="91"/>
<wire x1="124.46" y1="149.86" x2="124.46" y2="152.4" width="0.1524" layer="91"/>
<wire x1="124.46" y1="152.4" x2="121.92" y2="152.4" width="0.1524" layer="91"/>
<pinref part="IC1" gate="G$1" pin="RB0"/>
<pinref part="J1" gate="A" pin="9"/>
</segment>
</net>
<net name="B1" class="0">
<segment>
<wire x1="147.32" y1="152.4" x2="127" y2="152.4" width="0.1524" layer="91"/>
<wire x1="127" y1="152.4" x2="127" y2="154.94" width="0.1524" layer="91"/>
<wire x1="127" y1="154.94" x2="121.92" y2="154.94" width="0.1524" layer="91"/>
<pinref part="IC1" gate="G$1" pin="RB1"/>
<pinref part="J1" gate="A" pin="10"/>
</segment>
</net>
<net name="B2" class="0">
<segment>
<wire x1="147.32" y1="154.94" x2="129.54" y2="154.94" width="0.1524" layer="91"/>
<wire x1="129.54" y1="154.94" x2="129.54" y2="157.48" width="0.1524" layer="91"/>
<wire x1="129.54" y1="157.48" x2="121.92" y2="157.48" width="0.1524" layer="91"/>
<pinref part="IC1" gate="G$1" pin="RB2"/>
<pinref part="J1" gate="A" pin="11"/>
</segment>
</net>
<net name="B3" class="0">
<segment>
<wire x1="147.32" y1="157.48" x2="132.08" y2="157.48" width="0.1524" layer="91"/>
<wire x1="132.08" y1="157.48" x2="132.08" y2="160.02" width="0.1524" layer="91"/>
<wire x1="132.08" y1="160.02" x2="121.92" y2="160.02" width="0.1524" layer="91"/>
<pinref part="IC1" gate="G$1" pin="RB3"/>
<pinref part="J1" gate="A" pin="12"/>
</segment>
</net>
<net name="B4" class="0">
<segment>
<wire x1="147.32" y1="160.02" x2="134.62" y2="160.02" width="0.1524" layer="91"/>
<wire x1="134.62" y1="160.02" x2="134.62" y2="162.56" width="0.1524" layer="91"/>
<wire x1="134.62" y1="162.56" x2="121.92" y2="162.56" width="0.1524" layer="91"/>
<pinref part="IC1" gate="G$1" pin="RB4"/>
<pinref part="J1" gate="A" pin="13"/>
</segment>
</net>
<net name="B5" class="0">
<segment>
<wire x1="147.32" y1="162.56" x2="137.16" y2="162.56" width="0.1524" layer="91"/>
<wire x1="137.16" y1="162.56" x2="137.16" y2="165.1" width="0.1524" layer="91"/>
<wire x1="137.16" y1="165.1" x2="121.92" y2="165.1" width="0.1524" layer="91"/>
<pinref part="IC1" gate="G$1" pin="RB5"/>
<pinref part="J1" gate="A" pin="14"/>
</segment>
</net>
<net name="B6" class="0">
<segment>
<wire x1="147.32" y1="165.1" x2="139.7" y2="165.1" width="0.1524" layer="91"/>
<wire x1="139.7" y1="165.1" x2="139.7" y2="167.64" width="0.1524" layer="91"/>
<wire x1="139.7" y1="167.64" x2="121.92" y2="167.64" width="0.1524" layer="91"/>
<wire x1="139.7" y1="167.64" x2="139.7" y2="172.72" width="0.1524" layer="91"/>
<wire x1="139.7" y1="172.72" x2="147.32" y2="172.72" width="0.1524" layer="91"/>
<junction x="139.7" y="167.64"/>
<pinref part="IC1" gate="G$1" pin="RB6"/>
<pinref part="J1" gate="A" pin="15"/>
<pinref part="J1" gate="A" pin="18"/>
</segment>
</net>
<net name="B7" class="0">
<segment>
<wire x1="147.32" y1="167.64" x2="142.24" y2="167.64" width="0.1524" layer="91"/>
<wire x1="142.24" y1="167.64" x2="142.24" y2="170.18" width="0.1524" layer="91"/>
<wire x1="142.24" y1="170.18" x2="121.92" y2="170.18" width="0.1524" layer="91"/>
<wire x1="142.24" y1="170.18" x2="147.32" y2="170.18" width="0.1524" layer="91"/>
<junction x="142.24" y="170.18"/>
<pinref part="IC1" gate="G$1" pin="RB7"/>
<pinref part="J1" gate="A" pin="16"/>
<pinref part="J1" gate="A" pin="17"/>
</segment>
</net>
<net name="N$1" class="0">
<segment>
<wire x1="147.32" y1="175.26" x2="127" y2="175.26" width="0.1524" layer="91"/>
<wire x1="127" y1="175.26" x2="127" y2="180.34" width="0.1524" layer="91"/>
<wire x1="127" y1="180.34" x2="45.72" y2="180.34" width="0.1524" layer="91"/>
<wire x1="45.72" y1="180.34" x2="45.72" y2="152.4" width="0.1524" layer="91"/>
<wire x1="45.72" y1="152.4" x2="96.52" y2="152.4" width="0.1524" layer="91"/>
<wire x1="45.72" y1="180.34" x2="45.72" y2="185.42" width="0.1524" layer="91"/>
<junction x="45.72" y="180.34"/>
<pinref part="J1" gate="A" pin="19"/>
<pinref part="IC1" gate="G$1" pin="!MCLR"/>
<pinref part="D1" gate="G$1" pin="C"/>
</segment>
</net>
<net name="VCC" class="0">
<segment>
<wire x1="129.54" y1="129.54" x2="129.54" y2="134.62" width="0.1524" layer="91"/>
<wire x1="129.54" y1="134.62" x2="147.32" y2="134.62" width="0.1524" layer="91"/>
<pinref part="P+4" gate="VCC" pin="VCC"/>
<pinref part="J1" gate="A" pin="3"/>
</segment>
<segment>
<pinref part="R1" gate="G$1" pin="2"/>
<pinref part="P+1" gate="VCC" pin="VCC"/>
</segment>
<segment>
<wire x1="93.98" y1="172.72" x2="93.98" y2="170.18" width="0.1524" layer="91"/>
<wire x1="93.98" y1="170.18" x2="96.52" y2="170.18" width="0.1524" layer="91"/>
<pinref part="P+2" gate="VCC" pin="VCC"/>
<pinref part="IC1" gate="G$1" pin="VDD"/>
</segment>
<segment>
<wire x1="93.98" y1="101.6" x2="93.98" y2="99.06" width="0.1524" layer="91"/>
<wire x1="93.98" y1="99.06" x2="93.98" y2="96.52" width="0.1524" layer="91"/>
<wire x1="93.98" y1="99.06" x2="83.82" y2="99.06" width="0.1524" layer="91"/>
<wire x1="83.82" y1="99.06" x2="81.28" y2="99.06" width="0.1524" layer="91"/>
<wire x1="83.82" y1="96.52" x2="83.82" y2="99.06" width="0.1524" layer="91"/>
<junction x="93.98" y="99.06"/>
<junction x="83.82" y="99.06"/>
<label x="96.52" y="101.6" size="1.778" layer="95"/>
<pinref part="P+3" gate="VCC" pin="VCC"/>
<pinref part="C2" gate="1" pin="+"/>
<pinref part="U1" gate="A1" pin="VO"/>
<pinref part="C4" gate="G$1" pin="2"/>
</segment>
</net>
<net name="+12V" class="0">
<segment>
<wire x1="134.62" y1="129.54" x2="134.62" y2="132.08" width="0.1524" layer="91"/>
<wire x1="134.62" y1="132.08" x2="147.32" y2="132.08" width="0.1524" layer="91"/>
<pinref part="P+6" gate="1" pin="+12V"/>
<pinref part="J1" gate="A" pin="2"/>
</segment>
<segment>
<wire x1="60.96" y1="99.06" x2="55.88" y2="99.06" width="0.1524" layer="91"/>
<wire x1="55.88" y1="99.06" x2="48.26" y2="99.06" width="0.1524" layer="91"/>
<wire x1="48.26" y1="101.6" x2="48.26" y2="99.06" width="0.1524" layer="91"/>
<wire x1="48.26" y1="99.06" x2="48.26" y2="96.52" width="0.1524" layer="91"/>
<wire x1="55.88" y1="96.52" x2="55.88" y2="99.06" width="0.1524" layer="91"/>
<junction x="48.26" y="99.06"/>
<junction x="55.88" y="99.06"/>
<label x="38.1" y="101.6" size="1.778" layer="95"/>
<pinref part="U1" gate="A1" pin="VI"/>
<pinref part="P+5" gate="1" pin="+12V"/>
<pinref part="C1" gate="1" pin="+"/>
<pinref part="C3" gate="G$1" pin="2"/>
</segment>
</net>
<net name="GND" class="0">
<segment>
<wire x1="139.7" y1="129.54" x2="147.32" y2="129.54" width="0.1524" layer="91"/>
<pinref part="GND5" gate="1" pin="GND"/>
<pinref part="J1" gate="A" pin="1"/>
</segment>
<segment>
<wire x1="134.62" y1="182.88" x2="139.7" y2="182.88" width="0.1524" layer="91"/>
<wire x1="139.7" y1="182.88" x2="139.7" y2="177.8" width="0.1524" layer="91"/>
<wire x1="139.7" y1="177.8" x2="147.32" y2="177.8" width="0.1524" layer="91"/>
<pinref part="GND4" gate="1" pin="GND"/>
<pinref part="J1" gate="A" pin="20"/>
</segment>
<segment>
<pinref part="C5" gate="G$1" pin="1"/>
<pinref part="GND3" gate="1" pin="GND"/>
</segment>
<segment>
<pinref part="C6" gate="G$1" pin="1"/>
<pinref part="GND2" gate="1" pin="GND"/>
</segment>
<segment>
<wire x1="93.98" y1="134.62" x2="93.98" y2="137.16" width="0.1524" layer="91"/>
<wire x1="93.98" y1="137.16" x2="96.52" y2="137.16" width="0.1524" layer="91"/>
<pinref part="GND1" gate="1" pin="GND"/>
<pinref part="IC1" gate="G$1" pin="VSS"/>
</segment>
<segment>
<wire x1="71.12" y1="88.9" x2="71.12" y2="91.44" width="0.1524" layer="91"/>
<pinref part="U1" gate="A1" pin="GND"/>
<pinref part="GND6" gate="1" pin="GND"/>
</segment>
<segment>
<pinref part="C1" gate="1" pin="-"/>
<pinref part="GND7" gate="1" pin="GND"/>
</segment>
<segment>
<pinref part="C3" gate="G$1" pin="1"/>
<pinref part="GND8" gate="1" pin="GND"/>
</segment>
<segment>
<pinref part="C4" gate="G$1" pin="1"/>
<pinref part="GND9" gate="1" pin="GND"/>
</segment>
<segment>
<pinref part="C2" gate="1" pin="-"/>
<pinref part="GND10" gate="1" pin="GND"/>
</segment>
</net>
<net name="N$2" class="0">
<segment>
<pinref part="D1" gate="G$1" pin="A"/>
<pinref part="R1" gate="G$1" pin="1"/>
</segment>
</net>
<net name="N$3" class="0">
<segment>
<wire x1="96.52" y1="162.56" x2="91.44" y2="162.56" width="0.1524" layer="91"/>
<wire x1="91.44" y1="162.56" x2="91.44" y2="165.1" width="0.1524" layer="91"/>
<wire x1="91.44" y1="165.1" x2="86.36" y2="165.1" width="0.1524" layer="91"/>
<wire x1="86.36" y1="165.1" x2="83.82" y2="165.1" width="0.1524" layer="91"/>
<junction x="86.36" y="165.1"/>
<pinref part="IC1" gate="G$1" pin="OSC1"/>
<pinref part="C5" gate="G$1" pin="2"/>
<pinref part="Q1" gate="G$1" pin="2"/>
</segment>
</net>
<net name="N$4" class="0">
<segment>
<wire x1="73.66" y1="165.1" x2="68.58" y2="165.1" width="0.1524" layer="91"/>
<wire x1="73.66" y1="165.1" x2="73.66" y2="154.94" width="0.1524" layer="91"/>
<wire x1="73.66" y1="154.94" x2="96.52" y2="154.94" width="0.1524" layer="91"/>
<wire x1="96.52" y1="154.94" x2="96.52" y2="157.48" width="0.1524" layer="91"/>
<junction x="73.66" y="165.1"/>
<pinref part="Q1" gate="G$1" pin="1"/>
<pinref part="C6" gate="G$1" pin="2"/>
<pinref part="IC1" gate="G$1" pin="OSC2"/>
</segment>
</net>
</nets>
</sheet>
</sheets>
</schematic>
</drawing>
</eagle>
