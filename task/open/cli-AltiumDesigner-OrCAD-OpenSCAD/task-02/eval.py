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
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number if str(number) == str(value).strip() or isinstance(value, int) else None


def _source_semantics(path: Path) -> tuple[str, int, Counter[tuple[str, str, str]]]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    schematics = data.get("schematics")
    components = data.get("components")
    if not isinstance(schematics, list) or not isinstance(components, list):
        raise ValueError("invalid source")

    root = str(data.get("properties", {}).get("root") or data.get("name") or "").strip()
    by_name = {str(item.get("name", "")).strip(): item for item in schematics if isinstance(item, dict)}
    if not root or root not in by_name:
        raise ValueError("missing root")

    own_parts: dict[str, int] = {}
    all_blocks: Counter[tuple[str, str, str]] = Counter()
    children: dict[str, list[str]] = {}
    for name, schematic in by_name.items():
        pages = {str(page).strip() for page in schematic.get("pages", [])}
        own_parts[name] = sum(
            1 for component in components
            if isinstance(component, dict) and str(component.get("page", "")).strip() in pages
        )
        children[name] = []
        for block in schematic.get("hier_blocks", []):
            if not isinstance(block, dict):
                raise ValueError("invalid hierarchy block")
            parent = str(block.get("parent", name)).strip()
            ref = str(block.get("ref", "")).strip()
            child = str(block.get("child", "")).strip()
            if not parent or not ref or not child:
                raise ValueError("incomplete hierarchy block")
            all_blocks[(parent, ref, child)] += 1
            children[name].append(child)

    def flattened_count(name: str, active: frozenset[str] = frozenset()) -> int:
        if name in active or name not in own_parts:
            raise ValueError("cyclic or missing hierarchy")
        return own_parts[name] + sum(flattened_count(child, active | {name}) for child in children[name])

    return root, flattened_count(root), all_blocks


def evaluate() -> bool:
    desktop = _desktop()
    output = desktop / "result" / "flat.json"
    if not output.is_file():
        return False
    try:
        expected_root, expected_count, expected_blocks = _source_semantics(desktop / "fulladd.schematic.json")
        actual = json.loads(output.read_text(encoding="utf-8-sig"))
        if not isinstance(actual, dict):
            return False
        if str(actual.get("root_schematic", "")).strip() != expected_root:
            return False
        if _integer(actual.get("total_primitive_parts")) != expected_count:
            return False
        expansions = actual.get("hier_block_expansions")
        if not isinstance(expansions, list):
            return False
        actual_blocks: Counter[tuple[str, str, str]] = Counter()
        for block in expansions:
            if not isinstance(block, dict):
                return False
            record = tuple(str(block.get(key, "")).strip() for key in ("parent", "ref", "child"))
            if not all(record):
                return False
            actual_blocks[record] += 1
        return actual_blocks == expected_blocks
    except Exception:
        return False


if __name__ == "__main__":
    ok = evaluate()
    print("True" if ok else "False")
    sys.exit(0 if ok else 1)
