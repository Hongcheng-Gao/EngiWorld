from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path


REF_KEYS = {"ref", "reference", "refdes", "referencedesignator", "designator"}
VALUE_KEYS = {"value", "componentvalue", "partvalue"}


def _desktop() -> Path:
    return Path(__file__).resolve().parent


def _norm(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value).casefold())


def _json_components(path: Path) -> dict[str, dict[str, object]]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    found: dict[str, dict[str, object]] = {}

    def visit(value: object, parent_key: str = "") -> None:
        if isinstance(value, dict):
            normalized = {_norm(key): item for key, item in value.items()}
            ref = next((normalized[key] for key in REF_KEYS if key in normalized), None)
            if ref is None and re.fullmatch(r"[A-Za-z]+\d+", parent_key):
                ref = parent_key
            if ref is not None:
                ref_text = str(ref).strip().upper()
                properties: dict[str, object] = {}
                for key, item in value.items():
                    if _norm(key) in {"properties", "property", "parameters", "attributes", "fields"} and isinstance(item, dict):
                        properties.update(item)
                    elif _norm(key) not in REF_KEYS:
                        properties.setdefault(key, item)
                component_value = next((normalized[key] for key in VALUE_KEYS if key in normalized), None)
                candidate = {"value": component_value, "properties": properties}
                if ref_text and (ref_text not in found or len(properties) > len(found[ref_text]["properties"])):
                    found[ref_text] = candidate
            for key, item in value.items():
                visit(item, str(key))
        elif isinstance(value, list):
            for item in value:
                visit(item, parent_key)

    visit(data)
    return found


def _atom(node: object) -> str:
    if isinstance(node, str):
        if len(node) >= 2 and node[0] == node[-1] == '"':
            return node[1:-1].replace(r'\"', '"').replace(r"\\", "\\")
        return node
    if isinstance(node, list) and node:
        if _norm(node[0]) == "rename" and len(node) >= 3:
            return _atom(node[-1])
        if len(node) >= 2:
            return _atom(node[1])
    return ""


def _walk(node: object):
    if isinstance(node, list):
        yield node
        for child in node:
            yield from _walk(child)


def _edif_components(path: Path) -> dict[str, dict[str, object]]:
    tokens = re.findall(r'"(?:\\.|[^"\\])*"|[()]|[^\s()]+', path.read_text(encoding="utf-8-sig", errors="ignore"))
    roots: list[object] = []
    stack: list[list[object]] = []
    for token in tokens:
        if token == "(":
            node: list[object] = []
            (stack[-1] if stack else roots).append(node)
            stack.append(node)
        elif token == ")":
            if not stack:
                raise ValueError("unbalanced EDIF")
            stack.pop()
        elif stack:
            stack[-1].append(token)
    if stack:
        raise ValueError("unbalanced EDIF")

    result: dict[str, dict[str, object]] = {}
    for node in _walk(roots):
        if not node or _norm(node[0]) != "instance" or len(node) < 2:
            continue
        ref = _atom(node[1]).strip().upper()
        properties: dict[str, object] = {}
        for child in _walk(node[2:]):
            if child and _norm(child[0]) == "property" and len(child) >= 3:
                properties[_atom(child[1])] = _atom(child[2])
        for key, value in properties.items():
            if _norm(key) in REF_KEYS and str(value).strip():
                ref = str(value).strip().upper()
        value = next((item for key, item in properties.items() if _norm(key) in VALUE_KEYS), None)
        if ref:
            result[ref] = {"value": value, "properties": properties}
    return result


def _csv_rows(path: Path) -> list[tuple[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = {_norm(name): name for name in (reader.fieldnames or [])}
        old_header = next((headers[name] for name in {"oldref", "oldreference", "beforeref"} if name in headers), None)
        new_header = next((headers[name] for name in {"newref", "newreference", "afterref"} if name in headers), None)
        if not old_header or not new_header:
            raise ValueError("missing CSV columns")
        return [(str(row[old_header]).strip().upper(), str(row[new_header]).strip().upper()) for row in reader]


def _same_text(left: object, right: object) -> bool:
    return re.sub(r"\s+", "", str(left)).casefold() == re.sub(r"\s+", "", str(right)).casefold()


def _valid_generated_refs(refs: set[str], placeholders: list[dict[str, object]]) -> bool:
    expected_prefixes = Counter(str(item["ref"])[:-1].upper() for item in placeholders)
    actual_by_prefix: dict[str, list[int]] = {}
    for ref in refs:
        match = re.fullmatch(r"([A-Z]+)(\d+)", ref)
        if not match or int(match.group(2)) < 1:
            return False
        actual_by_prefix.setdefault(match.group(1), []).append(int(match.group(2)))
    if Counter({prefix: len(numbers) for prefix, numbers in actual_by_prefix.items()}) != expected_prefixes:
        return False
    return all(sorted(numbers) == list(range(min(numbers), min(numbers) + len(numbers))) for numbers in actual_by_prefix.values())


def evaluate() -> bool:
    desktop = _desktop()
    required = [desktop / "tutor2_reannotated.edif", desktop / "tutor2_reannotated.schematic.json", desktop / "annotation_report.csv"]
    if not all(path.is_file() and path.stat().st_size for path in required):
        return False
    try:
        source_data = json.loads((desktop / "tutor2_unannotated.schematic.json").read_text(encoding="utf-8-sig"))
        source_items = source_data.get("components")
        if not isinstance(source_items, list):
            return False
        placeholders = [item for item in source_items if isinstance(item, dict) and str(item.get("ref", "")).endswith("?")]
        preserved = {
            str(item["ref"]).strip().upper(): str(item.get("value", "")).strip()
            for item in source_items if isinstance(item, dict) and not str(item.get("ref", "")).endswith("?")
        }
        json_output = _json_components(required[1])
        edif_output = _edif_components(required[0])
        if len(json_output) != len(source_items) or not set(preserved).issubset(json_output):
            return False
        generated = set(json_output) - set(preserved)
        if not _valid_generated_refs(generated, placeholders) or set(json_output) != set(preserved) | generated:
            return False
        if not set(json_output).issubset(edif_output):
            return False
        for ref, value in preserved.items():
            if not _same_text(json_output[ref].get("value"), value) or not _same_text(edif_output[ref].get("value"), value):
                return False
        expected_values = Counter((str(item["ref"])[:-1].upper(), str(item.get("value", "")).casefold()) for item in placeholders)
        for output in (json_output, edif_output):
            generated_values = Counter((re.match(r"[A-Z]+", ref).group(), str(output[ref].get("value", "")).casefold()) for ref in generated)
            if generated_values != expected_values:
                return False
        rows = _csv_rows(required[2])
        expected_old = Counter(str(item["ref"]).strip().upper() for item in placeholders)
        return Counter(old for old, _ in rows) == expected_old and Counter(new for _, new in rows) == Counter(generated)
    except Exception:
        return False


if __name__ == "__main__":
    ok = evaluate()
    print("True" if ok else "False")
    sys.exit(0 if ok else 1)
