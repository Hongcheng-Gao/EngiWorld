from __future__ import annotations

import base64
import csv
import io
import json
import re
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
    return data.decode("utf-8", errors="replace").replace("\r\n", "\n").replace("\r", "\n").rstrip() + "\n"


_VOLATILE_JSON_KEYS = {
    "created_at", "exported_at", "generated_at", "generator", "timestamp",
    "tool_version", "exporter_version",
}
_VOLATILE_XML_ATTRS = {
    "created", "created_at", "date", "exported_at", "generated_at",
    "generator", "timestamp", "time", "tool_version", "exporter_version",
}


def _number(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str) and re.fullmatch(r"[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?", value.strip()):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _scalar_equal(actual, expected) -> bool:
    actual_number = _number(actual)
    expected_number = _number(expected)
    if actual_number is not None and expected_number is not None:
        tolerance = max(1e-6, abs(expected_number) * 1e-6)
        return abs(actual_number - expected_number) <= tolerance
    boolean_values = {"true": True, "false": False}
    actual_boolean = (
        boolean_values.get(actual.strip().lower())
        if isinstance(actual, str) else actual if isinstance(actual, bool) else None
    )
    expected_boolean = (
        boolean_values.get(expected.strip().lower())
        if isinstance(expected, str) else expected if isinstance(expected, bool) else None
    )
    if actual_boolean is not None and expected_boolean is not None:
        return actual_boolean == expected_boolean
    return actual == expected


def _json_value_equal(actual, expected) -> bool:
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            return False
        expected_keys = {key for key in expected if key.lower() not in _VOLATILE_JSON_KEYS}
        actual_keys = {key for key in actual if key.lower() not in _VOLATILE_JSON_KEYS}
        if actual_keys != expected_keys:
            return False
        return all(_json_value_equal(actual[key], expected[key]) for key in expected_keys)
    if isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            return False
        unmatched = list(actual)
        for expected_item in expected:
            for index, actual_item in enumerate(unmatched):
                if _json_value_equal(actual_item, expected_item):
                    unmatched.pop(index)
                    break
            else:
                return False
        return not unmatched
    return _scalar_equal(actual, expected)


def _json_equal(path: Path, expected: bytes) -> bool:
    try:
        actual_value = json.loads(path.read_text(encoding="utf-8-sig"))
        expected_value = json.loads(expected.decode("utf-8-sig"))
        return _json_value_equal(actual_value, expected_value)
    except Exception:
        return False


def _csv_rows(data: str):
    rows = [
        [cell.strip() for cell in row]
        for row in csv.reader(io.StringIO(data.replace("\r\n", "\n").replace("\r", "\n")))
        if any(cell.strip() for cell in row)
    ]
    if not rows or len(set(header.lower() for header in rows[0])) != len(rows[0]):
        return None
    headers = [header.lower() for header in rows[0]]
    records = []
    for row in rows[1:]:
        if len(row) != len(headers):
            return None
        records.append({header: value for header, value in zip(headers, row)})
    return set(headers), records


def _csv_row_equal(actual, expected, headers) -> bool:
    return all(_scalar_equal(actual[header], expected[header]) for header in headers)


def _csv_equal(path: Path, expected: bytes) -> bool:
    try:
        actual = _csv_rows(path.read_text(encoding="utf-8-sig"))
        target = _csv_rows(expected.decode("utf-8-sig"))
        if actual is None or target is None or actual[0] != target[0]:
            return False
        headers = sorted(target[0])
        unmatched = list(actual[1])
        if len(unmatched) != len(target[1]):
            return False
        for expected_row in target[1]:
            for index, actual_row in enumerate(unmatched):
                if _csv_row_equal(actual_row, expected_row, headers):
                    unmatched.pop(index)
                    break
            else:
                return False
        return not unmatched
    except Exception:
        return False


def _local_name(name: str) -> str:
    return name.rsplit("}", 1)[-1].lower()


def _xml_value_equal(actual: str, expected: str) -> bool:
    return _scalar_equal(" ".join(actual.split()), " ".join(expected.split()))


def _xml_element_equal(actual, expected) -> bool:
    if _local_name(actual.tag) != _local_name(expected.tag):
        return False

    actual_attrs = {
        _local_name(key): str(value)
        for key, value in actual.attrib.items()
        if _local_name(key) not in _VOLATILE_XML_ATTRS
    }
    expected_attrs = {
        _local_name(key): str(value)
        for key, value in expected.attrib.items()
        if _local_name(key) not in _VOLATILE_XML_ATTRS
    }
    if set(actual_attrs) != set(expected_attrs):
        return False
    if not all(_xml_value_equal(actual_attrs[key], expected_attrs[key]) for key in expected_attrs):
        return False
    if not _xml_value_equal(actual.text or "", expected.text or ""):
        return False

    unmatched = list(actual)
    if len(unmatched) != len(expected):
        return False
    for expected_child in expected:
        for index, actual_child in enumerate(unmatched):
            if _xml_element_equal(actual_child, expected_child):
                unmatched.pop(index)
                break
        else:
            return False
    return not unmatched


