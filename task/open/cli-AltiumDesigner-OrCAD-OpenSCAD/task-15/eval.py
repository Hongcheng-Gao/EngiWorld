from __future__ import annotations

import csv
import json
import math
import os
import sys
from pathlib import Path


DESKTOP = Path(os.environ.get("ENGIWORLD_DESKTOP", Path(__file__).resolve().parent))
RESULT_DIR = DESKTOP / "result"


def _csv_rows(path: Path, header: list[str]) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != header:
            raise ValueError("CSV header mismatch")
        return list(reader)


def _numbers_equal(actual: str, expected: float) -> bool:
    try:
        value = float(actual)
    except (TypeError, ValueError):
        return False
    return math.isfinite(value) and abs(value - expected) <= max(1e-6, abs(expected) * 1e-9)


def evaluate() -> bool:
    source_path = DESKTOP / "routed_board.pcb.json"
    locked_path = DESKTOP / "locked_release.pcb.json"
    etch_path = DESKTOP / "result" / "etch_lengths.csv"
    pair_path = DESKTOP / "result" / "diffpair_lengths.csv"
    if not source_path.is_file() or not locked_path.is_file() or not etch_path.is_file() or not pair_path.is_file():
        return False
    try:
        source = json.loads(source_path.read_text(encoding="utf-8"))
        locked = json.loads(locked_path.read_text(encoding="utf-8"))
        etch_rows = _csv_rows(etch_path, ["Net", "Length_mil"])
        pair_rows = _csv_rows(
            pair_path,
            ["Pair", "Negative_mil", "Positive_mil", "Delta_mil"],
        )
        expected_etch = {
            item["name"]: float(item["length_mil"])
            for item in source["etch_lengths"]
        }
        expected_pairs = {
            item["name"]: (
                float(item["length_n_mil"]),
                float(item["length_p_mil"]),
                abs(float(item["length_n_mil"]) - float(item["length_p_mil"])),
            )
            for item in source["diffpairs"]
        }
        locked_etch = {
            item["name"]: float(item["length_mil"])
            for item in locked["etch_lengths"]
        }
        locked_pairs = {
            item["name"]: (
                float(item["length_n_mil"]),
                float(item["length_p_mil"]),
                abs(float(item["length_n_mil"]) - float(item["length_p_mil"])),
            )
            for item in locked["diffpairs"]
        }
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return False

    if expected_etch != locked_etch or expected_pairs != locked_pairs:
        return False
    if len(etch_rows) != len(expected_etch) or len(pair_rows) != len(expected_pairs):
        return False
    if len({row.get("Net") for row in etch_rows}) != len(etch_rows):
        return False
    if len({row.get("Pair") for row in pair_rows}) != len(pair_rows):
        return False
    for row in etch_rows:
        name = row.get("Net")
        if name not in expected_etch or not _numbers_equal(row.get("Length_mil"), expected_etch[name]):
            return False
    for row in pair_rows:
        name = row.get("Pair")
        if name not in expected_pairs:
            return False
        expected = expected_pairs[name]
        actual = (row.get("Negative_mil"), row.get("Positive_mil"), row.get("Delta_mil"))
        if not all(_numbers_equal(value, target) for value, target in zip(actual, expected)):
            return False
    return True


if __name__ == "__main__":
    ok = evaluate()
    print("True" if ok else "False")
    sys.exit(0 if ok else 1)
