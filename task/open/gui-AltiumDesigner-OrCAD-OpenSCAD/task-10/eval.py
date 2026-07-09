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
  "fulladd_placed.ipc2581": "PD94bWwgdmVyc2lvbj0iMS4wIiA/Pgo8SVBDLTI1ODEgdmVyc2lvbj0iQiIgZ2VuZXJhdG9yPSJFbmdpd29ybGROZXV0cmFsIiBuYW1lPSJmdWxsYWRkX2JvYXJkIj4KICA8U3RhY2t1cD4KICAgIDxMYXllciBpbmRleD0iMSIgbmFtZT0iVE9QIiB0eXBlPSJTaWduYWwiIGRpZWxlY3RyaWNfY29uc3RhbnQ9IjQuMiIgY29wcGVyX21pbD0iMS4wIi8+CiAgICA8TGF5ZXIgaW5kZXg9IjIiIG5hbWU9IkdORCIgdHlwZT0iUGxhbmUiIGRpZWxlY3RyaWNfY29uc3RhbnQ9IjQuMiIgY29wcGVyX21pbD0iMS4wIi8+CiAgICA8TGF5ZXIgaW5kZXg9IjMiIG5hbWU9IlBXUiIgdHlwZT0iUGxhbmUiIGRpZWxlY3RyaWNfY29uc3RhbnQ9IjQuMiIgY29wcGVyX21pbD0iMS4wIi8+CiAgICA8TGF5ZXIgaW5kZXg9IjQiIG5hbWU9IkJPVFRPTSIgdHlwZT0iU2lnbmFsIiBkaWVsZWN0cmljX2NvbnN0YW50PSI0LjIiIGNvcHBlcl9taWw9IjEuMCIvPgogIDwvU3RhY2t1cD4KICA8Q29tcG9uZW50cz4KICAgIDxDb21wb25lbnQgcmVmPSJVMSIgeD0iMjAuMCIgeT0iMjAuMCIgc2lkZT0iVE9QIiByb3RhdGlvbj0iMCIgZm9vdHByaW50PSJRRk4zMiIgcGxhY2VkPSJ0cnVlIi8+CiAgICA8Q29tcG9uZW50IHJlZj0iUjEiIHg9IjEyLjAiIHk9IjI4LjAiIHNpZGU9IlRPUCIgcm90YXRpb249IjkwIiBmb290cHJpbnQ9IjA2MDMiIHBsYWNlZD0idHJ1ZSIvPgogICAgPENvbXBvbmVudCByZWY9IkMxIiB4PSIyOC4wIiB5PSIyOC4wIiBzaWRlPSJUT1AiIHJvdGF0aW9uPSI5MCIgZm9vdHByaW50PSIwNjAzIiBwbGFjZWQ9InRydWUiLz4KICAgIDxDb21wb25lbnQgcmVmPSJKMSIgeD0iNS4wIiB5PSIxMC4wIiBzaWRlPSJUT1AiIHJvdGF0aW9uPSIwIiBmb290cHJpbnQ9IkhEUjQiIHBsYWNlZD0idHJ1ZSIvPgogIDwvQ29tcG9uZW50cz4KICA8TmV0cz4KICAgIDxOZXQgbmFtZT0iR05EIj4KICAgICAgPFBpblJlZiBuYW1lPSJVMS4xIi8+CiAgICAgIDxQaW5SZWYgbmFtZT0iQzEuMiIvPgogICAgICA8UGluUmVmIG5hbWU9IkoxLjEiLz4KICAgIDwvTmV0PgogICAgPE5ldCBuYW1lPSJWQ0MiPgogICAgICA8UGluUmVmIG5hbWU9IlUxLjIiLz4KICAgICAgPFBpblJlZiBuYW1lPSJDMS4xIi8+CiAgICAgIDxQaW5SZWYgbmFtZT0iSjEuMiIvPgogICAgPC9OZXQ+CiAgICA8TmV0IG5hbWU9IlVTQjJfRF9OIj4KICAgICAgPFBpblJlZiBuYW1lPSJVMS41Ii8+CiAgICAgIDxQaW5SZWYgbmFtZT0iUjkuMSIvPgogICAgPC9OZXQ+CiAgICA8TmV0IG5hbWU9IlVTQjJfRF9QIj4KICAgICAgPFBpblJlZiBuYW1lPSJVMS42Ii8+CiAgICAgIDxQaW5SZWYgbmFtZT0iUjEwLjEiLz4KICAgIDwvTmV0PgogIDwvTmV0cz4KICA8Vmlhcz4KICAgIDxWaWEgaWQ9IlYxIiBuZXQ9IkdORCIgeD0iMTUuMCIgeT0iMTUuMCIgZnJvbT0iVE9QIiB0bz0iQk9UVE9NIiBwYWRzdGFjaz0iVklBMTIiLz4KICAgIDxWaWEgaWQ9IlYyIiBuZXQ9IlZDQyIgeD0iMzUuMCIgeT0iMTUuMCIgZnJvbT0iVE9QIiB0bz0iQk9UVE9NIiBwYWRzdGFjaz0iVklBMTIiLz4KICAgIDxWaWEgaWQ9IlYzIiBuZXQ9IkdORCIgeD0iMTUuMCIgeT0iMzUuMCIgZnJvbT0iVE9QIiB0bz0iQk9UVE9NIiBwYWRzdGFjaz0iVklBMTAiLz4KICA8L1ZpYXM+CiAgPFBhZHN0YWNrcz4KICAgIDxQYWRzdGFjayBuYW1lPSJWSUExMiIgaG9sZV9taWw9IjEyIiBkaWFtZXRlcl9taWw9IjI4IiBjb3VudD0iMiIvPgogICAgPFBhZHN0YWNrIG5hbWU9IlZJQTEwIiBob2xlX21pbD0iMTAiIGRpYW1ldGVyX21pbD0iMjQiIGNvdW50PSIxIi8+CiAgICA8UGFkc3RhY2sgbmFtZT0iU01EMDYwMyIgaG9sZV9taWw9IjAiIGRpYW1ldGVyX21pbD0iMzUiIGNvdW50PSIyIi8+CiAgPC9QYWRzdGFja3M+CiAgPERpZmZlcmVudGlhbFBhaXJzPgogICAgPERpZmZlcmVudGlhbFBhaXIgbmFtZT0iVVNCMl9EIiBuZWdhdGl2ZT0iVVNCMl9EX04iIHBvc2l0aXZlPSJVU0IyX0RfUCIgZ2FwX21pbD0iOCIgbGVuZ3RoX25fbWlsPSI5NTAiIGxlbmd0aF9wX21pbD0iOTUyIi8+CiAgICA8RGlmZmVyZW50aWFsUGFpciBuYW1lPSJQQ0lFX1RYMCIgbmVnYXRpdmU9IlBDSUVfVFgwX04iIHBvc2l0aXZlPSJQQ0lFX1RYMF9QIiBnYXBfbWlsPSI2IiBsZW5ndGhfbl9taWw9IjE4MjAiIGxlbmd0aF9wX21pbD0iMTgxNiIvPgogIDwvRGlmZmVyZW50aWFsUGFpcnM+CiAgPFZpb2xhdGlvbnM+CiAgICA8VmlvbGF0aW9uIGlkPSJEUkMwMDEiIHR5cGU9ImNsZWFyYW5jZSIgb2JqZWN0PSJVMS41LVI5LjEiIHNldmVyaXR5PSJlcnJvciIvPgogICAgPFZpb2xhdGlvbiBpZD0iRFJDMDAyIiB0eXBlPSJzaWxrc2NyZWVuIiBvYmplY3Q9IkoxIiBzZXZlcml0eT0id2FybmluZyIvPgogIDwvVmlvbGF0aW9ucz4KPC9JUEMtMjU4MT4K",
  "fulladd_placed.pcb.json": "ewogICJjb21wb25lbnRzIjogWwogICAgewogICAgICAiZm9vdHByaW50IjogIlFGTjMyIiwKICAgICAgInBsYWNlZCI6ICJ0cnVlIiwKICAgICAgInJlZiI6ICJVMSIsCiAgICAgICJyb3RhdGlvbiI6IDAsCiAgICAgICJzaWRlIjogIlRPUCIsCiAgICAgICJ4IjogMjAuMCwKICAgICAgInkiOiAyMC4wCiAgICB9LAogICAgewogICAgICAiZm9vdHByaW50IjogIjA2MDMiLAogICAgICAicGxhY2VkIjogInRydWUiLAogICAgICAicmVmIjogIlIxIiwKICAgICAgInJvdGF0aW9uIjogOTAsCiAgICAgICJzaWRlIjogIlRPUCIsCiAgICAgICJ4IjogMTIuMCwKICAgICAgInkiOiAyOC4wCiAgICB9LAogICAgewogICAgICAiZm9vdHByaW50IjogIjA2MDMiLAogICAgICAicGxhY2VkIjogInRydWUiLAogICAgICAicmVmIjogIkMxIiwKICAgICAgInJvdGF0aW9uIjogOTAsCiAgICAgICJzaWRlIjogIlRPUCIsCiAgICAgICJ4IjogMjguMCwKICAgICAgInkiOiAyOC4wCiAgICB9LAogICAgewogICAgICAiZm9vdHByaW50IjogIkhEUjQiLAogICAgICAicGxhY2VkIjogInRydWUiLAogICAgICAicmVmIjogIkoxIiwKICAgICAgInJvdGF0aW9uIjogMCwKICAgICAgInNpZGUiOiAiVE9QIiwKICAgICAgIngiOiA1LjAsCiAgICAgICJ5IjogMTAuMAogICAgfQogIF0sCiAgImRpZmZwYWlycyI6IFsKICAgIHsKICAgICAgImdhcF9taWwiOiA4LAogICAgICAibGVuZ3RoX25fbWlsIjogOTUwLAogICAgICAibGVuZ3RoX3BfbWlsIjogOTUyLAogICAgICAibmFtZSI6ICJVU0IyX0QiLAogICAgICAibmVnYXRpdmUiOiAiVVNCMl9EX04iLAogICAgICAicG9zaXRpdmUiOiAiVVNCMl9EX1AiCiAgICB9LAogICAgewogICAgICAiZ2FwX21pbCI6IDYsCiAgICAgICJsZW5ndGhfbl9taWwiOiAxODIwLAogICAgICAibGVuZ3RoX3BfbWlsIjogMTgxNiwKICAgICAgIm5hbWUiOiAiUENJRV9UWDAiLAogICAgICAibmVnYXRpdmUiOiAiUENJRV9UWDBfTiIsCiAgICAgICJwb3NpdGl2ZSI6ICJQQ0lFX1RYMF9QIgogICAgfQogIF0sCiAgImZvcm1hdCI6ICJlbmdpd29ybGQtbmV1dHJhbC1wY2ItdjEiLAogICJsYXllcnMiOiBbCiAgICB7CiAgICAgICJjb3BwZXJfbWlsIjogMS4wLAogICAgICAiZGllbGVjdHJpY19jb25zdGFudCI6IDQuMiwKICAgICAgImluZGV4IjogMSwKICAgICAgIm5hbWUiOiAiVE9QIiwKICAgICAgInR5cGUiOiAiU2lnbmFsIgogICAgfSwKICAgIHsKICAgICAgImNvcHBlcl9taWwiOiAxLjAsCiAgICAgICJkaWVsZWN0cmljX2NvbnN0YW50IjogNC4yLAogICAgICAiaW5kZXgiOiAyLAogICAgICAibmFtZSI6ICJHTkQiLAogICAgICAidHlwZSI6ICJQbGFuZSIKICAgIH0sCiAgICB7CiAgICAgICJjb3BwZXJfbWlsIjogMS4wLAogICAgICAiZGllbGVjdHJpY19jb25zdGFudCI6IDQuMiwKICAgICAgImluZGV4IjogMywKICAgICAgIm5hbWUiOiAiUFdSIiwKICAgICAgInR5cGUiOiAiUGxhbmUiCiAgICB9LAogICAgewogICAgICAiY29wcGVyX21pbCI6IDEuMCwKICAgICAgImRpZWxlY3RyaWNfY29uc3RhbnQiOiA0LjIsCiAgICAgICJpbmRleCI6IDQsCiAgICAgICJuYW1lIjogIkJPVFRPTSIsCiAgICAgICJ0eXBlIjogIlNpZ25hbCIKICAgIH0KICBdLAogICJuYW1lIjogImZ1bGxhZGRfYm9hcmQiLAogICJuZXRzIjogWwogICAgewogICAgICAibmFtZSI6ICJHTkQiLAogICAgICAicGlucyI6IFsKICAgICAgICAiVTEuMSIsCiAgICAgICAgIkMxLjIiLAogICAgICAgICJKMS4xIgogICAgICBdCiAgICB9LAogICAgewogICAgICAibmFtZSI6ICJWQ0MiLAogICAgICAicGlucyI6IFsKICAgICAgICAiVTEuMiIsCiAgICAgICAgIkMxLjEiLAogICAgICAgICJKMS4yIgogICAgICBdCiAgICB9LAogICAgewogICAgICAibmFtZSI6ICJVU0IyX0RfTiIsCiAgICAgICJwaW5zIjogWwogICAgICAgICJVMS41IiwKICAgICAgICAiUjkuMSIKICAgICAgXQogICAgfSwKICAgIHsKICAgICAgIm5hbWUiOiAiVVNCMl9EX1AiLAogICAgICAicGlucyI6IFsKICAgICAgICAiVTEuNiIsCiAgICAgICAgIlIxMC4xIgogICAgICBdCiAgICB9CiAgXSwKICAicGFkc3RhY2tzIjogWwogICAgewogICAgICAiY291bnQiOiAyLAogICAgICAiZGlhbWV0ZXJfbWlsIjogMjgsCiAgICAgICJob2xlX21pbCI6IDEyLAogICAgICAibmFtZSI6ICJWSUExMiIKICAgIH0sCiAgICB7CiAgICAgICJjb3VudCI6IDEsCiAgICAgICJkaWFtZXRlcl9taWwiOiAyNCwKICAgICAgImhvbGVfbWlsIjogMTAsCiAgICAgICJuYW1lIjogIlZJQTEwIgogICAgfSwKICAgIHsKICAgICAgImNvdW50IjogMiwKICAgICAgImRpYW1ldGVyX21pbCI6IDM1LAogICAgICAiaG9sZV9taWwiOiAwLAogICAgICAibmFtZSI6ICJTTUQwNjAzIgogICAgfQogIF0sCiAgInZpYXMiOiBbCiAgICB7CiAgICAgICJmcm9tIjogIlRPUCIsCiAgICAgICJpZCI6ICJWMSIsCiAgICAgICJuZXQiOiAiR05EIiwKICAgICAgInBhZHN0YWNrIjogIlZJQTEyIiwKICAgICAgInRvIjogIkJPVFRPTSIsCiAgICAgICJ4IjogMTUuMCwKICAgICAgInkiOiAxNS4wCiAgICB9LAogICAgewogICAgICAiZnJvbSI6ICJUT1AiLAogICAgICAiaWQiOiAiVjIiLAogICAgICAibmV0IjogIlZDQyIsCiAgICAgICJwYWRzdGFjayI6ICJWSUExMiIsCiAgICAgICJ0byI6ICJCT1RUT00iLAogICAgICAieCI6IDM1LjAsCiAgICAgICJ5IjogMTUuMAogICAgfSwKICAgIHsKICAgICAgImZyb20iOiAiVE9QIiwKICAgICAgImlkIjogIlYzIiwKICAgICAgIm5ldCI6ICJHTkQiLAogICAgICAicGFkc3RhY2siOiAiVklBMTAiLAogICAgICAidG8iOiAiQk9UVE9NIiwKICAgICAgIngiOiAxNS4wLAogICAgICAieSI6IDM1LjAKICAgIH0KICBdLAogICJ2aW9sYXRpb25zIjogWwogICAgewogICAgICAiaWQiOiAiRFJDMDAxIiwKICAgICAgIm9iamVjdCI6ICJVMS41LVI5LjEiLAogICAgICAic2V2ZXJpdHkiOiAiZXJyb3IiLAogICAgICAidHlwZSI6ICJjbGVhcmFuY2UiCiAgICB9LAogICAgewogICAgICAiaWQiOiAiRFJDMDAyIiwKICAgICAgIm9iamVjdCI6ICJKMSIsCiAgICAgICJzZXZlcml0eSI6ICJ3YXJuaW5nIiwKICAgICAgInR5cGUiOiAic2lsa3NjcmVlbiIKICAgIH0KICBdCn0K",
  "placement.csv": "UmVmZXJlbmNlLFhfbW0sWV9tbSxTaWRlLFJvdGF0aW9uDQpVMSwyMC4wLDIwLjAsVE9QLDANClIxLDEyLjAsMjguMCxUT1AsOTANCkMxLDI4LjAsMjguMCxUT1AsOTANCkoxLDUuMCwxMC4wLFRPUCwwDQo="
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
