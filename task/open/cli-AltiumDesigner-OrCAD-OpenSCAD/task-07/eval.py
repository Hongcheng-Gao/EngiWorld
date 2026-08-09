from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path
from xml.etree import ElementTree as ET


DESKTOP = Path(os.environ.get("ENGIWORLD_DESKTOP", Path(__file__).resolve().parent))


def evaluate() -> bool:
    source_path = DESKTOP / "hsd_fpga.ipc2581"
    report_path = DESKTOP / "stackup_report.json"
    if not source_path.is_file() or not report_path.is_file():
        return False
    try:
        root = ET.parse(source_path).getroot()
        report = json.loads(report_path.read_text(encoding="utf-8"))
        if not isinstance(report, dict):
            return False
        layers = root.findall("./Stackup/Layer")
        names = [layer.attrib["name"] for layer in layers]
        signal = [layer.attrib["name"] for layer in layers if layer.attrib["type"].casefold() == "signal"]
        planes = [layer.attrib["name"] for layer in layers if layer.attrib["type"].casefold() == "plane"]
        dielectric = [float(layer.attrib["dielectric_constant"]) for layer in layers]
    except (OSError, KeyError, TypeError, ValueError, ET.ParseError, json.JSONDecodeError):
        return False

    if not layers or len(names) != len(set(names)):
        return False
    if set(report) != {
        "average_dielectric_constant",
        "layer_count",
        "layers",
        "plane_layers",
        "signal_layers",
    }:
        return False
    try:
        average = float(report["average_dielectric_constant"])
        count = int(report["layer_count"])
    except (TypeError, ValueError):
        return False
    expected_average = sum(dielectric) / len(dielectric)
    if not math.isfinite(average) or abs(average - expected_average) > 5e-5:
        return False
    if count != len(layers):
        return False
    if report["layers"] != names:
        return False
    if report["signal_layers"] != signal or report["plane_layers"] != planes:
        return False
    return True


if __name__ == "__main__":
    ok = evaluate()
    print("True" if ok else "False")
    sys.exit(0 if ok else 1)
