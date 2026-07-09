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
  "mfr_properties.csv": "UmVmZXJlbmNlLE1mcixNZnIgUE4sRGF0YXNoZWV0IFVSTA0KUjEsWWFnZW8sUkMwNjAzRlItMDcxS0wsaHR0cHM6Ly9leGFtcGxlLmNvbS9yMS5wZGYNCkMxLE11cmF0YSxHUk0xODhSNzFIMTAzS0EwMSxodHRwczovL2V4YW1wbGUuY29tL2MxLnBkZg0KVTEsVEksTE0zNThEUixodHRwczovL2V4YW1wbGUuY29tL3UxLnBkZg0K",
  "tutor2_mfr.edif": "KGVkaWYgVFVUT1IyCiAgKGVkaWZWZXJzaW9uIDIgMCAwKQogIChlZGlmTGV2ZWwgMCkKICAoa2V5d29yZE1hcCAoa2V5d29yZExldmVsIDApKQogIChzdGF0dXMgKHdyaXR0ZW4gKHRpbWVTdGFtcCAyMDI2IDcgNSAwIDAgMCkgKHByb2dyYW0gIkVuZ2l3b3JsZE5ldXRyYWwiKSkpCiAgKGxpYnJhcnkgVFVUT1IyCiAgICAoY2VsbCBUVVRPUjIgKGNlbGxUeXBlIEdFTkVSSUMpKQogICkKICAoZGVzaWduIFRVVE9SMgogICAgKGluc3RhbmNlIFIxCiAgICAgIChwcm9wZXJ0eSBWYWx1ZSAoc3RyaW5nICIxayIpKQogICAgICAocHJvcGVydHkgUGFnZSAoc3RyaW5nICJUVVRPUjIiKSkKICAgICAgKHByb3BlcnR5IERhdGFzaGVldF9VUkwgKHN0cmluZyAiaHR0cHM6Ly9leGFtcGxlLmNvbS9yMS5wZGYiKSkKICAgICAgKHByb3BlcnR5IE1mciAoc3RyaW5nICJZYWdlbyIpKQogICAgICAocHJvcGVydHkgTWZyX1BOIChzdHJpbmcgIlJDMDYwM0ZSLTA3MUtMIikpCiAgICAgIChwcm9wZXJ0eSBQSU5fMSAoc3RyaW5nICIxIikpCiAgICAgIChwcm9wZXJ0eSBQSU5fMiAoc3RyaW5nICIyIikpCiAgICApCiAgICAoaW5zdGFuY2UgUjIKICAgICAgKHByb3BlcnR5IFZhbHVlIChzdHJpbmcgIjIuMmsiKSkKICAgICAgKHByb3BlcnR5IFBhZ2UgKHN0cmluZyAiVFVUT1IyIikpCiAgICAgIChwcm9wZXJ0eSBQSU5fMSAoc3RyaW5nICIxIikpCiAgICAgIChwcm9wZXJ0eSBQSU5fMiAoc3RyaW5nICIyIikpCiAgICApCiAgICAoaW5zdGFuY2UgUjMKICAgICAgKHByb3BlcnR5IFZhbHVlIChzdHJpbmcgIjgyMCIpKQogICAgICAocHJvcGVydHkgUGFnZSAoc3RyaW5nICJUVVRPUjIiKSkKICAgICAgKHByb3BlcnR5IFBJTl8xIChzdHJpbmcgIjEiKSkKICAgICAgKHByb3BlcnR5IFBJTl8yIChzdHJpbmcgIjIiKSkKICAgICkKICAgIChpbnN0YW5jZSBSNAogICAgICAocHJvcGVydHkgVmFsdWUgKHN0cmluZyAiNC43ayIpKQogICAgICAocHJvcGVydHkgUGFnZSAoc3RyaW5nICJUVVRPUjIiKSkKICAgICAgKHByb3BlcnR5IFBJTl8xIChzdHJpbmcgIjEiKSkKICAgICAgKHByb3BlcnR5IFBJTl8yIChzdHJpbmcgIjIiKSkKICAgICkKICAgIChpbnN0YW5jZSBDMQogICAgICAocHJvcGVydHkgVmFsdWUgKHN0cmluZyAiMTBuRiIpKQogICAgICAocHJvcGVydHkgUGFnZSAoc3RyaW5nICJUVVRPUjIiKSkKICAgICAgKHByb3BlcnR5IERhdGFzaGVldF9VUkwgKHN0cmluZyAiaHR0cHM6Ly9leGFtcGxlLmNvbS9jMS5wZGYiKSkKICAgICAgKHByb3BlcnR5IE1mciAoc3RyaW5nICJNdXJhdGEiKSkKICAgICAgKHByb3BlcnR5IE1mcl9QTiAoc3RyaW5nICJHUk0xODhSNzFIMTAzS0EwMSIpKQogICAgICAocHJvcGVydHkgUElOXzEgKHN0cmluZyAiMSIpKQogICAgICAocHJvcGVydHkgUElOXzIgKHN0cmluZyAiMiIpKQogICAgKQogICAgKGluc3RhbmNlIEMyCiAgICAgIChwcm9wZXJ0eSBWYWx1ZSAoc3RyaW5nICIxdUYiKSkKICAgICAgKHByb3BlcnR5IFBhZ2UgKHN0cmluZyAiVFVUT1IyIikpCiAgICAgIChwcm9wZXJ0eSBQSU5fMSAoc3RyaW5nICIxIikpCiAgICAgIChwcm9wZXJ0eSBQSU5fMiAoc3RyaW5nICIyIikpCiAgICApCiAgICAoaW5zdGFuY2UgVTEKICAgICAgKHByb3BlcnR5IFZhbHVlIChzdHJpbmcgIkxNMzU4IikpCiAgICAgIChwcm9wZXJ0eSBQYWdlIChzdHJpbmcgIlRVVE9SMiIpKQogICAgICAocHJvcGVydHkgRGF0YXNoZWV0X1VSTCAoc3RyaW5nICJodHRwczovL2V4YW1wbGUuY29tL3UxLnBkZiIpKQogICAgICAocHJvcGVydHkgTWZyIChzdHJpbmcgIlRJIikpCiAgICAgIChwcm9wZXJ0eSBNZnJfUE4gKHN0cmluZyAiTE0zNThEUiIpKQogICAgICAocHJvcGVydHkgUElOXzEgKHN0cmluZyAiMSIpKQogICAgICAocHJvcGVydHkgUElOXzIgKHN0cmluZyAiMiIpKQogICAgICAocHJvcGVydHkgUElOXzMgKHN0cmluZyAiMyIpKQogICAgICAocHJvcGVydHkgUElOXzQgKHN0cmluZyAiNCIpKQogICAgICAocHJvcGVydHkgUElOXzUgKHN0cmluZyAiNSIpKQogICAgICAocHJvcGVydHkgUElOXzYgKHN0cmluZyAiNiIpKQogICAgICAocHJvcGVydHkgUElOXzcgKHN0cmluZyAiNyIpKQogICAgICAocHJvcGVydHkgUElOXzggKHN0cmluZyAiOCIpKQogICAgKQogICAgKGluc3RhbmNlIFExCiAgICAgIChwcm9wZXJ0eSBWYWx1ZSAoc3RyaW5nICIyTjM5MDQiKSkKICAgICAgKHByb3BlcnR5IFBhZ2UgKHN0cmluZyAiVFVUT1IyIikpCiAgICAgIChwcm9wZXJ0eSBQSU5fMSAoc3RyaW5nICIxIikpCiAgICAgIChwcm9wZXJ0eSBQSU5fMiAoc3RyaW5nICIyIikpCiAgICApCiAgICAoaW5zdGFuY2UgRDEKICAgICAgKHByb3BlcnR5IFZhbHVlIChzdHJpbmcgIjFONDE0OCIpKQogICAgICAocHJvcGVydHkgUGFnZSAoc3RyaW5nICJUVVRPUjIiKSkKICAgICAgKHByb3BlcnR5IFBJTl8xIChzdHJpbmcgIjEiKSkKICAgICAgKHByb3BlcnR5IFBJTl8yIChzdHJpbmcgIjIiKSkKICAgICkKICAgIChpbnN0YW5jZSBTMQogICAgICAocHJvcGVydHkgVmFsdWUgKHN0cmluZyAiU1dfU1BTVCIpKQogICAgICAocHJvcGVydHkgUGFnZSAoc3RyaW5nICJUVVRPUjIiKSkKICAgICAgKHByb3BlcnR5IFBJTl8xIChzdHJpbmcgIjEiKSkKICAgICAgKHByb3BlcnR5IFBJTl8yIChzdHJpbmcgIjIiKSkKICAgICAgKHByb3BlcnR5IFBJTl8zIChzdHJpbmcgIjMiKSkKICAgICAgKHByb3BlcnR5IFBJTl80IChzdHJpbmcgIjQiKSkKICAgICAgKHByb3BlcnR5IFBJTl81IChzdHJpbmcgIjUiKSkKICAgICAgKHByb3BlcnR5IFBJTl82IChzdHJpbmcgIjYiKSkKICAgICAgKHByb3BlcnR5IFBJTl83IChzdHJpbmcgIjciKSkKICAgICAgKHByb3BlcnR5IFBJTl84IChzdHJpbmcgIjgiKSkKICAgICkKICAgIChpbnN0YW5jZSBCVDEKICAgICAgKHByb3BlcnR5IFZhbHVlIChzdHJpbmcgIkNSMjAzMiIpKQogICAgICAocHJvcGVydHkgUGFnZSAoc3RyaW5nICJUVVRPUjIiKSkKICAgICAgKHByb3BlcnR5IFBJTl8xIChzdHJpbmcgIjEiKSkKICAgICAgKHByb3BlcnR5IFBJTl8yIChzdHJpbmcgIjIiKSkKICAgICAgKHByb3BlcnR5IFBJTl8zIChzdHJpbmcgIjMiKSkKICAgICAgKHByb3BlcnR5IFBJTl80IChzdHJpbmcgIjQiKSkKICAgICAgKHByb3BlcnR5IFBJTl81IChzdHJpbmcgIjUiKSkKICAgICAgKHByb3BlcnR5IFBJTl82IChzdHJpbmcgIjYiKSkKICAgICAgKHByb3BlcnR5IFBJTl83IChzdHJpbmcgIjciKSkKICAgICAgKHByb3BlcnR5IFBJTl84IChzdHJpbmcgIjgiKSkKICAgICkKICApCikK",
  "tutor2_mfr.schematic.json": "ewogICJjb21wb25lbnRzIjogWwogICAgewogICAgICAicGFnZSI6ICJUVVRPUjIiLAogICAgICAicGlucyI6IFsKICAgICAgICAiMSIsCiAgICAgICAgIjIiCiAgICAgIF0sCiAgICAgICJwcm9wZXJ0aWVzIjogewogICAgICAgICJEYXRhc2hlZXQgVVJMIjogImh0dHBzOi8vZXhhbXBsZS5jb20vcjEucGRmIiwKICAgICAgICAiTWZyIjogIllhZ2VvIiwKICAgICAgICAiTWZyIFBOIjogIlJDMDYwM0ZSLTA3MUtMIgogICAgICB9LAogICAgICAicmVmIjogIlIxIiwKICAgICAgInZhbHVlIjogIjFrIgogICAgfSwKICAgIHsKICAgICAgInBhZ2UiOiAiVFVUT1IyIiwKICAgICAgInBpbnMiOiBbCiAgICAgICAgIjEiLAogICAgICAgICIyIgogICAgICBdLAogICAgICAicHJvcGVydGllcyI6IHt9LAogICAgICAicmVmIjogIlIyIiwKICAgICAgInZhbHVlIjogIjIuMmsiCiAgICB9LAogICAgewogICAgICAicGFnZSI6ICJUVVRPUjIiLAogICAgICAicGlucyI6IFsKICAgICAgICAiMSIsCiAgICAgICAgIjIiCiAgICAgIF0sCiAgICAgICJwcm9wZXJ0aWVzIjoge30sCiAgICAgICJyZWYiOiAiUjMiLAogICAgICAidmFsdWUiOiAiODIwIgogICAgfSwKICAgIHsKICAgICAgInBhZ2UiOiAiVFVUT1IyIiwKICAgICAgInBpbnMiOiBbCiAgICAgICAgIjEiLAogICAgICAgICIyIgogICAgICBdLAogICAgICAicHJvcGVydGllcyI6IHt9LAogICAgICAicmVmIjogIlI0IiwKICAgICAgInZhbHVlIjogIjQuN2siCiAgICB9LAogICAgewogICAgICAicGFnZSI6ICJUVVRPUjIiLAogICAgICAicGlucyI6IFsKICAgICAgICAiMSIsCiAgICAgICAgIjIiCiAgICAgIF0sCiAgICAgICJwcm9wZXJ0aWVzIjogewogICAgICAgICJEYXRhc2hlZXQgVVJMIjogImh0dHBzOi8vZXhhbXBsZS5jb20vYzEucGRmIiwKICAgICAgICAiTWZyIjogIk11cmF0YSIsCiAgICAgICAgIk1mciBQTiI6ICJHUk0xODhSNzFIMTAzS0EwMSIKICAgICAgfSwKICAgICAgInJlZiI6ICJDMSIsCiAgICAgICJ2YWx1ZSI6ICIxMG5GIgogICAgfSwKICAgIHsKICAgICAgInBhZ2UiOiAiVFVUT1IyIiwKICAgICAgInBpbnMiOiBbCiAgICAgICAgIjEiLAogICAgICAgICIyIgogICAgICBdLAogICAgICAicHJvcGVydGllcyI6IHt9LAogICAgICAicmVmIjogIkMyIiwKICAgICAgInZhbHVlIjogIjF1RiIKICAgIH0sCiAgICB7CiAgICAgICJwYWdlIjogIlRVVE9SMiIsCiAgICAgICJwaW5zIjogWwogICAgICAgICIxIiwKICAgICAgICAiMiIsCiAgICAgICAgIjMiLAogICAgICAgICI0IiwKICAgICAgICAiNSIsCiAgICAgICAgIjYiLAogICAgICAgICI3IiwKICAgICAgICAiOCIKICAgICAgXSwKICAgICAgInByb3BlcnRpZXMiOiB7CiAgICAgICAgIkRhdGFzaGVldCBVUkwiOiAiaHR0cHM6Ly9leGFtcGxlLmNvbS91MS5wZGYiLAogICAgICAgICJNZnIiOiAiVEkiLAogICAgICAgICJNZnIgUE4iOiAiTE0zNThEUiIKICAgICAgfSwKICAgICAgInJlZiI6ICJVMSIsCiAgICAgICJ2YWx1ZSI6ICJMTTM1OCIKICAgIH0sCiAgICB7CiAgICAgICJwYWdlIjogIlRVVE9SMiIsCiAgICAgICJwaW5zIjogWwogICAgICAgICIxIiwKICAgICAgICAiMiIKICAgICAgXSwKICAgICAgInByb3BlcnRpZXMiOiB7fSwKICAgICAgInJlZiI6ICJRMSIsCiAgICAgICJ2YWx1ZSI6ICIyTjM5MDQiCiAgICB9LAogICAgewogICAgICAicGFnZSI6ICJUVVRPUjIiLAogICAgICAicGlucyI6IFsKICAgICAgICAiMSIsCiAgICAgICAgIjIiCiAgICAgIF0sCiAgICAgICJwcm9wZXJ0aWVzIjoge30sCiAgICAgICJyZWYiOiAiRDEiLAogICAgICAidmFsdWUiOiAiMU40MTQ4IgogICAgfSwKICAgIHsKICAgICAgInBhZ2UiOiAiVFVUT1IyIiwKICAgICAgInBpbnMiOiBbCiAgICAgICAgIjEiLAogICAgICAgICIyIiwKICAgICAgICAiMyIsCiAgICAgICAgIjQiLAogICAgICAgICI1IiwKICAgICAgICAiNiIsCiAgICAgICAgIjciLAogICAgICAgICI4IgogICAgICBdLAogICAgICAicHJvcGVydGllcyI6IHt9LAogICAgICAicmVmIjogIlMxIiwKICAgICAgInZhbHVlIjogIlNXX1NQU1QiCiAgICB9LAogICAgewogICAgICAicGFnZSI6ICJUVVRPUjIiLAogICAgICAicGlucyI6IFsKICAgICAgICAiMSIsCiAgICAgICAgIjIiLAogICAgICAgICIzIiwKICAgICAgICAiNCIsCiAgICAgICAgIjUiLAogICAgICAgICI2IiwKICAgICAgICAiNyIsCiAgICAgICAgIjgiCiAgICAgIF0sCiAgICAgICJwcm9wZXJ0aWVzIjoge30sCiAgICAgICJyZWYiOiAiQlQxIiwKICAgICAgInZhbHVlIjogIkNSMjAzMiIKICAgIH0KICBdLAogICJmb3JtYXQiOiAiZW5naXdvcmxkLW5ldXRyYWwtc2NoZW1hdGljLXYxIiwKICAibmFtZSI6ICJUVVRPUjIiLAogICJwcm9wZXJ0aWVzIjoge30sCiAgInNjaGVtYXRpY3MiOiBbCiAgICB7CiAgICAgICJoaWVyX2Jsb2NrcyI6IFtdLAogICAgICAibmFtZSI6ICJUVVRPUjIiLAogICAgICAicGFnZXMiOiBbCiAgICAgICAgIlRVVE9SMiIKICAgICAgXQogICAgfQogIF0KfQo="
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
