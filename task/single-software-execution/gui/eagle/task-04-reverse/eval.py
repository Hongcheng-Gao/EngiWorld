from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from pathlib import Path

OUTPUT_ROOT = Path(os.environ.get("EVAL_OUTPUT_ROOT", "/home/user/Desktop"))
SPEC = {'kind': 'library', 'target': 'answer.lbr'}
FORBIDDEN = {".py", ".pyw", ".sh", ".bash", ".zsh", ".ps1", ".bat", ".cmd", ".tcl", ".scr"}


def no_gui_bypass():
    for path in OUTPUT_ROOT.iterdir():
        if path.is_file() and path.name != "eval.py" and path.suffix.lower() in FORBIDDEN:
            return False
    return True


def check_schematic(root):
    parts = {part.attrib.get("name"): part.attrib for part in root.findall(".//schematic/parts/part")}
    instances = {item.attrib.get("part") for item in root.findall(".//schematic/sheets/sheet/instances/instance")}
    nets = {}
    for net in root.findall(".//schematic/sheets/sheet/nets/net"):
        refs = {(pin.attrib.get("part"), pin.attrib.get("pin")) for pin in net.findall(".//pinref")}
        nets[net.attrib.get("name")] = refs
    for name, expected in SPEC["parts"].items():
        actual = parts.get(name)
        if actual is None or name not in instances:
            return False
        if "value" in expected and actual.get("value", "") != expected["value"]:
            return False
        if "deviceset" in expected and expected["deviceset"].lower() not in actual.get("deviceset", "").lower():
            return False
    for name, required in SPEC.get("nets", {}).items():
        if name not in nets or not {tuple(item) for item in required}.issubset(nets[name]):
            return False
    if SPEC.get("forbid_buses") and root.findall(".//schematic/sheets/sheet/busses/bus"):
        return False
    return True


def check_library(root):
    package = root.find(".//library/packages/package[@name='SOT23-3']")
    symbol = root.find(".//library/symbols/symbol[@name='LDO']")
    deviceset = root.find(".//library/devicesets/deviceset[@name='XC6206']")
    if package is None or symbol is None or deviceset is None or deviceset.attrib.get("prefix") != "U":
        return False
    pads = {pad.attrib.get("name") for pad in package.findall("smd")}
    pins = {pin.attrib.get("name"): pin.attrib.get("direction") for pin in symbol.findall("pin")}
    connects = {(item.attrib.get("pin"), item.attrib.get("pad")) for item in deviceset.findall(".//connect")}
    return pads == {"1", "2", "3"} and set(pins) == {"VIN", "GND", "VOUT"} and connects == {
        ("VIN", "1"), ("GND", "2"), ("VOUT", "3")
    }


def run():
    if not no_gui_bypass():
        return False
    answer = OUTPUT_ROOT / SPEC["target"]
    if not answer.is_file() or answer.stat().st_size < 500:
        return False
    root = ET.parse(answer).getroot()
    if root.tag != "eagle":
        return False
    return check_library(root) if SPEC["kind"] == "library" else check_schematic(root)


if __name__ == "__main__":
    try:
        print("True" if run() else "False")
    except Exception:
        print("False")
