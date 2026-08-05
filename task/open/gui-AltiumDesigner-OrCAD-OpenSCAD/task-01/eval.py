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
  "bcd_install.edif": "KGVkaWYgQkNECiAgKGVkaWZWZXJzaW9uIDIgMCAwKQogIChlZGlmTGV2ZWwgMCkKICAoa2V5d29yZE1hcCAoa2V5d29yZExldmVsIDApKQogIChzdGF0dXMgKHdyaXR0ZW4gKHRpbWVTdGFtcCAyMDI2IDcgNSAwIDAgMCkgKHByb2dyYW0gIkVuZ2l3b3JsZE5ldXRyYWwiKSkpCiAgKGxpYnJhcnkgQkNECiAgICAoY2VsbCBCQ0QgKGNlbGxUeXBlIEdFTkVSSUMpKQogICkKICAoZGVzaWduIEJDRAogICAgKGluc3RhbmNlIFUzMAogICAgICAocHJvcGVydHkgVmFsdWUgKHN0cmluZyAiQkNEX0NFTExfMzAiKSkKICAgICAgKHByb3BlcnR5IFBhZ2UgKHN0cmluZyAiQkNEIikpCiAgICAgIChwcm9wZXJ0eSBJbnN0YWxsIChzdHJpbmcgIlkiKSkKICAgICAgKHByb3BlcnR5IFBJTl8xIChzdHJpbmcgIjEiKSkKICAgICAgKHByb3BlcnR5IFBJTl8yIChzdHJpbmcgIjIiKSkKICAgICAgKHByb3BlcnR5IFBJTl8zIChzdHJpbmcgIjMiKSkKICAgICkKICAgIChpbnN0YW5jZSBVMzEKICAgICAgKHByb3BlcnR5IFZhbHVlIChzdHJpbmcgIkJDRF9DRUxMXzMxIikpCiAgICAgIChwcm9wZXJ0eSBQYWdlIChzdHJpbmcgIkJDRCIpKQogICAgICAocHJvcGVydHkgSW5zdGFsbCAoc3RyaW5nICJZIikpCiAgICAgIChwcm9wZXJ0eSBQSU5fMSAoc3RyaW5nICIxIikpCiAgICAgIChwcm9wZXJ0eSBQSU5fMiAoc3RyaW5nICIyIikpCiAgICAgIChwcm9wZXJ0eSBQSU5fMyAoc3RyaW5nICIzIikpCiAgICApCiAgICAoaW5zdGFuY2UgVTMyCiAgICAgIChwcm9wZXJ0eSBWYWx1ZSAoc3RyaW5nICJCQ0RfQ0VMTF8zMiIpKQogICAgICAocHJvcGVydHkgUGFnZSAoc3RyaW5nICJCQ0QiKSkKICAgICAgKHByb3BlcnR5IEluc3RhbGwgKHN0cmluZyAiTiIpKQogICAgICAocHJvcGVydHkgUElOXzEgKHN0cmluZyAiMSIpKQogICAgICAocHJvcGVydHkgUElOXzIgKHN0cmluZyAiMiIpKQogICAgICAocHJvcGVydHkgUElOXzMgKHN0cmluZyAiMyIpKQogICAgKQogICAgKGluc3RhbmNlIFUzMwogICAgICAocHJvcGVydHkgVmFsdWUgKHN0cmluZyAiQkNEX0NFTExfMzMiKSkKICAgICAgKHByb3BlcnR5IFBhZ2UgKHN0cmluZyAiQkNEIikpCiAgICAgIChwcm9wZXJ0eSBJbnN0YWxsIChzdHJpbmcgIlkiKSkKICAgICAgKHByb3BlcnR5IFBJTl8xIChzdHJpbmcgIjEiKSkKICAgICAgKHByb3BlcnR5IFBJTl8yIChzdHJpbmcgIjIiKSkKICAgICAgKHByb3BlcnR5IFBJTl8zIChzdHJpbmcgIjMiKSkKICAgICkKICAgIChpbnN0YW5jZSBVMzQKICAgICAgKHByb3BlcnR5IFZhbHVlIChzdHJpbmcgIkJDRF9DRUxMXzM0IikpCiAgICAgIChwcm9wZXJ0eSBQYWdlIChzdHJpbmcgIkJDRCIpKQogICAgICAocHJvcGVydHkgSW5zdGFsbCAoc3RyaW5nICJOIikpCiAgICAgIChwcm9wZXJ0eSBQSU5fMSAoc3RyaW5nICIxIikpCiAgICAgIChwcm9wZXJ0eSBQSU5fMiAoc3RyaW5nICIyIikpCiAgICAgIChwcm9wZXJ0eSBQSU5fMyAoc3RyaW5nICIzIikpCiAgICApCiAgICAoaW5zdGFuY2UgVTM1CiAgICAgIChwcm9wZXJ0eSBWYWx1ZSAoc3RyaW5nICJCQ0RfQ0VMTF8zNSIpKQogICAgICAocHJvcGVydHkgUGFnZSAoc3RyaW5nICJCQ0QiKSkKICAgICAgKHByb3BlcnR5IFBJTl8xIChzdHJpbmcgIjEiKSkKICAgICAgKHByb3BlcnR5IFBJTl8yIChzdHJpbmcgIjIiKSkKICAgICAgKHByb3BlcnR5IFBJTl8zIChzdHJpbmcgIjMiKSkKICAgICkKICAgIChpbnN0YW5jZSBVMzYKICAgICAgKHByb3BlcnR5IFZhbHVlIChzdHJpbmcgIkJDRF9DRUxMXzM2IikpCiAgICAgIChwcm9wZXJ0eSBQYWdlIChzdHJpbmcgIkJDRCIpKQogICAgICAocHJvcGVydHkgUElOXzEgKHN0cmluZyAiMSIpKQogICAgICAocHJvcGVydHkgUElOXzIgKHN0cmluZyAiMiIpKQogICAgICAocHJvcGVydHkgUElOXzMgKHN0cmluZyAiMyIpKQogICAgKQogICAgKGluc3RhbmNlIFUzNwogICAgICAocHJvcGVydHkgVmFsdWUgKHN0cmluZyAiQkNEX0NFTExfMzciKSkKICAgICAgKHByb3BlcnR5IFBhZ2UgKHN0cmluZyAiQkNEIikpCiAgICAgIChwcm9wZXJ0eSBQSU5fMSAoc3RyaW5nICIxIikpCiAgICAgIChwcm9wZXJ0eSBQSU5fMiAoc3RyaW5nICIyIikpCiAgICAgIChwcm9wZXJ0eSBQSU5fMyAoc3RyaW5nICIzIikpCiAgICApCiAgICAoaW5zdGFuY2UgVTM4CiAgICAgIChwcm9wZXJ0eSBWYWx1ZSAoc3RyaW5nICJCQ0RfQ0VMTF8zOCIpKQogICAgICAocHJvcGVydHkgUGFnZSAoc3RyaW5nICJCQ0QiKSkKICAgICAgKHByb3BlcnR5IFBJTl8xIChzdHJpbmcgIjEiKSkKICAgICAgKHByb3BlcnR5IFBJTl8yIChzdHJpbmcgIjIiKSkKICAgICAgKHByb3BlcnR5IFBJTl8zIChzdHJpbmcgIjMiKSkKICAgICkKICAgIChpbnN0YW5jZSBVMzkKICAgICAgKHByb3BlcnR5IFZhbHVlIChzdHJpbmcgIkJDRF9DRUxMXzM5IikpCiAgICAgIChwcm9wZXJ0eSBQYWdlIChzdHJpbmcgIkJDRCIpKQogICAgICAocHJvcGVydHkgUElOXzEgKHN0cmluZyAiMSIpKQogICAgICAocHJvcGVydHkgUElOXzIgKHN0cmluZyAiMiIpKQogICAgICAocHJvcGVydHkgUElOXzMgKHN0cmluZyAiMyIpKQogICAgKQogICAgKGluc3RhbmNlIFU0MAogICAgICAocHJvcGVydHkgVmFsdWUgKHN0cmluZyAiQkNEX0NFTExfNDAiKSkKICAgICAgKHByb3BlcnR5IFBhZ2UgKHN0cmluZyAiQkNEIikpCiAgICAgIChwcm9wZXJ0eSBQSU5fMSAoc3RyaW5nICIxIikpCiAgICAgIChwcm9wZXJ0eSBQSU5fMiAoc3RyaW5nICIyIikpCiAgICAgIChwcm9wZXJ0eSBQSU5fMyAoc3RyaW5nICIzIikpCiAgICApCiAgICAoaW5zdGFuY2UgVTQxCiAgICAgIChwcm9wZXJ0eSBWYWx1ZSAoc3RyaW5nICJCQ0RfQ0VMTF80MSIpKQogICAgICAocHJvcGVydHkgUGFnZSAoc3RyaW5nICJCQ0QiKSkKICAgICAgKHByb3BlcnR5IFBJTl8xIChzdHJpbmcgIjEiKSkKICAgICAgKHByb3BlcnR5IFBJTl8yIChzdHJpbmcgIjIiKSkKICAgICAgKHByb3BlcnR5IFBJTl8zIChzdHJpbmcgIjMiKSkKICAgICkKICAgIChpbnN0YW5jZSBVNDIKICAgICAgKHByb3BlcnR5IFZhbHVlIChzdHJpbmcgIkJDRF9DRUxMXzQyIikpCiAgICAgIChwcm9wZXJ0eSBQYWdlIChzdHJpbmcgIkJDRCIpKQogICAgICAocHJvcGVydHkgUElOXzEgKHN0cmluZyAiMSIpKQogICAgICAocHJvcGVydHkgUElOXzIgKHN0cmluZyAiMiIpKQogICAgICAocHJvcGVydHkgUElOXzMgKHN0cmluZyAiMyIpKQogICAgKQogICAgKGluc3RhbmNlIFU0MwogICAgICAocHJvcGVydHkgVmFsdWUgKHN0cmluZyAiQkNEX0NFTExfNDMiKSkKICAgICAgKHByb3BlcnR5IFBhZ2UgKHN0cmluZyAiQkNEIikpCiAgICAgIChwcm9wZXJ0eSBQSU5fMSAoc3RyaW5nICIxIikpCiAgICAgIChwcm9wZXJ0eSBQSU5fMiAoc3RyaW5nICIyIikpCiAgICAgIChwcm9wZXJ0eSBQSU5fMyAoc3RyaW5nICIzIikpCiAgICApCiAgICAoaW5zdGFuY2UgVTQ0CiAgICAgIChwcm9wZXJ0eSBWYWx1ZSAoc3RyaW5nICJCQ0RfQ0VMTF80NCIpKQogICAgICAocHJvcGVydHkgUGFnZSAoc3RyaW5nICJCQ0QiKSkKICAgICAgKHByb3BlcnR5IFBJTl8xIChzdHJpbmcgIjEiKSkKICAgICAgKHByb3BlcnR5IFBJTl8yIChzdHJpbmcgIjIiKSkKICAgICAgKHByb3BlcnR5IFBJTl8zIChzdHJpbmcgIjMiKSkKICAgICkKICAgIChpbnN0YW5jZSBVNDUKICAgICAgKHByb3BlcnR5IFZhbHVlIChzdHJpbmcgIkJDRF9DRUxMXzQ1IikpCiAgICAgIChwcm9wZXJ0eSBQYWdlIChzdHJpbmcgIkJDRCIpKQogICAgICAocHJvcGVydHkgUElOXzEgKHN0cmluZyAiMSIpKQogICAgICAocHJvcGVydHkgUElOXzIgKHN0cmluZyAiMiIpKQogICAgICAocHJvcGVydHkgUElOXzMgKHN0cmluZyAiMyIpKQogICAgKQogICAgKGluc3RhbmNlIFU0NgogICAgICAocHJvcGVydHkgVmFsdWUgKHN0cmluZyAiQkNEX0NFTExfNDYiKSkKICAgICAgKHByb3BlcnR5IFBhZ2UgKHN0cmluZyAiQkNEIikpCiAgICAgIChwcm9wZXJ0eSBQSU5fMSAoc3RyaW5nICIxIikpCiAgICAgIChwcm9wZXJ0eSBQSU5fMiAoc3RyaW5nICIyIikpCiAgICAgIChwcm9wZXJ0eSBQSU5fMyAoc3RyaW5nICIzIikpCiAgICApCiAgICAoaW5zdGFuY2UgVTQ3CiAgICAgIChwcm9wZXJ0eSBWYWx1ZSAoc3RyaW5nICJCQ0RfQ0VMTF80NyIpKQogICAgICAocHJvcGVydHkgUGFnZSAoc3RyaW5nICJCQ0QiKSkKICAgICAgKHByb3BlcnR5IFBJTl8xIChzdHJpbmcgIjEiKSkKICAgICAgKHByb3BlcnR5IFBJTl8yIChzdHJpbmcgIjIiKSkKICAgICAgKHByb3BlcnR5IFBJTl8zIChzdHJpbmcgIjMiKSkKICAgICkKICAgIChpbnN0YW5jZSBVNDgKICAgICAgKHByb3BlcnR5IFZhbHVlIChzdHJpbmcgIkJDRF9DRUxMXzQ4IikpCiAgICAgIChwcm9wZXJ0eSBQYWdlIChzdHJpbmcgIkJDRCIpKQogICAgICAocHJvcGVydHkgUElOXzEgKHN0cmluZyAiMSIpKQogICAgICAocHJvcGVydHkgUElOXzIgKHN0cmluZyAiMiIpKQogICAgICAocHJvcGVydHkgUElOXzMgKHN0cmluZyAiMyIpKQogICAgKQogICAgKGluc3RhbmNlIFU0OQogICAgICAocHJvcGVydHkgVmFsdWUgKHN0cmluZyAiQkNEX0NFTExfNDkiKSkKICAgICAgKHByb3BlcnR5IFBhZ2UgKHN0cmluZyAiQkNEIikpCiAgICAgIChwcm9wZXJ0eSBQSU5fMSAoc3RyaW5nICIxIikpCiAgICAgIChwcm9wZXJ0eSBQSU5fMiAoc3RyaW5nICIyIikpCiAgICAgIChwcm9wZXJ0eSBQSU5fMyAoc3RyaW5nICIzIikpCiAgICApCiAgKQopCg==",
  "bcd_install.schematic.json": "ewogICJjb21wb25lbnRzIjogWwogICAgewogICAgICAicGFnZSI6ICJCQ0QiLAogICAgICAicGlucyI6IFsKICAgICAgICAiMSIsCiAgICAgICAgIjIiLAogICAgICAgICIzIgogICAgICBdLAogICAgICAicHJvcGVydGllcyI6IHsKICAgICAgICAiSW5zdGFsbCI6ICJZIgogICAgICB9LAogICAgICAicmVmIjogIlUzMCIsCiAgICAgICJ2YWx1ZSI6ICJCQ0RfQ0VMTF8zMCIKICAgIH0sCiAgICB7CiAgICAgICJwYWdlIjogIkJDRCIsCiAgICAgICJwaW5zIjogWwogICAgICAgICIxIiwKICAgICAgICAiMiIsCiAgICAgICAgIjMiCiAgICAgIF0sCiAgICAgICJwcm9wZXJ0aWVzIjogewogICAgICAgICJJbnN0YWxsIjogIlkiCiAgICAgIH0sCiAgICAgICJyZWYiOiAiVTMxIiwKICAgICAgInZhbHVlIjogIkJDRF9DRUxMXzMxIgogICAgfSwKICAgIHsKICAgICAgInBhZ2UiOiAiQkNEIiwKICAgICAgInBpbnMiOiBbCiAgICAgICAgIjEiLAogICAgICAgICIyIiwKICAgICAgICAiMyIKICAgICAgXSwKICAgICAgInByb3BlcnRpZXMiOiB7CiAgICAgICAgIkluc3RhbGwiOiAiTiIKICAgICAgfSwKICAgICAgInJlZiI6ICJVMzIiLAogICAgICAidmFsdWUiOiAiQkNEX0NFTExfMzIiCiAgICB9LAogICAgewogICAgICAicGFnZSI6ICJCQ0QiLAogICAgICAicGlucyI6IFsKICAgICAgICAiMSIsCiAgICAgICAgIjIiLAogICAgICAgICIzIgogICAgICBdLAogICAgICAicHJvcGVydGllcyI6IHsKICAgICAgICAiSW5zdGFsbCI6ICJZIgogICAgICB9LAogICAgICAicmVmIjogIlUzMyIsCiAgICAgICJ2YWx1ZSI6ICJCQ0RfQ0VMTF8zMyIKICAgIH0sCiAgICB7CiAgICAgICJwYWdlIjogIkJDRCIsCiAgICAgICJwaW5zIjogWwogICAgICAgICIxIiwKICAgICAgICAiMiIsCiAgICAgICAgIjMiCiAgICAgIF0sCiAgICAgICJwcm9wZXJ0aWVzIjogewogICAgICAgICJJbnN0YWxsIjogIk4iCiAgICAgIH0sCiAgICAgICJyZWYiOiAiVTM0IiwKICAgICAgInZhbHVlIjogIkJDRF9DRUxMXzM0IgogICAgfSwKICAgIHsKICAgICAgInBhZ2UiOiAiQkNEIiwKICAgICAgInBpbnMiOiBbCiAgICAgICAgIjEiLAogICAgICAgICIyIiwKICAgICAgICAiMyIKICAgICAgXSwKICAgICAgInByb3BlcnRpZXMiOiB7fSwKICAgICAgInJlZiI6ICJVMzUiLAogICAgICAidmFsdWUiOiAiQkNEX0NFTExfMzUiCiAgICB9LAogICAgewogICAgICAicGFnZSI6ICJCQ0QiLAogICAgICAicGlucyI6IFsKICAgICAgICAiMSIsCiAgICAgICAgIjIiLAogICAgICAgICIzIgogICAgICBdLAogICAgICAicHJvcGVydGllcyI6IHt9LAogICAgICAicmVmIjogIlUzNiIsCiAgICAgICJ2YWx1ZSI6ICJCQ0RfQ0VMTF8zNiIKICAgIH0sCiAgICB7CiAgICAgICJwYWdlIjogIkJDRCIsCiAgICAgICJwaW5zIjogWwogICAgICAgICIxIiwKICAgICAgICAiMiIsCiAgICAgICAgIjMiCiAgICAgIF0sCiAgICAgICJwcm9wZXJ0aWVzIjoge30sCiAgICAgICJyZWYiOiAiVTM3IiwKICAgICAgInZhbHVlIjogIkJDRF9DRUxMXzM3IgogICAgfSwKICAgIHsKICAgICAgInBhZ2UiOiAiQkNEIiwKICAgICAgInBpbnMiOiBbCiAgICAgICAgIjEiLAogICAgICAgICIyIiwKICAgICAgICAiMyIKICAgICAgXSwKICAgICAgInByb3BlcnRpZXMiOiB7fSwKICAgICAgInJlZiI6ICJVMzgiLAogICAgICAidmFsdWUiOiAiQkNEX0NFTExfMzgiCiAgICB9LAogICAgewogICAgICAicGFnZSI6ICJCQ0QiLAogICAgICAicGlucyI6IFsKICAgICAgICAiMSIsCiAgICAgICAgIjIiLAogICAgICAgICIzIgogICAgICBdLAogICAgICAicHJvcGVydGllcyI6IHt9LAogICAgICAicmVmIjogIlUzOSIsCiAgICAgICJ2YWx1ZSI6ICJCQ0RfQ0VMTF8zOSIKICAgIH0sCiAgICB7CiAgICAgICJwYWdlIjogIkJDRCIsCiAgICAgICJwaW5zIjogWwogICAgICAgICIxIiwKICAgICAgICAiMiIsCiAgICAgICAgIjMiCiAgICAgIF0sCiAgICAgICJwcm9wZXJ0aWVzIjoge30sCiAgICAgICJyZWYiOiAiVTQwIiwKICAgICAgInZhbHVlIjogIkJDRF9DRUxMXzQwIgogICAgfSwKICAgIHsKICAgICAgInBhZ2UiOiAiQkNEIiwKICAgICAgInBpbnMiOiBbCiAgICAgICAgIjEiLAogICAgICAgICIyIiwKICAgICAgICAiMyIKICAgICAgXSwKICAgICAgInByb3BlcnRpZXMiOiB7fSwKICAgICAgInJlZiI6ICJVNDEiLAogICAgICAidmFsdWUiOiAiQkNEX0NFTExfNDEiCiAgICB9LAogICAgewogICAgICAicGFnZSI6ICJCQ0QiLAogICAgICAicGlucyI6IFsKICAgICAgICAiMSIsCiAgICAgICAgIjIiLAogICAgICAgICIzIgogICAgICBdLAogICAgICAicHJvcGVydGllcyI6IHt9LAogICAgICAicmVmIjogIlU0MiIsCiAgICAgICJ2YWx1ZSI6ICJCQ0RfQ0VMTF80MiIKICAgIH0sCiAgICB7CiAgICAgICJwYWdlIjogIkJDRCIsCiAgICAgICJwaW5zIjogWwogICAgICAgICIxIiwKICAgICAgICAiMiIsCiAgICAgICAgIjMiCiAgICAgIF0sCiAgICAgICJwcm9wZXJ0aWVzIjoge30sCiAgICAgICJyZWYiOiAiVTQzIiwKICAgICAgInZhbHVlIjogIkJDRF9DRUxMXzQzIgogICAgfSwKICAgIHsKICAgICAgInBhZ2UiOiAiQkNEIiwKICAgICAgInBpbnMiOiBbCiAgICAgICAgIjEiLAogICAgICAgICIyIiwKICAgICAgICAiMyIKICAgICAgXSwKICAgICAgInByb3BlcnRpZXMiOiB7fSwKICAgICAgInJlZiI6ICJVNDQiLAogICAgICAidmFsdWUiOiAiQkNEX0NFTExfNDQiCiAgICB9LAogICAgewogICAgICAicGFnZSI6ICJCQ0QiLAogICAgICAicGlucyI6IFsKICAgICAgICAiMSIsCiAgICAgICAgIjIiLAogICAgICAgICIzIgogICAgICBdLAogICAgICAicHJvcGVydGllcyI6IHt9LAogICAgICAicmVmIjogIlU0NSIsCiAgICAgICJ2YWx1ZSI6ICJCQ0RfQ0VMTF80NSIKICAgIH0sCiAgICB7CiAgICAgICJwYWdlIjogIkJDRCIsCiAgICAgICJwaW5zIjogWwogICAgICAgICIxIiwKICAgICAgICAiMiIsCiAgICAgICAgIjMiCiAgICAgIF0sCiAgICAgICJwcm9wZXJ0aWVzIjoge30sCiAgICAgICJyZWYiOiAiVTQ2IiwKICAgICAgInZhbHVlIjogIkJDRF9DRUxMXzQ2IgogICAgfSwKICAgIHsKICAgICAgInBhZ2UiOiAiQkNEIiwKICAgICAgInBpbnMiOiBbCiAgICAgICAgIjEiLAogICAgICAgICIyIiwKICAgICAgICAiMyIKICAgICAgXSwKICAgICAgInByb3BlcnRpZXMiOiB7fSwKICAgICAgInJlZiI6ICJVNDciLAogICAgICAidmFsdWUiOiAiQkNEX0NFTExfNDciCiAgICB9LAogICAgewogICAgICAicGFnZSI6ICJCQ0QiLAogICAgICAicGlucyI6IFsKICAgICAgICAiMSIsCiAgICAgICAgIjIiLAogICAgICAgICIzIgogICAgICBdLAogICAgICAicHJvcGVydGllcyI6IHt9LAogICAgICAicmVmIjogIlU0OCIsCiAgICAgICJ2YWx1ZSI6ICJCQ0RfQ0VMTF80OCIKICAgIH0sCiAgICB7CiAgICAgICJwYWdlIjogIkJDRCIsCiAgICAgICJwaW5zIjogWwogICAgICAgICIxIiwKICAgICAgICAiMiIsCiAgICAgICAgIjMiCiAgICAgIF0sCiAgICAgICJwcm9wZXJ0aWVzIjoge30sCiAgICAgICJyZWYiOiAiVTQ5IiwKICAgICAgInZhbHVlIjogIkJDRF9DRUxMXzQ5IgogICAgfQogIF0sCiAgImZvcm1hdCI6ICJlbmdpd29ybGQtbmV1dHJhbC1zY2hlbWF0aWMtdjEiLAogICJuYW1lIjogIkJDRCIsCiAgInByb3BlcnRpZXMiOiB7fSwKICAic2NoZW1hdGljcyI6IFsKICAgIHsKICAgICAgImhpZXJfYmxvY2tzIjogW10sCiAgICAgICJuYW1lIjogIkJDRCIsCiAgICAgICJwYWdlcyI6IFsKICAgICAgICAiQkNEIgogICAgICBdCiAgICB9CiAgXQp9Cg==",
  "install_properties.csv": "UmVmZXJlbmNlLEluc3RhbGwNClUzMCxZDQpVMzEsWQ0KVTMyLE4NClUzMyxZDQpVMzQsTg0K"
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
        actual_rows = [[cell.strip() for cell in row] for row in csv.reader(io.StringIO(actual_text)) if any(cell.strip() for cell in row)]
        expected_rows = [[cell.strip() for cell in row] for row in csv.reader(io.StringIO(expected_text)) if any(cell.strip() for cell in row)]
        if not actual_rows or not expected_rows:
            return actual_rows == expected_rows
        if actual_rows[0] != expected_rows[0]:
            return False
        return sorted(actual_rows[1:]) == sorted(expected_rows[1:])
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



def _edif_equal(path: Path, expected: bytes) -> bool:
    try:
        def tokens(text: str):
            return re.findall(r'"[^"]*"|[()]|[^\s()]+', text)
        actual_text = path.read_text(encoding="utf-8-sig", errors="ignore")
        expected_text = expected.decode("utf-8", errors="ignore")
        return tokens(actual_text) == tokens(expected_text)
    except Exception:
        return False

def _zip_equal(path: Path, expected: bytes) -> bool:
    try:
        with zipfile.ZipFile(path) as actual, zipfile.ZipFile(io.BytesIO(expected)) as exp:
            if sorted(actual.namelist()) != sorted(exp.namelist()):
                return False
            for name in exp.namelist():
                actual_data = actual.read(name)
                expected_data = exp.read(name)
                suffix = Path(name).suffix.lower()
                if suffix in {".txt", ".log", ".gbr", ".gtl", ".gbl", ".gts", ".gbs", ".gto", ".gbo", ".drl", ".gm1", ".gml"}:
                    if _text(actual_data) != _text(expected_data):
                        return False
                elif actual_data != expected_data:
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
        if path.suffix.lower() in {".edif"}:
            return _edif_equal(path, expected)
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
