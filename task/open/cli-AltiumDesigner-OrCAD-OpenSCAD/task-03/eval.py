from __future__ import annotations

import json
import re
import sys
from pathlib import Path


def _desktop() -> Path:
    return Path(__file__).resolve().parent


def _components(path: Path) -> dict[str, str]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    components = data.get("components")
    if not isinstance(components, list):
        raise ValueError("missing components")
    result: dict[str, str] = {}
    for component in components:
        if not isinstance(component, dict):
            raise ValueError("invalid component")
        ref = str(component.get("ref", "")).strip()
        value = str(component.get("value", "")).strip()
        if not ref:
            raise ValueError("missing refdes")
        if ref in result and result[ref] != value:
            raise ValueError("multipart value mismatch")
        result[ref] = value
    return result


def _normalized_value(value: object) -> str:
    return re.sub(r"\s+", "", str(value)).casefold().replace("ohms", "").replace("ohm", "").replace("ω", "")


def evaluate() -> bool:
    desktop = _desktop()
    output = desktop / "diff.json"
    if not output.is_file():
        return False
    try:
        before = _components(desktop / "rev_a.schematic.json")
        after = _components(desktop / "rev_b.schematic.json")
        expected_added = set(after) - set(before)
        expected_removed = set(before) - set(after)
        expected_changed = {ref for ref in set(before) & set(after) if _normalized_value(before[ref]) != _normalized_value(after[ref])}

        actual = json.loads(output.read_text(encoding="utf-8-sig"))
        if not isinstance(actual, dict):
            return False
        added = actual.get("refdes_added")
        removed = actual.get("refdes_removed")
        changes = actual.get("value_changes")
        if not isinstance(added, list) or not isinstance(removed, list) or not isinstance(changes, list):
            return False
        if {str(ref).strip() for ref in added} != expected_added or len(added) != len(expected_added):
            return False
        if {str(ref).strip() for ref in removed} != expected_removed or len(removed) != len(expected_removed):
            return False

        actual_changes: dict[str, tuple[str, str]] = {}
        for change in changes:
            if not isinstance(change, dict):
                return False
            ref = str(change.get("ref", "")).strip()
            if not ref or ref in actual_changes:
                return False
            actual_changes[ref] = (str(change.get("before", "")).strip(), str(change.get("after", "")).strip())
        if set(actual_changes) != expected_changed:
            return False
        return all(
            _normalized_value(actual_changes[ref][0]) == _normalized_value(before[ref])
            and _normalized_value(actual_changes[ref][1]) == _normalized_value(after[ref])
            for ref in expected_changed
        )
    except Exception:
        return False


if __name__ == "__main__":
    ok = evaluate()
    print("True" if ok else "False")
    sys.exit(0 if ok else 1)
