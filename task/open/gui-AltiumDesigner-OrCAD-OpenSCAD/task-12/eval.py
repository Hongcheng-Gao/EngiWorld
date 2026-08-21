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
  "annotation_report.csv": "T2xkUmVmLE5ld1JlZg0KUjQyLFIxDQpSMzMsUjINClIzOSxSMw0KUjM0LFI0DQpDMSxDMQ0KQzMsQzMNClExNixRMQ0KTDEsTDENClYyNCxWMQ0K",
  "oscillator_reannotated.edif": "KGVkaWYgb3NjaWxsYXRvcl9jb3JlCiAgKGVkaWZWZXJzaW9uIDIgMCAwKQogIChlZGlmTGV2ZWwgMCkKICAoa2V5d29yZE1hcCAoa2V5d29yZExldmVsIDApKQogIChzdGF0dXMgKHdyaXR0ZW4gKHRpbWVTdGFtcCAyMDI2IDcgNSAwIDAgMCkgKHByb2dyYW0gIkVuZ2l3b3JsZE5ldXRyYWwiKSkpCiAgKGxpYnJhcnkgb3NjaWxsYXRvcl9jb3JlCiAgICAoY2VsbCBNQUlOIChjZWxsVHlwZSBHRU5FUklDKSkKICApCiAgKGRlc2lnbiBvc2NpbGxhdG9yX2NvcmUKICAgIChpbnN0YW5jZSBSMQogICAgICAocHJvcGVydHkgVmFsdWUgKHN0cmluZyAiUmgiKSkKICAgICAgKHByb3BlcnR5IFBhZ2UgKHN0cmluZyAiTUFJTiIpKQogICAgICAocHJvcGVydHkgUElOXzEgKHN0cmluZyAiMSIpKQogICAgICAocHJvcGVydHkgUElOXzIgKHN0cmluZyAiMiIpKQogICAgKQogICAgKGluc3RhbmNlIFIyCiAgICAgIChwcm9wZXJ0eSBWYWx1ZSAoc3RyaW5nICJSayIpKQogICAgICAocHJvcGVydHkgUGFnZSAoc3RyaW5nICJNQUlOIikpCiAgICAgIChwcm9wZXJ0eSBQSU5fMSAoc3RyaW5nICIxIikpCiAgICAgIChwcm9wZXJ0eSBQSU5fMiAoc3RyaW5nICIyIikpCiAgICApCiAgICAoaW5zdGFuY2UgUjMKICAgICAgKHByb3BlcnR5IFZhbHVlIChzdHJpbmcgIlJsIikpCiAgICAgIChwcm9wZXJ0eSBQYWdlIChzdHJpbmcgIk1BSU4iKSkKICAgICAgKHByb3BlcnR5IFBJTl8xIChzdHJpbmcgIjEiKSkKICAgICAgKHByb3BlcnR5IFBJTl8yIChzdHJpbmcgIjIiKSkKICAgICkKICAgIChpbnN0YW5jZSBSNAogICAgICAocHJvcGVydHkgVmFsdWUgKHN0cmluZyAiUmUiKSkKICAgICAgKHByb3BlcnR5IFBhZ2UgKHN0cmluZyAiTUFJTiIpKQogICAgICAocHJvcGVydHkgUElOXzEgKHN0cmluZyAiMSIpKQogICAgICAocHJvcGVydHkgUElOXzIgKHN0cmluZyAiMiIpKQogICAgKQogICAgKGluc3RhbmNlIEMxCiAgICAgIChwcm9wZXJ0eSBWYWx1ZSAoc3RyaW5nICJDY2JmYiIpKQogICAgICAocHJvcGVydHkgUGFnZSAoc3RyaW5nICJNQUlOIikpCiAgICAgIChwcm9wZXJ0eSBQSU5fMSAoc3RyaW5nICIxIikpCiAgICAgIChwcm9wZXJ0eSBQSU5fMiAoc3RyaW5nICIyIikpCiAgICApCiAgICAoaW5zdGFuY2UgQzMKICAgICAgKHByb3BlcnR5IFZhbHVlIChzdHJpbmcgIkMwIikpCiAgICAgIChwcm9wZXJ0eSBQYWdlIChzdHJpbmcgIk1BSU4iKSkKICAgICAgKHByb3BlcnR5IFBJTl8xIChzdHJpbmcgIjEiKSkKICAgICAgKHByb3BlcnR5IFBJTl8yIChzdHJpbmcgIjIiKSkKICAgICkKICAgIChpbnN0YW5jZSBRMQogICAgICAocHJvcGVydHkgVmFsdWUgKHN0cmluZyAiMk4zOTA0IikpCiAgICAgIChwcm9wZXJ0eSBQYWdlIChzdHJpbmcgIk1BSU4iKSkKICAgICAgKHByb3BlcnR5IFBJTl9CIChzdHJpbmcgIkIiKSkKICAgICAgKHByb3BlcnR5IFBJTl9DIChzdHJpbmcgIkMiKSkKICAgICAgKHByb3BlcnR5IFBJTl9FIChzdHJpbmcgIkUiKSkKICAgICkKICAgIChpbnN0YW5jZSBMMQogICAgICAocHJvcGVydHkgVmFsdWUgKHN0cmluZyAiTDAiKSkKICAgICAgKHByb3BlcnR5IFBhZ2UgKHN0cmluZyAiTUFJTiIpKQogICAgICAocHJvcGVydHkgUElOXzEgKHN0cmluZyAiMSIpKQogICAgICAocHJvcGVydHkgUElOXzIgKHN0cmluZyAiMiIpKQogICAgKQogICAgKGluc3RhbmNlIFYxCiAgICAgIChwcm9wZXJ0eSBWYWx1ZSAoc3RyaW5nICJWY2MiKSkKICAgICAgKHByb3BlcnR5IFBhZ2UgKHN0cmluZyAiTUFJTiIpKQogICAgICAocHJvcGVydHkgUElOXzEgKHN0cmluZyAiMSIpKQogICAgICAocHJvcGVydHkgUElOXzIgKHN0cmluZyAiMiIpKQogICAgKQogICkKKQo=",
  "oscillator_reannotated.schematic.json": "ewogICJjb21wb25lbnRzIjogWwogICAgewogICAgICAicGFnZSI6ICJNQUlOIiwKICAgICAgInBpbnMiOiBbCiAgICAgICAgIjEiLAogICAgICAgICIyIgogICAgICBdLAogICAgICAicHJvcGVydGllcyI6IHt9LAogICAgICAicmVmIjogIlIxIiwKICAgICAgInZhbHVlIjogIlJoIgogICAgfSwKICAgIHsKICAgICAgInBhZ2UiOiAiTUFJTiIsCiAgICAgICJwaW5zIjogWwogICAgICAgICIxIiwKICAgICAgICAiMiIKICAgICAgXSwKICAgICAgInByb3BlcnRpZXMiOiB7fSwKICAgICAgInJlZiI6ICJSMiIsCiAgICAgICJ2YWx1ZSI6ICJSayIKICAgIH0sCiAgICB7CiAgICAgICJwYWdlIjogIk1BSU4iLAogICAgICAicGlucyI6IFsKICAgICAgICAiMSIsCiAgICAgICAgIjIiCiAgICAgIF0sCiAgICAgICJwcm9wZXJ0aWVzIjoge30sCiAgICAgICJyZWYiOiAiUjMiLAogICAgICAidmFsdWUiOiAiUmwiCiAgICB9LAogICAgewogICAgICAicGFnZSI6ICJNQUlOIiwKICAgICAgInBpbnMiOiBbCiAgICAgICAgIjEiLAogICAgICAgICIyIgogICAgICBdLAogICAgICAicHJvcGVydGllcyI6IHt9LAogICAgICAicmVmIjogIlI0IiwKICAgICAgInZhbHVlIjogIlJlIgogICAgfSwKICAgIHsKICAgICAgInBhZ2UiOiAiTUFJTiIsCiAgICAgICJwaW5zIjogWwogICAgICAgICIxIiwKICAgICAgICAiMiIKICAgICAgXSwKICAgICAgInByb3BlcnRpZXMiOiB7fSwKICAgICAgInJlZiI6ICJDMSIsCiAgICAgICJ2YWx1ZSI6ICJDY2JmYiIKICAgIH0sCiAgICB7CiAgICAgICJwYWdlIjogIk1BSU4iLAogICAgICAicGlucyI6IFsKICAgICAgICAiMSIsCiAgICAgICAgIjIiCiAgICAgIF0sCiAgICAgICJwcm9wZXJ0aWVzIjoge30sCiAgICAgICJyZWYiOiAiQzMiLAogICAgICAidmFsdWUiOiAiQzAiCiAgICB9LAogICAgewogICAgICAicGFnZSI6ICJNQUlOIiwKICAgICAgInBpbnMiOiBbCiAgICAgICAgIkIiLAogICAgICAgICJDIiwKICAgICAgICAiRSIKICAgICAgXSwKICAgICAgInByb3BlcnRpZXMiOiB7fSwKICAgICAgInJlZiI6ICJRMSIsCiAgICAgICJ2YWx1ZSI6ICIyTjM5MDQiCiAgICB9LAogICAgewogICAgICAicGFnZSI6ICJNQUlOIiwKICAgICAgInBpbnMiOiBbCiAgICAgICAgIjEiLAogICAgICAgICIyIgogICAgICBdLAogICAgICAicHJvcGVydGllcyI6IHt9LAogICAgICAicmVmIjogIkwxIiwKICAgICAgInZhbHVlIjogIkwwIgogICAgfSwKICAgIHsKICAgICAgInBhZ2UiOiAiTUFJTiIsCiAgICAgICJwaW5zIjogWwogICAgICAgICIxIiwKICAgICAgICAiMiIKICAgICAgXSwKICAgICAgInByb3BlcnRpZXMiOiB7fSwKICAgICAgInJlZiI6ICJWMSIsCiAgICAgICJ2YWx1ZSI6ICJWY2MiCiAgICB9CiAgXSwKICAiZm9ybWF0IjogImVuZ2l3b3JsZC1uZXV0cmFsLXNjaGVtYXRpYy12MSIsCiAgIm5hbWUiOiAib3NjaWxsYXRvcl9jb3JlIiwKICAicHJvcGVydGllcyI6IHt9LAogICJzY2hlbWF0aWNzIjogWwogICAgewogICAgICAiaGllcl9ibG9ja3MiOiBbXSwKICAgICAgIm5hbWUiOiAib3NjaWxsYXRvcl9jb3JlIiwKICAgICAgInBhZ2VzIjogWwogICAgICAgICJNQUlOIgogICAgICBdCiAgICB9CiAgXQp9Cg=="
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


