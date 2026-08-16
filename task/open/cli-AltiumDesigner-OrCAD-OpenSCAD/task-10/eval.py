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
  "fixes.json": "ewogICJEUkMwMDEiOiAicmV2aWV3ZWRfY2xlYXJhbmNlIiwKICAiRFJDMDAyIjogImFjY2VwdGVkX3NpbGtzY3JlZW5fd2FybmluZyIKfQo=",
  "gerbers.zip": "UEsDBBQAAAAIAPVs5VwMMhCWMAAAAC4AAAAKAAAAQk9UVE9NLmdicnM3MFFw8g8J8fdVcHcNcnINUnDzD1JISc3N51J1C/ZxjDAyiTQy0VLl8jUw0uICAFBLAwQUAAAACAD1bOVcbbxG/i0AAAArAAAABwAAAEdORC5nYnJzNzBRcPdzUXB3DXJyDVJw8w9SSEnNzedSdQv2cYwwMok0MtFS5fI1MNLiAgBQSwMEFAAAAAgA9WzlXEOMNpAtAAAALQAAAAkAAABQT1dFUi5nYnJzNzBRCPAPdw1ScHcNcgJSbv5BCimpuflcqm7BPo4RRiaRRiZaqly+BkZaXABQSwMEFAAAAAgA9WzlXGD4jJ8tAAAAKwAAAAcAAABUT1AuZ2JyczcwUQjxD1Bwdw1ycg1ScPMPUkhJzc3nUnUL9nGMMDKJNDLRUuXyNTDS4gIAUEsBAhQAFAAAAAgA9WzlXAwyEJYwAAAALgAAAAoAAAAAAAAAAAAAAIABAAAAAEJPVFRPTS5nYnJQSwECFAAUAAAACAD1bOVcbbxG/i0AAAArAAAABwAAAAAAAAAAAAAAgAFYAAAAR05ELmdiclBLAQIUABQAAAAIAPVs5VxDjDaQLQAAAC0AAAAJAAAAAAAAAAAAAACAAaoAAABQT1dFUi5nYnJQSwECFAAUAAAACAD1bOVcYPiMny0AAAArAAAABwAAAAAAAAAAAAAAgAH+AAAAVE9QLmdiclBLBQYAAAAABAAEANkAAABQAQAAAAA=",
  "photoplot.log": "R2VuZXJhdGVkIDQgR2VyYmVyIGZpbG1zOiBUT1AsIEJPVFRPTSwgR05ELCBQT1dFUgpObyBmYXRhbCBDQU0gZXJyb3JzLgo="
}

