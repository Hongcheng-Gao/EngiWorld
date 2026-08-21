from __future__ import annotations

import json
import re
import sys
from pathlib import Path


def _desktop() -> Path:
    return Path(__file__).resolve().parent


def _natural(value: str) -> list[object]:
    return [int(part) if part.isdigit() else part.casefold() for part in re.split(r"(\d+)", value)]


def _integer(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def evaluate() -> bool:
    desktop = _desktop()
    output = desktop / "result" / "pin_map.json"
    if not output.is_file():
        return False
    try:
        source = json.loads((desktop / "tutor2.schematic.json").read_text(encoding="utf-8-sig"))
        expected: dict[str, list[str]] = {}
        for component in source.get("components", []):
            ref = str(component.get("ref", "")).strip()
            pins = [str(pin).strip() for pin in component.get("pins", [])]
            if not ref or not pins or ref in expected:
                return False
            expected[ref] = sorted(pins, key=_natural)

        actual = json.loads(output.read_text(encoding="utf-8-sig"))
        parts = actual.get("parts") if isinstance(actual, dict) else None
        if not isinstance(parts, list):
            return False
        actual_refs = [str(part.get("ref", "")).strip() for part in parts if isinstance(part, dict)]
        if len(actual_refs) != len(parts) or actual_refs != sorted(expected, key=_natural):
            return False
        if set(actual_refs) != set(expected):
            return False
        for part in parts:
            pins = part.get("pin_numbers")
            if not isinstance(pins, list):
                return False
            normalized_pins = [str(pin).strip() for pin in pins]
            if normalized_pins != expected[str(part["ref"]).strip()]:
                return False
            if _integer(part.get("pin_count")) != len(normalized_pins):
                return False
        total_pins = sum(len(pins) for pins in expected.values())
        return _integer(actual.get("total_parts")) == len(expected) and _integer(actual.get("total_pins")) == total_pins
    except Exception:
        return False


if __name__ == "__main__":
    ok = evaluate()
    print("True" if ok else "False")
    sys.exit(0 if ok else 1)
