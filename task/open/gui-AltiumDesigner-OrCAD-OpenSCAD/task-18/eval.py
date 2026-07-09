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
  "constraints.json": "ewogICJEaWZmUGFpcnNSb3V0aW5nIjogewogICAgImdhcF9taWwiOiA4LAogICAgInNjb3BlIjogIkluRGlmZmVyZW50aWFsUGFpcignVVNCMl9EJykiLAogICAgIndpZHRoX21pbCI6IDYKICB9Cn0K",
  "eco_report.json": "ewogICJSMTBfZm9vdHByaW50IjogIlJFU0MxMDA1WDQwWDI1TkwwNVQwNSIsCiAgIlI5X2Zvb3RwcmludCI6ICJSRVNDMTAwNVg0MFgyNU5MMDVUMDUiLAogICJkaWZmcGFpcl9zY29wZSI6ICJVU0IyX0QiLAogICJyZW5hbWVfbmV0cyI6IHsKICAgICJQQTEyX1VTQl9EX04iOiAiVVNCMl9EX04iLAogICAgIlBBMTJfVVNCX0RfUCI6ICJVU0IyX0RfUCIKICB9Cn0K",
  "wifi_usb_eco.ipc2581": "PD94bWwgdmVyc2lvbj0iMS4wIiA/Pgo8SVBDLTI1ODEgdmVyc2lvbj0iQiIgZ2VuZXJhdG9yPSJFbmdpd29ybGROZXV0cmFsIiBuYW1lPSJ3aWZpX2JvYXJkIj4KICA8U3RhY2t1cD4KICAgIDxMYXllciBpbmRleD0iMSIgbmFtZT0iVE9QIiB0eXBlPSJTaWduYWwiIGRpZWxlY3RyaWNfY29uc3RhbnQ9IjQuMiIgY29wcGVyX21pbD0iMS4wIi8+CiAgICA8TGF5ZXIgaW5kZXg9IjIiIG5hbWU9IkdORCIgdHlwZT0iUGxhbmUiIGRpZWxlY3RyaWNfY29uc3RhbnQ9IjQuMiIgY29wcGVyX21pbD0iMS4wIi8+CiAgICA8TGF5ZXIgaW5kZXg9IjMiIG5hbWU9IlBXUiIgdHlwZT0iUGxhbmUiIGRpZWxlY3RyaWNfY29uc3RhbnQ9IjQuMiIgY29wcGVyX21pbD0iMS4wIi8+CiAgICA8TGF5ZXIgaW5kZXg9IjQiIG5hbWU9IkJPVFRPTSIgdHlwZT0iU2lnbmFsIiBkaWVsZWN0cmljX2NvbnN0YW50PSI0LjIiIGNvcHBlcl9taWw9IjEuMCIvPgogIDwvU3RhY2t1cD4KICA8Q29tcG9uZW50cz4KICAgIDxDb21wb25lbnQgcmVmPSJVMSIgeD0iMjUuMCIgeT0iMjUuMCIgc2lkZT0iVE9QIiByb3RhdGlvbj0iMCIgZm9vdHByaW50PSJRRk4zMiIvPgogICAgPENvbXBvbmVudCByZWY9IlIxIiB4PSIxOC4wIiB5PSIzMS4wIiBzaWRlPSJUT1AiIHJvdGF0aW9uPSI5MCIgZm9vdHByaW50PSIwNjAzIi8+CiAgICA8Q29tcG9uZW50IHJlZj0iQzEiIHg9IjMxLjAiIHk9IjMxLjAiIHNpZGU9IlRPUCIgcm90YXRpb249IjkwIiBmb290cHJpbnQ9IjA2MDMiLz4KICAgIDxDb21wb25lbnQgcmVmPSJKMSIgeD0iOC4wIiB5PSIxNS4wIiBzaWRlPSJUT1AiIHJvdGF0aW9uPSIwIiBmb290cHJpbnQ9IkhEUjQiLz4KICAgIDxDb21wb25lbnQgcmVmPSJSOSIgeD0iNDEuMCIgeT0iMTIuMCIgc2lkZT0iVE9QIiByb3RhdGlvbj0iMCIgZm9vdHByaW50PSJSRVNDMTAwNVg0MFgyNU5MMDVUMDUiLz4KICAgIDxDb21wb25lbnQgcmVmPSJSMTAiIHg9IjQxLjAiIHk9IjE0LjAiIHNpZGU9IlRPUCIgcm90YXRpb249IjAiIGZvb3RwcmludD0iUkVTQzEwMDVYNDBYMjVOTDA1VDA1Ii8+CiAgICA8Q29tcG9uZW50IHJlZj0iUjExIiB4PSI0MS4wIiB5PSIxNi4wIiBzaWRlPSJUT1AiIHJvdGF0aW9uPSIwIiBmb290cHJpbnQ9IlJFU0MwNjAzIi8+CiAgPC9Db21wb25lbnRzPgogIDxOZXRzPgogICAgPE5ldCBuYW1lPSJHTkQiPgogICAgICA8UGluUmVmIG5hbWU9IlUxLjEiLz4KICAgICAgPFBpblJlZiBuYW1lPSJDMS4yIi8+CiAgICAgIDxQaW5SZWYgbmFtZT0iSjEuMSIvPgogICAgPC9OZXQ+CiAgICA8TmV0IG5hbWU9IlZDQyI+CiAgICAgIDxQaW5SZWYgbmFtZT0iVTEuMiIvPgogICAgICA8UGluUmVmIG5hbWU9IkMxLjEiLz4KICAgICAgPFBpblJlZiBuYW1lPSJKMS4yIi8+CiAgICA8L05ldD4KICAgIDxOZXQgbmFtZT0iVVNCMl9EX04iPgogICAgICA8UGluUmVmIG5hbWU9IlUxLjUiLz4KICAgICAgPFBpblJlZiBuYW1lPSJSOS4xIi8+CiAgICA8L05ldD4KICAgIDxOZXQgbmFtZT0iVVNCMl9EX1AiPgogICAgICA8UGluUmVmIG5hbWU9IlUxLjYiLz4KICAgICAgPFBpblJlZiBuYW1lPSJSMTAuMSIvPgogICAgPC9OZXQ+CiAgICA8TmV0IG5hbWU9IlVTQjJfRF9OIj4KICAgICAgPFBpblJlZiBuYW1lPSJVMS4xNSIvPgogICAgICA8UGluUmVmIG5hbWU9IlI5LjEiLz4KICAgIDwvTmV0PgogICAgPE5ldCBuYW1lPSJVU0IyX0RfUCI+CiAgICAgIDxQaW5SZWYgbmFtZT0iVTEuMTYiLz4KICAgICAgPFBpblJlZiBuYW1lPSJSMTAuMSIvPgogICAgPC9OZXQ+CiAgPC9OZXRzPgogIDxWaWFzPgogICAgPFZpYSBpZD0iVjEiIG5ldD0iR05EIiB4PSIxNS4wIiB5PSIxNS4wIiBmcm9tPSJUT1AiIHRvPSJCT1RUT00iIHBhZHN0YWNrPSJWSUExMiIvPgogICAgPFZpYSBpZD0iVjIiIG5ldD0iVkNDIiB4PSIzNS4wIiB5PSIxNS4wIiBmcm9tPSJUT1AiIHRvPSJCT1RUT00iIHBhZHN0YWNrPSJWSUExMiIvPgogICAgPFZpYSBpZD0iVjMiIG5ldD0iR05EIiB4PSIxNS4wIiB5PSIzNS4wIiBmcm9tPSJUT1AiIHRvPSJCT1RUT00iIHBhZHN0YWNrPSJWSUExMCIvPgogIDwvVmlhcz4KICA8UGFkc3RhY2tzPgogICAgPFBhZHN0YWNrIG5hbWU9IlZJQTEyIiBob2xlX21pbD0iMTIiIGRpYW1ldGVyX21pbD0iMjgiIGNvdW50PSIyIi8+CiAgICA8UGFkc3RhY2sgbmFtZT0iVklBMTAiIGhvbGVfbWlsPSIxMCIgZGlhbWV0ZXJfbWlsPSIyNCIgY291bnQ9IjEiLz4KICAgIDxQYWRzdGFjayBuYW1lPSJTTUQwNjAzIiBob2xlX21pbD0iMCIgZGlhbWV0ZXJfbWlsPSIzNSIgY291bnQ9IjIiLz4KICA8L1BhZHN0YWNrcz4KICA8RGlmZmVyZW50aWFsUGFpcnM+CiAgICA8RGlmZmVyZW50aWFsUGFpciBuYW1lPSJVU0IyX0QiIG5lZ2F0aXZlPSJVU0IyX0RfTiIgcG9zaXRpdmU9IlVTQjJfRF9QIiBnYXBfbWlsPSI4IiBsZW5ndGhfbl9taWw9Ijk1MCIgbGVuZ3RoX3BfbWlsPSI5NTIiLz4KICAgIDxEaWZmZXJlbnRpYWxQYWlyIG5hbWU9IlBDSUVfVFgwIiBuZWdhdGl2ZT0iUENJRV9UWDBfTiIgcG9zaXRpdmU9IlBDSUVfVFgwX1AiIGdhcF9taWw9IjYiIGxlbmd0aF9uX21pbD0iMTgyMCIgbGVuZ3RoX3BfbWlsPSIxODE2Ii8+CiAgPC9EaWZmZXJlbnRpYWxQYWlycz4KICA8VmlvbGF0aW9ucz4KICAgIDxWaW9sYXRpb24gaWQ9IkRSQzAwMSIgdHlwZT0iY2xlYXJhbmNlIiBvYmplY3Q9IlUxLjUtUjkuMSIgc2V2ZXJpdHk9ImVycm9yIi8+CiAgICA8VmlvbGF0aW9uIGlkPSJEUkMwMDIiIHR5cGU9InNpbGtzY3JlZW4iIG9iamVjdD0iSjEiIHNldmVyaXR5PSJ3YXJuaW5nIi8+CiAgPC9WaW9sYXRpb25zPgo8L0lQQy0yNTgxPgo=",
  "wifi_usb_eco.pcb.json": "ewogICJjb21wb25lbnRzIjogWwogICAgewogICAgICAiZm9vdHByaW50IjogIlFGTjMyIiwKICAgICAgInJlZiI6ICJVMSIsCiAgICAgICJyb3RhdGlvbiI6IDAsCiAgICAgICJzaWRlIjogIlRPUCIsCiAgICAgICJ4IjogMjUuMCwKICAgICAgInkiOiAyNS4wCiAgICB9LAogICAgewogICAgICAiZm9vdHByaW50IjogIjA2MDMiLAogICAgICAicmVmIjogIlIxIiwKICAgICAgInJvdGF0aW9uIjogOTAsCiAgICAgICJzaWRlIjogIlRPUCIsCiAgICAgICJ4IjogMTguMCwKICAgICAgInkiOiAzMS4wCiAgICB9LAogICAgewogICAgICAiZm9vdHByaW50IjogIjA2MDMiLAogICAgICAicmVmIjogIkMxIiwKICAgICAgInJvdGF0aW9uIjogOTAsCiAgICAgICJzaWRlIjogIlRPUCIsCiAgICAgICJ4IjogMzEuMCwKICAgICAgInkiOiAzMS4wCiAgICB9LAogICAgewogICAgICAiZm9vdHByaW50IjogIkhEUjQiLAogICAgICAicmVmIjogIkoxIiwKICAgICAgInJvdGF0aW9uIjogMCwKICAgICAgInNpZGUiOiAiVE9QIiwKICAgICAgIngiOiA4LjAsCiAgICAgICJ5IjogMTUuMAogICAgfSwKICAgIHsKICAgICAgImZvb3RwcmludCI6ICJSRVNDMTAwNVg0MFgyNU5MMDVUMDUiLAogICAgICAicmVmIjogIlI5IiwKICAgICAgInJvdGF0aW9uIjogMCwKICAgICAgInNpZGUiOiAiVE9QIiwKICAgICAgIngiOiA0MS4wLAogICAgICAieSI6IDEyLjAKICAgIH0sCiAgICB7CiAgICAgICJmb290cHJpbnQiOiAiUkVTQzEwMDVYNDBYMjVOTDA1VDA1IiwKICAgICAgInJlZiI6ICJSMTAiLAogICAgICAicm90YXRpb24iOiAwLAogICAgICAic2lkZSI6ICJUT1AiLAogICAgICAieCI6IDQxLjAsCiAgICAgICJ5IjogMTQuMAogICAgfSwKICAgIHsKICAgICAgImZvb3RwcmludCI6ICJSRVNDMDYwMyIsCiAgICAgICJyZWYiOiAiUjExIiwKICAgICAgInJvdGF0aW9uIjogMCwKICAgICAgInNpZGUiOiAiVE9QIiwKICAgICAgIngiOiA0MS4wLAogICAgICAieSI6IDE2LjAKICAgIH0KICBdLAogICJkaWZmcGFpcnMiOiBbCiAgICB7CiAgICAgICJnYXBfbWlsIjogOCwKICAgICAgImxlbmd0aF9uX21pbCI6IDk1MCwKICAgICAgImxlbmd0aF9wX21pbCI6IDk1MiwKICAgICAgIm5hbWUiOiAiVVNCMl9EIiwKICAgICAgIm5lZ2F0aXZlIjogIlVTQjJfRF9OIiwKICAgICAgInBvc2l0aXZlIjogIlVTQjJfRF9QIgogICAgfSwKICAgIHsKICAgICAgImdhcF9taWwiOiA2LAogICAgICAibGVuZ3RoX25fbWlsIjogMTgyMCwKICAgICAgImxlbmd0aF9wX21pbCI6IDE4MTYsCiAgICAgICJuYW1lIjogIlBDSUVfVFgwIiwKICAgICAgIm5lZ2F0aXZlIjogIlBDSUVfVFgwX04iLAogICAgICAicG9zaXRpdmUiOiAiUENJRV9UWDBfUCIKICAgIH0KICBdLAogICJmb3JtYXQiOiAiZW5naXdvcmxkLW5ldXRyYWwtcGNiLXYxIiwKICAibGF5ZXJzIjogWwogICAgewogICAgICAiY29wcGVyX21pbCI6IDEuMCwKICAgICAgImRpZWxlY3RyaWNfY29uc3RhbnQiOiA0LjIsCiAgICAgICJpbmRleCI6IDEsCiAgICAgICJuYW1lIjogIlRPUCIsCiAgICAgICJ0eXBlIjogIlNpZ25hbCIKICAgIH0sCiAgICB7CiAgICAgICJjb3BwZXJfbWlsIjogMS4wLAogICAgICAiZGllbGVjdHJpY19jb25zdGFudCI6IDQuMiwKICAgICAgImluZGV4IjogMiwKICAgICAgIm5hbWUiOiAiR05EIiwKICAgICAgInR5cGUiOiAiUGxhbmUiCiAgICB9LAogICAgewogICAgICAiY29wcGVyX21pbCI6IDEuMCwKICAgICAgImRpZWxlY3RyaWNfY29uc3RhbnQiOiA0LjIsCiAgICAgICJpbmRleCI6IDMsCiAgICAgICJuYW1lIjogIlBXUiIsCiAgICAgICJ0eXBlIjogIlBsYW5lIgogICAgfSwKICAgIHsKICAgICAgImNvcHBlcl9taWwiOiAxLjAsCiAgICAgICJkaWVsZWN0cmljX2NvbnN0YW50IjogNC4yLAogICAgICAiaW5kZXgiOiA0LAogICAgICAibmFtZSI6ICJCT1RUT00iLAogICAgICAidHlwZSI6ICJTaWduYWwiCiAgICB9CiAgXSwKICAibmFtZSI6ICJ3aWZpX2JvYXJkIiwKICAibmV0cyI6IFsKICAgIHsKICAgICAgIm5hbWUiOiAiR05EIiwKICAgICAgInBpbnMiOiBbCiAgICAgICAgIlUxLjEiLAogICAgICAgICJDMS4yIiwKICAgICAgICAiSjEuMSIKICAgICAgXQogICAgfSwKICAgIHsKICAgICAgIm5hbWUiOiAiVkNDIiwKICAgICAgInBpbnMiOiBbCiAgICAgICAgIlUxLjIiLAogICAgICAgICJDMS4xIiwKICAgICAgICAiSjEuMiIKICAgICAgXQogICAgfSwKICAgIHsKICAgICAgIm5hbWUiOiAiVVNCMl9EX04iLAogICAgICAicGlucyI6IFsKICAgICAgICAiVTEuNSIsCiAgICAgICAgIlI5LjEiCiAgICAgIF0KICAgIH0sCiAgICB7CiAgICAgICJuYW1lIjogIlVTQjJfRF9QIiwKICAgICAgInBpbnMiOiBbCiAgICAgICAgIlUxLjYiLAogICAgICAgICJSMTAuMSIKICAgICAgXQogICAgfSwKICAgIHsKICAgICAgIm5hbWUiOiAiVVNCMl9EX04iLAogICAgICAicGlucyI6IFsKICAgICAgICAiVTEuMTUiLAogICAgICAgICJSOS4xIgogICAgICBdCiAgICB9LAogICAgewogICAgICAibmFtZSI6ICJVU0IyX0RfUCIsCiAgICAgICJwaW5zIjogWwogICAgICAgICJVMS4xNiIsCiAgICAgICAgIlIxMC4xIgogICAgICBdCiAgICB9CiAgXSwKICAicGFkc3RhY2tzIjogWwogICAgewogICAgICAiY291bnQiOiAyLAogICAgICAiZGlhbWV0ZXJfbWlsIjogMjgsCiAgICAgICJob2xlX21pbCI6IDEyLAogICAgICAibmFtZSI6ICJWSUExMiIKICAgIH0sCiAgICB7CiAgICAgICJjb3VudCI6IDEsCiAgICAgICJkaWFtZXRlcl9taWwiOiAyNCwKICAgICAgImhvbGVfbWlsIjogMTAsCiAgICAgICJuYW1lIjogIlZJQTEwIgogICAgfSwKICAgIHsKICAgICAgImNvdW50IjogMiwKICAgICAgImRpYW1ldGVyX21pbCI6IDM1LAogICAgICAiaG9sZV9taWwiOiAwLAogICAgICAibmFtZSI6ICJTTUQwNjAzIgogICAgfQogIF0sCiAgInZpYXMiOiBbCiAgICB7CiAgICAgICJmcm9tIjogIlRPUCIsCiAgICAgICJpZCI6ICJWMSIsCiAgICAgICJuZXQiOiAiR05EIiwKICAgICAgInBhZHN0YWNrIjogIlZJQTEyIiwKICAgICAgInRvIjogIkJPVFRPTSIsCiAgICAgICJ4IjogMTUuMCwKICAgICAgInkiOiAxNS4wCiAgICB9LAogICAgewogICAgICAiZnJvbSI6ICJUT1AiLAogICAgICAiaWQiOiAiVjIiLAogICAgICAibmV0IjogIlZDQyIsCiAgICAgICJwYWRzdGFjayI6ICJWSUExMiIsCiAgICAgICJ0byI6ICJCT1RUT00iLAogICAgICAieCI6IDM1LjAsCiAgICAgICJ5IjogMTUuMAogICAgfSwKICAgIHsKICAgICAgImZyb20iOiAiVE9QIiwKICAgICAgImlkIjogIlYzIiwKICAgICAgIm5ldCI6ICJHTkQiLAogICAgICAicGFkc3RhY2siOiAiVklBMTAiLAogICAgICAidG8iOiAiQk9UVE9NIiwKICAgICAgIngiOiAxNS4wLAogICAgICAieSI6IDM1LjAKICAgIH0KICBdLAogICJ2aW9sYXRpb25zIjogWwogICAgewogICAgICAiaWQiOiAiRFJDMDAxIiwKICAgICAgIm9iamVjdCI6ICJVMS41LVI5LjEiLAogICAgICAic2V2ZXJpdHkiOiAiZXJyb3IiLAogICAgICAidHlwZSI6ICJjbGVhcmFuY2UiCiAgICB9LAogICAgewogICAgICAiaWQiOiAiRFJDMDAyIiwKICAgICAgIm9iamVjdCI6ICJKMSIsCiAgICAgICJzZXZlcml0eSI6ICJ3YXJuaW5nIiwKICAgICAgInR5cGUiOiAic2lsa3NjcmVlbiIKICAgIH0KICBdCn0K"
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