EXPECTED_FILMS = ("TOP", "BOTTOM", "GND", "POWER")
EXPECTED_GERBER_UNITS = "INCH"
EXPECTED_FIXES = {
    "DRC001": "reviewed_clearance",
    "DRC002": "accepted_silkscreen_warning",
}
EXPECTED_GERBER_IMAGES = {
    "TOP": (
        ("draw", "C", 0.02000, 0.19685, 0.19685, 1.77165, 0.19685),
        ("flash", "C", 0.02400, 0.59055, 1.37795),
        ("flash", "C", 0.02800, 0.59055, 0.59055),
        ("flash", "C", 0.02800, 1.37795, 0.59055),
    ),
    "BOTTOM": (
        ("draw", "C", 0.02000, 0.19685, 1.77165, 1.77165, 1.77165),
        ("flash", "C", 0.02400, 0.59055, 1.37795),
        ("flash", "C", 0.02800, 0.59055, 0.59055),
        ("flash", "C", 0.02800, 1.37795, 0.59055),
    ),
    "GND": (
        ("draw", "C", 0.02000, 0.19685, 0.39370, 1.77165, 0.39370),
        ("draw", "C", 0.02000, 0.50000, 1.10000, 1.50000, 1.10000),
    ),
    "POWER": (
        ("draw", "C", 0.02000, 0.19685, 1.57480, 1.77165, 1.57480),
    ),
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
    unit_command = "%MOIN*%" if EXPECTED_GERBER_UNITS == "INCH" else "%MOMM*%"
    if text.count(unit_command) != 1:
        return False
    if len(re.findall(r"%FS[LT]AX[1-6][1-6]Y[1-6][1-6]\*%", text)) != 1:
        return False
    if text.count("M02*") != 1:
        return False
    operation = re.search(
        r"(?:X[-+]?\d+(?:Y[-+]?\d+)?|Y[-+]?\d+(?:X[-+]?\d+)?)D0[13]\*",
        text,
    )
    aperture_image = re.search(r"%ADD\d+[^%]*\*%", text) and operation
    region_image = "G36*" in text and "G37*" in text and operation
    return bool(aperture_image or region_image)


def _gerber_coord(token: str, integer_digits: int, decimal_digits: int, suppression: str) -> float:
    sign = -1 if token.startswith("-") else 1
    digits = token.lstrip("+-")
    if "." in digits:
        return sign * float(digits)
    total = integer_digits + decimal_digits
    if len(digits) > total:
        raise ValueError("coordinate wider than FS format")
    if suppression == "T":
        digits = digits.ljust(total, "0")
    else:
        digits = digits.rjust(total, "0")
    return sign * int(digits) / (10 ** decimal_digits)


def _gerber_image_signature(data: bytes) -> tuple[tuple[object, ...], ...] | None:
    text = _text(data).upper()
    fs = re.search(r"%FS([LT])A?X(\d)(\d)Y(\d)(\d)\*%", text)
    if fs is None or (fs.group(2), fs.group(3)) != (fs.group(4), fs.group(5)):
        return None
    suppression = fs.group(1)
    integer_digits = int(fs.group(2))
    decimal_digits = int(fs.group(3))

    apertures = {}
    for match in re.finditer(r"%ADD(\d+)([A-Z]+),?([^*%]*)\*%", text):
        params = [item for item in re.split(r"[X,]", match.group(3)) if item]
        if match.group(2) != "C" or not params:
            return None
        apertures[int(match.group(1))] = (match.group(2), round(float(params[0]), 5))

    body = re.sub(r"%[^%]*%", "", text)
    body = re.sub(r"G04[^*]*\*", "", body)
    current_aperture = None
    current_operation = None
    current_x = None
    current_y = None
    operations = []
    try:
        for raw_statement in body.split("*"):
            statement = "".join(raw_statement.split())
            if not statement:
                continue
            x_match = re.search(r"X([-+]?\d+(?:\.\d+)?)", statement)
            y_match = re.search(r"Y([-+]?\d+(?:\.\d+)?)", statement)
            d_match = re.search(r"D0*(\d+)$", statement)
            d_code = int(d_match.group(1)) if d_match else None

            if d_code is not None and d_code >= 10 and x_match is None and y_match is None:
                if d_code not in apertures:
                    return None
                current_aperture = d_code
                continue
            if d_code in {1, 2, 3}:
                current_operation = d_code

            next_x = current_x if x_match is None else _gerber_coord(
                x_match.group(1), integer_digits, decimal_digits, suppression
            )
            next_y = current_y if y_match is None else _gerber_coord(
                y_match.group(1), integer_digits, decimal_digits, suppression
            )
            if current_operation == 2 and (x_match is not None or y_match is not None):
                if next_x is None or next_y is None:
                    return None
                current_x, current_y = next_x, next_y
            elif current_operation == 1 and (x_match is not None or y_match is not None):
                if current_aperture is None or None in {current_x, current_y, next_x, next_y}:
                    return None
                start = (round(current_x, 5), round(current_y, 5))
                end = (round(next_x, 5), round(next_y, 5))
                if end < start:
                    start, end = end, start
                shape, size = apertures[current_aperture]
                operations.append(("draw", shape, size, *start, *end))
                current_x, current_y = next_x, next_y
            elif current_operation == 3:
                if x_match is not None or y_match is not None:
                    current_x, current_y = next_x, next_y
                if current_aperture is None or current_x is None or current_y is None:
                    return None
                shape, size = apertures[current_aperture]
                operations.append(
                    ("flash", shape, size, round(current_x, 5), round(current_y, 5))
                )
                current_operation = None
    except (KeyError, TypeError, ValueError):
        return None
    return tuple(sorted(operations))


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


def _fixes_valid(path: Path) -> bool:
    try:
        actual = json.loads(path.read_text(encoding="utf-8-sig"))
        return actual == EXPECTED_FIXES
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return False


def _photoplot_log_valid(data: bytes) -> bool:
    text = _text(data)
    films = EXPECTED_FILMS
    lowered = text.casefold()
    error_scan = re.sub(r"\bno\s+fatal(?:\s+\w+){0,3}\s+errors?\b", "", lowered)
    error_scan = re.sub(r"\bno\s+errors?\b", "", error_scan)
    return (
        re.search(rf"\b{len(films)}\b", lowered) is not None
        and ("gerber" in lowered or "film" in lowered)
        and all(re.search(rf"(?<![a-z0-9]){re.escape(film.casefold())}(?![a-z0-9])", lowered) for film in films)
        and re.search(r"\b(?:fatal|error|failed)\b", error_scan) is None
    )


def _drill_signature(data: bytes):
    text = _text(data).upper()
    units = "INCH" if "INCH" in text else "METRIC" if "METRIC" in text else None
    tools = sorted((tool, format(float(diameter), ".12g")) for tool, diameter in re.findall(r"T(\d+)C([0-9.]+)", text))
    coordinates = sorted(re.findall(r"X[-+]?\d+Y[-+]?\d+", text))
    return units, tools, coordinates


def _content_equal(name: str, actual: bytes, expected: bytes) -> bool:
    suffix = Path(name).suffix.lower()
    if suffix in {".gbr", ".gtl", ".gbl", ".gts", ".gbs", ".gto", ".gbo", ".gm1", ".gml"}:
        return _gerber_valid(actual)
    if name == "photoplot.log":
        return _photoplot_log_valid(actual)
    if suffix == ".log":
        return _log_equal(actual, expected)
    if suffix == ".drl":
        return _drill_signature(actual) == _drill_signature(expected)
    if suffix in {".xml", ".ipc2581"}:
        try:
            return _xml_element_equal(ET.fromstring(actual), ET.fromstring(expected))
        except Exception:
            return False
    return _text(actual) == _text(expected)


def _zip_equal(path: Path, _expected: bytes) -> bool:
    try:
        films = EXPECTED_FILMS
        with zipfile.ZipFile(path) as actual_zip:
            actual_entries = [item for item in actual_zip.infolist() if not item.is_dir()]
            if any(Path(item.filename).name != item.filename for item in actual_entries):
                return False
            if sum(item.file_size for item in actual_entries) > 40 * 1024 * 1024:
                return False
            actual_names = {Path(item.filename).name.lower(): item.filename for item in actual_entries}
            if len(actual_names) != len(actual_entries):
                return False
            expected_names = {f"{film}.gbr".casefold() for film in films}
            if set(actual_names) != expected_names:
                return False
            for film in films:
                member = actual_zip.read(actual_names[f"{film}.gbr".casefold()])
                if not _gerber_valid(member):
                    return False
                signature = _gerber_image_signature(member)
                if signature != tuple(sorted(EXPECTED_GERBER_IMAGES[film])):
                    return False
            return True
    except Exception:
        return False


def _bytes_equal(path: Path, expected: bytes) -> bool:
    try:
        if path.name == "fixes.json":
            return _fixes_valid(path)
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
    for rel in EXPECTED:
        path = desktop / rel
        if not path.is_file():
            return False
        if not _bytes_equal(path, _decode(rel)):
            return False
    return True


if __name__ == "__main__":
    ok = evaluate()
    print("True" if ok else "False")
    sys.exit(0 if ok else 1)
