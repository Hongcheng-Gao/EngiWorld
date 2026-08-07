from __future__ import annotations

import json
import sys
from pathlib import Path


def _desktop() -> Path:
    return Path(__file__).resolve().parent


def _references(path: Path) -> list[str]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    components = data.get("components")
    if not isinstance(components, list):
        raise ValueError("missing components")
    refs = []
    for component in components:
        if not isinstance(component, dict) or not isinstance(component.get("ref"), str):
            raise ValueError("invalid component")
        refs.append(component["ref"].strip())
    return refs


def evaluate() -> bool:
    desktop = _desktop()
    output = desktop / "merged_refdes.txt"
    if not output.is_file():
        return False
    try:
        expected = sorted(f"A:{ref}" for ref in _references(desktop / "design_a.schematic.json"))
        expected.extend(sorted(f"B:{ref}" for ref in _references(desktop / "design_b.schematic.json")))
        actual = [line.strip() for line in output.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
        return actual == expected
    except Exception:
        return False


if __name__ == "__main__":
    ok = evaluate()
    print("True" if ok else "False")
    sys.exit(0 if ok else 1)