def _content_equal(name: str, actual: bytes, expected: bytes) -> bool:
    suffix = Path(name).suffix.lower()
    if suffix in {".gbr", ".gtl", ".gbl", ".gts", ".gbs", ".gto", ".gbo", ".gm1", ".gml"}:
        return _gerber_valid(actual)
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


def _key(value) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value).casefold())


def _mapping_report_valid(path: Path) -> bool:
    expected = {"R42": "R1", "R33": "R2", "R39": "R3", "R34": "R4", "C1": "C1", "C3": "C3", "Q16": "Q1", "L1": "L1", "V24": "V1"}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = {_key(name): name for name in (reader.fieldnames or [])}
        old_header = next((headers[name] for name in ("oldref", "oldreference", "from", "source") if name in headers), None)
        new_header = next((headers[name] for name in ("newref", "newreference", "to", "target") if name in headers), None)
        if old_header is None or new_header is None:
            return False
        rows = list(reader)
    actual = {str(row[old_header]).strip().upper(): str(row[new_header]).strip().upper() for row in rows}
    return len(actual) == len(rows) and actual == expected


def evaluate() -> bool:
    desktop = _desktop()
    designs = ["oscillator_reannotated.edif", "oscillator_reannotated.schematic.json"]
    report = desktop / "result" / "annotation_report.csv"
    try:
        return (
            report.is_file() and report.stat().st_size > 0 and
            all((desktop / name).is_file() and _bytes_equal(desktop / name, _decode(name)) for name in designs) and
            _mapping_report_valid(report)
        )
    except Exception:
        return False


if __name__ == "__main__":
    ok = evaluate()
    print("True" if ok else "False")
    sys.exit(0 if ok else 1)
