from __future__ import annotations

import csv
import math
import re
import sys
from collections import Counter
from pathlib import Path


BASE = Path(__file__).resolve().parent
PCB_PATH = BASE / "board.kicad_pcb"
CSV_PATH = BASE / "pdn_analysis.csv"

FP_RE = re.compile(r'\(footprint\s+"([^"]+)"\s+\(layer\s+"[^"]+"\)\s+\(at\s+([-0-9.]+)\s+([-0-9.]+)\)')
REF_RE = re.compile(r'\(fp_text\s+reference\s+"([^"]+)"')
VAL_RE = re.compile(r'\(fp_text\s+value\s+"([^"]+)"')
PAD_RE = re.compile(r'\(pad\s+"[^"]+"\s+smd\s+rect\s+\(at\s+([-0-9.]+)\s+([-0-9.]+)\)\s+\(size\s+([-0-9.]+)\s+([-0-9.]+)\)\s+\(layers\s+"F.Cu"\s+"F.Mask"\)\s+\(net\s+\d+\s+"([^"]+)"\)\)')
ORIGINAL_C1_IDENTITY = (
    "100nF",
    "C_0402",
    Counter({
        (-0.5, 0.0, 0.5, 0.5, "3V3"): 1,
        (0.5, 0.0, 0.5, 0.5, "GND"): 1,
    }),
)


def _cap_impedance(f_hz: float, caps: list[tuple[float, float, float]]) -> float:
    y = 0j
    w = 2 * math.pi * f_hz
    for c, esr, esl in caps:
        z = esr + 1j * (w * esl - 1.0 / (w * c))
        y += 1.0 / z
    return abs(1.0 / y)


def _input_path(name: str) -> Path:
    direct = BASE / name
    return direct if direct.exists() else BASE / "init_file" / name


def _load_cap_models() -> dict[str, tuple[float, float, float]]:
    with _input_path("cap_models.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    required = {"value", "capacitance_f", "esr_ohm", "esl_h"}
    if not rows or not required.issubset(rows[0]):
        raise ValueError("cap_models.csv must provide value, capacitance_f, esr_ohm, esl_h")
    return {
        row["value"]: (float(row["capacitance_f"]), float(row["esr_ohm"]), float(row["esl_h"]))
        for row in rows
    }


def _load_targets() -> list[tuple[float, float]]:
    with _input_path("target_z.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return [(float(row["freq_hz"]), float(row["target_ohm"])) for row in rows]


def _parse_board(text: str, cap_models):
    footprints = []
    for raw_block in text.split("(footprint ")[1:]:
        block = "(footprint " + raw_block
        fp_m = FP_RE.search(block)
        ref_m = REF_RE.search(block)
        val_m = VAL_RE.search(block)
        if not (fp_m and ref_m and val_m):
            return None
        library = fp_m.group(1)
        x, y = float(fp_m.group(2)), float(fp_m.group(3))
        pads = []
        for pad_m in PAD_RE.finditer(block):
            pads.append({
                "x": x + float(pad_m.group(1)),
                "y": y + float(pad_m.group(2)),
                "rel_x": float(pad_m.group(1)),
                "rel_y": float(pad_m.group(2)),
                "w": float(pad_m.group(3)),
                "h": float(pad_m.group(4)),
                "net": pad_m.group(5),
            })
        footprints.append({
            "ref": ref_m.group(1),
            "value": val_m.group(1),
            "library": library,
            "x": x,
            "y": y,
            "pads": pads,
        })

    cap_footprints = [fp for fp in footprints if fp["ref"].startswith("C")]
    caps = []
    for fp in cap_footprints:
        if fp["value"] not in cap_models:
            return None
        caps.append(cap_models[fp["value"]])
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


def _check_csv(caps, targets) -> bool:
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
    for f, target in targets:
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

    try:
        cap_models = _load_cap_models()
        targets = _load_targets()
    except Exception:
        return False
    if len(targets) != 5:
        return False

    text = PCB_PATH.read_text(encoding="utf-8", errors="ignore")
    parsed = _parse_board(text, cap_models)
    if parsed is None:
        return False
    footprints, cap_footprints, caps = parsed
    refs = [fp["ref"] for fp in cap_footprints]
    if len(refs) != 6:
        return False
    if len(set(refs)) != 6:
        return False

    # The original C1 may be moved, but it must remain the same component and
    # retain its value, footprint, and two pad definitions.
    output_c1 = [fp for fp in cap_footprints if fp["ref"] == "C1"]
    if len(output_c1) != 1:
        return False
    def identity(fp):
        pads = Counter((pad["rel_x"], pad["rel_y"], pad["w"], pad["h"], pad["net"])
                       for pad in fp["pads"])
        return fp["value"], fp["library"], pads
    if identity(output_c1[0]) != ORIGINAL_C1_IDENTITY:
        return False

    rail_pads = [
        pad
        for fp in footprints if not fp["ref"].startswith("C")
        for pad in fp["pads"] if pad["net"] == "3V3"
    ]
    if not rail_pads:
        return False
    for cap in cap_footprints:
        if Counter(pad["net"] for pad in cap["pads"]) != Counter({"3V3": 1, "GND": 1}):
            return False
        if not (0 <= cap["x"] <= 80 and 0 <= cap["y"] <= 60):
            return False
        if min(math.hypot(cap["x"] - pad["x"], cap["y"] - pad["y"]) for pad in rail_pads) > 5.0 + 1e-6:
            return False
        for other in footprints:
            if other is not cap and _footprints_overlap(cap, other):
                return False

    if not _check_csv(caps, targets):
        return False
    for f, target in targets:
        if _cap_impedance(f, caps) > target + 1e-6:
            return False
    return True


if __name__ == "__main__":
    print("True" if evaluate() else "False")
