from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path


BASE = Path(__file__).resolve().parent
PRO_PATH = BASE / "board.kicad_pro"
PCB_PATH = BASE / "board.kicad_pcb"

TARGETS = {
    "USB_DP_DM": {"track_width": (0.13, 0.05), "diff_pair_width": (0.13, 0.05), "diff_pair_gap": (0.10, 0.10)},
    "ETH_MDI": {"track_width": (0.10, 0.10), "diff_pair_width": (0.10, 0.10), "diff_pair_gap": (0.15, 0.10)},
    "HDMI_TMDS": {"track_width": (0.10, 0.10), "diff_pair_width": (0.10, 0.10), "diff_pair_gap": (0.15, 0.10)},
}

NET_RE = re.compile(r'\(net\s+(\d+)\s+"([^"]+)"\)')
SEG_RE = re.compile(
    r'\(segment\s+\(start\s+([-0-9.]+)\s+([-0-9.]+)\)\s+'
    r'\(end\s+([-0-9.]+)\s+([-0-9.]+)\)\s+'
    r'\(width\s+([-0-9.]+)\)\s+'
    r'\(layer\s+"([^"]+)"\)\s+'
    r'\(net\s+(\d+)(?:\s+"([^"]+)")?\)\)'
)
VIA_RE = re.compile(
    r'\(via\s+\(at\s+([-0-9.]+)\s+([-0-9.]+)\)\s+'
    r'\(size\s+([-0-9.]+)\)\s+'
    r'\(drill\s+([-0-9.]+)\)\s+'
    r'\(layers\s+"([^"]+)"\s+"([^"]+)"\)\s+'
    r'\(net\s+(\d+)(?:\s+"([^"]+)")?\)\)'
)


def _check_close(actual, expected, rel_tol):
    return abs(float(actual) - expected) <= rel_tol * expected


def _load_board(text: str):
    net_map = {int(n): name for n, name in NET_RE.findall(text)}
    segments = []
    for m in SEG_RE.finditer(text):
        segments.append(
            {
                "x1": float(m.group(1)),
                "y1": float(m.group(2)),
                "x2": float(m.group(3)),
                "y2": float(m.group(4)),
                "width": float(m.group(5)),
                "layer": m.group(6),
                "net_id": int(m.group(7)),
                "net_name": m.group(8) or net_map.get(int(m.group(7)), ""),
            }
        )
    vias = []
    for m in VIA_RE.finditer(text):
        vias.append(
            {
                "x": float(m.group(1)),
                "y": float(m.group(2)),
                "size": float(m.group(3)),
                "drill": float(m.group(4)),
                "layer1": m.group(5),
                "layer2": m.group(6),
                "net_id": int(m.group(7)),
                "net_name": m.group(8) or net_map.get(int(m.group(7)), ""),
            }
        )
    return net_map, segments, vias


def evaluate() -> bool:
    if not PRO_PATH.exists() or not PCB_PATH.exists():
        return False

    try:
        pro = json.loads(PRO_PATH.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return False

    classes = {c.get("name"): c for c in pro.get("net_settings", {}).get("classes", [])}
    for name, fields in TARGETS.items():
        cls = classes.get(name)
        if cls is None:
            return False
        for field, (expected, rel_tol) in fields.items():
            actual = cls.get(field)
            if actual is None or not _check_close(actual, expected, rel_tol):
                return False
    if not all(name in classes for name in TARGETS):
        return False

    try:
        text = PCB_PATH.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return False

    _, segments, vias = _load_board(text)

    hdmi_segments = [
        s for s in segments
        if s["layer"] == "F.Cu" and s["net_name"].startswith("HDMI_TMDS")
    ]
    hdmi_nets = {s["net_name"] for s in hdmi_segments}
    if len(hdmi_nets) != 2 or any(not name for name in hdmi_nets):
        return False
    if any(abs(s["width"] - 0.10) > 0.01 for s in hdmi_segments):
        return False

    def point(x, y):
        return round(x, 6), round(y, 6)

    def connected_endpoints(net_segments):
        adjacency = {}
        degrees = {}
        for segment in net_segments:
            start = point(segment["x1"], segment["y1"])
            end = point(segment["x2"], segment["y2"])
            adjacency.setdefault(start, set()).add(end)
            adjacency.setdefault(end, set()).add(start)
            degrees[start] = degrees.get(start, 0) + 1
            degrees[end] = degrees.get(end, 0) + 1
        pending = [next(iter(adjacency))]
        visited = set()
        while pending:
            current = pending.pop()
            if current in visited:
                continue
            visited.add(current)
            pending.extend(adjacency[current] - visited)
        if visited != set(adjacency):
            return None
        return [value for value, degree in degrees.items() if degree % 2 == 1]

    endpoints = []
    for name in sorted(hdmi_nets):
        values = connected_endpoints([s for s in hdmi_segments if s["net_name"] == name])
        if values is None or len(values) != 2:
            return False
        endpoints.append(values)

    # Either end may be the source. Require one corresponding endpoint pair to
    # have the requested approximately 0.25 mm center-to-center spacing.
    endpoint_gaps = [
        math.hypot(a[0] - b[0], a[1] - b[1])
        for a in endpoints[0]
        for b in endpoints[1]
    ]
    if not any(abs(gap - 0.25) <= 0.05 for gap in endpoint_gaps):
        return False

    gnd_vias = [
        v for v in vias
        if v["net_name"] == "GND" and 35.0 <= v["x"] <= 70.0 and abs(v["y"] - 20.0) <= 3.0
    ]
    if len(gnd_vias) != 6:
        return False

    xs = sorted({round(v["x"], 3) for v in gnd_vias})
    if len(xs) != 6:
        return False
    if any(xs[i + 1] - xs[i] > 5.0 + 1e-6 for i in range(len(xs) - 1)):
        return False

    return True


if __name__ == "__main__":
    print("True" if evaluate() else "False")
