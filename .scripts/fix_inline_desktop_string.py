"""Fix broken \\desktop\\ string in inlined GUI bypass blocks."""
from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
APPS = (
    "ansys", "autocad", "freecad", "freecad-path", "librecad",
    "openscad", "solidcam", "solidworks", "solvespace",
)

BAD = '            if ("/desktop/" in line or "\\desktop\\" in line) and any('
GOOD = '            if ("/desktop/" in line or "\\\\desktop\\\\" in line) and any('

IMPORT_RE = re.compile(
    r"\nimport sys\n\n_TASK_V_ROOT = Path\(__file__\)\.resolve\(\)\.parents\[2\]\n"
    r"if str\(_TASK_V_ROOT\) not in sys\.path:\n"
    r"    sys\.path\.insert\(0, str\(_TASK_V_ROOT\)\)\n"
    r"from _gui_bypass import check_no_gui_bypass\n\n",
    re.MULTILINE,
)

n = 0
for app in APPS:
    for path in (REPO / "task" / "task-v" / app).glob("task-*/eval.py"):
        text = path.read_text(encoding="utf-8")
        orig = text
        text = text.replace(BAD, GOOD)
        text = IMPORT_RE.sub("\n", text)
        if text != orig:
            path.write_text(text, encoding="utf-8")
            n += 1
print(f"fixed {n} files")
