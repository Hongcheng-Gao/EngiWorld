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
  "panel_summary.json": "ewogICJib2FyZF9jb3VudCI6IDEyLAogICJjb2x1bW5fc3BhY2luZ19taWwiOiAxMzM4LjU4MjcsCiAgImNvbHVtbnMiOiAzLAogICJtaXJyb3IiOiB0cnVlLAogICJvcmlnaW5fbW9kZSI6IDEsCiAgInJvdXRlX3Rvb2xfcGF0aCI6IHRydWUsCiAgInJvd19zcGFjaW5nX21pbCI6IDExMzMuODU4MywKICAicm93cyI6IDQsCiAgInNvdXJjZSI6ICJ3aWZpX2JvYXJkLmlwYzI1ODEiCn0K",
  "wifi_panel.ipc2581": "PD94bWwgdmVyc2lvbj0iMS4wIiA/Pgo8SVBDLTI1ODEgdmVyc2lvbj0iQiIgZ2VuZXJhdG9yPSJFbmdpd29ybGROZXV0cmFsIiBuYW1lPSJ3aWZpX2JvYXJkIj4KICA8U3RhY2t1cD4KICAgIDxMYXllciBpbmRleD0iMSIgbmFtZT0iVE9QIiB0eXBlPSJTaWduYWwiIGRpZWxlY3RyaWNfY29uc3RhbnQ9IjQuMiIgY29wcGVyX21pbD0iMS4wIi8+CiAgICA8TGF5ZXIgaW5kZXg9IjIiIG5hbWU9IkdORCIgdHlwZT0iUGxhbmUiIGRpZWxlY3RyaWNfY29uc3RhbnQ9IjQuMiIgY29wcGVyX21pbD0iMS4wIi8+CiAgICA8TGF5ZXIgaW5kZXg9IjMiIG5hbWU9IlBXUiIgdHlwZT0iUGxhbmUiIGRpZWxlY3RyaWNfY29uc3RhbnQ9IjQuMiIgY29wcGVyX21pbD0iMS4wIi8+CiAgICA8TGF5ZXIgaW5kZXg9IjQiIG5hbWU9IkJPVFRPTSIgdHlwZT0iU2lnbmFsIiBkaWVsZWN0cmljX2NvbnN0YW50PSI0LjIiIGNvcHBlcl9taWw9IjEuMCIvPgogIDwvU3RhY2t1cD4KICA8Q29tcG9uZW50cz4KICAgIDxDb21wb25lbnQgcmVmPSJVMSIgeD0iMjUuMCIgeT0iMjUuMCIgc2lkZT0iVE9QIiByb3RhdGlvbj0iMCIgZm9vdHByaW50PSJRRk4zMiIvPgogICAgPENvbXBvbmVudCByZWY9IlIxIiB4PSIxOC4wIiB5PSIzMS4wIiBzaWRlPSJUT1AiIHJvdGF0aW9uPSI5MCIgZm9vdHByaW50PSIwNjAzIi8+CiAgICA8Q29tcG9uZW50IHJlZj0iQzEiIHg9IjMxLjAiIHk9IjMxLjAiIHNpZGU9IlRPUCIgcm90YXRpb249IjkwIiBmb290cHJpbnQ9IjA2MDMiLz4KICAgIDxDb21wb25lbnQgcmVmPSJKMSIgeD0iOC4wIiB5PSIxNS4wIiBzaWRlPSJUT1AiIHJvdGF0aW9uPSIwIiBmb290cHJpbnQ9IkhEUjQiLz4KICAgIDxDb21wb25lbnQgcmVmPSJSOSIgeD0iNDEuMCIgeT0iMTIuMCIgc2lkZT0iVE9QIiByb3RhdGlvbj0iMCIgZm9vdHByaW50PSJSRVNDMDYwMyIvPgogICAgPENvbXBvbmVudCByZWY9IlIxMCIgeD0iNDEuMCIgeT0iMTQuMCIgc2lkZT0iVE9QIiByb3RhdGlvbj0iMCIgZm9vdHByaW50PSJSRVNDMDYwMyIvPgogICAgPENvbXBvbmVudCByZWY9IlIxMSIgeD0iNDEuMCIgeT0iMTYuMCIgc2lkZT0iVE9QIiByb3RhdGlvbj0iMCIgZm9vdHByaW50PSJSRVNDMDYwMyIvPgogIDwvQ29tcG9uZW50cz4KICA8TmV0cz4KICAgIDxOZXQgbmFtZT0iR05EIj4KICAgICAgPFBpblJlZiBuYW1lPSJVMS4xIi8+CiAgICAgIDxQaW5SZWYgbmFtZT0iQzEuMiIvPgogICAgICA8UGluUmVmIG5hbWU9IkoxLjEiLz4KICAgIDwvTmV0PgogICAgPE5ldCBuYW1lPSJWQ0MiPgogICAgICA8UGluUmVmIG5hbWU9IlUxLjIiLz4KICAgICAgPFBpblJlZiBuYW1lPSJDMS4xIi8+CiAgICAgIDxQaW5SZWYgbmFtZT0iSjEuMiIvPgogICAgPC9OZXQ+CiAgICA8TmV0IG5hbWU9IlVTQjJfRF9OIj4KICAgICAgPFBpblJlZiBuYW1lPSJVMS41Ii8+CiAgICAgIDxQaW5SZWYgbmFtZT0iUjkuMSIvPgogICAgPC9OZXQ+CiAgICA8TmV0IG5hbWU9IlVTQjJfRF9QIj4KICAgICAgPFBpblJlZiBuYW1lPSJVMS42Ii8+CiAgICAgIDxQaW5SZWYgbmFtZT0iUjEwLjEiLz4KICAgIDwvTmV0PgogICAgPE5ldCBuYW1lPSJQQTEyX1VTQl9EX04iPgogICAgICA8UGluUmVmIG5hbWU9IlUxLjE1Ii8+CiAgICAgIDxQaW5SZWYgbmFtZT0iUjkuMSIvPgogICAgPC9OZXQ+CiAgICA8TmV0IG5hbWU9IlBBMTJfVVNCX0RfUCI+CiAgICAgIDxQaW5SZWYgbmFtZT0iVTEuMTYiLz4KICAgICAgPFBpblJlZiBuYW1lPSJSMTAuMSIvPgogICAgPC9OZXQ+CiAgPC9OZXRzPgogIDxWaWFzPgogICAgPFZpYSBpZD0iVjEiIG5ldD0iR05EIiB4PSIxNS4wIiB5PSIxNS4wIiBmcm9tPSJUT1AiIHRvPSJCT1RUT00iIHBhZHN0YWNrPSJWSUExMiIvPgogICAgPFZpYSBpZD0iVjIiIG5ldD0iVkNDIiB4PSIzNS4wIiB5PSIxNS4wIiBmcm9tPSJUT1AiIHRvPSJCT1RUT00iIHBhZHN0YWNrPSJWSUExMiIvPgogICAgPFZpYSBpZD0iVjMiIG5ldD0iR05EIiB4PSIxNS4wIiB5PSIzNS4wIiBmcm9tPSJUT1AiIHRvPSJCT1RUT00iIHBhZHN0YWNrPSJWSUExMCIvPgogIDwvVmlhcz4KICA8UGFkc3RhY2tzPgogICAgPFBhZHN0YWNrIG5hbWU9IlZJQTEyIiBob2xlX21pbD0iMTIiIGRpYW1ldGVyX21pbD0iMjgiIGNvdW50PSIyIi8+CiAgICA8UGFkc3RhY2sgbmFtZT0iVklBMTAiIGhvbGVfbWlsPSIxMCIgZGlhbWV0ZXJfbWlsPSIyNCIgY291bnQ9IjEiLz4KICAgIDxQYWRzdGFjayBuYW1lPSJTTUQwNjAzIiBob2xlX21pbD0iMCIgZGlhbWV0ZXJfbWlsPSIzNSIgY291bnQ9IjIiLz4KICA8L1BhZHN0YWNrcz4KICA8RGlmZmVyZW50aWFsUGFpcnM+CiAgICA8RGlmZmVyZW50aWFsUGFpciBuYW1lPSJVU0IyX0QiIG5lZ2F0aXZlPSJVU0IyX0RfTiIgcG9zaXRpdmU9IlVTQjJfRF9QIiBnYXBfbWlsPSI4IiBsZW5ndGhfbl9taWw9Ijk1MCIgbGVuZ3RoX3BfbWlsPSI5NTIiLz4KICAgIDxEaWZmZXJlbnRpYWxQYWlyIG5hbWU9IlBDSUVfVFgwIiBuZWdhdGl2ZT0iUENJRV9UWDBfTiIgcG9zaXRpdmU9IlBDSUVfVFgwX1AiIGdhcF9taWw9IjYiIGxlbmd0aF9uX21pbD0iMTgyMCIgbGVuZ3RoX3BfbWlsPSIxODE2Ii8+CiAgPC9EaWZmZXJlbnRpYWxQYWlycz4KICA8VmlvbGF0aW9ucz4KICAgIDxWaW9sYXRpb24gaWQ9IkRSQzAwMSIgdHlwZT0iY2xlYXJhbmNlIiBvYmplY3Q9IlUxLjUtUjkuMSIgc2V2ZXJpdHk9ImVycm9yIi8+CiAgICA8VmlvbGF0aW9uIGlkPSJEUkMwMDIiIHR5cGU9InNpbGtzY3JlZW4iIG9iamVjdD0iSjEiIHNldmVyaXR5PSJ3YXJuaW5nIi8+CiAgPC9WaW9sYXRpb25zPgo8L0lQQy0yNTgxPgo=",
  "wifi_panel.pcb.json": "ewogICJjb21wb25lbnRzIjogWwogICAgewogICAgICAiZm9vdHByaW50IjogIlFGTjMyIiwKICAgICAgInJlZiI6ICJVMSIsCiAgICAgICJyb3RhdGlvbiI6IDAsCiAgICAgICJzaWRlIjogIlRPUCIsCiAgICAgICJ4IjogMjUuMCwKICAgICAgInkiOiAyNS4wCiAgICB9LAogICAgewogICAgICAiZm9vdHByaW50IjogIjA2MDMiLAogICAgICAicmVmIjogIlIxIiwKICAgICAgInJvdGF0aW9uIjogOTAsCiAgICAgICJzaWRlIjogIlRPUCIsCiAgICAgICJ4IjogMTguMCwKICAgICAgInkiOiAzMS4wCiAgICB9LAogICAgewogICAgICAiZm9vdHByaW50IjogIjA2MDMiLAogICAgICAicmVmIjogIkMxIiwKICAgICAgInJvdGF0aW9uIjogOTAsCiAgICAgICJzaWRlIjogIlRPUCIsCiAgICAgICJ4IjogMzEuMCwKICAgICAgInkiOiAzMS4wCiAgICB9LAogICAgewogICAgICAiZm9vdHByaW50IjogIkhEUjQiLAogICAgICAicmVmIjogIkoxIiwKICAgICAgInJvdGF0aW9uIjogMCwKICAgICAgInNpZGUiOiAiVE9QIiwKICAgICAgIngiOiA4LjAsCiAgICAgICJ5IjogMTUuMAogICAgfSwKICAgIHsKICAgICAgImZvb3RwcmludCI6ICJSRVNDMDYwMyIsCiAgICAgICJyZWYiOiAiUjkiLAogICAgICAicm90YXRpb24iOiAwLAogICAgICAic2lkZSI6ICJUT1AiLAogICAgICAieCI6IDQxLjAsCiAgICAgICJ5IjogMTIuMAogICAgfSwKICAgIHsKICAgICAgImZvb3RwcmludCI6ICJSRVNDMDYwMyIsCiAgICAgICJyZWYiOiAiUjEwIiwKICAgICAgInJvdGF0aW9uIjogMCwKICAgICAgInNpZGUiOiAiVE9QIiwKICAgICAgIngiOiA0MS4wLAogICAgICAieSI6IDE0LjAKICAgIH0sCiAgICB7CiAgICAgICJmb290cHJpbnQiOiAiUkVTQzA2MDMiLAogICAgICAicmVmIjogIlIxMSIsCiAgICAgICJyb3RhdGlvbiI6IDAsCiAgICAgICJzaWRlIjogIlRPUCIsCiAgICAgICJ4IjogNDEuMCwKICAgICAgInkiOiAxNi4wCiAgICB9CiAgXSwKICAiZGlmZnBhaXJzIjogWwogICAgewogICAgICAiZ2FwX21pbCI6IDgsCiAgICAgICJsZW5ndGhfbl9taWwiOiA5NTAsCiAgICAgICJsZW5ndGhfcF9taWwiOiA5NTIsCiAgICAgICJuYW1lIjogIlVTQjJfRCIsCiAgICAgICJuZWdhdGl2ZSI6ICJVU0IyX0RfTiIsCiAgICAgICJwb3NpdGl2ZSI6ICJVU0IyX0RfUCIKICAgIH0sCiAgICB7CiAgICAgICJnYXBfbWlsIjogNiwKICAgICAgImxlbmd0aF9uX21pbCI6IDE4MjAsCiAgICAgICJsZW5ndGhfcF9taWwiOiAxODE2LAogICAgICAibmFtZSI6ICJQQ0lFX1RYMCIsCiAgICAgICJuZWdhdGl2ZSI6ICJQQ0lFX1RYMF9OIiwKICAgICAgInBvc2l0aXZlIjogIlBDSUVfVFgwX1AiCiAgICB9CiAgXSwKICAiZm9ybWF0IjogImVuZ2l3b3JsZC1uZXV0cmFsLXBjYi12MSIsCiAgImxheWVycyI6IFsKICAgIHsKICAgICAgImNvcHBlcl9taWwiOiAxLjAsCiAgICAgICJkaWVsZWN0cmljX2NvbnN0YW50IjogNC4yLAogICAgICAiaW5kZXgiOiAxLAogICAgICAibmFtZSI6ICJUT1AiLAogICAgICAidHlwZSI6ICJTaWduYWwiCiAgICB9LAogICAgewogICAgICAiY29wcGVyX21pbCI6IDEuMCwKICAgICAgImRpZWxlY3RyaWNfY29uc3RhbnQiOiA0LjIsCiAgICAgICJpbmRleCI6IDIsCiAgICAgICJuYW1lIjogIkdORCIsCiAgICAgICJ0eXBlIjogIlBsYW5lIgogICAgfSwKICAgIHsKICAgICAgImNvcHBlcl9taWwiOiAxLjAsCiAgICAgICJkaWVsZWN0cmljX2NvbnN0YW50IjogNC4yLAogICAgICAiaW5kZXgiOiAzLAogICAgICAibmFtZSI6ICJQV1IiLAogICAgICAidHlwZSI6ICJQbGFuZSIKICAgIH0sCiAgICB7CiAgICAgICJjb3BwZXJfbWlsIjogMS4wLAogICAgICAiZGllbGVjdHJpY19jb25zdGFudCI6IDQuMiwKICAgICAgImluZGV4IjogNCwKICAgICAgIm5hbWUiOiAiQk9UVE9NIiwKICAgICAgInR5cGUiOiAiU2lnbmFsIgogICAgfQogIF0sCiAgIm5hbWUiOiAid2lmaV9ib2FyZCIsCiAgIm5ldHMiOiBbCiAgICB7CiAgICAgICJuYW1lIjogIkdORCIsCiAgICAgICJwaW5zIjogWwogICAgICAgICJVMS4xIiwKICAgICAgICAiQzEuMiIsCiAgICAgICAgIkoxLjEiCiAgICAgIF0KICAgIH0sCiAgICB7CiAgICAgICJuYW1lIjogIlZDQyIsCiAgICAgICJwaW5zIjogWwogICAgICAgICJVMS4yIiwKICAgICAgICAiQzEuMSIsCiAgICAgICAgIkoxLjIiCiAgICAgIF0KICAgIH0sCiAgICB7CiAgICAgICJuYW1lIjogIlVTQjJfRF9OIiwKICAgICAgInBpbnMiOiBbCiAgICAgICAgIlUxLjUiLAogICAgICAgICJSOS4xIgogICAgICBdCiAgICB9LAogICAgewogICAgICAibmFtZSI6ICJVU0IyX0RfUCIsCiAgICAgICJwaW5zIjogWwogICAgICAgICJVMS42IiwKICAgICAgICAiUjEwLjEiCiAgICAgIF0KICAgIH0sCiAgICB7CiAgICAgICJuYW1lIjogIlBBMTJfVVNCX0RfTiIsCiAgICAgICJwaW5zIjogWwogICAgICAgICJVMS4xNSIsCiAgICAgICAgIlI5LjEiCiAgICAgIF0KICAgIH0sCiAgICB7CiAgICAgICJuYW1lIjogIlBBMTJfVVNCX0RfUCIsCiAgICAgICJwaW5zIjogWwogICAgICAgICJVMS4xNiIsCiAgICAgICAgIlIxMC4xIgogICAgICBdCiAgICB9CiAgXSwKICAicGFkc3RhY2tzIjogWwogICAgewogICAgICAiY291bnQiOiAyLAogICAgICAiZGlhbWV0ZXJfbWlsIjogMjgsCiAgICAgICJob2xlX21pbCI6IDEyLAogICAgICAibmFtZSI6ICJWSUExMiIKICAgIH0sCiAgICB7CiAgICAgICJjb3VudCI6IDEsCiAgICAgICJkaWFtZXRlcl9taWwiOiAyNCwKICAgICAgImhvbGVfbWlsIjogMTAsCiAgICAgICJuYW1lIjogIlZJQTEwIgogICAgfSwKICAgIHsKICAgICAgImNvdW50IjogMiwKICAgICAgImRpYW1ldGVyX21pbCI6IDM1LAogICAgICAiaG9sZV9taWwiOiAwLAogICAgICAibmFtZSI6ICJTTUQwNjAzIgogICAgfQogIF0sCiAgInBhbmVsIjogewogICAgImNvbHVtbl9zcGFjaW5nX21pbCI6IDEzMzguNTgyNywKICAgICJjb2x1bW5zIjogMywKICAgICJtaXJyb3IiOiB0cnVlLAogICAgIm9yaWdpbl9tb2RlIjogMSwKICAgICJyb3dfc3BhY2luZ19taWwiOiAxMTMzLjg1ODMsCiAgICAicm93cyI6IDQKICB9LAogICJ2aWFzIjogWwogICAgewogICAgICAiZnJvbSI6ICJUT1AiLAogICAgICAiaWQiOiAiVjEiLAogICAgICAibmV0IjogIkdORCIsCiAgICAgICJwYWRzdGFjayI6ICJWSUExMiIsCiAgICAgICJ0byI6ICJCT1RUT00iLAogICAgICAieCI6IDE1LjAsCiAgICAgICJ5IjogMTUuMAogICAgfSwKICAgIHsKICAgICAgImZyb20iOiAiVE9QIiwKICAgICAgImlkIjogIlYyIiwKICAgICAgIm5ldCI6ICJWQ0MiLAogICAgICAicGFkc3RhY2siOiAiVklBMTIiLAogICAgICAidG8iOiAiQk9UVE9NIiwKICAgICAgIngiOiAzNS4wLAogICAgICAieSI6IDE1LjAKICAgIH0sCiAgICB7CiAgICAgICJmcm9tIjogIlRPUCIsCiAgICAgICJpZCI6ICJWMyIsCiAgICAgICJuZXQiOiAiR05EIiwKICAgICAgInBhZHN0YWNrIjogIlZJQTEwIiwKICAgICAgInRvIjogIkJPVFRPTSIsCiAgICAgICJ4IjogMTUuMCwKICAgICAgInkiOiAzNS4wCiAgICB9CiAgXSwKICAidmlvbGF0aW9ucyI6IFsKICAgIHsKICAgICAgImlkIjogIkRSQzAwMSIsCiAgICAgICJvYmplY3QiOiAiVTEuNS1SOS4xIiwKICAgICAgInNldmVyaXR5IjogImVycm9yIiwKICAgICAgInR5cGUiOiAiY2xlYXJhbmNlIgogICAgfSwKICAgIHsKICAgICAgImlkIjogIkRSQzAwMiIsCiAgICAgICJvYmplY3QiOiAiSjEiLAogICAgICAic2V2ZXJpdHkiOiAid2FybmluZyIsCiAgICAgICJ0eXBlIjogInNpbGtzY3JlZW4iCiAgICB9CiAgXQp9Cg=="
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
