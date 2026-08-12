from __future__ import annotations

import json
import math
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path


DESKTOP = Path(os.environ.get("ENGIWORLD_DESKTOP", Path.home() / "Desktop"))
TASK = json.loads(r"""{
  "board": [
    110,
    66
  ],
  "clearance": 3.0,
  "fixed": {
    "J1": [
      -48,
      0
    ],
    "J2": [
      48,
      0
    ],
    "U1": [
      8,
      0
    ]
  },
  "instruction_tail": "Shrink the input hot loop while leaving enough thermal spacing around D1 and L1.",
  "metric": "hot-loop compactness with thermal spacing",
  "movable": {
    "CIN1": {
      "baseline": [
        -20,
        8
      ],
      "ideal": [
        -12,
        4
      ],
      "seed": [
        -35,
        22
      ],
      "weight": 2.0
    },
    "CIN2": {
      "baseline": [
        -20,
        -8
      ],
      "ideal": [
        -12,
        -4
      ],
      "seed": [
        -35,
        -22
      ],
      "weight": 2.0
    },
    "D1": {
      "baseline": [
        20,
        8
      ],
      "ideal": [
        17,
        3
      ],
      "seed": [
        26,
        22
      ],
      "weight": 1.4
    },
    "L1": {
      "baseline": [
        24,
        -8
      ],
      "ideal": [
        20,
        -4
      ],
      "seed": [
        30,
        -22
      ],
      "weight": 1.3
    }
  },
  "routes": [
    [
      "J1",
      "CIN1"
    ],
    [
      "J1",
      "CIN2"
    ],
    [
      "CIN1",
      "U1"
    ],
    [
      "CIN2",
      "U1"
    ],
    [
      "U1",
      "D1"
    ],
    [
      "U1",
      "L1"
    ],
    [
      "L1",
      "J2"
    ]
  ],
  "title": "Optimize power-entry hot-loop and bulk capacitor placement",
  "via_penalty": 1.5
}""")
BASELINE = json.loads(r"""{
  "cost": 69.7216,
  "details": {
    "CIN1_target_distance": 8.9443,
    "CIN2_target_distance": 8.9443,
    "D1_target_distance": 5.831,
    "L1_target_distance": 5.6569
  },
  "minimum_movable_clearance_mm": 16.0,
  "route_length_mm": 174.0907,
  "score": 61.6531,
  "via_count": 3
}""")


def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _tokenize_sexpr(text):
    tokens = []
    index = 0
    while index < len(text):
        char = text[index]
        if char.isspace():
            index += 1
            continue
        if char == ";":
            newline = text.find("\n", index)
            index = len(text) if newline < 0 else newline + 1
            continue
        if char in "()":
            tokens.append(char)
            index += 1
            continue
        if char == '"':
            index += 1
            value = []
            while index < len(text):
                char = text[index]
                if char == '"':
                    index += 1
                    break
                if char == "\\":
                    index += 1
                    if index >= len(text):
                        raise ValueError("unterminated escape")
                    escapes = {"n": "\n", "r": "\r", "t": "\t"}
                    value.append(escapes.get(text[index], text[index]))
                    index += 1
                    continue
                value.append(char)
                index += 1
            else:
                raise ValueError("unterminated string")
            tokens.append("".join(value))
            continue
        end = index
        while end < len(text) and not text[end].isspace() and text[end] not in "();":
            end += 1
        if end == index:
            raise ValueError("invalid token")
        tokens.append(text[index:end])
        index = end
    return tokens


def _parse_sexpr(path):
    tokens = _tokenize_sexpr(path.read_text(encoding="utf-8"))
    roots = []
    stack = []
    for token in tokens:
        if token == "(":
            node = []
            if stack:
                stack[-1].append(node)
            else:
                roots.append(node)
            stack.append(node)
        elif token == ")":
            if not stack:
                raise ValueError("unexpected close parenthesis")
            stack.pop()
        else:
            if not stack:
                raise ValueError("atom outside expression")
            stack[-1].append(token)
    if stack or len(roots) != 1:
        raise ValueError("unbalanced or multiple root expressions")
    return roots[0]


def _children(node, head):
    return [
        child
        for child in node[1:]
        if isinstance(child, list) and child and child[0] == head
    ]


def _first_child(node, head):
    matches = _children(node, head)
    if len(matches) != 1:
        raise ValueError(f"expected one {head}")
    return matches[0]


def _normalize(node, net_by_ordinal):
    if not isinstance(node, list):
        return node
    if node and node[0] in {"uuid", "tstamp"}:
        return None
    if node and node[0] == "net":
        if len(node) >= 3:
            return ["net", node[2]]
        if len(node) == 2:
            return ["net", net_by_ordinal.get(node[1], node[1])]
    normalized = []
    for item in node:
        value = _normalize(item, net_by_ordinal)
        if value is not None:
            normalized.append(value)
    return normalized


def _collect_net_names(node, net_by_ordinal):
    names = set()
    if not isinstance(node, list):
        return names
    if node and node[0] == "net":
        if len(node) >= 3:
            name = node[2]
        elif len(node) == 2:
            name = net_by_ordinal.get(node[1], node[1])
        else:
            name = ""
        if name:
            names.add(name)
    for item in node[1:]:
        names.update(_collect_net_names(item, net_by_ordinal))
    return names


