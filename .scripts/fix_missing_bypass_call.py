"""Ensure evaluate()/main() calls check_no_gui_bypass when inline block exists."""
from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
APPS = (
    "ansys", "autocad", "freecad", "freecad-path", "librecad",
    "openscad", "solidcam", "solidworks", "solvespace",
)

IMPORT_RE = re.compile(
    r"\nimport sys\n\n_TASK_V_ROOT = Path\(__file__\)\.resolve\(\)\.parents\[2\]\n"
    r"if str\(_TASK_V_ROOT\) not in sys\.path:\n"
    r"    sys\.path\.insert\(0, str\(_TASK_V_ROOT\)\)\n"
    r"from _gui_bypass import check_no_gui_bypass\n\n",
    re.MULTILINE,
)


def detect_root_var(text: str) -> str | None:
    for name in ("DESKTOP", "OUTPUT_ROOT", "TARGET"):
        if re.search(rf"^{name}\s*=", text, re.M):
            return name
    return None


def add_calls(text: str, root: str) -> str:
    bypass = f"    if not check_no_gui_bypass({root}):\n        return False\n"
    if "check_no_gui_bypass(" in text.split("def check_no_gui_bypass")[0]:
        pass  # already has call before helper def? unlikely
    # If evaluate exists without call right after def line
    for pat in (
        r"(def evaluate\([^)]*\)\s*(?:->\s*bool)?\s*:\n)(?!\s+if not check_no_gui_bypass)",
        r"(def main\(\)\s*->\s*bool:\n)(?!\s+if not check_no_gui_bypass)",
    ):
        text = re.sub(pat, r"\1" + bypass, text, count=1)
    # solidcam __main__
    pat = r'(if __name__ == ["\']__main__["\']:\n\s+try:\n)(?!\s+if not check_no_gui_bypass)'
    inner = (
        f"        if not check_no_gui_bypass({root}):\n"
        "            ok = False\n"
        "        else:\n"
        "            "
    )
    if re.search(pat, text) and "check_no_gui_bypass" not in re.search(pat, text).group(0) if False else text:
        m = re.search(pat, text)
        if m and "if not check_no_gui_bypass" not in text[m.end() : m.end() + 80]:
            text = text[: m.end()] + inner + text[m.end() :].lstrip()
    return text


def main() -> None:
    n = 0
    for app in APPS:
        for path in (REPO / "task" / "task-v" / app).glob("task-*/eval.py"):
            text = path.read_text(encoding="utf-8")
            text = IMPORT_RE.sub("\n", text)
            if "GUI_BYPASS_FORBIDDEN_EXTENSIONS" not in text:
                continue
            root = detect_root_var(text)
            if not root:
                continue
            orig = text
            text = add_calls(text, root)
            if text != orig:
                path.write_text(text, encoding="utf-8")
                n += 1
    print(f"added calls in {n} files")


if __name__ == "__main__":
    main()
