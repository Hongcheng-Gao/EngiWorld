from __future__ import annotations

import json
import math
import os
import re
from pathlib import Path


DESKTOP = Path(os.environ.get("ENGIWORLD_DESKTOP", Path.home() / "Desktop"))
TASK = json.loads(r"""{
  "antenna_keepout": {
    "center": [
      0,
      24
    ],
    "radius": 18
  },
  "board": [
    76,
    76
  ],
  "clearance": 2.6,
  "fixed": {
    "A1": [
      0,
      24
    ],
    "J1": [
      34,
      -20
    ],
    "U1": [
      -12,
      -14
    ]
  },
  "instruction_tail": "Shorten the RF feed chain while keeping non-antenna parts outside the antenna keepout.",
  "metric": "RF feed length and keepout margin",
  "movable": {
    "C1": {
      "baseline": [
        10,
        9
      ],
      "ideal": [
        5,
        12
      ],
      "seed": [
        22,
        12
      ],
      "weight": 1.4
    },
    "C2": {
      "baseline": [
        12,
        -1
      ],
      "ideal": [
        7,
        1
      ],
      "seed": [
        26,
        -4
      ],
      "weight": 1.4
    },
    "L1": {
      "baseline": [
        17,
        -12
      ],
      "ideal": [
        12,
        -9
      ],
      "seed": [
        30,
        -18
      ],
      "weight": 1.8
    },
    "TP1": {
      "baseline": [
        -18,
        -22
      ],
      "ideal": [
        -16,
        -18
      ],
      "seed": [
        -26,
        -28
      ],
      "weight": 0.8
    }
  },
  "routes": [
    [
      "A1",
      "C1"
    ],
    [
      "C1",
      "C2"
    ],
    [
      "C2",
      "L1"
    ],
    [
      "L1",
      "J1"
    ],
    [
      "U1",
      "TP1"
    ]
  ],
  "title": "Optimize RF feed placement and antenna keepout margin",
  "via_penalty": 2.2
}""")
BASELINE = json.loads(r"""{
  "cost": 41.9038,
  "details": {
    "C1_target_distance": 5.831,
    "C2_target_distance": 5.3852,
    "L1_target_distance": 5.831,
    "TP1_target_distance": 4.4721
  },
  "minimum_movable_clearance_mm": 10.198,
  "route_length_mm": 69.0971,
  "score": 76.9529,
  "via_count": 3
}""")


def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def parse_board(path):
    text = path.read_text(encoding="utf-8", errors="ignore")
    positions = {}
    for match in re.finditer(r'\(footprint\s+"[^"]+"\s+\(layer\s+"[^"]+"\)\s+\(at\s+([-0-9.]+)\s+([-0-9.]+)[^)]*\).*?\(property\s+"Reference"\s+"([^"]+)"\)', text, re.S):
        x, y, ref = match.groups()
        positions[ref] = [float(x), float(y)]
    via_count = len(re.findall(r'\(via\s+\(at\s+', text))
    return positions, via_count


def score(positions, via_count):
    bx, by = TASK["board"]
    movable = TASK["movable"]
    cost = 0.0
    details = {}
    for ref, item in movable.items():
        if ref not in positions:
            cost += 100.0
            details[f"{ref}_missing"] = 1
            continue
        d = dist(positions[ref], item["ideal"])
        details[f"{ref}_target_distance"] = round(d, 4)
        cost += d * item["weight"]
        if abs(positions[ref][0]) > bx / 2 - 2 or abs(positions[ref][1]) > by / 2 - 2:
            cost += 50.0
    refs = [ref for ref in movable if ref in positions]
    min_clearance = 999.0
    for i, a_ref in enumerate(refs):
        for b_ref in refs[i + 1:]:
            d = dist(positions[a_ref], positions[b_ref])
            min_clearance = min(min_clearance, d)
            if d < TASK["clearance"]:
                cost += (TASK["clearance"] - d) * 35.0
    route_len = 0.0
    fixed = TASK["fixed"]
    for start, end in TASK["routes"]:
        a = positions.get(start, fixed.get(start))
        b = positions.get(end, fixed.get(end))
        if a and b:
            route_len += dist(a, b)
        else:
            cost += 20.0
    cost += route_len * 0.08
    cost += via_count * TASK["via_penalty"]
    for a_ref, b_ref in TASK.get("pair_match", []):
        if a_ref in positions and b_ref in positions:
            cost += abs(abs(positions[a_ref][1]) - abs(positions[b_ref][1])) * 4.0
            cost += abs(positions[a_ref][0] - positions[b_ref][0]) * 1.5
    if "antenna_keepout" in TASK:
        center = TASK["antenna_keepout"]["center"]
        radius = TASK["antenna_keepout"]["radius"]
        for ref, pos in positions.items():
            if ref != "A1" and ref in movable and dist(pos, center) < radius:
                cost += (radius - dist(pos, center)) * 3.5
    if "access_bonus" in TASK:
        present = [positions[ref][1] for ref in TASK["access_bonus"] if ref in positions]
        if present:
            cost += max(0.0, 10.0 - sum(present) / len(present)) * 2.0
    return {
        "score": round(max(0.0, 100.0 - cost * 0.55), 4),
        "cost": round(cost, 4),
        "route_length_mm": round(route_len, 4),
        "via_count": via_count,
        "minimum_movable_clearance_mm": round(min_clearance, 4),
        "details": details,
    }


def main():
    board = DESKTOP / "optimized_board.kicad_pcb"
    if not board.exists():
        print(json.dumps({"score": 0.0, "error": "missing optimized_board.kicad_pcb", "baseline_score": BASELINE["score"]}, sort_keys=True))
        return
    positions, via_count = parse_board(board)
    result = score(positions, via_count)
    result.update({"metric_direction": "maximize", "metric_name": TASK["metric"], "baseline_score": BASELINE["score"]})
    report = DESKTOP / "optimization_report.json"
    if report.exists():
        try:
            result["submitted_report"] = json.loads(report.read_text(encoding="utf-8"))
        except Exception:
            result["report_parse_error"] = True
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
