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
  "panel_summary.json": "ewogICJib2FyZF9jb3VudCI6IDEyLAogICJjb2x1bW5fc3BhY2luZ19taWwiOiAxMzM4LjU4MjcsCiAgImNvbHVtbnMiOiAzLAogICJtaXJyb3IiOiB0cnVlLAogICJvcmlnaW5fbW9kZSI6IDEsCiAgInJvdXRlX3Rvb2xfcGF0aCI6IHRydWUsCiAgInJvd19zcGFjaW5nX21pbCI6IDExMzMuODU4MywKICAicm93cyI6IDQsCiAgInNvdXJjZSI6ICJ3aWZpX2JvYXJkLmlwYzI1ODEiCn0K",
  "wifi_panel.ipc2581": "PD94bWwgdmVyc2lvbj0iMS4wIiA/Pgo8SVBDLTI1ODEgdmVyc2lvbj0iQiIgZ2VuZXJhdG9yPSJFbmdpd29ybGROZXV0cmFsIiBuYW1lPSJ3aWZpX2JvYXJkIj4KICA8U3RhY2t1cD4KICAgIDxMYXllciBpbmRleD0iMSIgbmFtZT0iVE9QIiB0eXBlPSJTaWduYWwiIGRpZWxlY3RyaWNfY29uc3RhbnQ9IjQuMiIgY29wcGVyX21pbD0iMS4wIi8+CiAgICA8TGF5ZXIgaW5kZXg9IjIiIG5hbWU9IkdORCIgdHlwZT0iUGxhbmUiIGRpZWxlY3RyaWNfY29uc3RhbnQ9IjQuMiIgY29wcGVyX21pbD0iMS4wIi8+CiAgICA8TGF5ZXIgaW5kZXg9IjMiIG5hbWU9IlBXUiIgdHlwZT0iUGxhbmUiIGRpZWxlY3RyaWNfY29uc3RhbnQ9IjQuMiIgY29wcGVyX21pbD0iMS4wIi8+CiAgICA8TGF5ZXIgaW5kZXg9IjQiIG5hbWU9IkJPVFRPTSIgdHlwZT0iU2lnbmFsIiBkaWVsZWN0cmljX2NvbnN0YW50PSI0LjIiIGNvcHBlcl9taWw9IjEuMCIvPgogIDwvU3RhY2t1cD4KICA8Q29tcG9uZW50cz4KICAgIDxDb21wb25lbnQgcmVmPSJVMSIgeD0iMjUuMCIgeT0iMjUuMCIgc2lkZT0iVE9QIiByb3RhdGlvbj0iMCIgZm9vdHByaW50PSJRRk4zMiIvPgogICAgPENvbXBvbmVudCByZWY9IlIxIiB4PSIxOC4wIiB5PSIzMS4wIiBzaWRlPSJUT1AiIHJvdGF0aW9uPSI5MCIgZm9vdHByaW50PSIwNjAzIi8+CiAgICA8Q29tcG9uZW50IHJlZj0iQzEiIHg9IjMxLjAiIHk9IjMxLjAiIHNpZGU9IlRPUCIgcm90YXRpb249IjkwIiBmb290cHJpbnQ9IjA2MDMiLz4KICAgIDxDb21wb25lbnQgcmVmPSJKMSIgeD0iOC4wIiB5PSIxNS4wIiBzaWRlPSJUT1AiIHJvdGF0aW9uPSIwIiBmb290cHJpbnQ9IkhEUjQiLz4KICAgIDxDb21wb25lbnQgcmVmPSJSOSIgeD0iNDEuMCIgeT0iMTIuMCIgc2lkZT0iVE9QIiByb3RhdGlvbj0iMCIgZm9vdHByaW50PSJSRVNDMDYwMyIvPgogICAgPENvbXBvbmVudCByZWY9IlIxMCIgeD0iNDEuMCIgeT0iMTQuMCIgc2lkZT0iVE9QIiByb3RhdGlvbj0iMCIgZm9vdHByaW50PSJSRVNDMDYwMyIvPgogICAgPENvbXBvbmVudCByZWY9IlIxMSIgeD0iNDEuMCIgeT0iMTYuMCIgc2lkZT0iVE9QIiByb3RhdGlvbj0iMCIgZm9vdHByaW50PSJSRVNDMDYwMyIvPgogIDwvQ29tcG9uZW50cz4KICA8TmV0cz4KICAgIDxOZXQgbmFtZT0iR05EIj4KICAgICAgPFBpblJlZiBuYW1lPSJVMS4xIi8+CiAgICAgIDxQaW5SZWYgbmFtZT0iQzEuMiIvPgogICAgICA8UGluUmVmIG5hbWU9IkoxLjEiLz4KICAgIDwvTmV0PgogICAgPE5ldCBuYW1lPSJWQ0MiPgogICAgICA8UGluUmVmIG5hbWU9IlUxLjIiLz4KICAgICAgPFBpblJlZiBuYW1lPSJDMS4xIi8+CiAgICAgIDxQaW5SZWYgbmFtZT0iSjEuMiIvPgogICAgPC9OZXQ+CiAgICA8TmV0IG5hbWU9IlVTQjJfRF9OIj4KICAgICAgPFBpblJlZiBuYW1lPSJVMS41Ii8+CiAgICAgIDxQaW5SZWYgbmFtZT0iUjkuMSIvPgogICAgPC9OZXQ+CiAgICA8TmV0IG5hbWU9IlVTQjJfRF9QIj4KICAgICAgPFBpblJlZiBuYW1lPSJVMS42Ii8+CiAgICAgIDxQaW5SZWYgbmFtZT0iUjEwLjEiLz4KICAgIDwvTmV0PgogICAgPE5ldCBuYW1lPSJQQTEyX1VTQl9EX04iPgogICAgICA8UGluUmVmIG5hbWU9IlUxLjE1Ii8+CiAgICAgIDxQaW5SZWYgbmFtZT0iUjkuMSIvPgogICAgPC9OZXQ+CiAgICA8TmV0IG5hbWU9IlBBMTJfVVNCX0RfUCI+CiAgICAgIDxQaW5SZWYgbmFtZT0iVTEuMTYiLz4KICAgICAgPFBpblJlZiBuYW1lPSJSMTAuMSIvPgogICAgPC9OZXQ+CiAgPC9OZXRzPgogIDxWaWFzPgogICAgPFZpYSBpZD0iVjEiIG5ldD0iR05EIiB4PSIxNS4wIiB5PSIxNS4wIiBmcm9tPSJUT1AiIHRvPSJCT1RUT00iIHBhZHN0YWNrPSJWSUExMiIvPgogICAgPFZpYSBpZD0iVjIiIG5ldD0iVkNDIiB4PSIzNS4wIiB5PSIxNS4wIiBmcm9tPSJUT1AiIHRvPSJCT1RUT00iIHBhZHN0YWNrPSJWSUExMiIvPgogICAgPFZpYSBpZD0iVjMiIG5ldD0iR05EIiB4PSIxNS4wIiB5PSIzNS4wIiBmcm9tPSJUT1AiIHRvPSJCT1RUT00iIHBhZHN0YWNrPSJWSUExMCIvPgogIDwvVmlhcz4KICA8UGFkc3RhY2tzPgogICAgPFBhZHN0YWNrIG5hbWU9IlZJQTEyIiBob2xlX21pbD0iMTIiIGRpYW1ldGVyX21pbD0iMjgiIGNvdW50PSIyIi8+CiAgICA8UGFkc3RhY2sgbmFtZT0iVklBMTAiIGhvbGVfbWlsPSIxMCIgZGlhbWV0ZXJfbWlsPSIyNCIgY291bnQ9IjEiLz4KICAgIDxQYWRzdGFjayBuYW1lPSJTTUQwNjAzIiBob2xlX21pbD0iMCIgZGlhbWV0ZXJfbWlsPSIzNSIgY291bnQ9IjIiLz4KICA8L1BhZHN0YWNrcz4KICA8RGlmZmVyZW50aWFsUGFpcnM+CiAgICA8RGlmZmVyZW50aWFsUGFpciBuYW1lPSJVU0IyX0QiIG5lZ2F0aXZlPSJVU0IyX0RfTiIgcG9zaXRpdmU9IlVTQjJfRF9QIiBnYXBfbWlsPSI4IiBsZW5ndGhfbl9taWw9Ijk1MCIgbGVuZ3RoX3BfbWlsPSI5NTIiLz4KICAgIDxEaWZmZXJlbnRpYWxQYWlyIG5hbWU9IlBDSUVfVFgwIiBuZWdhdGl2ZT0iUENJRV9UWDBfTiIgcG9zaXRpdmU9IlBDSUVfVFgwX1AiIGdhcF9taWw9IjYiIGxlbmd0aF9uX21pbD0iMTgyMCIgbGVuZ3RoX3BfbWlsPSIxODE2Ii8+CiAgPC9EaWZmZXJlbnRpYWxQYWlycz4KICA8VmlvbGF0aW9ucz4KICAgIDxWaW9sYXRpb24gaWQ9IkRSQzAwMSIgdHlwZT0iY2xlYXJhbmNlIiBvYmplY3Q9IlUxLjUtUjkuMSIgc2V2ZXJpdHk9ImVycm9yIi8+CiAgICA8VmlvbGF0aW9uIGlkPSJEUkMwMDIiIHR5cGU9InNpbGtzY3JlZW4iIG9iamVjdD0iSjEiIHNldmVyaXR5PSJ3YXJuaW5nIi8+CiAgPC9WaW9sYXRpb25zPgo8L0lQQy0yNTgxPgo=",
  "wifi_panel.pcb.json": "ewogICJjb21wb25lbnRzIjogWwogICAgewogICAgICAiZm9vdHByaW50IjogIlFGTjMyIiwKICAgICAgInJlZiI6ICJVMSIsCiAgICAgICJyb3RhdGlvbiI6IDAsCiAgICAgICJzaWRlIjogIlRPUCIsCiAgICAgICJ4IjogMjUuMCwKICAgICAgInkiOiAyNS4wCiAgICB9LAogICAgewogICAgICAiZm9vdHByaW50IjogIjA2MDMiLAogICAgICAicmVmIjogIlIxIiwKICAgICAgInJvdGF0aW9uIjogOTAsCiAgICAgICJzaWRlIjogIlRPUCIsCiAgICAgICJ4IjogMTguMCwKICAgICAgInkiOiAzMS4wCiAgICB9LAogICAgewogICAgICAiZm9vdHByaW50IjogIjA2MDMiLAogICAgICAicmVmIjogIkMxIiwKICAgICAgInJvdGF0aW9uIjogOTAsCiAgICAgICJzaWRlIjogIlRPUCIsCiAgICAgICJ4IjogMzEuMCwKICAgICAgInkiOiAzMS4wCiAgICB9LAogICAgewogICAgICAiZm9vdHByaW50IjogIkhEUjQiLAogICAgICAicmVmIjogIkoxIiwKICAgICAgInJvdGF0aW9uIjogMCwKICAgICAgInNpZGUiOiAiVE9QIiwKICAgICAgIngiOiA4LjAsCiAgICAgICJ5IjogMTUuMAogICAgfSwKICAgIHsKICAgICAgImZvb3RwcmludCI6ICJSRVNDMDYwMyIsCiAgICAgICJyZWYiOiAiUjkiLAogICAgICAicm90YXRpb24iOiAwLAogICAgICAic2lkZSI6ICJUT1AiLAogICAgICAieCI6IDQxLjAsCiAgICAgICJ5IjogMTIuMAogICAgfSwKICAgIHsKICAgICAgImZvb3RwcmludCI6ICJSRVNDMDYwMyIsCiAgICAgICJyZWYiOiAiUjEwIiwKICAgICAgInJvdGF0aW9uIjogMCwKICAgICAgInNpZGUiOiAiVE9QIiwKICAgICAgIngiOiA0MS4wLAogICAgICAieSI6IDE0LjAKICAgIH0sCiAgICB7CiAgICAgICJmb290cHJpbnQiOiAiUkVTQzA2MDMiLAogICAgICAicmVmIjogIlIxMSIsCiAgICAgICJyb3RhdGlvbiI6IDAsCiAgICAgICJzaWRlIjogIlRPUCIsCiAgICAgICJ4IjogNDEuMCwKICAgICAgInkiOiAxNi4wCiAgICB9CiAgXSwKICAiZGlmZnBhaXJzIjogWwogICAgewogICAgICAiZ2FwX21pbCI6IDgsCiAgICAgICJsZW5ndGhfbl9taWwiOiA5NTAsCiAgICAgICJsZW5ndGhfcF9taWwiOiA5NTIsCiAgICAgICJuYW1lIjogIlVTQjJfRCIsCiAgICAgICJuZWdhdGl2ZSI6ICJVU0IyX0RfTiIsCiAgICAgICJwb3NpdGl2ZSI6ICJVU0IyX0RfUCIKICAgIH0sCiAgICB7CiAgICAgICJnYXBfbWlsIjogNiwKICAgICAgImxlbmd0aF9uX21pbCI6IDE4MjAsCiAgICAgICJsZW5ndGhfcF9taWwiOiAxODE2LAogICAgICAibmFtZSI6ICJQQ0lFX1RYMCIsCiAgICAgICJuZWdhdGl2ZSI6ICJQQ0lFX1RYMF9OIiwKICAgICAgInBvc2l0aXZlIjogIlBDSUVfVFgwX1AiCiAgICB9CiAgXSwKICAiZm9ybWF0IjogImVuZ2l3b3JsZC1uZXV0cmFsLXBjYi12MSIsCiAgImxheWVycyI6IFsKICAgIHsKICAgICAgImNvcHBlcl9taWwiOiAxLjAsCiAgICAgICJkaWVsZWN0cmljX2NvbnN0YW50IjogNC4yLAogICAgICAiaW5kZXgiOiAxLAogICAgICAibmFtZSI6ICJUT1AiLAogICAgICAidHlwZSI6ICJTaWduYWwiCiAgICB9LAogICAgewogICAgICAiY29wcGVyX21pbCI6IDEuMCwKICAgICAgImRpZWxlY3RyaWNfY29uc3RhbnQiOiA0LjIsCiAgICAgICJpbmRleCI6IDIsCiAgICAgICJuYW1lIjogIkdORCIsCiAgICAgICJ0eXBlIjogIlBsYW5lIgogICAgfSwKICAgIHsKICAgICAgImNvcHBlcl9taWwiOiAxLjAsCiAgICAgICJkaWVsZWN0cmljX2NvbnN0YW50IjogNC4yLAogICAgICAiaW5kZXgiOiAzLAogICAgICAibmFtZSI6ICJQV1IiLAogICAgICAidHlwZSI6ICJQbGFuZSIKICAgIH0sCiAgICB7CiAgICAgICJjb3BwZXJfbWlsIjogMS4wLAogICAgICAiZGllbGVjdHJpY19jb25zdGFudCI6IDQuMiwKICAgICAgImluZGV4IjogNCwKICAgICAgIm5hbWUiOiAiQk9UVE9NIiwKICAgICAgInR5cGUiOiAiU2lnbmFsIgogICAgfQogIF0sCiAgIm5hbWUiOiAid2lmaV9ib2FyZCIsCiAgIm5ldHMiOiBbCiAgICB7CiAgICAgICJuYW1lIjogIkdORCIsCiAgICAgICJwaW5zIjogWwogICAgICAgICJVMS4xIiwKICAgICAgICAiQzEuMiIsCiAgICAgICAgIkoxLjEiCiAgICAgIF0KICAgIH0sCiAgICB7CiAgICAgICJuYW1lIjogIlZDQyIsCiAgICAgICJwaW5zIjogWwogICAgICAgICJVMS4yIiwKICAgICAgICAiQzEuMSIsCiAgICAgICAgIkoxLjIiCiAgICAgIF0KICAgIH0sCiAgICB7CiAgICAgICJuYW1lIjogIlVTQjJfRF9OIiwKICAgICAgInBpbnMiOiBbCiAgICAgICAgIlUxLjUiLAogICAgICAgICJSOS4xIgogICAgICBdCiAgICB9LAogICAgewogICAgICAibmFtZSI6ICJVU0IyX0RfUCIsCiAgICAgICJwaW5zIjogWwogICAgICAgICJVMS42IiwKICAgICAgICAiUjEwLjEiCiAgICAgIF0KICAgIH0sCiAgICB7CiAgICAgICJuYW1lIjogIlBBMTJfVVNCX0RfTiIsCiAgICAgICJwaW5zIjogWwogICAgICAgICJVMS4xNSIsCiAgICAgICAgIlI5LjEiCiAgICAgIF0KICAgIH0sCiAgICB7CiAgICAgICJuYW1lIjogIlBBMTJfVVNCX0RfUCIsCiAgICAgICJwaW5zIjogWwogICAgICAgICJVMS4xNiIsCiAgICAgICAgIlIxMC4xIgogICAgICBdCiAgICB9CiAgXSwKICAicGFkc3RhY2tzIjogWwogICAgewogICAgICAiY291bnQiOiAyLAogICAgICAiZGlhbWV0ZXJfbWlsIjogMjgsCiAgICAgICJob2xlX21pbCI6IDEyLAogICAgICAibmFtZSI6ICJWSUExMiIKICAgIH0sCiAgICB7CiAgICAgICJjb3VudCI6IDEsCiAgICAgICJkaWFtZXRlcl9taWwiOiAyNCwKICAgICAgImhvbGVfbWlsIjogMTAsCiAgICAgICJuYW1lIjogIlZJQTEwIgogICAgfSwKICAgIHsKICAgICAgImNvdW50IjogMiwKICAgICAgImRpYW1ldGVyX21pbCI6IDM1LAogICAgICAiaG9sZV9taWwiOiAwLAogICAgICAibmFtZSI6ICJTTUQwNjAzIgogICAgfQogIF0sCiAgInBhbmVsIjogewogICAgImNvbHVtbl9zcGFjaW5nX21pbCI6IDEzMzguNTgyNywKICAgICJjb2x1bW5zIjogMywKICAgICJtaXJyb3IiOiB0cnVlLAogICAgIm9yaWdpbl9tb2RlIjogMSwKICAgICJyb3dfc3BhY2luZ19taWwiOiAxMTMzLjg1ODMsCiAgICAicm93cyI6IDQKICB9LAogICJ2aWFzIjogWwogICAgewogICAgICAiZnJvbSI6ICJUT1AiLAogICAgICAiaWQiOiAiVjEiLAogICAgICAibmV0IjogIkdORCIsCiAgICAgICJwYWRzdGFjayI6ICJWSUExMiIsCiAgICAgICJ0byI6ICJCT1RUT00iLAogICAgICAieCI6IDE1LjAsCiAgICAgICJ5IjogMTUuMAogICAgfSwKICAgIHsKICAgICAgImZyb20iOiAiVE9QIiwKICAgICAgImlkIjogIlYyIiwKICAgICAgIm5ldCI6ICJWQ0MiLAogICAgICAicGFkc3RhY2siOiAiVklBMTIiLAogICAgICAidG8iOiAiQk9UVE9NIiwKICAgICAgIngiOiAzNS4wLAogICAgICAieSI6IDE1LjAKICAgIH0sCiAgICB7CiAgICAgICJmcm9tIjogIlRPUCIsCiAgICAgICJpZCI6ICJWMyIsCiAgICAgICJuZXQiOiAiR05EIiwKICAgICAgInBhZHN0YWNrIjogIlZJQTEwIiwKICAgICAgInRvIjogIkJPVFRPTSIsCiAgICAgICJ4IjogMTUuMCwKICAgICAgInkiOiAzNS4wCiAgICB9CiAgXSwKICAidmlvbGF0aW9ucyI6IFsKICAgIHsKICAgICAgImlkIjogIkRSQzAwMSIsCiAgICAgICJvYmplY3QiOiAiVTEuNS1SOS4xIiwKICAgICAgInNldmVyaXR5IjogImVycm9yIiwKICAgICAgInR5cGUiOiAiY2xlYXJhbmNlIgogICAgfSwKICAgIHsKICAgICAgImlkIjogIkRSQzAwMiIsCiAgICAgICJvYmplY3QiOiAiSjEiLAogICAgICAic2V2ZXJpdHkiOiAid2FybmluZyIsCiAgICAgICJ0eXBlIjogInNpbGtzY3JlZW4iCiAgICB9CiAgXQp9Cg=="
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
