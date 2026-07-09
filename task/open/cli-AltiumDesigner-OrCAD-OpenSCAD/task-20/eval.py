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
  "component_values.csv": "UmVmZXJlbmNlLFZhbHVlDQpSNDIsMWsNClIzMywxMGsNClIzOSw0N2sNClIzNCw0LjdrDQpDMSwzM3ANCkMzLDEwcA0KUTE2LDJOMzkwNA0KTDEsMTB1DQpWMjQsVmNjDQo=",
  "oscillator_tuned.edif": "KGVkaWYgb3NjaWxsYXRvcl9jb3JlCiAgKGVkaWZWZXJzaW9uIDIgMCAwKQogIChlZGlmTGV2ZWwgMCkKICAoa2V5d29yZE1hcCAoa2V5d29yZExldmVsIDApKQogIChzdGF0dXMgKHdyaXR0ZW4gKHRpbWVTdGFtcCAyMDI2IDcgNSAwIDAgMCkgKHByb2dyYW0gIkVuZ2l3b3JsZE5ldXRyYWwiKSkpCiAgKGxpYnJhcnkgb3NjaWxsYXRvcl9jb3JlCiAgICAoY2VsbCBNQUlOIChjZWxsVHlwZSBHRU5FUklDKSkKICApCiAgKGRlc2lnbiBvc2NpbGxhdG9yX2NvcmUKICAgIChpbnN0YW5jZSBSNDIKICAgICAgKHByb3BlcnR5IFZhbHVlIChzdHJpbmcgIjFrIikpCiAgICAgIChwcm9wZXJ0eSBQYWdlIChzdHJpbmcgIk1BSU4iKSkKICAgICAgKHByb3BlcnR5IFBJTl8xIChzdHJpbmcgIjEiKSkKICAgICAgKHByb3BlcnR5IFBJTl8yIChzdHJpbmcgIjIiKSkKICAgICkKICAgIChpbnN0YW5jZSBSMzMKICAgICAgKHByb3BlcnR5IFZhbHVlIChzdHJpbmcgIjEwayIpKQogICAgICAocHJvcGVydHkgUGFnZSAoc3RyaW5nICJNQUlOIikpCiAgICAgIChwcm9wZXJ0eSBQSU5fMSAoc3RyaW5nICIxIikpCiAgICAgIChwcm9wZXJ0eSBQSU5fMiAoc3RyaW5nICIyIikpCiAgICApCiAgICAoaW5zdGFuY2UgUjM5CiAgICAgIChwcm9wZXJ0eSBWYWx1ZSAoc3RyaW5nICI0N2siKSkKICAgICAgKHByb3BlcnR5IFBhZ2UgKHN0cmluZyAiTUFJTiIpKQogICAgICAocHJvcGVydHkgUElOXzEgKHN0cmluZyAiMSIpKQogICAgICAocHJvcGVydHkgUElOXzIgKHN0cmluZyAiMiIpKQogICAgKQogICAgKGluc3RhbmNlIFIzNAogICAgICAocHJvcGVydHkgVmFsdWUgKHN0cmluZyAiNC43ayIpKQogICAgICAocHJvcGVydHkgUGFnZSAoc3RyaW5nICJNQUlOIikpCiAgICAgIChwcm9wZXJ0eSBQSU5fMSAoc3RyaW5nICIxIikpCiAgICAgIChwcm9wZXJ0eSBQSU5fMiAoc3RyaW5nICIyIikpCiAgICApCiAgICAoaW5zdGFuY2UgQzEKICAgICAgKHByb3BlcnR5IFZhbHVlIChzdHJpbmcgIjMzcCIpKQogICAgICAocHJvcGVydHkgUGFnZSAoc3RyaW5nICJNQUlOIikpCiAgICAgIChwcm9wZXJ0eSBQSU5fMSAoc3RyaW5nICIxIikpCiAgICAgIChwcm9wZXJ0eSBQSU5fMiAoc3RyaW5nICIyIikpCiAgICApCiAgICAoaW5zdGFuY2UgQzMKICAgICAgKHByb3BlcnR5IFZhbHVlIChzdHJpbmcgIjEwcCIpKQogICAgICAocHJvcGVydHkgUGFnZSAoc3RyaW5nICJNQUlOIikpCiAgICAgIChwcm9wZXJ0eSBQSU5fMSAoc3RyaW5nICIxIikpCiAgICAgIChwcm9wZXJ0eSBQSU5fMiAoc3RyaW5nICIyIikpCiAgICApCiAgICAoaW5zdGFuY2UgUTE2CiAgICAgIChwcm9wZXJ0eSBWYWx1ZSAoc3RyaW5nICIyTjM5MDQiKSkKICAgICAgKHByb3BlcnR5IFBhZ2UgKHN0cmluZyAiTUFJTiIpKQogICAgICAocHJvcGVydHkgUElOX0IgKHN0cmluZyAiQiIpKQogICAgICAocHJvcGVydHkgUElOX0MgKHN0cmluZyAiQyIpKQogICAgICAocHJvcGVydHkgUElOX0UgKHN0cmluZyAiRSIpKQogICAgKQogICAgKGluc3RhbmNlIEwxCiAgICAgIChwcm9wZXJ0eSBWYWx1ZSAoc3RyaW5nICIxMHUiKSkKICAgICAgKHByb3BlcnR5IFBhZ2UgKHN0cmluZyAiTUFJTiIpKQogICAgICAocHJvcGVydHkgUElOXzEgKHN0cmluZyAiMSIpKQogICAgICAocHJvcGVydHkgUElOXzIgKHN0cmluZyAiMiIpKQogICAgKQogICAgKGluc3RhbmNlIFYyNAogICAgICAocHJvcGVydHkgVmFsdWUgKHN0cmluZyAiVmNjIikpCiAgICAgIChwcm9wZXJ0eSBQYWdlIChzdHJpbmcgIk1BSU4iKSkKICAgICAgKHByb3BlcnR5IFBJTl8xIChzdHJpbmcgIjEiKSkKICAgICAgKHByb3BlcnR5IFBJTl8yIChzdHJpbmcgIjIiKSkKICAgICkKICApCikK",
  "oscillator_tuned.schematic.json": "ewogICJjb21wb25lbnRzIjogWwogICAgewogICAgICAicGFnZSI6ICJNQUlOIiwKICAgICAgInBpbnMiOiBbCiAgICAgICAgIjEiLAogICAgICAgICIyIgogICAgICBdLAogICAgICAicHJvcGVydGllcyI6IHt9LAogICAgICAicmVmIjogIlI0MiIsCiAgICAgICJ2YWx1ZSI6ICIxayIKICAgIH0sCiAgICB7CiAgICAgICJwYWdlIjogIk1BSU4iLAogICAgICAicGlucyI6IFsKICAgICAgICAiMSIsCiAgICAgICAgIjIiCiAgICAgIF0sCiAgICAgICJwcm9wZXJ0aWVzIjoge30sCiAgICAgICJyZWYiOiAiUjMzIiwKICAgICAgInZhbHVlIjogIjEwayIKICAgIH0sCiAgICB7CiAgICAgICJwYWdlIjogIk1BSU4iLAogICAgICAicGlucyI6IFsKICAgICAgICAiMSIsCiAgICAgICAgIjIiCiAgICAgIF0sCiAgICAgICJwcm9wZXJ0aWVzIjoge30sCiAgICAgICJyZWYiOiAiUjM5IiwKICAgICAgInZhbHVlIjogIjQ3ayIKICAgIH0sCiAgICB7CiAgICAgICJwYWdlIjogIk1BSU4iLAogICAgICAicGlucyI6IFsKICAgICAgICAiMSIsCiAgICAgICAgIjIiCiAgICAgIF0sCiAgICAgICJwcm9wZXJ0aWVzIjoge30sCiAgICAgICJyZWYiOiAiUjM0IiwKICAgICAgInZhbHVlIjogIjQuN2siCiAgICB9LAogICAgewogICAgICAicGFnZSI6ICJNQUlOIiwKICAgICAgInBpbnMiOiBbCiAgICAgICAgIjEiLAogICAgICAgICIyIgogICAgICBdLAogICAgICAicHJvcGVydGllcyI6IHt9LAogICAgICAicmVmIjogIkMxIiwKICAgICAgInZhbHVlIjogIjMzcCIKICAgIH0sCiAgICB7CiAgICAgICJwYWdlIjogIk1BSU4iLAogICAgICAicGlucyI6IFsKICAgICAgICAiMSIsCiAgICAgICAgIjIiCiAgICAgIF0sCiAgICAgICJwcm9wZXJ0aWVzIjoge30sCiAgICAgICJyZWYiOiAiQzMiLAogICAgICAidmFsdWUiOiAiMTBwIgogICAgfSwKICAgIHsKICAgICAgInBhZ2UiOiAiTUFJTiIsCiAgICAgICJwaW5zIjogWwogICAgICAgICJCIiwKICAgICAgICAiQyIsCiAgICAgICAgIkUiCiAgICAgIF0sCiAgICAgICJwcm9wZXJ0aWVzIjoge30sCiAgICAgICJyZWYiOiAiUTE2IiwKICAgICAgInZhbHVlIjogIjJOMzkwNCIKICAgIH0sCiAgICB7CiAgICAgICJwYWdlIjogIk1BSU4iLAogICAgICAicGlucyI6IFsKICAgICAgICAiMSIsCiAgICAgICAgIjIiCiAgICAgIF0sCiAgICAgICJwcm9wZXJ0aWVzIjoge30sCiAgICAgICJyZWYiOiAiTDEiLAogICAgICAidmFsdWUiOiAiMTB1IgogICAgfSwKICAgIHsKICAgICAgInBhZ2UiOiAiTUFJTiIsCiAgICAgICJwaW5zIjogWwogICAgICAgICIxIiwKICAgICAgICAiMiIKICAgICAgXSwKICAgICAgInByb3BlcnRpZXMiOiB7fSwKICAgICAgInJlZiI6ICJWMjQiLAogICAgICAidmFsdWUiOiAiVmNjIgogICAgfQogIF0sCiAgImZvcm1hdCI6ICJlbmdpd29ybGQtbmV1dHJhbC1zY2hlbWF0aWMtdjEiLAogICJuYW1lIjogIm9zY2lsbGF0b3JfY29yZSIsCiAgInByb3BlcnRpZXMiOiB7fSwKICAic2NoZW1hdGljcyI6IFsKICAgIHsKICAgICAgImhpZXJfYmxvY2tzIjogW10sCiAgICAgICJuYW1lIjogIm9zY2lsbGF0b3JfY29yZSIsCiAgICAgICJwYWdlcyI6IFsKICAgICAgICAiTUFJTiIKICAgICAgXQogICAgfQogIF0KfQo="
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
