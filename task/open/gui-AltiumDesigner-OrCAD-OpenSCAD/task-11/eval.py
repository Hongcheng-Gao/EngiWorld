from __future__ import annotations

import base64
import csv
import io
import json
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

EXPECTED = {
  "project_structure.json": "ewogICJzaGVldF9zeW1ib2xzIjogewogICAgIlhTMSI6ICJTTF9Db25maWdfMkUuU2NoRG9jIiwKICAgICJYUzIiOiAiU0xfTENEX1NXX0xFRF8yRS5TY2hEb2MiLAogICAgIlhTMyI6ICJTTF9GUEdBX0F1dG9fMkUuU2NoRG9jIiwKICAgICJYUzQiOiAiU0xfUG93ZXIuU2NoRG9jIgogIH0KfQo=",
  "spiritlevel_fixed.edif": "KGVkaWYgc3Bpcml0bGV2ZWwKICAoZWRpZlZlcnNpb24gMiAwIDApCiAgKGVkaWZMZXZlbCAwKQogIChrZXl3b3JkTWFwIChrZXl3b3JkTGV2ZWwgMCkpCiAgKHN0YXR1cyAod3JpdHRlbiAodGltZVN0YW1wIDIwMjYgNyA1IDAgMCAwKSAocHJvZ3JhbSAiRW5naXdvcmxkTmV1dHJhbCIpKSkKICAobGlicmFyeSBzcGlyaXRsZXZlbAogICAgKGNlbGwgTUFJTiAoY2VsbFR5cGUgR0VORVJJQykpCiAgKQogIChkZXNpZ24gc3Bpcml0bGV2ZWwKICAgIChpbnN0YW5jZSBYUzEKICAgICAgKHByb3BlcnR5IFZhbHVlIChzdHJpbmcgIlNoZWV0U3ltYm9sIikpCiAgICAgIChwcm9wZXJ0eSBQYWdlIChzdHJpbmcgIk1BSU4iKSkKICAgICAgKHByb3BlcnR5IFRhcmdldEZpbGUgKHN0cmluZyAiU0xfQ29uZmlnXzJFLlNjaERvYyIpKQogICAgICAocHJvcGVydHkgUElOXzEgKHN0cmluZyAiMSIpKQogICAgICAocHJvcGVydHkgUElOXzIgKHN0cmluZyAiMiIpKQogICAgKQogICAgKGluc3RhbmNlIFhTMgogICAgICAocHJvcGVydHkgVmFsdWUgKHN0cmluZyAiU2hlZXRTeW1ib2wiKSkKICAgICAgKHByb3BlcnR5IFBhZ2UgKHN0cmluZyAiTUFJTiIpKQogICAgICAocHJvcGVydHkgVGFyZ2V0RmlsZSAoc3RyaW5nICJTTF9MQ0RfU1dfTEVEXzJFLlNjaERvYyIpKQogICAgICAocHJvcGVydHkgUElOXzEgKHN0cmluZyAiMSIpKQogICAgICAocHJvcGVydHkgUElOXzIgKHN0cmluZyAiMiIpKQogICAgKQogICAgKGluc3RhbmNlIFhTMwogICAgICAocHJvcGVydHkgVmFsdWUgKHN0cmluZyAiU2hlZXRTeW1ib2wiKSkKICAgICAgKHByb3BlcnR5IFBhZ2UgKHN0cmluZyAiTUFJTiIpKQogICAgICAocHJvcGVydHkgVGFyZ2V0RmlsZSAoc3RyaW5nICJTTF9GUEdBX0F1dG9fMkUuU2NoRG9jIikpCiAgICAgIChwcm9wZXJ0eSBQSU5fMSAoc3RyaW5nICIxIikpCiAgICAgIChwcm9wZXJ0eSBQSU5fMiAoc3RyaW5nICIyIikpCiAgICApCiAgICAoaW5zdGFuY2UgWFM0CiAgICAgIChwcm9wZXJ0eSBWYWx1ZSAoc3RyaW5nICJTaGVldFN5bWJvbCIpKQogICAgICAocHJvcGVydHkgUGFnZSAoc3RyaW5nICJNQUlOIikpCiAgICAgIChwcm9wZXJ0eSBUYXJnZXRGaWxlIChzdHJpbmcgIlNMX1Bvd2VyLlNjaERvYyIpKQogICAgICAocHJvcGVydHkgUElOXzEgKHN0cmluZyAiMSIpKQogICAgICAocHJvcGVydHkgUElOXzIgKHN0cmluZyAiMiIpKQogICAgKQogICkKKQo=",
  "spiritlevel_fixed.schematic.json": "ewogICJjb21wb25lbnRzIjogWwogICAgewogICAgICAicGFnZSI6ICJNQUlOIiwKICAgICAgInBpbnMiOiBbCiAgICAgICAgIjEiLAogICAgICAgICIyIgogICAgICBdLAogICAgICAicHJvcGVydGllcyI6IHsKICAgICAgICAiVGFyZ2V0RmlsZSI6ICJTTF9Db25maWdfMkUuU2NoRG9jIgogICAgICB9LAogICAgICAicmVmIjogIlhTMSIsCiAgICAgICJ2YWx1ZSI6ICJTaGVldFN5bWJvbCIKICAgIH0sCiAgICB7CiAgICAgICJwYWdlIjogIk1BSU4iLAogICAgICAicGlucyI6IFsKICAgICAgICAiMSIsCiAgICAgICAgIjIiCiAgICAgIF0sCiAgICAgICJwcm9wZXJ0aWVzIjogewogICAgICAgICJUYXJnZXRGaWxlIjogIlNMX0xDRF9TV19MRURfMkUuU2NoRG9jIgogICAgICB9LAogICAgICAicmVmIjogIlhTMiIsCiAgICAgICJ2YWx1ZSI6ICJTaGVldFN5bWJvbCIKICAgIH0sCiAgICB7CiAgICAgICJwYWdlIjogIk1BSU4iLAogICAgICAicGlucyI6IFsKICAgICAgICAiMSIsCiAgICAgICAgIjIiCiAgICAgIF0sCiAgICAgICJwcm9wZXJ0aWVzIjogewogICAgICAgICJUYXJnZXRGaWxlIjogIlNMX0ZQR0FfQXV0b18yRS5TY2hEb2MiCiAgICAgIH0sCiAgICAgICJyZWYiOiAiWFMzIiwKICAgICAgInZhbHVlIjogIlNoZWV0U3ltYm9sIgogICAgfSwKICAgIHsKICAgICAgInBhZ2UiOiAiTUFJTiIsCiAgICAgICJwaW5zIjogWwogICAgICAgICIxIiwKICAgICAgICAiMiIKICAgICAgXSwKICAgICAgInByb3BlcnRpZXMiOiB7CiAgICAgICAgIlRhcmdldEZpbGUiOiAiU0xfUG93ZXIuU2NoRG9jIgogICAgICB9LAogICAgICAicmVmIjogIlhTNCIsCiAgICAgICJ2YWx1ZSI6ICJTaGVldFN5bWJvbCIKICAgIH0KICBdLAogICJmb3JtYXQiOiAiZW5naXdvcmxkLW5ldXRyYWwtc2NoZW1hdGljLXYxIiwKICAibmFtZSI6ICJzcGlyaXRsZXZlbCIsCiAgInByb3BlcnRpZXMiOiB7fSwKICAic2NoZW1hdGljcyI6IFsKICAgIHsKICAgICAgImhpZXJfYmxvY2tzIjogW10sCiAgICAgICJuYW1lIjogInNwaXJpdGxldmVsIiwKICAgICAgInBhZ2VzIjogWwogICAgICAgICJNQUlOIgogICAgICBdCiAgICB9CiAgXQp9Cg=="
}


