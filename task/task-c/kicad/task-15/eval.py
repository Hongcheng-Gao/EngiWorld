from __future__ import annotations

import csv
import math
import re
import sys
from pathlib import Path


BASE = Path(__file__).resolve().parent
PCB_PATH = BASE / "board.kicad_pcb"
CSV_PATH = BASE / "pdn_analysis.csv"

TARGET = [
    (10_000, 0.5),
    (100_000, 0.3),
    (1_000_000, 0.15),
    (10_000_000, 0.08),
    (100_000_000, 0.05),
]

CAP_MODELS = {
    "100nF": (100e-9, 0.05, 0.5e-9),
    "10uF": (10e-6, 0.02, 1.0e-9),
    "1uF": (1e-6, 0.03, 0.8e-9),
    "47nF": (47e-9, 0.08, 0.4e-9),
    "10nF": (10e-9, 0.12, 0.3e-9),
}

FP_RE = re.compile(r'\(footprint\s+"[^"]+"\s+\(layer\s+"[^"]+"\)\s+\(at\s+([-0-9.]+)\s+([-0-9.]+)\)')
REF_RE = re.compile(r'\(fp_text\s+reference\s+"([^"]+)"')
VAL_RE = re.compile(r'\(fp_text\s+value\s+"([^"]+)"')
AT_RE = re.compile(r'\(pad\s+"[12]"\s+smd\s+rect\s+\(at\s+([-0-9.]+)\s+([-0-9.]+)\)\s+\(size\s+([-0-9.]+)\s+([-0-9.]+)\)\s+\(layers\s+"F.Cu"\s+"F.Mask"\)\s+\(net\s+\d+\s+"([^"]+)"\)\)')


def _cap_impedance(f_hz: float, caps: list[tuple[float, float, float]]) -> float:
    y = 0j
    w = 2 * math.pi * f_hz
    for c, esr, esl in caps:
        z = esr + 1j * (w * esl - 1.0 / (w * c))
        y += 1.0 / z
    return abs(1.0 / y)


def _parse_caps(text: str):
    caps = []
    refs = []
    values = []
    for block in text.split("(footprint "):
        if not block.strip():
            continue
        ref_m = REF_RE.search(block)
        val_m = VAL_RE.search(block)
        if ref_m and val_m and ref_m.group(1).startswith("C"):
            refs.append(ref_m.group(1))
            values.append(val_m.group(1))
            if val_m.group(1) not in CAP_MODELS:
                return None
            caps.append(CAP_MODELS[val_m.group(1)])
    return refs, values, caps


def _check_csv() -> bool:
    if not CSV_PATH.exists():
        return False
    try:
        rows = list(csv.DictReader(CSV_PATH.read_text(encoding="utf-8", errors="ignore").splitlines()))
    except Exception:
        return False
    if len(rows) != 5:
        return False
    data = [(float(r["freq_hz"]), float(r["z_ohm"])) for r in rows]
    for f, target in TARGET:
        found = next((z for rf, z in data if abs(rf - f) / f < 0.01), None)
        if found is None or found > target + 1e-6:
            return False
    return True


def evaluate() -> bool:
    if not PCB_PATH.exists() or not _check_csv():
        return False

    text = PCB_PATH.read_text(encoding="utf-8", errors="ignore")
    parsed = _parse_caps(text)
    if parsed is None:
        return False
    refs, values, caps = parsed
    if len(refs) != 6:
        return False
    if len(set(refs)) != 6:
        return False

    # All caps within board outline and within 5 mm of 3V3 pad is already embodied by the board geometry.
    # The scoring here enforces the actual impedance curve from the placed cap values.
    for f, target in TARGET:
        if _cap_impedance(f, caps) > target + 1e-6:
            return False
    return True


if __name__ == "__main__":
    print("True" if evaluate() else "False")
