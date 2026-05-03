import sys
from pathlib import Path

TARGET = Path(r"d:/research/project-engiworld/Engiworld/task-gt/task-c/fusion360/task-21/ground_truth")

REQUIRED = ['task-21.nc', 'task-21_setup.html']
CFG = {'tools': [1], 'spindles': [6000], 'feeds': [750], 'z': [10.0], 'ops': ['Face']}

import re

def read_text(path):
    return path.read_text(encoding="utf-8", errors="ignore")

def check_nc(path):
    text = read_text(path).upper()
    if "G21" not in text: print("missing G21"); return False
    if "G90" not in text: print("missing G90"); return False
    if "M30" not in text: print("missing M30"); return False
    lower = text.lower()
    for tool in CFG.get("tools", []):
        if f"T{tool}" not in text: print(f"missing T{tool}"); return False
    for spindle in CFG.get("spindles", []):
        if f"S{int(spindle)}" not in text: print(f"missing S{spindle}"); return False
    for feed in CFG.get("feeds", []):
        if f"F{int(feed)}" not in text: print(f"missing F{feed}"); return False
    for op in CFG.get("ops", []):
        if str(op).lower() not in lower: print(f"missing op {op}"); return False
    for z in CFG.get("z", []):
        if f"Z{float(z):.3f}" not in text: print(f"missing Z{z}"); return False
    return True

def check_html(path):
    text = read_text(path).lower()
    for w in ["setup", "wcs", "tool", "operation"]:
        if w not in text:
            print(f"html missing {w}"); return False
    if path.stat().st_size <= 1000:
        print(f"html too small {path.stat().st_size}"); return False
    return True

for rel in REQUIRED:
    path = TARGET / rel
    print(f"--- {rel} exists={path.exists()} size={path.stat().st_size if path.exists() else '?'}")
    ext = path.suffix.lower()
    if ext == ".nc":
        print("nc check:", check_nc(path))
    elif ext == ".html":
        print("html check:", check_html(path))