def _desktop() -> Path:
    return Path(__file__).resolve().parent


def _decode(name: str) -> bytes:
    return base64.b64decode(EXPECTED[name].encode("ascii"))


def _text(data: bytes) -> str:
    return data.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n").rstrip() + "\n"


def _json_equal(path: Path, expected: bytes) -> bool:
    try:
        return json.loads(path.read_text(encoding="utf-8")) == json.loads(expected.decode("utf-8"))
    except Exception:
        return False


def _csv_equal(path: Path, expected: bytes) -> bool:
    try:
        actual_text = path.read_text(encoding="utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")
        expected_text = expected.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")
        actual_rows = list(csv.reader(io.StringIO(actual_text)))
        expected_rows = list(csv.reader(io.StringIO(expected_text)))
        return actual_rows == expected_rows
    except Exception:
        return False


def _xml_equal(path: Path, expected: bytes) -> bool:
    try:
        actual_root = ET.parse(path).getroot()
        expected_root = ET.fromstring(expected)
    except Exception:
        return False

    def canon(elem):
        return (
            elem.tag,
            tuple(sorted((k, str(v)) for k, v in elem.attrib.items())),
            (elem.text or "").strip(),
            tuple(canon(child) for child in list(elem)),
        )

    return canon(actual_root) == canon(expected_root)


def _zip_equal(path: Path, expected: bytes) -> bool:
    try:
        with zipfile.ZipFile(path) as actual, zipfile.ZipFile(io.BytesIO(expected)) as exp:
            if sorted(actual.namelist()) != sorted(exp.namelist()):
                return False
            for name in exp.namelist():
                if actual.read(name) != exp.read(name):
                    return False
        return True
    except Exception:
        return False


def _bytes_equal(path: Path, expected: bytes) -> bool:
    try:
        if path.suffix.lower() in {".json"}:
            return _json_equal(path, expected)
        if path.suffix.lower() in {".csv"}:
            return _csv_equal(path, expected)
        if path.suffix.lower() in {".ipc2581", ".xml"}:
            return _xml_equal(path, expected)
        if path.suffix.lower() in {".zip"}:
            return _zip_equal(path, expected)
        return _text(path.read_bytes()) == _text(expected)
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
