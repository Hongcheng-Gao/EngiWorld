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
  "tolerance_report.csv": "UmVmZXJlbmNlLFRvbGVyYW5jZQ0KUjEsMSUNClIyLDElDQpSMywxJQ0KUjQsMSUNCg==",
  "tutor2_tolerance.edif": "KGVkaWYgVFVUT1IyCiAgKGVkaWZWZXJzaW9uIDIgMCAwKQogIChlZGlmTGV2ZWwgMCkKICAoa2V5d29yZE1hcCAoa2V5d29yZExldmVsIDApKQogIChzdGF0dXMgKHdyaXR0ZW4gKHRpbWVTdGFtcCAyMDI2IDcgNSAwIDAgMCkgKHByb2dyYW0gIkVuZ2l3b3JsZE5ldXRyYWwiKSkpCiAgKGxpYnJhcnkgVFVUT1IyCiAgICAoY2VsbCBUVVRPUjIgKGNlbGxUeXBlIEdFTkVSSUMpKQogICkKICAoZGVzaWduIFRVVE9SMgogICAgKGluc3RhbmNlIFIxCiAgICAgIChwcm9wZXJ0eSBWYWx1ZSAoc3RyaW5nICIxayIpKQogICAgICAocHJvcGVydHkgUGFnZSAoc3RyaW5nICJUVVRPUjIiKSkKICAgICAgKHByb3BlcnR5IFRvbGVyYW5jZSAoc3RyaW5nICIxJSIpKQogICAgICAocHJvcGVydHkgUElOXzEgKHN0cmluZyAiMSIpKQogICAgICAocHJvcGVydHkgUElOXzIgKHN0cmluZyAiMiIpKQogICAgKQogICAgKGluc3RhbmNlIFIyCiAgICAgIChwcm9wZXJ0eSBWYWx1ZSAoc3RyaW5nICIyLjJrIikpCiAgICAgIChwcm9wZXJ0eSBQYWdlIChzdHJpbmcgIlRVVE9SMiIpKQogICAgICAocHJvcGVydHkgVG9sZXJhbmNlIChzdHJpbmcgIjElIikpCiAgICAgIChwcm9wZXJ0eSBQSU5fMSAoc3RyaW5nICIxIikpCiAgICAgIChwcm9wZXJ0eSBQSU5fMiAoc3RyaW5nICIyIikpCiAgICApCiAgICAoaW5zdGFuY2UgUjMKICAgICAgKHByb3BlcnR5IFZhbHVlIChzdHJpbmcgIjgyMCIpKQogICAgICAocHJvcGVydHkgUGFnZSAoc3RyaW5nICJUVVRPUjIiKSkKICAgICAgKHByb3BlcnR5IFRvbGVyYW5jZSAoc3RyaW5nICIxJSIpKQogICAgICAocHJvcGVydHkgUElOXzEgKHN0cmluZyAiMSIpKQogICAgICAocHJvcGVydHkgUElOXzIgKHN0cmluZyAiMiIpKQogICAgKQogICAgKGluc3RhbmNlIFI0CiAgICAgIChwcm9wZXJ0eSBWYWx1ZSAoc3RyaW5nICI0LjdrIikpCiAgICAgIChwcm9wZXJ0eSBQYWdlIChzdHJpbmcgIlRVVE9SMiIpKQogICAgICAocHJvcGVydHkgVG9sZXJhbmNlIChzdHJpbmcgIjElIikpCiAgICAgIChwcm9wZXJ0eSBQSU5fMSAoc3RyaW5nICIxIikpCiAgICAgIChwcm9wZXJ0eSBQSU5fMiAoc3RyaW5nICIyIikpCiAgICApCiAgICAoaW5zdGFuY2UgQzEKICAgICAgKHByb3BlcnR5IFZhbHVlIChzdHJpbmcgIjEwbkYiKSkKICAgICAgKHByb3BlcnR5IFBhZ2UgKHN0cmluZyAiVFVUT1IyIikpCiAgICAgIChwcm9wZXJ0eSBQSU5fMSAoc3RyaW5nICIxIikpCiAgICAgIChwcm9wZXJ0eSBQSU5fMiAoc3RyaW5nICIyIikpCiAgICApCiAgICAoaW5zdGFuY2UgQzIKICAgICAgKHByb3BlcnR5IFZhbHVlIChzdHJpbmcgIjF1RiIpKQogICAgICAocHJvcGVydHkgUGFnZSAoc3RyaW5nICJUVVRPUjIiKSkKICAgICAgKHByb3BlcnR5IFBJTl8xIChzdHJpbmcgIjEiKSkKICAgICAgKHByb3BlcnR5IFBJTl8yIChzdHJpbmcgIjIiKSkKICAgICkKICAgIChpbnN0YW5jZSBVMQogICAgICAocHJvcGVydHkgVmFsdWUgKHN0cmluZyAiTE0zNTgiKSkKICAgICAgKHByb3BlcnR5IFBhZ2UgKHN0cmluZyAiVFVUT1IyIikpCiAgICAgIChwcm9wZXJ0eSBQSU5fMSAoc3RyaW5nICIxIikpCiAgICAgIChwcm9wZXJ0eSBQSU5fMiAoc3RyaW5nICIyIikpCiAgICAgIChwcm9wZXJ0eSBQSU5fMyAoc3RyaW5nICIzIikpCiAgICAgIChwcm9wZXJ0eSBQSU5fNCAoc3RyaW5nICI0IikpCiAgICAgIChwcm9wZXJ0eSBQSU5fNSAoc3RyaW5nICI1IikpCiAgICAgIChwcm9wZXJ0eSBQSU5fNiAoc3RyaW5nICI2IikpCiAgICAgIChwcm9wZXJ0eSBQSU5fNyAoc3RyaW5nICI3IikpCiAgICAgIChwcm9wZXJ0eSBQSU5fOCAoc3RyaW5nICI4IikpCiAgICApCiAgICAoaW5zdGFuY2UgUTEKICAgICAgKHByb3BlcnR5IFZhbHVlIChzdHJpbmcgIjJOMzkwNCIpKQogICAgICAocHJvcGVydHkgUGFnZSAoc3RyaW5nICJUVVRPUjIiKSkKICAgICAgKHByb3BlcnR5IFBJTl8xIChzdHJpbmcgIjEiKSkKICAgICAgKHByb3BlcnR5IFBJTl8yIChzdHJpbmcgIjIiKSkKICAgICkKICAgIChpbnN0YW5jZSBEMQogICAgICAocHJvcGVydHkgVmFsdWUgKHN0cmluZyAiMU40MTQ4IikpCiAgICAgIChwcm9wZXJ0eSBQYWdlIChzdHJpbmcgIlRVVE9SMiIpKQogICAgICAocHJvcGVydHkgUElOXzEgKHN0cmluZyAiMSIpKQogICAgICAocHJvcGVydHkgUElOXzIgKHN0cmluZyAiMiIpKQogICAgKQogICAgKGluc3RhbmNlIFMxCiAgICAgIChwcm9wZXJ0eSBWYWx1ZSAoc3RyaW5nICJTV19TUFNUIikpCiAgICAgIChwcm9wZXJ0eSBQYWdlIChzdHJpbmcgIlRVVE9SMiIpKQogICAgICAocHJvcGVydHkgUElOXzEgKHN0cmluZyAiMSIpKQogICAgICAocHJvcGVydHkgUElOXzIgKHN0cmluZyAiMiIpKQogICAgICAocHJvcGVydHkgUElOXzMgKHN0cmluZyAiMyIpKQogICAgICAocHJvcGVydHkgUElOXzQgKHN0cmluZyAiNCIpKQogICAgICAocHJvcGVydHkgUElOXzUgKHN0cmluZyAiNSIpKQogICAgICAocHJvcGVydHkgUElOXzYgKHN0cmluZyAiNiIpKQogICAgICAocHJvcGVydHkgUElOXzcgKHN0cmluZyAiNyIpKQogICAgICAocHJvcGVydHkgUElOXzggKHN0cmluZyAiOCIpKQogICAgKQogICAgKGluc3RhbmNlIEJUMQogICAgICAocHJvcGVydHkgVmFsdWUgKHN0cmluZyAiQ1IyMDMyIikpCiAgICAgIChwcm9wZXJ0eSBQYWdlIChzdHJpbmcgIlRVVE9SMiIpKQogICAgICAocHJvcGVydHkgUElOXzEgKHN0cmluZyAiMSIpKQogICAgICAocHJvcGVydHkgUElOXzIgKHN0cmluZyAiMiIpKQogICAgICAocHJvcGVydHkgUElOXzMgKHN0cmluZyAiMyIpKQogICAgICAocHJvcGVydHkgUElOXzQgKHN0cmluZyAiNCIpKQogICAgICAocHJvcGVydHkgUElOXzUgKHN0cmluZyAiNSIpKQogICAgICAocHJvcGVydHkgUElOXzYgKHN0cmluZyAiNiIpKQogICAgICAocHJvcGVydHkgUElOXzcgKHN0cmluZyAiNyIpKQogICAgICAocHJvcGVydHkgUElOXzggKHN0cmluZyAiOCIpKQogICAgKQogICkKKQo=",
  "tutor2_tolerance.schematic.json": "ewogICJjb21wb25lbnRzIjogWwogICAgewogICAgICAicGFnZSI6ICJUVVRPUjIiLAogICAgICAicGlucyI6IFsKICAgICAgICAiMSIsCiAgICAgICAgIjIiCiAgICAgIF0sCiAgICAgICJwcm9wZXJ0aWVzIjogewogICAgICAgICJUb2xlcmFuY2UiOiAiMSUiCiAgICAgIH0sCiAgICAgICJyZWYiOiAiUjEiLAogICAgICAidmFsdWUiOiAiMWsiCiAgICB9LAogICAgewogICAgICAicGFnZSI6ICJUVVRPUjIiLAogICAgICAicGlucyI6IFsKICAgICAgICAiMSIsCiAgICAgICAgIjIiCiAgICAgIF0sCiAgICAgICJwcm9wZXJ0aWVzIjogewogICAgICAgICJUb2xlcmFuY2UiOiAiMSUiCiAgICAgIH0sCiAgICAgICJyZWYiOiAiUjIiLAogICAgICAidmFsdWUiOiAiMi4yayIKICAgIH0sCiAgICB7CiAgICAgICJwYWdlIjogIlRVVE9SMiIsCiAgICAgICJwaW5zIjogWwogICAgICAgICIxIiwKICAgICAgICAiMiIKICAgICAgXSwKICAgICAgInByb3BlcnRpZXMiOiB7CiAgICAgICAgIlRvbGVyYW5jZSI6ICIxJSIKICAgICAgfSwKICAgICAgInJlZiI6ICJSMyIsCiAgICAgICJ2YWx1ZSI6ICI4MjAiCiAgICB9LAogICAgewogICAgICAicGFnZSI6ICJUVVRPUjIiLAogICAgICAicGlucyI6IFsKICAgICAgICAiMSIsCiAgICAgICAgIjIiCiAgICAgIF0sCiAgICAgICJwcm9wZXJ0aWVzIjogewogICAgICAgICJUb2xlcmFuY2UiOiAiMSUiCiAgICAgIH0sCiAgICAgICJyZWYiOiAiUjQiLAogICAgICAidmFsdWUiOiAiNC43ayIKICAgIH0sCiAgICB7CiAgICAgICJwYWdlIjogIlRVVE9SMiIsCiAgICAgICJwaW5zIjogWwogICAgICAgICIxIiwKICAgICAgICAiMiIKICAgICAgXSwKICAgICAgInByb3BlcnRpZXMiOiB7fSwKICAgICAgInJlZiI6ICJDMSIsCiAgICAgICJ2YWx1ZSI6ICIxMG5GIgogICAgfSwKICAgIHsKICAgICAgInBhZ2UiOiAiVFVUT1IyIiwKICAgICAgInBpbnMiOiBbCiAgICAgICAgIjEiLAogICAgICAgICIyIgogICAgICBdLAogICAgICAicHJvcGVydGllcyI6IHt9LAogICAgICAicmVmIjogIkMyIiwKICAgICAgInZhbHVlIjogIjF1RiIKICAgIH0sCiAgICB7CiAgICAgICJwYWdlIjogIlRVVE9SMiIsCiAgICAgICJwaW5zIjogWwogICAgICAgICIxIiwKICAgICAgICAiMiIsCiAgICAgICAgIjMiLAogICAgICAgICI0IiwKICAgICAgICAiNSIsCiAgICAgICAgIjYiLAogICAgICAgICI3IiwKICAgICAgICAiOCIKICAgICAgXSwKICAgICAgInByb3BlcnRpZXMiOiB7fSwKICAgICAgInJlZiI6ICJVMSIsCiAgICAgICJ2YWx1ZSI6ICJMTTM1OCIKICAgIH0sCiAgICB7CiAgICAgICJwYWdlIjogIlRVVE9SMiIsCiAgICAgICJwaW5zIjogWwogICAgICAgICIxIiwKICAgICAgICAiMiIKICAgICAgXSwKICAgICAgInByb3BlcnRpZXMiOiB7fSwKICAgICAgInJlZiI6ICJRMSIsCiAgICAgICJ2YWx1ZSI6ICIyTjM5MDQiCiAgICB9LAogICAgewogICAgICAicGFnZSI6ICJUVVRPUjIiLAogICAgICAicGlucyI6IFsKICAgICAgICAiMSIsCiAgICAgICAgIjIiCiAgICAgIF0sCiAgICAgICJwcm9wZXJ0aWVzIjoge30sCiAgICAgICJyZWYiOiAiRDEiLAogICAgICAidmFsdWUiOiAiMU40MTQ4IgogICAgfSwKICAgIHsKICAgICAgInBhZ2UiOiAiVFVUT1IyIiwKICAgICAgInBpbnMiOiBbCiAgICAgICAgIjEiLAogICAgICAgICIyIiwKICAgICAgICAiMyIsCiAgICAgICAgIjQiLAogICAgICAgICI1IiwKICAgICAgICAiNiIsCiAgICAgICAgIjciLAogICAgICAgICI4IgogICAgICBdLAogICAgICAicHJvcGVydGllcyI6IHt9LAogICAgICAicmVmIjogIlMxIiwKICAgICAgInZhbHVlIjogIlNXX1NQU1QiCiAgICB9LAogICAgewogICAgICAicGFnZSI6ICJUVVRPUjIiLAogICAgICAicGlucyI6IFsKICAgICAgICAiMSIsCiAgICAgICAgIjIiLAogICAgICAgICIzIiwKICAgICAgICAiNCIsCiAgICAgICAgIjUiLAogICAgICAgICI2IiwKICAgICAgICAiNyIsCiAgICAgICAgIjgiCiAgICAgIF0sCiAgICAgICJwcm9wZXJ0aWVzIjoge30sCiAgICAgICJyZWYiOiAiQlQxIiwKICAgICAgInZhbHVlIjogIkNSMjAzMiIKICAgIH0KICBdLAogICJmb3JtYXQiOiAiZW5naXdvcmxkLW5ldXRyYWwtc2NoZW1hdGljLXYxIiwKICAibmFtZSI6ICJUVVRPUjIiLAogICJwcm9wZXJ0aWVzIjoge30sCiAgInNjaGVtYXRpY3MiOiBbCiAgICB7CiAgICAgICJoaWVyX2Jsb2NrcyI6IFtdLAogICAgICAibmFtZSI6ICJUVVRPUjIiLAogICAgICAicGFnZXMiOiBbCiAgICAgICAgIlRVVE9SMiIKICAgICAgXQogICAgfQogIF0KfQo="
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
