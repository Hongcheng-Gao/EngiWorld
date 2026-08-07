from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path


def _desktop() -> Path:
    return Path(__file__).resolve().parent


def _integer(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _expected(path: Path) -> tuple[str, dict[str, tuple[int, int, Counter[str]]]]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    components = data.get("components")
    schematics = data.get("schematics")
    if not isinstance(components, list) or not isinstance(schematics, list):
        raise ValueError("invalid source")
    root = str(data.get("properties", {}).get("root") or data.get("name") or "").strip()
    result: dict[str, tuple[int, int, Counter[str]]] = {}
    for schematic in schematics:
        if not isinstance(schematic, dict):
            raise ValueError("invalid schematic")
        name = str(schematic.get("name", "")).strip()
        pages = [str(page).strip() for page in schematic.get("pages", [])]
        blocks = schematic.get("hier_blocks", [])
        if not name or not isinstance(blocks, list):
            raise ValueError("invalid hierarchy")
        total_parts = sum(
            1 for component in components
            if isinstance(component, dict) and str(component.get("page", "")).strip() in set(pages)
        )
        child_names = Counter(str(block.get("child", "")).strip() for block in blocks if isinstance(block, dict))
        if "" in child_names:
            raise ValueError("missing hierarchy child")
        result[name] = (len(pages), total_parts, child_names)
    return root, result


def evaluate() -> bool:
    desktop = _desktop()
    output = desktop / "hierarchy.json"
    if not output.is_file():
        return False
    try:
        expected_root, expected_schematics = _expected(desktop / "fulladd.schematic.json")
        actual = json.loads(output.read_text(encoding="utf-8-sig"))
        if not isinstance(actual, dict) or str(actual.get("root", "")).strip() != expected_root:
            return False
        schematics = actual.get("schematics")
        if not isinstance(schematics, dict) or set(schematics) != set(expected_schematics):
            return False
        for name, (page_count, total_parts, child_names) in expected_schematics.items():
            entry = schematics.get(name)
            if not isinstance(entry, dict):
                return False
            blocks = entry.get("referenced_hier_blocks")
            if not isinstance(blocks, list):
                return False
            if _integer(entry.get("page_count")) != page_count or _integer(entry.get("total_parts")) != total_parts:
                return False
            if Counter(str(child).strip() for child in blocks) != child_names:
                return False
        return True
    except Exception:
        return False


if __name__ == "__main__":
    ok = evaluate()
    print("True" if ok else "False")
    sys.exit(0 if ok else 1)