def _board_semantics(path):
    root = _parse_sexpr(path)
    if not root or root[0] != "kicad_pcb":
        raise ValueError("not a KiCad PCB")

    net_by_ordinal = {}
    for net in _children(root, "net"):
        if len(net) != 3 or net[1] in net_by_ordinal:
            raise ValueError("invalid net table")
        net_by_ordinal[net[1]] = net[2]
    net_names = _collect_net_names(root, net_by_ordinal)
    if not net_names:
        raise ValueError("board has no named nets")

    positions = {}
    pad_fingerprints = {}
    for footprint in _children(root, "footprint"):
        references = [
            item[2]
            for item in _children(footprint, "property")
            if len(item) >= 3 and item[1] == "Reference"
        ]
        if len(references) != 1 or references[0] in positions:
            raise ValueError("invalid or duplicate footprint reference")
        ref = references[0]
        at = _first_child(footprint, "at")
        if len(at) < 3:
            raise ValueError("invalid footprint position")
        positions[ref] = [float(at[1]), float(at[2])]
        pads = _children(footprint, "pad")
        if not pads:
            raise ValueError(f"{ref} has no pads")
        pad_fingerprints[ref] = tuple(
            sorted(
                json.dumps(_normalize(pad, net_by_ordinal), separators=(",", ":"), sort_keys=False)
                for pad in pads
            )
        )

    edge_fingerprint = tuple(
        sorted(
            json.dumps(_normalize(item, net_by_ordinal), separators=(",", ":"), sort_keys=False)
            for item in root[1:]
            if isinstance(item, list)
            and item
            and item[0].startswith("gr_")
            and any(
                isinstance(child, list)
                and len(child) >= 2
                and child[0] == "layer"
                and child[1] == "Edge.Cuts"
                for child in item[1:]
            )
        )
    )
    if not edge_fingerprint:
        raise ValueError("board has no Edge.Cuts geometry")
    route_count = len(_children(root, "segment")) + len(_children(root, "arc"))
    if route_count == 0:
        raise ValueError("board has no routed tracks")
    return {
        "positions": positions,
        "via_count": len(_children(root, "via")),
        "net_names": frozenset(net_names),
        "pads": pad_fingerprints,
        "edges": edge_fingerprint,
    }


def _run_cli(arguments):
    try:
        return subprocess.run(
            ["kicad-cli", *arguments],
            capture_output=True,
            text=True,
            timeout=90,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise ValueError(f"kicad-cli failed: {exc}") from exc


def validate_board(board):
    executable = shutil.which("kicad-cli")
    if not executable:
        raise ValueError("kicad-cli is unavailable")
    version = _run_cli(["version"])
    if version.returncode != 0 or not re.match(r"^10\.0\.2(?:\D|$)", version.stdout.strip()):
        raise ValueError("evaluator requires KiCad 10.0.2")

    seed = DESKTOP / "seed_board.kicad_pcb"
    if not seed.is_file():
        raise ValueError("missing seed_board.kicad_pcb")
    with tempfile.TemporaryDirectory(prefix="engiworld-kicad-eval-") as temp:
        temp_dir = Path(temp)
        candidate_copy = temp_dir / "candidate.kicad_pcb"
        seed_copy = temp_dir / "seed.kicad_pcb"
        shutil.copy2(board, candidate_copy)
        shutil.copy2(seed, seed_copy)
        for copy in (candidate_copy, seed_copy):
            upgraded = _run_cli(["pcb", "upgrade", "--force", str(copy)])
            if upgraded.returncode != 0:
                message = (upgraded.stderr or upgraded.stdout).strip()
                raise ValueError(f"KiCad cannot load board: {message[:240]}")
        drc_path = temp_dir / "candidate-drc.json"
        drc = _run_cli(
            [
                "pcb",
                "drc",
                "--format",
                "json",
                "--severity-all",
                "--exit-code-violations",
                "--output",
                str(drc_path),
                str(candidate_copy),
            ]
        )
        if drc.returncode != 0:
            raise ValueError("candidate board is not DRC-clean")
        candidate = _board_semantics(candidate_copy)
        source = _board_semantics(seed_copy)

    expected_refs = set(TASK["fixed"]) | set(TASK["movable"])
    if set(candidate["positions"]) != expected_refs or set(source["positions"]) != expected_refs:
        raise ValueError("reference set differs from the objective")
    if candidate["net_names"] != source["net_names"]:
        raise ValueError("net table changed")
    if candidate["pads"] != source["pads"]:
        raise ValueError("pad or pad/net topology changed")
    if candidate["edges"] != source["edges"]:
        raise ValueError("board outline changed")
    for ref, expected in TASK["fixed"].items():
        actual = candidate["positions"][ref]
        if dist(actual, expected) > 1e-3:
            raise ValueError(f"fixed anchor {ref} moved")
    return candidate["positions"], candidate["via_count"]


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
    report = DESKTOP / "optimization_report.json"
    if not report.is_file():
        print(json.dumps({"score": 0.0, "error": "missing optimization_report.json", "baseline_score": BASELINE["score"]}, sort_keys=True))
        return
    try:
        submitted_report = json.loads(report.read_text(encoding="utf-8"))
        if not isinstance(submitted_report, dict):
            raise ValueError("report must be a JSON object")
        positions, via_count = validate_board(board)
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"score": 0.0, "error": str(exc), "baseline_score": BASELINE["score"]}, sort_keys=True))
        return
    result = score(positions, via_count)
    result.update({"metric_direction": "maximize", "metric_name": TASK["metric"], "baseline_score": BASELINE["score"]})
    result["submitted_report"] = submitted_report
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
