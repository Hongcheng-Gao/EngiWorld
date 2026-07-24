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
    (10_000, 0.53),
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
PAD_RE = re.compile(r'\(pad\s+"[^"]+"\s+smd\s+rect\s+\(at\s+([-0-9.]+)\s+([-0-9.]+)\)\s+\(size\s+([-0-9.]+)\s+([-0-9.]+)\)\s+\(layers\s+"F.Cu"\s+"F.Mask"\)\s+\(net\s+\d+\s+"([^"]+)"\)\)')


def _cap_impedance(f_hz: float, caps: list[tuple[float, float, float]]) -> float:
    y = 0j
    w = 2 * math.pi * f_hz
    for c, esr, esl in caps:
        z = esr + 1j * (w * esl - 1.0 / (w * c))
        y += 1.0 / z
    return abs(1.0 / y)


def _parse_board(text: str):
    footprints = []
    for raw_block in text.split("(footprint ")[1:]:
        block = "(footprint " + raw_block
        fp_m = FP_RE.search(block)
        ref_m = REF_RE.search(block)
        val_m = VAL_RE.search(block)
        if not (fp_m and ref_m and val_m):
            return None
        x, y = float(fp_m.group(1)), float(fp_m.group(2))
        pads = []
        for pad_m in PAD_RE.finditer(block):
            pads.append({
                "x": x + float(pad_m.group(1)),
                "y": y + float(pad_m.group(2)),
                "w": float(pad_m.group(3)),
                "h": float(pad_m.group(4)),
                "net": pad_m.group(5),
            })
        footprints.append({
            "ref": ref_m.group(1),
            "value": val_m.group(1),
            "x": x,
            "y": y,
            "pads": pads,
        })

    cap_footprints = [fp for fp in footprints if fp["ref"].startswith("C")]
    caps = []
    for fp in cap_footprints:
        if fp["value"] not in CAP_MODELS:
            return None
        caps.append(CAP_MODELS[fp["value"]])
    return footprints, cap_footprints, caps


def _pad_bbox(pad):
    return (
        pad["x"] - pad["w"] / 2,
        pad["y"] - pad["h"] / 2,
        pad["x"] + pad["w"] / 2,
        pad["y"] + pad["h"] / 2,
    )


def _overlaps(a, b) -> bool:
    return min(a[2], b[2]) - max(a[0], b[0]) > 1e-6 and min(a[3], b[3]) - max(a[1], b[1]) > 1e-6


def _footprints_overlap(a, b) -> bool:
    return any(
        _overlaps(_pad_bbox(a_pad), _pad_bbox(b_pad))
        for a_pad in a["pads"]
        for b_pad in b["pads"]
    )


def _check_csv(caps) -> bool:
    if not CSV_PATH.exists():
        return False
    try:
        reader = csv.DictReader(CSV_PATH.read_text(encoding="utf-8", errors="ignore").splitlines())
        if reader.fieldnames != ["freq_hz", "z_ohm"]:
            return False
        rows = list(reader)
        data = [(float(r["freq_hz"]), float(r["z_ohm"])) for r in rows]
    except Exception:
        return False
    if len(rows) != 5:
        return False
    for f, target in TARGET:
        matches = [z for rf, z in data if abs(rf - f) / f < 0.01]
        if len(matches) != 1:
            return False
        reported = matches[0]
        computed = _cap_impedance(f, caps)
        if not math.isfinite(reported) or reported < 0 or reported > target + 1e-6:
            return False
        if abs(reported - computed) > max(1e-6, computed * 1e-3):
            return False
    return True


def evaluate() -> bool:
    if not PCB_PATH.exists() or not CSV_PATH.exists():
        return False

    text = PCB_PATH.read_text(encoding="utf-8", errors="ignore")
    parsed = _parse_board(text)
    if parsed is None:
        return False
    footprints, cap_footprints, caps = parsed
    refs = [fp["ref"] for fp in cap_footprints]
    if len(refs) != 6:
        return False
    if len(set(refs)) != 6:
        return False

    rail_pads = [
        pad
        for fp in footprints if not fp["ref"].startswith("C")
        for pad in fp["pads"] if pad["net"] == "3V3"
    ]
    if not rail_pads:
        return False
    for cap in cap_footprints:
        if not (0 <= cap["x"] <= 80 and 0 <= cap["y"] <= 60):
            return False
        if min(math.hypot(cap["x"] - pad["x"], cap["y"] - pad["y"]) for pad in rail_pads) > 5.0 + 1e-6:
            return False
        for other in footprints:
            if other is not cap and _footprints_overlap(cap, other):
                return False

    if not _check_csv(caps):
        return False
    for f, target in TARGET:
        if _cap_impedance(f, caps) > target + 1e-6:
            return False
    return True


if __name__ == "__main__":
    print("True" if evaluate() else "False")
