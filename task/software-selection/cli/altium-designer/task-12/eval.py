from __future__ import annotations

import base64
import csv
import io
import json
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

EXPECTED = {
  "collision_report.json": "ewogICJjaGVja2VkX2NvbXBvbmVudHMiOiA0LAogICJjb2xsaXNpb25zIjogW10sCiAgInN0YXR1cyI6ICJjbGVhciIKfQo=",
  "demo.drl": "TTQ4DQo7TGF5ZXJfQ29sb3I9OTQ3NDMwNA0KO0ZJTEVfRk9STUFUPTI6NQ0KSU5DSCxMWg0KO1RZUEU9UExBVEVEDQpUMUYwMFMwMEMwLjAxMDAwDQpUMkYwMFMwMEMwLjAxMjAwDQolDQpUMDENClgwMDU5MDU1WTAxMzc3OTUNClQwMg0KWDAwNTkwNTVZMDA1OTA1NQ0KWDAxMzc3OTUNCk0zMA0K",
  "ncdrill.log": "LS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLQ0KTkNEcmlsbCBGaWxlIFJlcG9ydCBGb3I6IGRlbW8uUGNiRG9jICAgOC8xNi8yMDI2ICAxOjAzOjUzIFBNDQotLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tDQoNCkxheWVyIFBhaXIgOiBUb3AgTGF5ZXIgdG8gQm90dG9tIExheWVyDQpBU0NJSSBSb3VuZEhvbGVzIEZpbGUgOiBkZW1vLlRYVA0KDQpUb29sICAgICAgIEhvbGUgU2l6ZSAgICAgICAgICAgICAgIEhvbGUgVG9sZXJhbmNlICAgICAgICAgICAgICAgSG9sZSBUeXBlICAgICAgIEhvbGUgQ291bnQgICBQbGF0ZWQgICAgICAgICBUb29sIFRyYXZlbA0KLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLQ0KVDEgICAgICAxMG1pbCAoMC4yNTRtbSkgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgUm91bmQgICAgICAgICAgICAgMSAgICAgICAgIFBUSCAgICAgICAgMC4wMGluY2ggKDAuMDBtbSkNClQyICAgICAgMTJtaWwgKDAuMzA1bW0pICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIFJvdW5kICAgICAgICAgICAgIDIgICAgICAgICBQVEggICAgICAgIDAuNzlpbmNoICgyMC4wMG1tKQ0KLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLQ0KVG90YWxzICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgMw0KDQpUb3RhbCBQcm9jZXNzaW5nIFRpbWUgKGhoOm1tOnNzKSA6IDAwOjAwOjAwDQo="
}

EXPECTED_UNITS = "INCH"
EXPECTED_PLATED = True
EXPECTED_HITS_MM = sorted(
    [
        (0.254, 15.0, 35.0),
        (0.3048, 15.0, 15.0),
        (0.3048, 35.0, 15.0),
    ]
)
EXPECTED_TOOL_COUNTS_MIL = {10.0: 1, 12.0: 2}
EXPECTED_COLLISION_REPORT = {
    "checked_components": 4,
    "collisions": [],
    "status": "clear",
}


def _desktop() -> Path:
    return Path(__file__).resolve().parent


def _decode(name: str) -> bytes:
    return base64.b64decode(EXPECTED[name].encode("ascii"))


def _text(data: bytes) -> str:
    return data.decode("utf-8", errors="replace").replace("\r\n", "\n").replace("\r", "\n").rstrip() + "\n"


_VOLATILE_JSON_KEYS = {
    "created_at", "exported_at", "generated_at", "generator", "timestamp",
    "tool_version", "exporter_version",
}
_VOLATILE_XML_ATTRS = {
    "created", "created_at", "date", "exported_at", "generated_at",
    "generator", "timestamp", "time", "tool_version", "exporter_version",
}


def _number(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str) and re.fullmatch(r"[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?", value.strip()):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _scalar_equal(actual, expected) -> bool:
    actual_number = _number(actual)
    expected_number = _number(expected)
    if actual_number is not None and expected_number is not None:
        tolerance = max(1e-6, abs(expected_number) * 1e-6)
        return abs(actual_number - expected_number) <= tolerance
    boolean_values = {"true": True, "false": False}
    actual_boolean = (
        boolean_values.get(actual.strip().lower())
        if isinstance(actual, str) else actual if isinstance(actual, bool) else None
    )
    expected_boolean = (
        boolean_values.get(expected.strip().lower())
        if isinstance(expected, str) else expected if isinstance(expected, bool) else None
    )
    if actual_boolean is not None and expected_boolean is not None:
        return actual_boolean == expected_boolean
    return actual == expected