def _xml_equal(path: Path, expected: bytes) -> bool:
    try:
        actual_root = ET.parse(path).getroot()
        expected_root = ET.fromstring(expected)
        return _xml_element_equal(actual_root, expected_root)
    except Exception:
        return False


def _edif_parse(text: str):
    tokens = re.findall(r'"(?:[^"\\]|\\.)*"|[()]|[^\s()]+', text)
    index = 0

    def parse_one():
        nonlocal index
        if index >= len(tokens):
            raise ValueError("unexpected end of EDIF")
        token = tokens[index]
        index += 1
        if token != "(":
            if token == ")":
                raise ValueError("unexpected close parenthesis")
            return token
        values = []
        while index < len(tokens) and tokens[index] != ")":
            values.append(parse_one())
        if index >= len(tokens):
            raise ValueError("unclosed EDIF expression")
        index += 1
        return values

    value = parse_one()
    if index != len(tokens):
        raise ValueError("trailing EDIF tokens")
    return value


def _edif_canon(value):
    if not isinstance(value, list):
        return value
    atoms = []
    children = []
    for item in value:
        if isinstance(item, list):
            canonical = _edif_canon(item)
            head = canonical[0][0].lower() if canonical and canonical[0] else ""
            if head != "status":
                children.append(canonical)
        else:
            atoms.append(item)
    return (tuple(atoms), tuple(sorted(children, key=repr)))


def _edif_equal(path: Path, expected: bytes) -> bool:
    try:
        actual = _edif_parse(path.read_text(encoding="utf-8-sig", errors="ignore"))
        target = _edif_parse(expected.decode("utf-8-sig", errors="ignore"))
        return _edif_canon(actual) == _edif_canon(target)
    except Exception:
        return False


def _gerber_valid(data: bytes) -> bool:
    text = _text(data).upper()
    return bool(re.search(r"%FS[^%]*\*%", text)) and "M02*" in text


def _log_equal(actual: bytes, expected: bytes) -> bool:
    actual_text = _text(actual)
    expected_text = _text(expected)
    critical = set(re.findall(r"\b[A-Z][A-Z0-9_.-]+\b|\b\d+(?:-\d+)?\b|\b[\w.-]+\.[A-Za-z0-9]+\b", expected_text))
    lowered = actual_text.lower()
    if not all(token.lower() in lowered for token in critical):
        return False
    if re.search(r"\bno\s+fatal\b", expected_text, re.IGNORECASE):
        return bool(re.search(r"\bno\s+fatal\b", actual_text, re.IGNORECASE))
    return True


def _drill_signature(data: bytes):
    text = _text(data).upper()
    units = "INCH" if "INCH" in text else "METRIC" if "METRIC" in text else None
    tools = sorted((tool, format(float(diameter), ".12g")) for tool, diameter in re.findall(r"T(\d+)C([0-9.]+)", text))
    coordinates = sorted(re.findall(r"X[-+]?\d+Y[-+]?\d+", text))
    return units, tools, coordinates


def _content_equal(name: str, actual: bytes, expected: bytes) -> bool:
    suffix = Path(name).suffix.lower()
    if suffix in {".gbr", ".gtl", ".gbl", ".gts", ".gbs", ".gto", ".gbo", ".gm1", ".gml"}:
        return _gerber_valid(actual)
    if suffix == ".log":
        return _log_equal(actual, expected)
    if suffix == ".drl":
        return _drill_signature(actual) == _drill_signature(expected)
    if suffix in {".xml", ".ipc2581"}:
        try:
            return _xml_element_equal(ET.fromstring(actual), ET.fromstring(expected))
        except Exception:
            return False
    return _text(actual) == _text(expected)


def _zip_equal(path: Path, expected: bytes) -> bool:
    try:
        with zipfile.ZipFile(path) as actual_zip, zipfile.ZipFile(io.BytesIO(expected)) as expected_zip:
            actual_names = {Path(name).name.lower(): name for name in actual_zip.namelist() if not name.endswith("/")}
            expected_names = {Path(name).name.lower(): name for name in expected_zip.namelist() if not name.endswith("/")}
            if set(actual_names) != set(expected_names):
                return False
            return all(
                _content_equal(
                    expected_names[key],
                    actual_zip.read(actual_names[key]),
                    expected_zip.read(expected_names[key]),
                )
                for key in expected_names
            )
    except Exception:
        return False


def _bytes_equal(path: Path, expected: bytes) -> bool:
    try:
        suffix = path.suffix.lower()
        if suffix == ".json":
            return _json_equal(path, expected)
        if suffix == ".csv":
            return _csv_equal(path, expected)
        if suffix in {".ipc2581", ".xml"}:
            return _xml_equal(path, expected)
        if suffix == ".zip":
            return _zip_equal(path, expected)
        if suffix == ".edif":
            return _edif_equal(path, expected)
        return _content_equal(path.name, path.read_bytes(), expected)
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
