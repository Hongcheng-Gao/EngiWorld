from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path


DESKTOP = Path(os.environ.get("ENGIWORLD_DESKTOP", Path(__file__).resolve().parent))
RESULT_DIR = DESKTOP / "result"


def _load_json(name: str):
    return json.loads((DESKTOP / name).read_text(encoding="utf-8"))


def _load_result_json(name: str):
    return json.loads((RESULT_DIR / name).read_text(encoding="utf-8"))


def evaluate() -> bool:
    source_required = (
        "demo.pcb.json",
        "rules.txt",
        "base_padstack.txt",
        "devices.json",
    )
    output_required = (
        "board_summary.json",
        "plan.json",
    )
    if not all((DESKTOP / name).is_file() for name in source_required):
        return False
    if not all((RESULT_DIR / name).is_file() for name in output_required):
        return False
    try:
        board = _load_json("demo.pcb.json")
        devices = _load_json("devices.json")
        summary = _load_result_json("board_summary.json")
        plan = _load_result_json("plan.json")
        rules = (DESKTOP / "rules.txt").read_text(encoding="utf-8")
        padstacks = (DESKTOP / "base_padstack.txt").read_text(encoding="utf-8")
        clearance_match = re.search(r"Min\s+clearance\s*:\s*([0-9]+(?:\.[0-9]+)?)\s*mil", rules, re.I)
        drill_match = re.search(r"Min\s+drill\s*:\s*([0-9]+(?:\.[0-9]+)?)\s*mil", rules, re.I)
        if not clearance_match or not drill_match:
            return False
        min_clearance = float(clearance_match.group(1))
        min_drill = float(drill_match.group(1))
        padstack_drills = [
            float(parts[1])
            for line in padstacks.splitlines()
            if len(parts := line.split()) >= 3
        ]
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        return False

    expected_summary = {
        "component_count": len(board.get("components", [])),
        "layer_count": len(board.get("layers", [])),
        "net_count": len(board.get("nets", [])),
        "via_count": len(board.get("vias", [])),
    }
    if summary != expected_summary:
        return False

    blockers = [
        violation.get("id")
        for violation in board.get("violations", [])
        if str(violation.get("severity", "")).casefold() == "error"
    ]
    variants = devices.get("assembly_variants")
    if not isinstance(variants, list) or not all(isinstance(item, str) for item in variants):
        return False
    expected_plan = {
        "assembly_variants": variants,
        "blocking_violation_ids": blockers,
        "fab_ready": not blockers,
        "min_clearance_mil": min_clearance,
        "min_drill_mil": min_drill,
    }
    if plan != expected_plan:
        return False
    return bool(padstack_drills) and min(padstack_drills) == min_drill


if __name__ == "__main__":
    ok = evaluate()
    print("True" if ok else "False")
    sys.exit(0 if ok else 1)