def _json_value_equal(actual, expected) -> bool:
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            return False
        expected_keys = {key for key in expected if key.lower() not in _VOLATILE_JSON_KEYS}
        actual_keys = {key for key in actual if key.lower() not in _VOLATILE_JSON_KEYS}
        if actual_keys != expected_keys:
            return False
        return all(_json_value_equal(actual[key], expected[key]) for key in expected_keys)
    if isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            return False
        unmatched = list(actual)
        for expected_item in expected:
            for index, actual_item in enumerate(unmatched):
                if _json_value_equal(actual_item, expected_item):
                    unmatched.pop(index)
                    break
            else:
                return False
        return not unmatched
    return _scalar_equal(actual, expected)


def _json_equal(path: Path, expected: bytes) -> bool:
    try:
        actual_value = json.loads(path.read_text(encoding="utf-8-sig"))
        expected_value = json.loads(expected.decode("utf-8-sig"))
        return _json_value_equal(actual_value, expected_value)
    except Exception:
        return False


def _csv_rows(data: str):
    rows = [
        [cell.strip() for cell in row]
        for row in csv.reader(io.StringIO(data.replace("\r\n", "\n").replace("\r", "\n")))
        if any(cell.strip() for cell in row)
    ]
    if not rows or len(set(header.lower() for header in rows[0])) != len(rows[0]):
        return None
    headers = [header.lower() for header in rows[0]]
    records = []
    for row in rows[1:]:
        if len(row) != len(headers):
            return None
        records.append({header: value for header, value in zip(headers, row)})
    return set(headers), records


def _csv_row_equal(actual, expected, headers) -> bool:
    return all(_scalar_equal(actual[header], expected[header]) for header in headers)


def _csv_equal(path: Path, expected: bytes) -> bool:
    try:
        actual = _csv_rows(path.read_text(encoding="utf-8-sig"))
        target = _csv_rows(expected.decode("utf-8-sig"))
        if actual is None or target is None or actual[0] != target[0]:
            return False
        headers = sorted(target[0])
        unmatched = list(actual[1])
        if len(unmatched) != len(target[1]):
            return False
        for expected_row in target[1]:
            for index, actual_row in enumerate(unmatched):
                if _csv_row_equal(actual_row, expected_row, headers):
                    unmatched.pop(index)
                    break
            else:
                return False
        return not unmatched
    except Exception:
        return False


def _local_name(name: str) -> str:
    return name.rsplit("}", 1)[-1].lower()


def _xml_value_equal(actual: str, expected: str) -> bool:
    return _scalar_equal(" ".join(actual.split()), " ".join(expected.split()))


def _xml_element_equal(actual, expected) -> bool:
    if _local_name(actual.tag) != _local_name(expected.tag):
        return False

    actual_attrs = {
        _local_name(key): str(value)
        for key, value in actual.attrib.items()
        if _local_name(key) not in _VOLATILE_XML_ATTRS
    }
    expected_attrs = {
        _local_name(key): str(value)
        for key, value in expected.attrib.items()
        if _local_name(key) not in _VOLATILE_XML_ATTRS
    }
    if set(actual_attrs) != set(expected_attrs):
        return False
    if not all(_xml_value_equal(actual_attrs[key], expected_attrs[key]) for key in expected_attrs):
        return False
    if not _xml_value_equal(actual.text or "", expected.text or ""):
        return False

    unmatched = list(actual)
    if len(unmatched) != len(expected):
        return False
    for expected_child in expected:
        for index, actual_child in enumerate(unmatched):
            if _xml_element_equal(actual_child, expected_child):
                unmatched.pop(index)
                break
        else:
            return False
    return not unmatched


def _xml_equal(path: Path, expected: bytes) -> bool:
    try:
        actual_root = ET.parse(path).getroot()
        expected_root = ET.fromstring(expected)
        return _xml_element_equal(actual_root, expected_root)
    except Exception:
        return False


def _edif_parse(text: str):
    tokens = re.findall(r'"(?:[^"\\]|\\.)*"|[()]|[^\s()]+', text)
    index = 0

    def parse_one():
        nonlocal index
        if index >= len(tokens):
            raise ValueError("unexpected end of EDIF")
        token = tokens[index]
        index += 1
        if token != "(":
            if token == ")":
                raise ValueError("unexpected close parenthesis")
            return token
        values = []
        while index < len(tokens) and tokens[index] != ")":
            values.append(parse_one())
        if index >= len(tokens):
            raise ValueError("unclosed EDIF expression")
        index += 1
        return values

    value = parse_one()
    if index != len(tokens):
        raise ValueError("trailing EDIF tokens")
    return value


