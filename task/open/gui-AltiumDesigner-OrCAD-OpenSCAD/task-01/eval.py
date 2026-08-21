from __future__ import annotations

import csv
import json
import re
import sys
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


def _property(component: dict[str, object], *names: str) -> object | None:
    aliases = {_norm(name) for name in names}
    properties = component.get("properties", {})
    if not isinstance(properties, dict):
        return None
    return next((value for key, value in properties.items() if _norm(key) in aliases), None)


def _same_text(left: object, right: object) -> bool:
    return re.sub(r"\s+", "", str(left)).casefold() == re.sub(r"\s+", "", str(right)).casefold()


def _install(value: object) -> str | None:
    normalized = _norm(value)
    if normalized in {"y", "yes", "true", "1", "installed", "fitted", "populate", "populated"}:
        return "Y"
    if normalized in {"n", "no", "false", "0", "notinstalled", "notfitted", "dnp", "donotpopulate"}:
        return "N"
    return None


def _csv_rows(path: Path) -> list[tuple[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = {_norm(name): name for name in (reader.fieldnames or [])}
        ref_header = next((headers[name] for name in REF_KEYS if name in headers), None)
        install_header = next((headers[name] for name in {"install", "fitted", "populate"} if name in headers), None)
        if not ref_header or not install_header:
            raise ValueError("missing CSV columns")
        return [(str(row[ref_header]).strip().upper(), str(row[install_header]).strip()) for row in reader]


def evaluate() -> bool:
    desktop = _desktop()
    required = [desktop / "result" / "bcd_install.edif", desktop / "result" / "bcd_install.schematic.json", desktop / "result" / "install_properties.csv"]
    if not all(path.is_file() and path.stat().st_size for path in required):
        return False
    try:
        source = _json_components(desktop / "bcd.schematic.json")
        json_output = _json_components(required[1])
        edif_output = _edif_components(required[0])
        expected_install = {"U30": "Y", "U31": "Y", "U32": "N", "U33": "Y", "U34": "N"}
        if set(json_output) != set(source) or not set(source).issubset(edif_output):
            return False
        for ref, original in source.items():
            for output in (json_output, edif_output):
                if not _same_text(output[ref].get("value"), original.get("value")):
                    return False
                install = _property(output[ref], "Install", "Fitted", "Populate")
                if ref in expected_install:
                    if _install(install) != expected_install[ref]:
                        return False
                elif install not in (None, ""):
                    return False
        rows = _csv_rows(required[2])
        return len(rows) == len(expected_install) and {ref: _install(value) for ref, value in rows} == expected_install
    except Exception:
        return False


if __name__ == "__main__":
    ok = evaluate()
    print("True" if ok else "False")
    sys.exit(0 if ok else 1)
