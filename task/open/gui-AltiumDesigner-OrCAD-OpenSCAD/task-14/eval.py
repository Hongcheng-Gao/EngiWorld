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
  "component_properties.csv": "UmVmZXJlbmNlLFRvbGVyYW5jZQ0KUjQyLDElDQpSMzMsNSUNClIzOSw1JQ0KUjM0LDUlDQpDMSwNCkMzLA0KUTE2LA0KTDEsDQpWMjQsDQo=",
  "oscillator_tolerance.edif": "KGVkaWYgb3NjaWxsYXRvcl9jb3JlCiAgKGVkaWZWZXJzaW9uIDIgMCAwKQogIChlZGlmTGV2ZWwgMCkKICAoa2V5d29yZE1hcCAoa2V5d29yZExldmVsIDApKQogIChzdGF0dXMgKHdyaXR0ZW4gKHRpbWVTdGFtcCAyMDI2IDcgNSAwIDAgMCkgKHByb2dyYW0gIkVuZ2l3b3JsZE5ldXRyYWwiKSkpCiAgKGxpYnJhcnkgb3NjaWxsYXRvcl9jb3JlCiAgICAoY2VsbCBNQUlOIChjZWxsVHlwZSBHRU5FUklDKSkKICApCiAgKGRlc2lnbiBvc2NpbGxhdG9yX2NvcmUKICAgIChpbnN0YW5jZSBSNDIKICAgICAgKHByb3BlcnR5IFZhbHVlIChzdHJpbmcgIlJoIikpCiAgICAgIChwcm9wZXJ0eSBQYWdlIChzdHJpbmcgIk1BSU4iKSkKICAgICAgKHByb3BlcnR5IFRvbGVyYW5jZSAoc3RyaW5nICIxJSIpKQogICAgICAocHJvcGVydHkgUElOXzEgKHN0cmluZyAiMSIpKQogICAgICAocHJvcGVydHkgUElOXzIgKHN0cmluZyAiMiIpKQogICAgKQogICAgKGluc3RhbmNlIFIzMwogICAgICAocHJvcGVydHkgVmFsdWUgKHN0cmluZyAiUmsiKSkKICAgICAgKHByb3BlcnR5IFBhZ2UgKHN0cmluZyAiTUFJTiIpKQogICAgICAocHJvcGVydHkgVG9sZXJhbmNlIChzdHJpbmcgIjUlIikpCiAgICAgIChwcm9wZXJ0eSBQSU5fMSAoc3RyaW5nICIxIikpCiAgICAgIChwcm9wZXJ0eSBQSU5fMiAoc3RyaW5nICIyIikpCiAgICApCiAgICAoaW5zdGFuY2UgUjM5CiAgICAgIChwcm9wZXJ0eSBWYWx1ZSAoc3RyaW5nICJSbCIpKQogICAgICAocHJvcGVydHkgUGFnZSAoc3RyaW5nICJNQUlOIikpCiAgICAgIChwcm9wZXJ0eSBUb2xlcmFuY2UgKHN0cmluZyAiNSUiKSkKICAgICAgKHByb3BlcnR5IFBJTl8xIChzdHJpbmcgIjEiKSkKICAgICAgKHByb3BlcnR5IFBJTl8yIChzdHJpbmcgIjIiKSkKICAgICkKICAgIChpbnN0YW5jZSBSMzQKICAgICAgKHByb3BlcnR5IFZhbHVlIChzdHJpbmcgIlJlIikpCiAgICAgIChwcm9wZXJ0eSBQYWdlIChzdHJpbmcgIk1BSU4iKSkKICAgICAgKHByb3BlcnR5IFRvbGVyYW5jZSAoc3RyaW5nICI1JSIpKQogICAgICAocHJvcGVydHkgUElOXzEgKHN0cmluZyAiMSIpKQogICAgICAocHJvcGVydHkgUElOXzIgKHN0cmluZyAiMiIpKQogICAgKQogICAgKGluc3RhbmNlIEMxCiAgICAgIChwcm9wZXJ0eSBWYWx1ZSAoc3RyaW5nICJDY2JmYiIpKQogICAgICAocHJvcGVydHkgUGFnZSAoc3RyaW5nICJNQUlOIikpCiAgICAgIChwcm9wZXJ0eSBQSU5fMSAoc3RyaW5nICIxIikpCiAgICAgIChwcm9wZXJ0eSBQSU5fMiAoc3RyaW5nICIyIikpCiAgICApCiAgICAoaW5zdGFuY2UgQzMKICAgICAgKHByb3BlcnR5IFZhbHVlIChzdHJpbmcgIkMwIikpCiAgICAgIChwcm9wZXJ0eSBQYWdlIChzdHJpbmcgIk1BSU4iKSkKICAgICAgKHByb3BlcnR5IFBJTl8xIChzdHJpbmcgIjEiKSkKICAgICAgKHByb3BlcnR5IFBJTl8yIChzdHJpbmcgIjIiKSkKICAgICkKICAgIChpbnN0YW5jZSBRMTYKICAgICAgKHByb3BlcnR5IFZhbHVlIChzdHJpbmcgIjJOMzkwNCIpKQogICAgICAocHJvcGVydHkgUGFnZSAoc3RyaW5nICJNQUlOIikpCiAgICAgIChwcm9wZXJ0eSBQSU5fQiAoc3RyaW5nICJCIikpCiAgICAgIChwcm9wZXJ0eSBQSU5fQyAoc3RyaW5nICJDIikpCiAgICAgIChwcm9wZXJ0eSBQSU5fRSAoc3RyaW5nICJFIikpCiAgICApCiAgICAoaW5zdGFuY2UgTDEKICAgICAgKHByb3BlcnR5IFZhbHVlIChzdHJpbmcgIkwwIikpCiAgICAgIChwcm9wZXJ0eSBQYWdlIChzdHJpbmcgIk1BSU4iKSkKICAgICAgKHByb3BlcnR5IFBJTl8xIChzdHJpbmcgIjEiKSkKICAgICAgKHByb3BlcnR5IFBJTl8yIChzdHJpbmcgIjIiKSkKICAgICkKICAgIChpbnN0YW5jZSBWMjQKICAgICAgKHByb3BlcnR5IFZhbHVlIChzdHJpbmcgIlZjYyIpKQogICAgICAocHJvcGVydHkgUGFnZSAoc3RyaW5nICJNQUlOIikpCiAgICAgIChwcm9wZXJ0eSBQSU5fMSAoc3RyaW5nICIxIikpCiAgICAgIChwcm9wZXJ0eSBQSU5fMiAoc3RyaW5nICIyIikpCiAgICApCiAgKQopCg==",
  "oscillator_tolerance.schematic.json": "ewogICJjb21wb25lbnRzIjogWwogICAgewogICAgICAicGFnZSI6ICJNQUlOIiwKICAgICAgInBpbnMiOiBbCiAgICAgICAgIjEiLAogICAgICAgICIyIgogICAgICBdLAogICAgICAicHJvcGVydGllcyI6IHsKICAgICAgICAiVG9sZXJhbmNlIjogIjElIgogICAgICB9LAogICAgICAicmVmIjogIlI0MiIsCiAgICAgICJ2YWx1ZSI6ICJSaCIKICAgIH0sCiAgICB7CiAgICAgICJwYWdlIjogIk1BSU4iLAogICAgICAicGlucyI6IFsKICAgICAgICAiMSIsCiAgICAgICAgIjIiCiAgICAgIF0sCiAgICAgICJwcm9wZXJ0aWVzIjogewogICAgICAgICJUb2xlcmFuY2UiOiAiNSUiCiAgICAgIH0sCiAgICAgICJyZWYiOiAiUjMzIiwKICAgICAgInZhbHVlIjogIlJrIgogICAgfSwKICAgIHsKICAgICAgInBhZ2UiOiAiTUFJTiIsCiAgICAgICJwaW5zIjogWwogICAgICAgICIxIiwKICAgICAgICAiMiIKICAgICAgXSwKICAgICAgInByb3BlcnRpZXMiOiB7CiAgICAgICAgIlRvbGVyYW5jZSI6ICI1JSIKICAgICAgfSwKICAgICAgInJlZiI6ICJSMzkiLAogICAgICAidmFsdWUiOiAiUmwiCiAgICB9LAogICAgewogICAgICAicGFnZSI6ICJNQUlOIiwKICAgICAgInBpbnMiOiBbCiAgICAgICAgIjEiLAogICAgICAgICIyIgogICAgICBdLAogICAgICAicHJvcGVydGllcyI6IHsKICAgICAgICAiVG9sZXJhbmNlIjogIjUlIgogICAgICB9LAogICAgICAicmVmIjogIlIzNCIsCiAgICAgICJ2YWx1ZSI6ICJSZSIKICAgIH0sCiAgICB7CiAgICAgICJwYWdlIjogIk1BSU4iLAogICAgICAicGlucyI6IFsKICAgICAgICAiMSIsCiAgICAgICAgIjIiCiAgICAgIF0sCiAgICAgICJwcm9wZXJ0aWVzIjoge30sCiAgICAgICJyZWYiOiAiQzEiLAogICAgICAidmFsdWUiOiAiQ2NiZmIiCiAgICB9LAogICAgewogICAgICAicGFnZSI6ICJNQUlOIiwKICAgICAgInBpbnMiOiBbCiAgICAgICAgIjEiLAogICAgICAgICIyIgogICAgICBdLAogICAgICAicHJvcGVydGllcyI6IHt9LAogICAgICAicmVmIjogIkMzIiwKICAgICAgInZhbHVlIjogIkMwIgogICAgfSwKICAgIHsKICAgICAgInBhZ2UiOiAiTUFJTiIsCiAgICAgICJwaW5zIjogWwogICAgICAgICJCIiwKICAgICAgICAiQyIsCiAgICAgICAgIkUiCiAgICAgIF0sCiAgICAgICJwcm9wZXJ0aWVzIjoge30sCiAgICAgICJyZWYiOiAiUTE2IiwKICAgICAgInZhbHVlIjogIjJOMzkwNCIKICAgIH0sCiAgICB7CiAgICAgICJwYWdlIjogIk1BSU4iLAogICAgICAicGlucyI6IFsKICAgICAgICAiMSIsCiAgICAgICAgIjIiCiAgICAgIF0sCiAgICAgICJwcm9wZXJ0aWVzIjoge30sCiAgICAgICJyZWYiOiAiTDEiLAogICAgICAidmFsdWUiOiAiTDAiCiAgICB9LAogICAgewogICAgICAicGFnZSI6ICJNQUlOIiwKICAgICAgInBpbnMiOiBbCiAgICAgICAgIjEiLAogICAgICAgICIyIgogICAgICBdLAogICAgICAicHJvcGVydGllcyI6IHt9LAogICAgICAicmVmIjogIlYyNCIsCiAgICAgICJ2YWx1ZSI6ICJWY2MiCiAgICB9CiAgXSwKICAiZm9ybWF0IjogImVuZ2l3b3JsZC1uZXV0cmFsLXNjaGVtYXRpYy12MSIsCiAgIm5hbWUiOiAib3NjaWxsYXRvcl9jb3JlIiwKICAicHJvcGVydGllcyI6IHt9LAogICJzY2hlbWF0aWNzIjogWwogICAgewogICAgICAiaGllcl9ibG9ja3MiOiBbXSwKICAgICAgIm5hbWUiOiAib3NjaWxsYXRvcl9jb3JlIiwKICAgICAgInBhZ2VzIjogWwogICAgICAgICJNQUlOIgogICAgICBdCiAgICB9CiAgXQp9Cg=="
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