def _edif_canon(value):
    if not isinstance(value, list):
        return value
    atoms = []
    children = []
    for item in value:
        if isinstance(item, list):
            canonical = _edif_canon(item)
            head = canonical[0][0].lower() if canonical and canonical[0] else ""
            if head != "status":
                children.append(canonical)
        else:
            atoms.append(item)
    return (tuple(atoms), tuple(sorted(children, key=repr)))


def _edif_equal(path: Path, expected: bytes) -> bool:
    try:
        actual = _edif_parse(path.read_text(encoding="utf-8-sig", errors="ignore"))
        target = _edif_parse(expected.decode("utf-8-sig", errors="ignore"))
        return _edif_canon(actual) == _edif_canon(target)
    except Exception:
        return False


def _gerber_valid(data: bytes) -> bool:
    text = _text(data).upper()
    return bool(re.search(r"%FS[^%]*\*%", text)) and "M02*" in text


def _log_equal(actual: bytes, expected: bytes) -> bool:
    actual_text = _text(actual)
    expected_text = _text(expected)
    critical = set(re.findall(r"\b[A-Z][A-Z0-9_.-]+\b|\b\d+(?:-\d+)?\b|\b[\w.-]+\.[A-Za-z0-9]+\b", expected_text))
    lowered = actual_text.lower()
    if not all(token.lower() in lowered for token in critical):
        return False
    if re.search(r"\bno\s+fatal\b", expected_text, re.IGNORECASE):
        return bool(re.search(r"\bno\s+fatal\b", actual_text, re.IGNORECASE))
    return True


def _drill_signature(data: bytes):
    text = _text(data).upper()
    units = "INCH" if "INCH" in text else "METRIC" if "METRIC" in text else None
    tools = sorted((tool, format(float(diameter), ".12g")) for tool, diameter in re.findall(r"T(\d+)C([0-9.]+)", text))
    coordinates = sorted(re.findall(r"X[-+]?\d+Y[-+]?\d+", text))
    return units, tools, coordinates


def _drill_number(token: str, decimal_digits: int | None) -> float:
    if "." in token:
        return float(token)
    if decimal_digits is None:
        raise ValueError("integer coordinates require FILE_FORMAT")
    return int(token) / (10 ** decimal_digits)


def _drill_valid(data: bytes) -> bool:
    text = _text(data).upper()
    if text.count("M48") != 1 or text.count("M30") != 1:
        return False
    units = "INCH" if re.search(r"\bINCH\b", text) else "METRIC" if re.search(r"\bMETRIC\b", text) else None
    if units is None:
        return False
    if units != EXPECTED_UNITS:
        return False

    plating_name = "PLATED" if EXPECTED_PLATED else "NONPLATED"
    if (
        re.search(rf"^\s*;\s*TYPE\s*=\s*{plating_name}\s*$", text, re.MULTILINE) is None
        or re.search(r"^\s*%\s*$", text, re.MULTILINE) is None
        or (EXPECTED_PLATED and re.search(r"^\s*;\s*TYPE\s*=\s*NONPLATED\s*$", text, re.MULTILINE) is not None)
    ):
        return False

    format_match = re.search(r"FILE_FORMAT\s*=\s*\d+\s*:\s*(\d+)", text)
    decimal_digits = int(format_match.group(1)) if format_match else None

    tool_diameters = {
        match.group(1).lstrip("0") or "0": float(match.group(2))
        for match in re.finditer(r"^T(\d+)(?:F\d+)?(?:S\d+)?C([0-9.]+)", text, re.MULTILINE)
    }
    active_tool = None
    hits = []
    last_x = None
    last_y = None
    scale = 25.4 if units == "INCH" else 1.0
    try:
        for raw_line in text.splitlines():
            line = raw_line.strip().rstrip("*")
            selection = re.fullmatch(r"T(\d+)", line)
            if selection:
                active_tool = selection.group(1).lstrip("0") or "0"
                continue
            coordinate = re.fullmatch(
                r"(?:X([-+]?(?:\d+(?:\.\d*)?|\.\d+)))?"
                r"(?:Y([-+]?(?:\d+(?:\.\d*)?|\.\d+)))?",
                line,
            )
            if coordinate and (coordinate.group(1) is not None or coordinate.group(2) is not None):
                if active_tool not in tool_diameters:
                    return False
                if coordinate.group(1) is not None:
                    last_x = _drill_number(coordinate.group(1), decimal_digits)
                if coordinate.group(2) is not None:
                    last_y = _drill_number(coordinate.group(2), decimal_digits)
                if last_x is None or last_y is None:
                    return False
                diameter = tool_diameters[active_tool]
                hits.append((diameter * scale, last_x * scale, last_y * scale))

        expected = EXPECTED_HITS_MM
    except (TypeError, ValueError):
        return False

    expected_diameters = sorted({hit[0] for hit in expected})
    actual_diameters = sorted(diameter * scale for diameter in tool_diameters.values())
    if len(actual_diameters) != len(expected_diameters) or any(
        abs(actual - expected_value) > 0.003
        for actual, expected_value in zip(actual_diameters, expected_diameters)
    ):
        return False

    actual = sorted(hits)
    if len(actual) != len(expected):
        return False
    return all(
        max(abs(a_value - e_value) for a_value, e_value in zip(actual_hit, expected_hit)) <= 0.003
        for actual_hit, expected_hit in zip(actual, expected)
    )


