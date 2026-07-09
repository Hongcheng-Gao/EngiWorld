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
  "renumber_report.csv": "T2xkUmVmLE5ld1JlZg0KQzEsQzMwMQ0KQzIsQzMwMg0KUTEsUTQwMQ0KUjEsUjIwMQ0KUjIsUjIwMg0KUjMsUjIwMw0KUjQsUjIwNA0KVTEsVTEwMQ0K",
  "tutor2_renumbered.edif": "KGVkaWYgVFVUT1IyCiAgKGVkaWZWZXJzaW9uIDIgMCAwKQogIChlZGlmTGV2ZWwgMCkKICAoa2V5d29yZE1hcCAoa2V5d29yZExldmVsIDApKQogIChzdGF0dXMgKHdyaXR0ZW4gKHRpbWVTdGFtcCAyMDI2IDcgNSAwIDAgMCkgKHByb2dyYW0gIkVuZ2l3b3JsZE5ldXRyYWwiKSkpCiAgKGxpYnJhcnkgVFVUT1IyCiAgICAoY2VsbCBUVVRPUjIgKGNlbGxUeXBlIEdFTkVSSUMpKQogICkKICAoZGVzaWduIFRVVE9SMgogICAgKGluc3RhbmNlIFIyMDEKICAgICAgKHByb3BlcnR5IFZhbHVlIChzdHJpbmcgIjFrIikpCiAgICAgIChwcm9wZXJ0eSBQYWdlIChzdHJpbmcgIlRVVE9SMiIpKQogICAgICAocHJvcGVydHkgUElOXzEgKHN0cmluZyAiMSIpKQogICAgICAocHJvcGVydHkgUElOXzIgKHN0cmluZyAiMiIpKQogICAgKQogICAgKGluc3RhbmNlIFIyMDIKICAgICAgKHByb3BlcnR5IFZhbHVlIChzdHJpbmcgIjIuMmsiKSkKICAgICAgKHByb3BlcnR5IFBhZ2UgKHN0cmluZyAiVFVUT1IyIikpCiAgICAgIChwcm9wZXJ0eSBQSU5fMSAoc3RyaW5nICIxIikpCiAgICAgIChwcm9wZXJ0eSBQSU5fMiAoc3RyaW5nICIyIikpCiAgICApCiAgICAoaW5zdGFuY2UgUjIwMwogICAgICAocHJvcGVydHkgVmFsdWUgKHN0cmluZyAiODIwIikpCiAgICAgIChwcm9wZXJ0eSBQYWdlIChzdHJpbmcgIlRVVE9SMiIpKQogICAgICAocHJvcGVydHkgUElOXzEgKHN0cmluZyAiMSIpKQogICAgICAocHJvcGVydHkgUElOXzIgKHN0cmluZyAiMiIpKQogICAgKQogICAgKGluc3RhbmNlIFIyMDQKICAgICAgKHByb3BlcnR5IFZhbHVlIChzdHJpbmcgIjQuN2siKSkKICAgICAgKHByb3BlcnR5IFBhZ2UgKHN0cmluZyAiVFVUT1IyIikpCiAgICAgIChwcm9wZXJ0eSBQSU5fMSAoc3RyaW5nICIxIikpCiAgICAgIChwcm9wZXJ0eSBQSU5fMiAoc3RyaW5nICIyIikpCiAgICApCiAgICAoaW5zdGFuY2UgQzMwMQogICAgICAocHJvcGVydHkgVmFsdWUgKHN0cmluZyAiMTBuRiIpKQogICAgICAocHJvcGVydHkgUGFnZSAoc3RyaW5nICJUVVRPUjIiKSkKICAgICAgKHByb3BlcnR5IFBJTl8xIChzdHJpbmcgIjEiKSkKICAgICAgKHByb3BlcnR5IFBJTl8yIChzdHJpbmcgIjIiKSkKICAgICkKICAgIChpbnN0YW5jZSBDMzAyCiAgICAgIChwcm9wZXJ0eSBWYWx1ZSAoc3RyaW5nICIxdUYiKSkKICAgICAgKHByb3BlcnR5IFBhZ2UgKHN0cmluZyAiVFVUT1IyIikpCiAgICAgIChwcm9wZXJ0eSBQSU5fMSAoc3RyaW5nICIxIikpCiAgICAgIChwcm9wZXJ0eSBQSU5fMiAoc3RyaW5nICIyIikpCiAgICApCiAgICAoaW5zdGFuY2UgVTEwMQogICAgICAocHJvcGVydHkgVmFsdWUgKHN0cmluZyAiTE0zNTgiKSkKICAgICAgKHByb3BlcnR5IFBhZ2UgKHN0cmluZyAiVFVUT1IyIikpCiAgICAgIChwcm9wZXJ0eSBQSU5fMSAoc3RyaW5nICIxIikpCiAgICAgIChwcm9wZXJ0eSBQSU5fMiAoc3RyaW5nICIyIikpCiAgICAgIChwcm9wZXJ0eSBQSU5fMyAoc3RyaW5nICIzIikpCiAgICAgIChwcm9wZXJ0eSBQSU5fNCAoc3RyaW5nICI0IikpCiAgICAgIChwcm9wZXJ0eSBQSU5fNSAoc3RyaW5nICI1IikpCiAgICAgIChwcm9wZXJ0eSBQSU5fNiAoc3RyaW5nICI2IikpCiAgICAgIChwcm9wZXJ0eSBQSU5fNyAoc3RyaW5nICI3IikpCiAgICAgIChwcm9wZXJ0eSBQSU5fOCAoc3RyaW5nICI4IikpCiAgICApCiAgICAoaW5zdGFuY2UgUTQwMQogICAgICAocHJvcGVydHkgVmFsdWUgKHN0cmluZyAiMk4zOTA0IikpCiAgICAgIChwcm9wZXJ0eSBQYWdlIChzdHJpbmcgIlRVVE9SMiIpKQogICAgICAocHJvcGVydHkgUElOXzEgKHN0cmluZyAiMSIpKQogICAgICAocHJvcGVydHkgUElOXzIgKHN0cmluZyAiMiIpKQogICAgKQogICAgKGluc3RhbmNlIEQxCiAgICAgIChwcm9wZXJ0eSBWYWx1ZSAoc3RyaW5nICIxTjQxNDgiKSkKICAgICAgKHByb3BlcnR5IFBhZ2UgKHN0cmluZyAiVFVUT1IyIikpCiAgICAgIChwcm9wZXJ0eSBQSU5fMSAoc3RyaW5nICIxIikpCiAgICAgIChwcm9wZXJ0eSBQSU5fMiAoc3RyaW5nICIyIikpCiAgICApCiAgICAoaW5zdGFuY2UgUzEKICAgICAgKHByb3BlcnR5IFZhbHVlIChzdHJpbmcgIlNXX1NQU1QiKSkKICAgICAgKHByb3BlcnR5IFBhZ2UgKHN0cmluZyAiVFVUT1IyIikpCiAgICAgIChwcm9wZXJ0eSBQSU5fMSAoc3RyaW5nICIxIikpCiAgICAgIChwcm9wZXJ0eSBQSU5fMiAoc3RyaW5nICIyIikpCiAgICAgIChwcm9wZXJ0eSBQSU5fMyAoc3RyaW5nICIzIikpCiAgICAgIChwcm9wZXJ0eSBQSU5fNCAoc3RyaW5nICI0IikpCiAgICAgIChwcm9wZXJ0eSBQSU5fNSAoc3RyaW5nICI1IikpCiAgICAgIChwcm9wZXJ0eSBQSU5fNiAoc3RyaW5nICI2IikpCiAgICAgIChwcm9wZXJ0eSBQSU5fNyAoc3RyaW5nICI3IikpCiAgICAgIChwcm9wZXJ0eSBQSU5fOCAoc3RyaW5nICI4IikpCiAgICApCiAgICAoaW5zdGFuY2UgQlQxCiAgICAgIChwcm9wZXJ0eSBWYWx1ZSAoc3RyaW5nICJDUjIwMzIiKSkKICAgICAgKHByb3BlcnR5IFBhZ2UgKHN0cmluZyAiVFVUT1IyIikpCiAgICAgIChwcm9wZXJ0eSBQSU5fMSAoc3RyaW5nICIxIikpCiAgICAgIChwcm9wZXJ0eSBQSU5fMiAoc3RyaW5nICIyIikpCiAgICAgIChwcm9wZXJ0eSBQSU5fMyAoc3RyaW5nICIzIikpCiAgICAgIChwcm9wZXJ0eSBQSU5fNCAoc3RyaW5nICI0IikpCiAgICAgIChwcm9wZXJ0eSBQSU5fNSAoc3RyaW5nICI1IikpCiAgICAgIChwcm9wZXJ0eSBQSU5fNiAoc3RyaW5nICI2IikpCiAgICAgIChwcm9wZXJ0eSBQSU5fNyAoc3RyaW5nICI3IikpCiAgICAgIChwcm9wZXJ0eSBQSU5fOCAoc3RyaW5nICI4IikpCiAgICApCiAgKQopCg==",
  "tutor2_renumbered.schematic.json": "ewogICJjb21wb25lbnRzIjogWwogICAgewogICAgICAicGFnZSI6ICJUVVRPUjIiLAogICAgICAicGlucyI6IFsKICAgICAgICAiMSIsCiAgICAgICAgIjIiCiAgICAgIF0sCiAgICAgICJwcm9wZXJ0aWVzIjoge30sCiAgICAgICJyZWYiOiAiUjIwMSIsCiAgICAgICJ2YWx1ZSI6ICIxayIKICAgIH0sCiAgICB7CiAgICAgICJwYWdlIjogIlRVVE9SMiIsCiAgICAgICJwaW5zIjogWwogICAgICAgICIxIiwKICAgICAgICAiMiIKICAgICAgXSwKICAgICAgInByb3BlcnRpZXMiOiB7fSwKICAgICAgInJlZiI6ICJSMjAyIiwKICAgICAgInZhbHVlIjogIjIuMmsiCiAgICB9LAogICAgewogICAgICAicGFnZSI6ICJUVVRPUjIiLAogICAgICAicGlucyI6IFsKICAgICAgICAiMSIsCiAgICAgICAgIjIiCiAgICAgIF0sCiAgICAgICJwcm9wZXJ0aWVzIjoge30sCiAgICAgICJyZWYiOiAiUjIwMyIsCiAgICAgICJ2YWx1ZSI6ICI4MjAiCiAgICB9LAogICAgewogICAgICAicGFnZSI6ICJUVVRPUjIiLAogICAgICAicGlucyI6IFsKICAgICAgICAiMSIsCiAgICAgICAgIjIiCiAgICAgIF0sCiAgICAgICJwcm9wZXJ0aWVzIjoge30sCiAgICAgICJyZWYiOiAiUjIwNCIsCiAgICAgICJ2YWx1ZSI6ICI0LjdrIgogICAgfSwKICAgIHsKICAgICAgInBhZ2UiOiAiVFVUT1IyIiwKICAgICAgInBpbnMiOiBbCiAgICAgICAgIjEiLAogICAgICAgICIyIgogICAgICBdLAogICAgICAicHJvcGVydGllcyI6IHt9LAogICAgICAicmVmIjogIkMzMDEiLAogICAgICAidmFsdWUiOiAiMTBuRiIKICAgIH0sCiAgICB7CiAgICAgICJwYWdlIjogIlRVVE9SMiIsCiAgICAgICJwaW5zIjogWwogICAgICAgICIxIiwKICAgICAgICAiMiIKICAgICAgXSwKICAgICAgInByb3BlcnRpZXMiOiB7fSwKICAgICAgInJlZiI6ICJDMzAyIiwKICAgICAgInZhbHVlIjogIjF1RiIKICAgIH0sCiAgICB7CiAgICAgICJwYWdlIjogIlRVVE9SMiIsCiAgICAgICJwaW5zIjogWwogICAgICAgICIxIiwKICAgICAgICAiMiIsCiAgICAgICAgIjMiLAogICAgICAgICI0IiwKICAgICAgICAiNSIsCiAgICAgICAgIjYiLAogICAgICAgICI3IiwKICAgICAgICAiOCIKICAgICAgXSwKICAgICAgInByb3BlcnRpZXMiOiB7fSwKICAgICAgInJlZiI6ICJVMTAxIiwKICAgICAgInZhbHVlIjogIkxNMzU4IgogICAgfSwKICAgIHsKICAgICAgInBhZ2UiOiAiVFVUT1IyIiwKICAgICAgInBpbnMiOiBbCiAgICAgICAgIjEiLAogICAgICAgICIyIgogICAgICBdLAogICAgICAicHJvcGVydGllcyI6IHt9LAogICAgICAicmVmIjogIlE0MDEiLAogICAgICAidmFsdWUiOiAiMk4zOTA0IgogICAgfSwKICAgIHsKICAgICAgInBhZ2UiOiAiVFVUT1IyIiwKICAgICAgInBpbnMiOiBbCiAgICAgICAgIjEiLAogICAgICAgICIyIgogICAgICBdLAogICAgICAicHJvcGVydGllcyI6IHt9LAogICAgICAicmVmIjogIkQxIiwKICAgICAgInZhbHVlIjogIjFONDE0OCIKICAgIH0sCiAgICB7CiAgICAgICJwYWdlIjogIlRVVE9SMiIsCiAgICAgICJwaW5zIjogWwogICAgICAgICIxIiwKICAgICAgICAiMiIsCiAgICAgICAgIjMiLAogICAgICAgICI0IiwKICAgICAgICAiNSIsCiAgICAgICAgIjYiLAogICAgICAgICI3IiwKICAgICAgICAiOCIKICAgICAgXSwKICAgICAgInByb3BlcnRpZXMiOiB7fSwKICAgICAgInJlZiI6ICJTMSIsCiAgICAgICJ2YWx1ZSI6ICJTV19TUFNUIgogICAgfSwKICAgIHsKICAgICAgInBhZ2UiOiAiVFVUT1IyIiwKICAgICAgInBpbnMiOiBbCiAgICAgICAgIjEiLAogICAgICAgICIyIiwKICAgICAgICAiMyIsCiAgICAgICAgIjQiLAogICAgICAgICI1IiwKICAgICAgICAiNiIsCiAgICAgICAgIjciLAogICAgICAgICI4IgogICAgICBdLAogICAgICAicHJvcGVydGllcyI6IHt9LAogICAgICAicmVmIjogIkJUMSIsCiAgICAgICJ2YWx1ZSI6ICJDUjIwMzIiCiAgICB9CiAgXSwKICAiZm9ybWF0IjogImVuZ2l3b3JsZC1uZXV0cmFsLXNjaGVtYXRpYy12MSIsCiAgIm5hbWUiOiAiVFVUT1IyIiwKICAicHJvcGVydGllcyI6IHt9LAogICJzY2hlbWF0aWNzIjogWwogICAgewogICAgICAiaGllcl9ibG9ja3MiOiBbXSwKICAgICAgIm5hbWUiOiAiVFVUT1IyIiwKICAgICAgInBhZ2VzIjogWwogICAgICAgICJUVVRPUjIiCiAgICAgIF0KICAgIH0KICBdCn0K"
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
