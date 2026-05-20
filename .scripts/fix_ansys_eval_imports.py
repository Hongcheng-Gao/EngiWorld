"""Move _gui_bypass imports to module top in task-v/ansys eval.py files."""
from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ANSYS = REPO / "task" / "task-v" / "ansys"

BLOCK = """import sys

_TASK_V_ROOT = Path(__file__).resolve().parents[2]
if str(_TASK_V_ROOT) not in sys.path:
    sys.path.insert(0, str(_TASK_V_ROOT))
from _gui_bypass import check_no_gui_bypass

"""

BLOCK_RE = re.compile(
    r"\nimport sys\n\n_TASK_V_ROOT = Path\(__file__\)\.resolve\(\)\.parents\[2\]\n"
    r"if str\(_TASK_V_ROOT\) not in sys\.path:\n"
    r"    sys\.path\.insert\(0, str\(_TASK_V_ROOT\)\)\n"
    r"from _gui_bypass import check_no_gui_bypass\n\n+",
    re.MULTILINE,
)


def fix(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    orig = text
    text = text.replace(
        "check_no_gui_bypass(Path(r\"C:\\Users\\user\\Desktop\"))",
        "check_no_gui_bypass(DESKTOP)",
    )
    count = len(BLOCK_RE.findall(text))
    if count > 1:
        # drop all inline blocks, keep one at top
        text = BLOCK_RE.sub("\n", text)
        count = 0
    elif count == 1 and "from _gui_bypass import" in text.split("def ", 1)[0]:
        count = 0  # already only at top
    else:
        text = BLOCK_RE.sub("\n", text)

    if "from _gui_bypass import check_no_gui_bypass" not in text:
        marker = "import subprocess\n\n"
        if marker in text:
            text = text.replace(marker, marker + BLOCK, 1)
        else:
            text = text.replace("from pathlib import Path\n\n", "from pathlib import Path\n\n" + BLOCK, 1)

    if text != orig:
        path.write_text(text, encoding="utf-8")
        return True
    return False


def main() -> None:
    n = sum(fix(p) for p in ANSYS.glob("task-*/eval.py"))
    print(f"updated {n} files")


if __name__ == "__main__":
    main()