def _nc_log_valid(data: bytes) -> bool:
    return _drill_report_valid(data)


def _drill_report_valid(data: bytes) -> bool:
    text = _text(data).upper()
    if re.search(r"LAYER\s+PAIR\s*:\s*TOP\s+LAYER\s+TO\s+BOTTOM\s+LAYER", text) is None:
        return False
    if re.search(r"ASCII\s+ROUNDHOLES\s+FILE\s*:\s*DEMO\.TXT\b", text) is None:
        return False

    actual_counts = {}
    for line in text.splitlines():
        match = re.match(r"^T\d+\s+([0-9.]+)MIL\b.*?\bROUND\s+(\d+)\s+PTH\b", line)
        if match:
            actual_counts[float(match.group(1))] = int(match.group(2))
    return actual_counts == EXPECTED_TOOL_COUNTS_MIL


def _collision_report_valid(path: Path) -> bool:
    try:
        actual = json.loads(path.read_text(encoding="utf-8-sig"))
        return actual == EXPECTED_COLLISION_REPORT
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return False


def _content_equal(name: str, actual: bytes, expected: bytes) -> bool:
    suffix = Path(name).suffix.lower()
    if suffix in {".gbr", ".gtl", ".gbl", ".gts", ".gbs", ".gto", ".gbo", ".gm1", ".gml"}:
        return _gerber_valid(actual)
    if name == "ncdrill.log":
        return _nc_log_valid(actual)
    if suffix == ".log":
        return _log_equal(actual, expected)
    if suffix == ".drl":
        return _drill_valid(actual)
    if suffix in {".xml", ".ipc2581"}:
        try:
            return _xml_element_equal(ET.fromstring(actual), ET.fromstring(expected))
        except Exception:
            return False
    return _text(actual) == _text(expected)


def _zip_equal(path: Path, expected: bytes) -> bool:
    try:
        with zipfile.ZipFile(path) as actual_zip, zipfile.ZipFile(io.BytesIO(expected)) as expected_zip:
            actual_names = {Path(name).name.lower(): name for name in actual_zip.namelist() if not name.endswith("/")}
            expected_names = {Path(name).name.lower(): name for name in expected_zip.namelist() if not name.endswith("/")}
            if set(actual_names) != set(expected_names):
                return False
            return all(
                _content_equal(
                    expected_names[key],
                    actual_zip.read(actual_names[key]),
                    expected_zip.read(expected_names[key]),
                )
                for key in expected_names
            )
    except Exception:
        return False


def _bytes_equal(path: Path, expected: bytes) -> bool:
    try:
        if path.name == "collision_report.json":
            return _collision_report_valid(path)
        suffix = path.suffix.lower()
        if suffix == ".json":
            return _json_equal(path, expected)
        if suffix == ".csv":
            return _csv_equal(path, expected)
        if suffix in {".ipc2581", ".xml"}:
            return _xml_equal(path, expected)
        if suffix == ".zip":
            return _zip_equal(path, expected)
        if suffix == ".edif":
            return _edif_equal(path, expected)
        return _content_equal(path.name, path.read_bytes(), expected)
    except Exception:
        return False


def evaluate() -> bool:
    desktop = _desktop()
    for rel in ("collision_report.json", "demo.drl", "ncdrill.log"):
        path = desktop / "result" / rel
        if not path.is_file():
            return False
        if not _bytes_equal(path, _decode(rel)):
            return False
    return True


if __name__ == "__main__":
    ok = evaluate()
    print("True" if ok else "False")
    sys.exit(0 if ok else 1)
