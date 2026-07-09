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
  "component_properties.csv": "UmVmZXJlbmNlLFZhbHVlLENvbW1lbnQNClIzLDEwaywNClI2LDQuN2ssRmVlZGJhY2sgNC43aw0KSjEsQ09OTjcsQ29ubmVjdG9yIDctcGluIGhhcm5lc3MNClUxLE1DVSwNCg==",
  "harness_sheet_fixed.edif": "KGVkaWYgaGFybmVzc19zaGVldAogIChlZGlmVmVyc2lvbiAyIDAgMCkKICAoZWRpZkxldmVsIDApCiAgKGtleXdvcmRNYXAgKGtleXdvcmRMZXZlbCAwKSkKICAoc3RhdHVzICh3cml0dGVuICh0aW1lU3RhbXAgMjAyNiA3IDUgMCAwIDApIChwcm9ncmFtICJFbmdpd29ybGROZXV0cmFsIikpKQogIChsaWJyYXJ5IGhhcm5lc3Nfc2hlZXQKICAgIChjZWxsIE1BSU4gKGNlbGxUeXBlIEdFTkVSSUMpKQogICkKICAoZGVzaWduIGhhcm5lc3Nfc2hlZXQKICAgIChpbnN0YW5jZSBSMwogICAgICAocHJvcGVydHkgVmFsdWUgKHN0cmluZyAiMTBrIikpCiAgICAgIChwcm9wZXJ0eSBQYWdlIChzdHJpbmcgIk1BSU4iKSkKICAgICAgKHByb3BlcnR5IFBJTl8xIChzdHJpbmcgIjEiKSkKICAgICAgKHByb3BlcnR5IFBJTl8yIChzdHJpbmcgIjIiKSkKICAgICkKICAgIChpbnN0YW5jZSBSNgogICAgICAocHJvcGVydHkgVmFsdWUgKHN0cmluZyAiNC43ayIpKQogICAgICAocHJvcGVydHkgUGFnZSAoc3RyaW5nICJNQUlOIikpCiAgICAgIChwcm9wZXJ0eSBDb21tZW50IChzdHJpbmcgIkZlZWRiYWNrIDQuN2siKSkKICAgICAgKHByb3BlcnR5IFBJTl8xIChzdHJpbmcgIjEiKSkKICAgICAgKHByb3BlcnR5IFBJTl8yIChzdHJpbmcgIjIiKSkKICAgICkKICAgIChpbnN0YW5jZSBKMQogICAgICAocHJvcGVydHkgVmFsdWUgKHN0cmluZyAiQ09OTjciKSkKICAgICAgKHByb3BlcnR5IFBhZ2UgKHN0cmluZyAiTUFJTiIpKQogICAgICAocHJvcGVydHkgQ29tbWVudCAoc3RyaW5nICJDb25uZWN0b3IgNy1waW4gaGFybmVzcyIpKQogICAgICAocHJvcGVydHkgUElOXzEgKHN0cmluZyAiMSIpKQogICAgICAocHJvcGVydHkgUElOXzIgKHN0cmluZyAiMiIpKQogICAgKQogICAgKGluc3RhbmNlIFUxCiAgICAgIChwcm9wZXJ0eSBWYWx1ZSAoc3RyaW5nICJNQ1UiKSkKICAgICAgKHByb3BlcnR5IFBhZ2UgKHN0cmluZyAiTUFJTiIpKQogICAgICAocHJvcGVydHkgUElOXzEgKHN0cmluZyAiMSIpKQogICAgICAocHJvcGVydHkgUElOXzIgKHN0cmluZyAiMiIpKQogICAgKQogICkKKQo=",
  "harness_sheet_fixed.schematic.json": "ewogICJjb21wb25lbnRzIjogWwogICAgewogICAgICAicGFnZSI6ICJNQUlOIiwKICAgICAgInBpbnMiOiBbCiAgICAgICAgIjEiLAogICAgICAgICIyIgogICAgICBdLAogICAgICAicHJvcGVydGllcyI6IHt9LAogICAgICAicmVmIjogIlIzIiwKICAgICAgInZhbHVlIjogIjEwayIKICAgIH0sCiAgICB7CiAgICAgICJwYWdlIjogIk1BSU4iLAogICAgICAicGlucyI6IFsKICAgICAgICAiMSIsCiAgICAgICAgIjIiCiAgICAgIF0sCiAgICAgICJwcm9wZXJ0aWVzIjogewogICAgICAgICJDb21tZW50IjogIkZlZWRiYWNrIDQuN2siCiAgICAgIH0sCiAgICAgICJyZWYiOiAiUjYiLAogICAgICAidmFsdWUiOiAiNC43ayIKICAgIH0sCiAgICB7CiAgICAgICJwYWdlIjogIk1BSU4iLAogICAgICAicGlucyI6IFsKICAgICAgICAiMSIsCiAgICAgICAgIjIiCiAgICAgIF0sCiAgICAgICJwcm9wZXJ0aWVzIjogewogICAgICAgICJDb21tZW50IjogIkNvbm5lY3RvciA3LXBpbiBoYXJuZXNzIgogICAgICB9LAogICAgICAicmVmIjogIkoxIiwKICAgICAgInZhbHVlIjogIkNPTk43IgogICAgfSwKICAgIHsKICAgICAgInBhZ2UiOiAiTUFJTiIsCiAgICAgICJwaW5zIjogWwogICAgICAgICIxIiwKICAgICAgICAiMiIKICAgICAgXSwKICAgICAgInByb3BlcnRpZXMiOiB7fSwKICAgICAgInJlZiI6ICJVMSIsCiAgICAgICJ2YWx1ZSI6ICJNQ1UiCiAgICB9CiAgXSwKICAiZm9ybWF0IjogImVuZ2l3b3JsZC1uZXV0cmFsLXNjaGVtYXRpYy12MSIsCiAgIm5hbWUiOiAiaGFybmVzc19zaGVldCIsCiAgInByb3BlcnRpZXMiOiB7fSwKICAic2NoZW1hdGljcyI6IFsKICAgIHsKICAgICAgImhpZXJfYmxvY2tzIjogW10sCiAgICAgICJuYW1lIjogImhhcm5lc3Nfc2hlZXQiLAogICAgICAicGFnZXMiOiBbCiAgICAgICAgIk1BSU4iCiAgICAgIF0KICAgIH0KICBdCn0K"
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
