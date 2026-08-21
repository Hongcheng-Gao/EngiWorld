from __future__ import annotations

import csv
import json
import re
import sys
from decimal import Decimal, InvalidOperation
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


def _engineering_value(value: object) -> Decimal | None:
    text = str(value).strip().casefold().replace("µ", "u").replace("μ", "u").replace("ω", "ohm")
    text = re.sub(r"\s+", "", text)
    text = re.sub(r"(?:ohms?|farads?|f)$", "", text)
    embedded = re.fullmatch(r"([+-]?\d+)(meg|[tgkmunpr])(\d+)", text)
    multipliers = {
        "t": Decimal("1e12"), "g": Decimal("1e9"), "meg": Decimal("1e6"),
        "k": Decimal("1e3"), "r": Decimal(1), "m": Decimal("1e-3"),
        "u": Decimal("1e-6"), "n": Decimal("1e-9"), "p": Decimal("1e-12"),
    }
    try:
        if embedded:
            return Decimal(f"{embedded.group(1)}.{embedded.group(3)}") * multipliers[embedded.group(2)]
        match = re.fullmatch(r"([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?)(meg|[tgkmunp]?)", text)
        if not match:
            return None
        return Decimal(match.group(1)) * multipliers.get(match.group(2), Decimal(1))
    except InvalidOperation:
        return None


def _same_value(left: object, right: object) -> bool:
    left_number, right_number = _engineering_value(left), _engineering_value(right)
    if left_number is not None and right_number is not None:
        return left_number == right_number
    return re.sub(r"\s+", "", str(left)).casefold() == re.sub(r"\s+", "", str(right)).casefold()


def _csv_values(path: Path) -> dict[str, str]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = {_norm(name): name for name in (reader.fieldnames or [])}
        ref_header = next((headers[name] for name in REF_KEYS if name in headers), None)
        value_header = next((headers[name] for name in VALUE_KEYS if name in headers), None)
        if not ref_header or not value_header:
            raise ValueError("missing CSV columns")
        result: dict[str, str] = {}
        for row in reader:
            ref = str(row[ref_header]).strip().upper()
            if not ref or ref in result:
                raise ValueError("invalid CSV refdes")
            result[ref] = str(row[value_header]).strip()
        return result


def evaluate() -> bool:
    desktop = _desktop()
    required = [desktop / "result" / "tutor2_values.edif", desktop / "result" / "tutor2_values.schematic.json", desktop / "result" / "value_report.csv"]
    if not all(path.is_file() and path.stat().st_size for path in required):
        return False
    try:
        source = _json_components(desktop / "tutor2_wrong_values.schematic.json")
        expected_changes = {"R1": "10k", "R2": "4.7k", "C1": "100nF", "C2": "10uF"}
        json_output = _json_components(required[1])
        edif_output = _edif_components(required[0])
        if set(json_output) != set(source) or not set(source).issubset(edif_output):
            return False
        for ref, original in source.items():
            expected = expected_changes.get(ref, original.get("value"))
            if not _same_value(json_output[ref].get("value"), expected) or not _same_value(edif_output[ref].get("value"), expected):
                return False
        report = _csv_values(required[2])
        return set(report) == set(expected_changes) and all(_same_value(report[ref], value) for ref, value in expected_changes.items())
    except Exception:
        return False


if __name__ == "__main__":
    ok = evaluate()
    print("True" if ok else "False")
    sys.exit(0 if ok else 1)
