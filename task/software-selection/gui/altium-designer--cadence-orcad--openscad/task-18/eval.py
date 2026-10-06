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


def _key(value) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value).casefold())


def _component_map(items):
    result = {}
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict) or "ref" not in item:
            return None
        ref = str(item["ref"]).strip().upper()
        if not ref or ref in result:
            return None
        result[ref] = item
    return result


def _net_map(items):
    result = {}
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict) or "name" not in item or not isinstance(item.get("pins"), list):
            return None
        name = str(item["name"]).strip().upper()
        if not name or name in result:
            return None
        result[name] = {str(pin).strip().upper() for pin in item["pins"]}
    return result


def _expected_nets(source, rename):
    merged = {}
    rename_upper = {str(old).upper(): str(new).upper() for old, new in rename.items()}
    for item in source.get("nets", []):
        name = str(item.get("name", "")).upper()
        name = rename_upper.get(name, name)
        merged.setdefault(name, set()).update(str(pin).upper() for pin in item.get("pins", []))
    return merged


def _pcb_valid(desktop: Path) -> bool:
    source = json.loads((desktop / "wifi_board.pcb.json").read_text(encoding="utf-8-sig"))
    spec = json.loads((desktop / "eco_spec.json").read_text(encoding="utf-8-sig"))
    actual = json.loads((desktop / "result" / "wifi_usb_eco.pcb.json").read_text(encoding="utf-8-sig"))
    source_components = _component_map(source.get("components"))
    actual_components = _component_map(actual.get("components"))
    if not source_components or not actual_components or set(source_components) != set(actual_components):
        return False
    wanted_footprints = {"R9": spec["R9_footprint"], "R10": spec["R10_footprint"]}
    for ref, source_item in source_components.items():
        actual_item = actual_components[ref]
        expected_item = dict(source_item)
        if ref in wanted_footprints:
            expected_item["footprint"] = wanted_footprints[ref]
        if not _json_value_equal(actual_item, expected_item):
            return False
    actual_nets = _net_map(actual.get("nets"))
    expected_nets = _expected_nets(source, spec.get("rename_nets", {}))
    if actual_nets != expected_nets:
        return False
    for key, value in source.items():
        if _key(key) in {"components", "nets"}:
            continue
        if key not in actual or not _json_value_equal(actual[key], value):
            return False
    return True


def _xml_attr(element, name):
    return next((value for key, value in element.attrib.items() if _key(key) == _key(name)), None)


def _ipc_valid(desktop: Path) -> bool:
    source = ET.parse(desktop / "wifi_board.ipc2581").getroot()
    actual = ET.parse(desktop / "result" / "wifi_usb_eco.ipc2581").getroot()
    spec = json.loads((desktop / "eco_spec.json").read_text(encoding="utf-8-sig"))
    source_sections = {_local_name(child.tag): child for child in source}
    actual_sections = {_local_name(child.tag): child for child in actual}
    for name, source_section in source_sections.items():
        if name in {"components", "nets"}:
            continue
        if name not in actual_sections or not _xml_element_equal(actual_sections[name], source_section):
            return False
    components = {}
    for element in actual.iter():
        if _local_name(element.tag) == "component":
            ref = str(_xml_attr(element, "ref") or "").upper()
            if not ref or ref in components:
                return False
            components[ref] = element
    if set(components) != {"U1", "R1", "C1", "J1", "R9", "R10", "R11"}:
        return False
    if str(_xml_attr(components["R9"], "footprint")) != str(spec["R9_footprint"]):
        return False
    if str(_xml_attr(components["R10"], "footprint")) != str(spec["R10_footprint"]):
        return False
    nets = {}
    for element in actual.iter():
        if _local_name(element.tag) != "net":
            continue
        name = str(_xml_attr(element, "name") or "").upper()
        if not name or name in nets:
            return False
        nets[name] = {str(_xml_attr(pin, "name") or "").upper() for pin in element if _local_name(pin.tag) == "pinref"}
    source_json = json.loads((desktop / "wifi_board.pcb.json").read_text(encoding="utf-8-sig"))
    return nets == _expected_nets(source_json, spec.get("rename_nets", {}))


def _report_valid(desktop: Path) -> bool:
    spec = json.loads((desktop / "eco_spec.json").read_text(encoding="utf-8-sig"))
    report = json.loads((desktop / "result" / "eco_report.json").read_text(encoding="utf-8-sig"))
    if isinstance(report, dict) and isinstance(report.get("changes"), dict):
        report = report["changes"]
    return isinstance(report, dict) and all(
        any(_key(actual_key) == _key(expected_key) and _json_value_equal(actual_value, expected_value)
            for actual_key, actual_value in report.items())
        for expected_key, expected_value in spec.items()
    )


def _constraints_valid(desktop: Path) -> bool:
    actual = json.loads((desktop / "result" / "constraints.json").read_text(encoding="utf-8-sig"))
    rule = actual.get("DiffPairsRouting") or actual.get("diff_pairs_routing")
    if not isinstance(rule, dict):
        return False
    scope = str(rule.get("scope", ""))
    return (
        "USB2_D" in scope
        and "PA12_USB_D" not in scope
        and _scalar_equal(rule.get("gap_mil"), 8)
        and _scalar_equal(rule.get("width_mil"), 6)
    )


def evaluate() -> bool:
    desktop = _desktop()
    required = [desktop / "result" / name for name in EXPECTED]
    if not all(path.is_file() and path.stat().st_size > 0 for path in required):
        return False
    try:
        return _pcb_valid(desktop) and _ipc_valid(desktop) and _report_valid(desktop) and _constraints_valid(desktop)
    except Exception:
        return False


if __name__ == "__main__":
    ok = evaluate()
    print("True" if ok else "False")
    sys.exit(0 if ok else 1)
