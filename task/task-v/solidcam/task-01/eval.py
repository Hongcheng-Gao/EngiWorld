from __future__ import annotations

import os
import re
from pathlib import Path
import sys

_TASK_V_ROOT = Path(__file__).resolve().parents[2]
if str(_TASK_V_ROOT) not in sys.path:
    sys.path.insert(0, str(_TASK_V_ROOT))
from _gui_bypass import check_no_gui_bypass


TARGET = Path(os.environ.get("EVAL_TARGET_DIR", r"C:\Users\User\Desktop"))
REQUIRED = "task-1.nc"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore").upper()


def nums(src: str, axis: str) -> list[float]:
    return [float(m.group(1)) for m in re.finditer(rf"\b{axis}([+-]?\d+(?:\.\d+)?)", src)]


def motion_block_count(src: str) -> int:
    active_motion = False
    count = 0
    for line in src.splitlines():
        if re.search(r"\bG0?(?:0|1|2|3)\b|\bG8[123]\b", line):
            active_motion = True
        if active_motion and re.search(r"\b[XYZABC][+-]?\d", line):
            count += 1
    return count


def check_nc(path: Path) -> bool:
    if not path.exists() or path.stat().st_size == 0:
        return False
    text = read_text(path)
    if "G21" not in text or "G90" not in text or "M30" not in text:
        return False
    if re.search(r"\bT0*\d+\b", text) is None:
        return False
    if "FACE" not in text:
        return False
    if not nums(text, "X") or not nums(text, "Y") or not nums(text, "Z"):
        return False
    if motion_block_count(text) < 4:
        return False
    return True


if __name__ == "__main__":
    try:
        if not check_no_gui_bypass(TARGET):
            ok = False
        else:
            ok = check_nc(TARGET / REQUIRED)
    except Exception:
        ok = False
    print("True" if ok else "False")
    raise SystemExit(0)
